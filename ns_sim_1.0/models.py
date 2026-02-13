from dataclasses import dataclass
from typing import Optional, Tuple

Vec = Tuple[float, float]

@dataclass
class Creature:
    id: int
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
    dist_traveled_today: float = 0.0

    def pos(self) -> Vec: return (self.x, self.y)
    def at_home(self, margin: float) -> bool:
        hx, hy = self.home
        dx, dy = self.x - hx, self.y - hy
        return (dx*dx + dy*dy) <= (margin*margin)
    def effective_speed(self) -> float:
        return self.speed
