# evo_sim/sim/world.py
from __future__ import annotations
from typing import List, Optional, Tuple
import math

from .models import Food, Creature
from .rng import RNG
from .config import WORLD, ENERGY

class World:
    def __init__(self, width: float = WORLD.width, height: float = WORLD.height):
        self.width = width
        self.height = height
        self.food: List[Food] = []
        self._food_id = 0

    def _next_food_id(self) -> int:
        self._food_id += 1
        return self._food_id

    # --- spawning ---
    def spawn_food_uniform(self, n: int) -> None:
        self.food = []
        for _ in range(n):
            x = RNG.uniform(0.0, self.width)
            y = RNG.uniform(0.0, self.height)
            self.food.append(Food(x=x, y=y, id=self._next_food_id()))

    def spawn_creatures_at_edges(self, population: List[Creature]) -> None:
        for c in population:
            side = RNG.choice(["left", "right", "top", "bottom"])
            if side == "left":
                x, y = 0.0, RNG.uniform(0, self.height)
            elif side == "right":
                x, y = self.width, RNG.uniform(0, self.height)
            elif side == "top":
                x, y = RNG.uniform(0, self.width), self.height
            else:
                x, y = RNG.uniform(0, self.width), 0.0
            c.x, c.y = x, y
            c.home = (x, y)
            c.energy = ENERGY.base_energy
            c.eaten = 0
            c.alive = True
            c.going_home = False
            c.target = None
            # reset per-day counters
            c.prey_kills_today = 0
            # tick injuries across days
            if c.injury_days_left > 0:
                c.injury_days_left -= 1
                if c.injury_days_left <= 0:
                    c.injury_days_left = 0
                    c.injury_speed_mult = 1.0

    # --- spatial helpers ---
    def nearest_food_within(self, x: float, y: float, radius: float) -> Optional[Food]:
        best = None
        best_d2 = radius * radius
        for f in self.food:
            d2 = (f.x - x)**2 + (f.y - y)**2
            if d2 <= best_d2:
                best = f
                best_d2 = d2
        return best

    def remove_food(self, fid: int) -> None:
        self.food = [f for f in self.food if f.id != fid]

    @staticmethod
    def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(a[0]-b[0], a[1]-b[1])

    def clamp_inside(self, x: float, y: float) -> Tuple[float, float]:
        return min(max(x, 0.0), self.width), min(max(y, 0.0), self.height)
