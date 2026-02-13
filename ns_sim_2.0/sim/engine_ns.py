
from __future__ import annotations
from typing import List, Tuple
import math

from evo_sim.sim.config import WORLD, ENERGY
from .behaviors_ns import step_behavior, bite_radius, EAT_RATIO


def _clamp_speed(vx: float, vy: float, vmax: float) -> Tuple[float, float]:
    spd = math.hypot(vx, vy)
    if spd <= vmax or spd <= 1e-12:
        return (vx, vy)
    f = vmax / spd
    return (vx * f, vy * f)

def _apply_motion(world, me, vx: float, vy: float, dt: float) -> None:
    me.x, me.y = world.clamp_inside(me.x + vx*dt, me.y + vy*dt)

def _apply_energy(me, moving_speed: float, dt: float) -> None:
    base  = ENERGY.C_size * (me.size ** 3)
    sense = ENERGY.C_sense * me.sense
    move  = ENERGY.C_move * (me.size ** 3) * (moving_speed ** 2)
    me.energy -= (base + sense + move) * dt
    if me.energy <= 0:
        me.alive = False

def _consume_food_if_reached(world, me) -> None:
    if not me.alive:
        return
    r = bite_radius(me.size)
    f = world.nearest_food_within(me.x, me.y, r)
    if f is not None and ((f.x - me.x)**2 + (f.y - me.y)**2) <= r*r:
        me.eaten += 1
        world.remove_food(f.id)

def _consume_prey_if_reached(me, others: List) -> None:
    if not me.alive:
        return
    r = bite_radius(me.size)
    target = None
    best_d2 = r*r
    for o in others:
        if (not o.alive) or (o.id == me.id):
            continue
        if me.size >= EAT_RATIO * o.size:
            d2 = (o.x - me.x)**2 + (o.y - me.y)**2
            if d2 <= best_d2:
                target = o; best_d2 = d2
    if target is not None:
        if ((target.x - me.x)**2 + (target.y - me.y)**2) <= best_d2:
            target.alive = False
            me.eaten += 1

def simulate_day(world, population: List) -> None:
    world.spawn_food_uniform(int(WORLD.n_food))
    world.spawn_creatures_at_edges(population)
    dt = WORLD.dt
    for step in range(int(WORLD.day_steps)):
        steps_left = int(WORLD.day_steps) - step
        vlist = []
        for me in population:
            if not me.alive:
                vlist.append((me.id, 0.0, 0.0)); continue
            vx, vy = step_behavior(world, me, population, dt, steps_left)
            vx, vy = _clamp_speed(vx, vy, me.effective_speed())
            vlist.append((me.id, vx, vy))
        id_map = {c.id: c for c in population}
        for cid, vx, vy in vlist:
            me = id_map[cid]
            if not me.alive:
                continue
            spd = math.hypot(vx, vy)
            _apply_energy(me, spd, dt)
            if not me.alive:
                continue
            _apply_motion(world, me, vx, vy, dt)
        for me in population:
            if not me.alive:
                continue
            _consume_prey_if_reached(me, population)
            _consume_food_if_reached(world, me)

def end_of_day_selection(population: List) -> Tuple[List, List]:
    survivors: List = []
    repro: List = []
    for c in population:
        if not c.alive:
            continue
        if c.eaten == 0:
            c.alive = False
            continue
        if c.eaten >= 1 and (not c.at_home(WORLD.home_margin)):
            c.alive = False
            continue
        survivors.append(c)
        if c.eaten >= 2:
            repro.append(c)
    return survivors, repro
