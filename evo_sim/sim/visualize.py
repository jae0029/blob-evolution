# evo_sim/sim/visualize.py
from __future__ import annotations
from typing import List
import matplotlib.pyplot as plt

from .models import Creature, Food
from .world import World

def snapshot(world: World, population: List[Creature], title: str = ""):
    fig, ax = plt.subplots(figsize=(6,6))
    ax.set_xlim(0, world.width)
    ax.set_ylim(0, world.height)
    # food
    if world.food:
        fx = [f.x for f in world.food]
        fy = [f.y for f in world.food]
        ax.scatter(fx, fy, c="green", s=10, alpha=0.5, label="Food")
    # creatures
    xs = [c.x for c in population if c.alive]
    ys = [c.y for c in population if c.alive]
    sizes = [20 * (c.size ** 1.2) for c in population if c.alive]
    ax.scatter(xs, ys, c="blue", s=sizes, alpha=0.7, label="Creatures")
    ax.set_title(title or "Snapshot")
    ax.legend()
    plt.tight_layout()
    plt.show()
