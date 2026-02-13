# evo_sim/main.py
from __future__ import annotations
import argparse
from typing import List

from .sim.config import SIM, WORLD
from .sim.rng import RNG
from .sim.models import Creature, Species
from .sim.world import World
from .sim.engine import simulate_day, end_of_day_selection
from .sim.genetics import reproduce_N_children
from .sim.metrics import summarize_day, append_csv
from .ui.app import run_ui  # UI entry (unchanged)

def _seed_species():
    return [
        Species(id=1, name="Azure",   color=(70,140,240), aggression=0.35, bravery=0.55, metabolism=1.00, diet="omnivore"),
        Species(id=2, name="Amber",   color=(240,160,60), aggression=0.10, bravery=0.80, metabolism=0.95, diet="herbivore"),
        Species(id=3, name="Viridian",color=(60,200,120), aggression=0.65, bravery=0.40, metabolism=1.05, diet="carnivore"),
    ]

def init_population(n: int, start_id: int = 1, seed: int | None = None) -> List[Creature]:
    if seed is not None:
        RNG.seed(seed)
    pops: List[Creature] = []
    species = _seed_species()
    for i in range(n):
        sp = species[i % len(species)]
        pops.append(Creature(
            id=start_id + i,
            species=sp,
            speed=RNG.uniform(0.75, 1.25),
            size=RNG.uniform(0.75, 1.25),
            sense=RNG.uniform(8.0, 15.0),
            x=0.0, y=0.0, home=(0.0,0.0), energy=0.0,
        ))
    return pops

def run():
    parser = argparse.ArgumentParser(description="Evolution simulation (Rules of Survival) with Species and Risky Predation")
    parser.add_argument("--days", type=int, default=SIM.days)
    parser.add_argument("--seed", type=int, default=SIM.seed)
    parser.add_argument("--pop", type=int, default=SIM.initial_population)
    parser.add_argument("--csv", type=str, default=SIM.track_csv)
    parser.add_argument("--plot", action="store_true", default=SIM.enable_plot)
    parser.add_argument("--ui", action="store_true", help="launch real-time UI")
    args = parser.parse_args()

    if args.ui:
        run_ui()
        return

    RNG.seed(args.seed)
    world = World()

    population = init_population(args.pop, seed=args.seed)
    next_id = max(c.id for c in population) + 1
    next_species_id = max(c.species.id for c in population) + 1

    for day in range(1, args.days + 1):
        simulate_day(world, population)
        survivors, repro_orders = end_of_day_selection(population)

        summary = summarize_day(day, population)
        print(
            f"Day {day:3d} | N={summary['n']:3.0f} "
            f"alive={summary['alive']:3.0f} ate0={summary['ate0']:3.0f} "
            f"ate1={summary['ate1']:3.0f} ate2+={summary['ate2p']:3.0f} "
            f"avg_speed={summary['avg_speed']:.2f} avg_size={summary['avg_size']:.2f} avg_sense={summary['avg_sense']:.2f}"
        )
        if args.csv:
            append_csv(args.csv, summary)

        new_population: List[Creature] = []
        for s in survivors:
            new_population.append(Creature(
                id=s.id, species=s.species,
                speed=s.speed, size=s.size, sense=s.sense,
                x=0.0, y=0.0, home=(0.0,0.0), energy=0.0,
                hungry_streak=s.hungry_streak
            ))

        for parent, num_kids in repro_orders:
            kids, next_id, next_species_id, _events = reproduce_N_children(
                parent=parent, n_offspring=num_kids,
                next_creature_id=next_id, next_species_id=next_species_id,
                mutate_speed=True, mutate_size=True, mutate_sense=True
            )
            new_population.extend(kids)

        if len(new_population) == 0:
            new_population = init_population(args.pop, start_id=next_id, seed=args.seed)
            next_id = max(c.id for c in new_population) + 1
            next_species_id = max(c.species.id for c in new_population) + 1

        population = new_population

        if args.plot:
            # optional snapshot (you can re-enable visualize if desired)
            pass

if __name__ == "__main__":
    run()