
from __future__ import annotations
from typing import List, Tuple
import math

from evo_sim.sim.config import WORLD, TRAITS, BEHAV

Vec = Tuple[float, float]
EAT_RATIO = 1.2

def _unit(v: Vec) -> Vec:
    x,y = v
    n = math.hypot(x,y)
    return (0.0,0.0) if n==0 else (x/n, y/n)

def _mul(v: Vec, k: float) -> Vec:
    return (v[0]*k, v[1]*k)

def bite_radius(size: float) -> float:
    return WORLD.bite_radius_scale * size


def step_behavior(world, me, others: List, dt: float, steps_left: int) -> Vec:
    if not me.alive:
        return (0.0, 0.0)
    eff = me.effective_speed()
    r_food = me.sense * TRAITS.sense_food_scale
    r_pred = me.sense * TRAITS.sense_pred_scale
    predator = None
    best_d2 = r_pred * r_pred
    for o in others:
        if not o.alive or o.id == me.id:
            continue
        if o.size >= EAT_RATIO * me.size:
            d2 = (o.x - me.x)**2 + (o.y - me.y)**2
            if d2 <= best_d2:
                predator = o; best_d2 = d2
    if predator is not None:
        away = (me.x - predator.x, me.y - predator.y)
        return _mul(_unit(away), eff)
    if me.going_home:
        to_home = (me.home[0] - me.x, me.home[1] - me.y)
        return _mul(_unit(to_home), eff)
    f = world.nearest_food_within(me.x, me.y, r_food)
    if f is not None:
        to_food = (f.x - me.x, f.y - me.y)
        return _mul(_unit(to_food), eff)
    drift = (BEHAV.wander_turn_rate * dt)
    me.heading += drift * (0.5 - (hash((me.id, me.x, me.y)) & 1))
    vmag = BEHAV.wander_speed_fraction * eff
    return (math.cos(me.heading) * vmag, math.sin(me.heading) * vmag)
