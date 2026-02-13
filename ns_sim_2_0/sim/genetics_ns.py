from __future__ import annotations
from dataclasses import dataclass
from evo_sim.sim.config import TRAITS
from evo_sim.sim.rng import RNG
from evo_sim.sim.models import Creature

@dataclass(frozen=True)
class NSReproConfig:
    mutation_rate: float = 0.30   # probability per trait
    mutation_sd_frac: float = 0.20  # Gaussian sd as a fraction of current value
    min_sd: float = 0.05            # absolute minimum sd for tiny values

NS_REPRO = NSReproConfig()

def _mutate_value(val: float, lo: float, hi: float, enabled: bool) -> float:
    if not enabled:
        return max(lo, min(hi, val))
    if RNG.uniform(0.0, 1.0) <= NS_REPRO.mutation_rate:
        sd = max(NS_REPRO.mutation_sd_frac * abs(val), NS_REPRO.min_sd)
        val = RNG.gauss(val, sd)
    return max(lo, min(hi, val))

def make_child_from(parent: Creature, next_id: int,
                    mutate_speed: bool = True,
                    mutate_size: bool = True,
                    mutate_sense: bool = True,
                    species=None) -> Creature:
    spd = _mutate_value(parent.speed, TRAITS.min_speed, TRAITS.max_speed, mutate_speed)
    sze = _mutate_value(parent.size,  TRAITS.min_size,  TRAITS.max_size,  mutate_size)
    sen = _mutate_value(parent.sense, TRAITS.min_sense, TRAITS.max_sense, mutate_sense)
    return Creature(
        id=next_id,
        species=species or parent.species,
        speed=spd, size=sze, sense=sen,
        x=0.0, y=0.0, home=(0.0,0.0), energy=0.0
    )
