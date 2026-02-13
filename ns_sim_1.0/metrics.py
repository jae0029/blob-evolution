from __future__ import annotations
from typing import Dict, List
from .models import Creature

def summarize_day(day: int, population: List[Creature]) -> Dict:
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
