# evo_sim/sim/config.py
from dataclasses import dataclass

# ------------------------------------------------------------
# WORLD / SIMULATION SPATIAL SETTINGS
# ------------------------------------------------------------
@dataclass(frozen=False)  # mutable so UI can tweak n_food at runtime
class WorldConfig:
    width: float = 250.0
    height: float = 250.0
    # fixed-length days: ONLY this ends the day
    day_steps: int = 1500
    dt: float = 0.05
    # food
    n_food: int = 180
    # home + bite
    home_margin: float = 1.5
    bite_radius_scale: float = 0.70

# ------------------------------------------------------------
# ENERGY MODEL COEFFICIENTS (matches rules)
# ------------------------------------------------------------
@dataclass(frozen=True)
class EnergyConfig:
    base_energy=190.0
    C_size=0.0035
    C_sense=0.0042
    C_move=0.0065   # ↓ from 0.0105 (about 30% cheaper to move fast)


# ------------------------------------------------------------
# TRAIT RANGES
# ------------------------------------------------------------
@dataclass(frozen=True)
class TraitConfig:
    min_speed: float = 0.2
    max_speed: float = 10.0
    min_size: float = 0.3
    max_size: float = 8.0
    min_sense: float = 5.0
    max_sense: float = 140.0
    sense_food_scale: float = 1.25
    sense_pred_scale: float = 1.25
    sense_prey_scale: float = 1.0

# ------------------------------------------------------------
# BEHAVIOR TUNING
# ------------------------------------------------------------
@dataclass(frozen=True)
class BehaviorConfig:
    wander_turn_rate: float = 1.4
    wander_speed_fraction: float = 0.85
    return_energy_margin: float = 1.20

# ------------------------------------------------------------
# REPRODUCTION / MUTATION
# ------------------------------------------------------------
@dataclass(frozen=True)
class ReproConfig:
    reproduction_offspring: int = 1    # base count (may be overridden per diet rule)
    mutation_rate: float = 0.10        # tune freely
    mutation_sd_frac: float = 0.15

# ------------------------------------------------------------
# SPECIATION
# ------------------------------------------------------------
@dataclass(frozen=True)
class SpeciationConfig:
    threshold_frac: float = 0.40
    min_metabolism: float = 0.80
    max_metabolism: float = 1.20

# ------------------------------------------------------------
# ATTACK RISK / INJURY
# ------------------------------------------------------------
@dataclass(frozen=True)
class RiskConfig:
    base_p_kill: float = 0.45
    size_weight: float = 0.60
    speed_weight: float = 0.50
    min_p_kill: float = 0.05
    max_p_kill: float = 0.98
    injury_on_fail_prob: float = 0.55
    injury_days_min: int = 1
    injury_days_max: int = 3
    injury_speed_mult_lo: float = 0.60
    injury_speed_mult_hi: float = 0.90
    energy_loss_on_fail: float = 8.0
    fatal_counterattack_prob: float = 0.06     # if prey >= 1.2x size
    injury_energy_leak_per_time: float = 0.003 # per time unit while injured

# ------------------------------------------------------------
# HEADLESS SETTINGS
# ------------------------------------------------------------
@dataclass(frozen=False)
class SimConfig:
    seed: int = 42
    initial_population: int = 60
    days: int = 100
    track_csv: str | None = "runs/summary.csv"
    enable_plot: bool = False

# ------------------------------------------------------------
# EXPORT SINGLETONS
# ------------------------------------------------------------
WORLD = WorldConfig()
ENERGY = EnergyConfig()
TRAITS = TraitConfig()
BEHAV = BehaviorConfig()
REPRO = ReproConfig()
SPECIATION = SpeciationConfig()
RISK = RiskConfig()
SIM = SimConfig()