from dataclasses import dataclass

# ---------------- World / time ----------------
@dataclass(frozen=False)
class WorldConfig:
    width: float = 200.0
    height: float = 200.0
    day_steps: int = 1600
    dt: float = 0.05
    n_food: int = 260
    home_margin: float = 1.6
    bite_radius_scale: float = 0.70

# ---------------- Energy ----------------------
@dataclass(frozen=True)
class EnergyConfig:
    base_energy: float = 160.0
    C_size: float = 0.0025      # maintenance ~ size^3
    C_sense: float = 0.0040     # constant sensing drain
    C_move: float = 0.0085      # movement ~ size^3 * v^2

# ---------------- Traits ----------------------
@dataclass(frozen=True)
class TraitConfig:
    min_speed: float = 0.2
    max_speed: float = 6.0
    min_size: float = 0.3
    max_size: float = 4.0
    min_sense: float = 5.0
    max_sense: float = 140.0
    sense_food_scale: float = 1.10
    sense_pred_scale: float = 1.30
    sense_prey_scale: float = 1.10

# ---------------- Behavior --------------------
@dataclass(frozen=True)
class BehaviorConfig:
    wander_turn_rate: float = 1.4
    wander_speed_fraction: float = 0.80
    return_energy_margin: float = 1.20

# ---------------- Reproduction / mutation ----
@dataclass(frozen=True)
class ReproConfig:
    mutation_rate: float = 0.30
    mutation_sd_frac: float = 0.20

WORLD = WorldConfig()
ENERGY = EnergyConfig()
TRAITS = TraitConfig()
BEHAV = BehaviorConfig()
REPRO = ReproConfig()
