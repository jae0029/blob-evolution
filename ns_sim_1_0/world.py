from __future__ import annotations
from typing import List, Optional, Tuple
import math

from .models import Creature
from .config import WORLD
from .rng import RNG

class World:
    def __init__(self, width: float = WORLD.width, height: float = WORLD.height):
        self.width, self.height = width, height
        self.food: List[Tuple[float,float,int]] = []
        self._food_id = 0
    def _next_food_id(self) -> int:
        self._food_id += 1; return self._food_id
    def spawn_food_uniform(self, n: int) -> None:
        self.food = []
        for _ in range(n):
            x = RNG.uniform(0.0, self.width); y = RNG.uniform(0.0, self.height)
            self.food.append((x,y,self._next_food_id()))
    def _random_edge_point(self) -> Tuple[float,float]:
        side = RNG.choice(['left','right','top','bottom'])
        if side=='left':  return (0.0, self.height * RNG.uniform(0,1))
        if side=='right': return (self.width, self.height * RNG.uniform(0,1))
        if side=='top':   return (self.width * RNG.uniform(0,1), self.height)
        return (self.width * RNG.uniform(0,1), 0.0)
    def spawn_creatures_at_edges(self, population: List[Creature]) -> None:
        from .config import ENERGY
        for c in population:
            x,y = self._random_edge_point()
            c.x, c.y = x, y
            c.home = (x, y)
            c.energy = ENERGY.base_energy
            c.eaten = 0; c.alive = True; c.going_home = False; c.target = None
            c.dist_traveled_today = 0.0
    def nearest_food_within(self, x: float, y: float, radius: float):
        best = None; best_d2 = radius*radius
        for fx,fy,fid in self.food:
            d2 = (fx-x)**2 + (fy-y)**2
            if d2 <= best_d2:
                best = (fx,fy,fid); best_d2 = d2
        return best
    def remove_food(self, fid: int) -> None:
        self.food = [t for t in self.food if t[2] != fid]
    def clamp_inside(self, x: float, y: float) -> Tuple[float,float]:
        return min(max(x,0.0), self.width), min(max(y,0.0), self.height)
