from __future__ import annotations
from typing import List, Tuple
import math

from .models import Creature
from .world import World
from .behaviors import step_behavior, bite_radius, EAT_RATIO
from .config import WORLD, ENERGY

# Motion/energy

def _clamp_speed(vx: float, vy: float, vmax: float) -> Tuple[float,float]:
    spd = math.hypot(vx, vy)
    if spd <= vmax or spd <= 1e-12: return (vx, vy)
    f = vmax / spd
    return (vx*f, vy*f)

def _apply_motion(world: World, me: Creature, vx: float, vy: float, dt: float) -> None:
    me.x, me.y = world.clamp_inside(me.x + vx*dt, me.y + vy*dt)

def _apply_energy(me: Creature, moving_speed: float, dt: float) -> None:
    base  = ENERGY.C_size * (me.size ** 3)
    sense = ENERGY.C_sense * me.sense
    move  = ENERGY.C_move * (me.size ** 3) * (moving_speed ** 2)
    me.energy -= (base + sense + move) * dt
    if me.energy <= 0: me.alive = False

# Interactions

def _consume_food_if_reached(world: World, me: Creature) -> None:
    if not me.alive: return
    r = bite_radius(me)
    f = world.nearest_food_within(me.x, me.y, r)
    if f is not None:
        fx, fy, fid = f
        if math.hypot(fx - me.x, fy - me.y) <= r:
            me.eaten += 1
            world.remove_food(fid)

def _consume_prey_if_reached(me: Creature, others: List[Creature]) -> None:
    if not me.alive: return
    r = bite_radius(me)
    target = None; best_d2 = r*r
    for o in others:
        if (not o.alive) or (o is me): continue
        if me.size >= EAT_RATIO * o.size:
            d2 = (o.x - me.x)**2 + (o.y - me.y)**2
            if d2 <= best_d2:
                target = o; best_d2 = d2
    if target is not None:
        if math.hypot(target.x - me.x, target.y - me.y) <= r:
            target.alive = False
            me.eaten += 1

# Day loop

def simulate_day(world: World, population: List[Creature]) -> None:
    world.spawn_food_uniform(int(WORLD.n_food))
    world.spawn_creatures_at_edges(population)
    dt = WORLD.dt
    for step in range(int(WORLD.day_steps)):
        steps_left = int(WORLD.day_steps) - step
        vlist = []
        for me in population:
            if not me.alive: vlist.append((me.id,0.0,0.0)); continue
            vx, vy = step_behavior(world, me, population, dt, steps_left)
            vx, vy = _clamp_speed(vx, vy, me.effective_speed())
            vlist.append((me.id, vx, vy))
        id_map = {c.id: c for c in population}
        for cid, vx, vy in vlist:
            me = id_map[cid]
            if not me.alive: continue
            spd = math.hypot(vx, vy)
            _apply_energy(me, spd, dt)
            if not me.alive: continue
            _apply_motion(world, me, vx, vy, dt)
            me.dist_traveled_today += spd * dt
        for me in population:
            if not me.alive: continue
            _consume_prey_if_reached(me, population)
            _consume_food_if_reached(world, me)

# Selection

def end_of_day_selection(population: List[Creature]):
    survivors: List[Creature] = []
    repro_parents: List[Creature] = []
    for c in population:
        if not c.alive: continue
        if c.eaten == 0: c.alive = False; continue
        if c.eaten >= 1 and not c.at_home(WORLD.home_margin): c.alive = False; continue
        survivors.append(c)
        if c.eaten >= 2: repro_parents.append(c)
    return survivors, repro_parents
