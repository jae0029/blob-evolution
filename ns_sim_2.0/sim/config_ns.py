
from dataclasses import dataclass

@dataclass(frozen=True)
class NSFlags:
    enable_speciation: bool = False
    enable_diets: bool = False
    enable_injuries: bool = False
    one_kill_per_day: bool = False
    size_predation_ratio: float = 1.2

NS = NSFlags()
