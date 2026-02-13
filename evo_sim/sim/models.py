# evo_sim/sim/models.py
from dataclasses import dataclass
from typing import Optional, Tuple

Vec = Tuple[float, float]

@dataclass
class Species:
    id: int
    name: str
    color: Tuple[int, int, int]
    aggression: float
    bravery: float
    metabolism: float
    diet: str  # "herbivore" | "carnivore" | "omnivore"

@dataclass
class Food:
    x: float
    y: float
    id: int

@dataclass
class Creature:
    id: int
    species: Species
    speed: float
    size: float
    sense: float
    x: float
    y: float
    home: Vec
    energy: float
    eaten: int = 0
    alive: bool = True
    going_home: bool = False
    heading: float = 0.0
    target: Optional[Vec] = None

    hungry_streak: int = 0
    prey_kills_today: int = 0

    # Injury state
    injury_days_left: int = 0
    injury_speed_mult: float = 1.0  # <1.0 while injured

    def pos(self) -> Vec:
        return (self.x, self.y)

    def at_home(self, margin: float) -> bool:
        hx, hy = self.home
        return ((self.x - hx) ** 2 + (self.y - hy) ** 2) ** 0.5 <= margin

    def effective_speed(self) -> float:
        return self.speed * (self.injury_speed_mult if self.injury_days_left > 0 else 1.0)