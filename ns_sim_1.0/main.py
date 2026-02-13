from __future__ import annotations
import argparse, os, csv
from typing import List

from .rng import RNG
from .models import Creature
from .world import World
from .engine import simulate_day, end_of_day_selection
from .genetics import reproduce_and_mutate
from .metrics import summarize_day


def _append_csv(path: str, row: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_header = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header: w.writeheader()
        w.writerow(row)


def init_population(n: int, seed: int | None = None, start_id: int = 1) -> List[Creature]:
    if seed is not None: RNG.seed(seed)
    pop: List[Creature] = []
    import random
    for i in range(n):
        pop.append(Creature(
            id=start_id + i,
            speed=random.uniform(1.2, 3.2),
            size=random.uniform(0.8, 1.6),
            sense=random.uniform(15.0, 40.0),
            x=0.0, y=0.0, home=(0.0,0.0), energy=0.0,
        ))
    return pop


def run():
    ap = argparse.ArgumentParser(description='Natural Selection sim (no speciation, classic rules)')
    ap.add_argument('--days', type=int, default=40)
    ap.add_argument('--pop', type=int, default=60)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--csv', type=str, default='runs_ns/summary.csv')
    args = ap.parse_args()

    RNG.seed(args.seed)
    world = World()
    population = init_population(args.pop, seed=args.seed)
    next_id = max(c.id for c in population) + 1

    for day in range(1, args.days + 1):
        simulate_day(world, population)
        survivors, repro_parents = end_of_day_selection(population)

        summary = summarize_day(day, population)
        print(f"Day {day:3d} | N={summary['n']:3.0f} alive={summary['alive']:3.0f} "
              f"ate0={summary['ate0']:3.0f} ate1={summary['ate1']:3.0f} ate2+={summary['ate2p']:3.0f} "
              f"avg_speed={summary['avg_speed']:.2f} avg_size={summary['avg_size']:.2f} avg_sense={summary['avg_sense']:.2f}")
        if args.csv: _append_csv(args.csv, summary)

        new_pop: List[Creature] = []
        for s in survivors:
            new_pop.append(Creature(id=s.id, speed=s.speed, size=s.size, sense=s.sense,
                                    x=0.0, y=0.0, home=(0.0,0.0), energy=0.0))
        for p in repro_parents:
            kids, next_id = reproduce_and_mutate(p, next_id)
            new_pop.extend(kids)

        if len(new_pop)==0:
            new_pop = init_population(args.pop, seed=args.seed, start_id=next_id)
            next_id = max(c.id for c in new_pop) + 1
        population = new_pop

if __name__ == '__main__':
    run()
