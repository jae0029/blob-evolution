# evo_sim/sim/world.py
from __future__ import annotations
from typing import List, Optional, Tuple
import math

from .models import Food, Creature
from .rng import RNG
from .config import WORLD, ENERGY, PRED_HOME


class World:
    def __init__(self, width: float = WORLD.width, height: float = WORLD.height):
        self.width = width
        self.height = height
        self.food: List[Food] = []
        self._food_id = 0

    def _next_food_id(self) -> int:
        self._food_id += 1
        return self._food_id

    def spawn_food_uniform(self, n: int) -> None:
        self.food = []
        for _ in range(n):
            x = RNG.uniform(0.0, self.width)
            y = RNG.uniform(0.0, self.height)
            self.food.append(Food(x=x, y=y, id=self._next_food_id()))

    # --- helpers for placement ---
    def _random_edge_point(self) -> Tuple[float, float]:
        side = RNG.choice(["left", "right", "top", "bottom"])
        if side == "left":
            return (0.0, RNG.uniform(0, self.height))
        if side == "right":
            return (self.width, RNG.uniform(0, self.height))
        if side == "top":
            return (RNG.uniform(0, self.width), self.height)
        return (RNG.uniform(0, self.width), 0.0)

    def _predator_center_point(self) -> Tuple[float, float]:
        """Place predators on a small ring around the world center (or exactly at center)."""
        cx, cy = self.width * 0.5, self.height * 0.5
        r0 = max(0.0, float(PRED_HOME.center_ring_radius))
        if r0 <= 1e-6:
            # exact center
            return (cx, cy)
        # small ring with jitter
        rj = max(0.0, float(PRED_HOME.ring_jitter))
        r = max(0.0, r0 + RNG.uniform(-rj, rj))
        ang = RNG.uniform(0.0, 2.0 * math.pi)
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        # clamp inside world bounds just in case
        x = min(max(x, 0.0), self.width)
        y = min(max(y, 0.0), self.height)
        return (x, y)

    def spawn_creatures_at_edges(self, population: List[Creature]) -> None:
        """
        Start of day placement/reset:
          - Herbivores spawn on edges; home = that edge point (original behavior).
          - Predators (carnivores & omnivores) spawn at/near the world center; home = center location.
        """
        for c in population:
            diet = c.species.diet.lower()

            # if diet == "herbivore":
            #     # Original behavior: edges
            #     x, y = self._random_edge_point()
            #     c.x, c.y = x, y
            #     c.home = (x, y)
            # else:
            # Predators: center their home (and optionally spawn there)
            hx, hy = self._predator_center_point()
            c.home = (hx, hy)
            if PRED_HOME.spawn_at_home:
                c.x, c.y = hx, hy
            else:
                # If you prefer predators to still start at edges but *return* to center, uncomment:
                # x, y = self._random_edge_point()
                # c.x, c.y = x, y
                # For now we'll place them at home to avoid instant edge interactions.
                c.x, c.y = hx, hy

            # Reset per-day state
            c.energy = ENERGY.base_energy
            c.eaten = 0
            c.alive = True
            c.going_home = False
            c.target = None
            c.prey_kills_today = 0

            # Tick injuries across days (as you had before)
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
