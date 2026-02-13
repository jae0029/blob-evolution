# evo_sim/sim/genetics.py
from __future__ import annotations
from typing import List, Tuple

from .models import Creature, Species
from .config import REPRO, TRAITS, SPECIATION
from .rng import RNG

def _mutate_value(val: float, min_v: float, max_v: float) -> float:
    if RNG.uniform(0.0, 1.0) <= REPRO.mutation_rate:
        sd = abs(val) * REPRO.mutation_sd_frac
        if sd <= 1e-6:
            sd = REPRO.mutation_sd_frac
        val = RNG.gauss(val, sd)
    return min(max(val, min_v), max_v)

def _random_color():
    r = int(RNG.uniform(70, 240))
    g = int(RNG.uniform(70, 240))
    b = int(RNG.uniform(70, 240))
    return (r, g, b)

def _maybe_speciate(parent: Creature, child: Creature, next_species_id: int) -> Tuple[Creature, int, bool, Species | None]:
    def rel(a, b): 
        return abs(a - b) / max(1e-6, abs(b))
    drift_speed = rel(child.speed, parent.speed)
    drift_size  = rel(child.size,  parent.size)
    drift_sense = rel(child.sense, parent.sense)
    if max(drift_speed, drift_size, drift_sense) >= SPECIATION.threshold_frac:
        new_sp = Species(
            id=next_species_id,
            name=f"Species {next_species_id}",
            color=_random_color(),
            aggression=RNG.uniform(0.0, 1.0),
            bravery=RNG.uniform(0.0, 1.0),
            metabolism=RNG.uniform(SPECIATION.min_metabolism, SPECIATION.max_metabolism),
            diet=RNG.choice(["herbivore", "carnivore", "omnivore"]),
        )
        child.species = new_sp
        return child, next_species_id + 1, True, new_sp
    else:
        child.species = parent.species
        return child, next_species_id, False, None

def reproduce_N_children(
    parent: Creature,
    n_offspring: int,
    next_creature_id: int,
    next_species_id: int,
    mutate_speed: bool = True,
    mutate_size: bool = True,
    mutate_sense: bool = True,
) -> Tuple[List[Creature], int, int, List[Tuple[Species, Species]]]:
    """
    Create n_offspring children from parent (species-aware + speciation reporting).
    Returns (children, next_creature_id, next_species_id, speciation_events)
    """
    children: List[Creature] = []
    speciation_events: List[Tuple[Species, Species]] = []

    for _ in range(n_offspring):
        spd = parent.speed
        sze = parent.size
        sen = parent.sense

        if mutate_speed: spd = _mutate_value(spd, TRAITS.min_speed, TRAITS.max_speed)
        if mutate_size:  sze = _mutate_value(sze, TRAITS.min_size,  TRAITS.max_size)
        if mutate_sense: sen = _mutate_value(sen, TRAITS.min_sense, TRAITS.max_sense)

        child = Creature(
            id=next_creature_id,
            species=parent.species,
            speed=spd, size=sze, sense=sen,
            x=0.0, y=0.0, home=(0.0,0.0), energy=0.0
        )
        next_creature_id += 1

        child, next_species_id, new_flag, new_sp = _maybe_speciate(parent, child, next_species_id)
        if new_flag and new_sp is not None:
            speciation_events.append((parent.species, new_sp))

        children.append(child)

    return children, next_creature_id, next_species_id, speciation_events