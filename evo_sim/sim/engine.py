# evo_sim/sim/engine.py
from __future__ import annotations
from typing import List, Tuple, Optional
import math

from .models import Creature
from .world import World
from .behaviors import step_behavior, bite_radius, can_eat
from .config import WORLD, ENERGY, RISK
from .rng import RNG

def _clamp_speed(vx: float, vy: float, vmax: float) -> Tuple[float, float]:
    spd = math.hypot(vx, vy)
    if spd <= vmax or spd <= 1e-12:
        return (vx, vy)
    f = vmax / spd
    return (vx * f, vy * f)

def _apply_motion(world: World, me: Creature, vx: float, vy: float, dt: float) -> None:
    me.x, me.y = world.clamp_inside(me.x + vx * dt, me.y + vy * dt)

def _apply_energy(me: Creature, moving_speed: float, dt: float) -> None:
    base = ENERGY.C_size * (me.size ** 3) + ENERGY.C_sense * me.sense
    move = ENERGY.C_move * (me.size ** 3) * (moving_speed ** 2)
    leak = RISK.injury_energy_leak_per_time if me.injury_days_left > 0 else 0.0
    mult = me.species.metabolism
    me.energy -= ((base + move) * mult + leak) * dt
    if me.energy <= 0:
        me.alive = False

def _kill_probability(pred: Creature, prey: Creature) -> float:
    size_ratio = pred.size / max(1e-6, prey.size)
    speed_adv = pred.speed - prey.speed
    p = (RISK.base_p_kill
         + RISK.size_weight * (size_ratio - 1.0)
         + RISK.speed_weight * (speed_adv / 6.0))
    return max(RISK.min_p_kill, min(RISK.max_p_kill, p))

def _resolve_attack(pred: Creature, prey: Creature) -> None:
    if not pred.alive or not prey.alive:
        return
    if pred.prey_kills_today >= 1:
        return
    if not can_eat(pred, prey):
        return
    if prey.species.diet.lower() == "carnivore" and pred.hungry_streak < 1:
        return

    p_kill = _kill_probability(pred, prey)
    if RNG.uniform(0.0, 1.0) <= p_kill:
        prey.alive = False
        pred.eaten += 1
        pred.prey_kills_today += 1
        return

    # fail: energy loss
    pred.energy -= RISK.energy_loss_on_fail
    if pred.energy <= 0:
        pred.alive = False
        return

    # injury on fail
    if RNG.uniform(0.0, 1.0) <= RISK.injury_on_fail_prob:
        days = int(RNG.uniform(RISK.injury_days_min, RISK.injury_days_max + 1))
        mult = RNG.uniform(RISK.injury_speed_mult_lo, RISK.injury_speed_mult_hi)
        pred.injury_days_left = max(pred.injury_days_left, days)
        pred.injury_speed_mult = min(pred.injury_speed_mult, mult) if pred.injury_speed_mult < 1.0 else mult

    # rare fatal counter if prey significantly larger
    if prey.size >= 1.2 * pred.size:
        if RNG.uniform(0.0, 1.0) <= RISK.fatal_counterattack_prob:
            pred.alive = False

def _consume_food_if_reached(world: World, me: Creature) -> None:
    if not me.alive:
        return

    # --- NEW: carnivores never eat plant food ---
    if me.species.diet.lower() == "carnivore":
        return

    r = bite_radius(me)
    f = world.nearest_food_within(me.x, me.y, r)
    if f is not None and math.hypot(f.x - me.x, f.y - me.y) <= r:
        me.eaten += 1
        world.remove_food(f.id)

def _consume_prey_if_reached(me: Creature, others: List[Creature]) -> None:
    if not me.alive:
        return
    r = bite_radius(me)
    target: Optional[Creature] = None
    best_d2 = r * r
    for o in others:
        if (not o.alive) or (o.id == me.id):
            continue
        if not can_eat(me, o):
            continue
        d2 = (o.x - me.x) ** 2 + (o.y - me.y) ** 2
        if d2 <= best_d2:
            target = o
            best_d2 = d2
    if target is not None:
        if math.hypot(target.x - me.x, target.y - me.y) <= r:
            _resolve_attack(me, target)

def simulate_day(world: World, population: List[Creature]) -> None:
    world.spawn_food_uniform(int(WORLD.n_food))
    world.spawn_creatures_at_edges(population)
    dt = WORLD.dt

    for step in range(int(WORLD.day_steps)):
        steps_left = int(WORLD.day_steps) - step
        velocities: List[Tuple[int, float, float]] = []
        for me in population:
            if not me.alive:
                velocities.append((me.id, 0.0, 0.0))
                continue
            vx, vy = step_behavior(world, me, population, dt, steps_left)
            vmax = me.effective_speed()
            vx, vy = _clamp_speed(vx, vy, vmax)
            velocities.append((me.id, vx, vy))

        id_map = {c.id: c for c in population}
        for cid, vx, vy in velocities:
            me = id_map[cid]
            if not me.alive:
                continue
            move_speed = math.hypot(vx, vy)
            _apply_energy(me, move_speed, dt)
            if not me.alive:
                continue
            _apply_motion(world, me, vx, vy, dt)

        for me in population:
            if not me.alive:
                continue
            _consume_prey_if_reached(me, population)   # predation first
            _consume_food_if_reached(world, me)        # then food

def end_of_day_selection(population: List[Creature]) -> Tuple[List[Creature], List[Tuple[Creature, int]]]:
    """
    Returns (survivors, repro_orders) where each repro order is (parent, num_offspring).

    Starvation memory:
      eaten == 0 -> hungry_streak += 1 else reset
      if hungry_streak >= 2 -> die

    Home gate:
      if eaten >= 1, must be home to survive/reproduce
      if eaten == 0 and hungry_streak < 2 -> may persist (no repro)

    Reproduction:
      carnivore: if prey_kills_today >= 1 and home -> 1 offspring
      omnivore : if (prey_kills_today >= 1 or eaten >= 2) and home -> 1 offspring
      herbivore: if eaten >= 3 and home -> 2 offspring
                 elif eaten >= 2 and home -> 1 offspring
    """
    survivors: List[Creature] = []
    repro_orders: List[Tuple[Creature, int]] = []

    for c in population:
        if not c.alive:
            continue

        # starvation memory
        if c.eaten == 0:
            c.hungry_streak += 1
        else:
            c.hungry_streak = 0

        if c.hungry_streak >= 2:
            c.alive = False
            continue

        diet = c.species.diet.lower()

        if c.eaten >= 1:
            if not c.at_home(WORLD.home_margin):
                c.alive = False
                continue
            survivors.append(c)

            if diet == "carnivore":
                if c.prey_kills_today >= 1:
                    repro_orders.append((c, 1))
            elif diet == "omnivore":
                if (c.prey_kills_today >= 1) or (c.eaten >= 2):
                    repro_orders.append((c, 1))
            else:  # herbivore
                if c.eaten >= 3:
                    repro_orders.append((c, 2))
                elif c.eaten >= 2:
                    repro_orders.append((c, 1))
        else:
            # ate 0, but streak < 2: persist, no reproduction
            survivors.append(c)

    return survivors, repro_orders