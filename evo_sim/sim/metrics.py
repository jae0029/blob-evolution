# evo_sim/sim/metrics.py
from __future__ import annotations
from typing import List, Dict
import os
import csv

from .models import Creature

def summarize_day(day: int, population: List[Creature]) -> Dict[str, float]:
    alive = sum(1 for c in population if c.alive)
    ate0 = sum(1 for c in population if c.eaten == 0)
    ate1 = sum(1 for c in population if c.eaten == 1)
    ate2p = sum(1 for c in population if c.eaten >= 2)
    avg_speed = sum(c.speed for c in population) / max(len(population), 1)
    avg_size = sum(c.size for c in population) / max(len(population), 1)
    avg_sense = sum(c.sense for c in population) / max(len(population), 1)
    return dict(
        day=day, n=len(population), alive=alive, ate0=ate0, ate1=ate1, ate2p=ate2p,
        avg_speed=avg_speed, avg_size=avg_size, avg_sense=avg_sense
    )

def append_csv(path: str, row: Dict[str, float]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_header = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            w.writeheader()
        w.writerow(row)