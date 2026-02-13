from __future__ import annotations
import argparse, os, csv
from typing import List

from evo_sim.sim.config import SIM
from evo_sim.sim.models import Creature, Species
from evo_sim.sim.world import World

from ns_sim_2_0.ui.app import run_ui
from ns_sim_2_0.sim.engine_ns import simulate_day, end_of_day_selection
from ns_sim_2_0.sim.genetics_ns import make_child_from


def _append_csv(path: str, row: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_header = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header: w.writeheader()
        w.writerow(row)


def _summary(day: int, population: List[Creature]):
    n = len(population)
    alive = sum(1 for c in population if c.alive)
    ate0 = sum(1 for c in population if c.eaten == 0)
    ate1 = sum(1 for c in population if c.eaten == 1)
    ate2p = sum(1 for c in population if c.eaten >= 2)
    avg = lambda xs: (sum(xs)/len(xs)) if xs else float('nan')
    return dict(day=day, n=n, alive=alive, ate0=ate0, ate1=ate1, ate2p=ate2p,
                avg_speed=avg([c.speed for c in population]),
                avg_size=avg([c.size for c in population]),
                avg_sense=avg([c.sense for c in population]))


def _init_population(n: int, start_id: int = 1):
    sp = Species(1, "NS", (120,160,240), aggression=0.0, bravery=0.0, metabolism=1.0, diet="omnivore")
    pop: List[Creature] = []
    from random import uniform
    for i in range(n):
        pop.append(Creature(id=start_id+i, species=sp,
                            speed=uniform(1.2,3.0), size=uniform(0.8,1.6), sense=uniform(15.0,40.0),
                            x=0.0,y=0.0, home=(0.0,0.0), energy=0.0))
    return pop


def run():
    ap = argparse.ArgumentParser(description='Natural Selection 2.0 (UI/headless)')
    ap.add_argument('--ui', action='store_true', help='launch real-time UI')
    ap.add_argument('--days', type=int, default=40)
    ap.add_argument('--pop', type=int, default=60)
    ap.add_argument('--seed', type=int, default=SIM.seed)
    ap.add_argument('--csv', type=str, default='runs_ns/summary.csv')
    # mutation toggles for headless (UI has its own toggles in HUD)
    ap.add_argument('--mut_speed', action='store_true', default=True)
    ap.add_argument('--mut_size',  action='store_true', default=True)
    ap.add_argument('--mut_sense', action='store_true', default=True)
    args = ap.parse_args()

    if args.ui:
        raise SystemExit(run_ui())

    from evo_sim.sim.rng import RNG
    RNG.seed(args.seed)
    world = World()
    population = _init_population(args.pop)
    next_id = max((c.id for c in population), default=0) + 1

    for day in range(1, args.days + 1):
        simulate_day(world, population)
        survivors, repro = end_of_day_selection(population)
        summary = _summary(day, population)
        print(f"Day {day:3d} | N={summary['n']:3.0f} alive={summary['alive']:3.0f} "
              f"ate0={summary['ate0']:3.0f} ate1={summary['ate1']:3.0f} ate2+={summary['ate2p']:3.0f} "
              f"avg_speed={summary['avg_speed']:.2f} avg_size={summary['avg_size']:.2f} avg_sense={summary['avg_sense']:.2f}")
        if args.csv:
            _append_csv(args.csv, summary)

        new_pop: List[Creature] = []
        for s in survivors:
            new_pop.append(Creature(id=s.id, species=s.species, speed=s.speed, size=s.size, sense=s.sense,
                                    x=0.0,y=0.0, home=(0.0,0.0), energy=0.0))
        for p in repro:
            kid = make_child_from(parent=p, next_id=next_id,
                                  mutate_speed=args.mut_speed,
                                  mutate_size=args.mut_size,
                                  mutate_sense=args.mut_sense,
                                  species=p.species)
            new_pop.append(kid)
            next_id += 1
        if len(new_pop) == 0:
            new_pop = _init_population(args.pop, start_id=next_id)
            next_id = max((c.id for c in new_pop), default=0) + 1
        population = new_pop

if __name__ == '__main__':
    run()
