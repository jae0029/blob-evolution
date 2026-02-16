from __future__ import annotations
from typing import List, Tuple
from .models import Creature
from .config import TRAITS, REPRO
from .rng import RNG

def _mutate(val: float, lo: float, hi: float) -> float:
    if RNG.uniform(0.0,1.0) <= REPRO.mutation_rate:
        sd = max(REPRO.mutation_sd_frac * abs(val), REPRO.mutation_sd_frac)
        val = RNG.gauss(val, sd)
    return max(lo, min(hi, val))

def reproduce_and_mutate(parent: Creature, next_id: int):
    child = Creature(
        id=next_id,
        speed=_mutate(parent.speed, TRAITS.min_speed, TRAITS.max_speed),
        size=_mutate(parent.size, TRAITS.min_size, TRAITS.max_size),
        sense=_mutate(parent.sense, TRAITS.min_sense, TRAITS.max_sense),
        x=0.0, y=0.0, home=(0.0,0.0), energy=0.0
    )
    return [child], next_id + 1
