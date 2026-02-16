
from __future__ import annotations
from typing import List, Tuple
import math

from evo_sim.sim.config import WORLD, TRAITS, BEHAV

Vec = Tuple[float, float]

def _nearest_edge_target(x: float, y: float) -> Tuple[float, float, float]:
    """
    Return (tx, ty, dist) where (tx,ty) is the closest point on any world edge to (x,y),
    and dist is the Euclidean distance to that point.
    """
    W, H = WORLD.width, WORLD.height
    candidates = [
        (0.0, y),       # left
        (W,   y),       # right
        (x,   0.0),     # bottom
        (x,   H),       # top
    ]
    tx, ty = min(candidates, key=lambda p: (p[0]-x)**2 + (p[1]-y)**2)
    dist = math.hypot(tx - x, ty - y)
    return tx, ty, dist

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
    # Always go home after 2 foods
    if me.eaten >= 2:
        me.going_home = True

    # After 1 food: if time is tight to reach the nearest edge, go home
    if me.eaten == 1:
        tx, ty, dist = _nearest_edge_target(me.x, me.y)
        time_need = dist / max(eff, 1e-6)     # seconds needed to reach edge
        time_have = steps_left * dt           # seconds left in day
        if time_need >= 0.92 * time_have:     # conservative safety margin
            me.going_home = True

    # If we're going home, steer to the nearest edge point
    if me.going_home:
        tx, ty, _ = _nearest_edge_target(me.x, me.y)
        to_edge = (tx - me.x, ty - me.y)
        return _mul(_unit(to_edge), eff)
    f = world.nearest_food_within(me.x, me.y, r_food)
    if f is not None:
        to_food = (f.x - me.x, f.y - me.y)
        return _mul(_unit(to_food), eff)
    drift = (BEHAV.wander_turn_rate * dt)
    me.heading += drift * (0.5 - (hash((me.id, me.x, me.y)) & 1))
    vmag = BEHAV.wander_speed_fraction * eff
    return (math.cos(me.heading) * vmag, math.sin(me.heading) * vmag)
