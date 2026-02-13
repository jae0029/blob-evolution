# evo_sim/sim/behaviors.py
from __future__ import annotations
from typing import List, Tuple
import math

from .models import Creature
from .config import TRAITS, BEHAV, WORLD, ENERGY, RISK
from .rng import RNG
from .world import World
from .config import PREY_AVOID

Vec = Tuple[float, float]

# --- Predator density avoidance (prey) knobs ---
AVOID_RADIUS_MULT = getattr(PREY_AVOID, "radius_mult", 1.6)
AVOID_MIN_COUNT   = getattr(PREY_AVOID, "min_count",   2)

# ---------------- vector helpers ----------------
def _unit(v: Vec) -> Vec:
    x, y = v
    n = math.hypot(x, y)
    return (0.0, 0.0) if n == 0 else (x/n, y/n)

def _mul(v: Vec, k: float) -> Vec:
    return (v[0]*k, v[1]*k)

def _add(a: Vec, b: Vec) -> Vec:
    return (a[0] + b[0], a[1] + b[1])

# ---------------- radii / bite ----------------
def bite_radius(c: Creature) -> float:
    return WORLD.bite_radius_scale * c.size

def _sense_radii(me: Creature):
    s = me.sense
    r_food = s * TRAITS.sense_food_scale
    r_pred = s * TRAITS.sense_pred_scale
    r_prey = s * TRAITS.sense_prey_scale
    # species modifiers
    r_prey *= (1.0 + 0.5 * max(0.0, min(1.0, me.species.aggression)))         # aggression → expand prey radius
    r_pred *= (1.0 + 0.5 * max(0.0, min(1.0, (1.0 - me.species.bravery))))    # low bravery → expand predator radius
    # (Optional) tiny herbivore boost to plant detection; safe to keep
    if me.species.diet.lower() == "herbivore":
        r_food *= 1.10
    return r_food, r_pred, r_prey

# ---------------- diet-specific predation rules ----------------
def can_eat(pred: Creature, prey: Creature) -> bool:
    """
    Predators may eat omnivores; still forbid any carnivore-on-carnivore.
    Size thresholds:
      - Carnivore: prey may be up to 1.4x bigger (prey.size <= 1.4 * pred.size)
      - Omnivore: must be >= 1.2x larger than prey (pred.size >= 1.2 * prey.size)
    Herbivores never hunt.
    """
    pred_diet = pred.species.diet.lower()
    prey_diet = prey.species.diet.lower()

    if pred_diet == "herbivore":
        return False

    # Forbid carnivore-on-carnivore; allow eating omnivores
    if prey_diet == "carnivore":
        return False

    if pred_diet == "carnivore":
        # can eat herbivores or omnivores up to 1.4x larger
        return prey.size <= 1.4 * pred.size

    if pred_diet == "omnivore":
        # can eat herbivores or omnivores only if >= 1.2x larger
        return pred.size >= 1.2 * prey.size

    return False

# ---------------- risk scoring used for chase prioritization ----------------
def _kill_probability(pred: Creature, prey: Creature) -> float:
    size_ratio = pred.size / max(1e-6, prey.size)
    speed_adv = pred.speed - prey.speed
    p = (float(RISK.base_p_kill)
         + float(RISK.size_weight) * (size_ratio - 1.0)
         + float(RISK.speed_weight) * (speed_adv / 6.0))
    return max(float(RISK.min_p_kill), min(float(RISK.max_p_kill), p))

# ---------------- main behavior ----------------
def step_behavior(world: World, me: Creature, others: List[Creature], dt: float, steps_left: int) -> Vec:
    """
    Decide velocity vector for current step.

    Includes:
      - Speed-aware, energy-aware return-home.
      - Herbivore reproduction-first logic with home-biased foraging after first food;
        allows pushing for 3rd food when time/energy permit.
      - Predators: dynamic kill cap (1 normally; 2 if hungry_streak >= 1),
                   predator-on-predator ban, allow predators to eat omnivores.
    """
    if not me.alive:
        return (0.0, 0.0)

    # Bind diet EARLY so it's available in all branches
    diet = me.species.diet.lower()

    eff_speed = me.effective_speed()
    Cmove  = float(ENERGY.C_move)
    Csize  = float(ENERGY.C_size)
    Csense = float(ENERGY.C_sense)

    r_food, r_pred, r_prey = _sense_radii(me)

    # ---------- Step-aware & energy-aware return-home ----------
    dxh, dyh = (me.home[0] - me.x, me.home[1] - me.y)
    dist_home = math.hypot(dxh, dyh)
    steps_required = dist_home / max(eff_speed * dt, 1e-6)

    # (A) Step gate:
    # - Herbivores: repro-first; after 1 food, stricter time gate; after 2, prefer home unless safe to try for 3.
    # - Others: gentle 5% grace.
    if diet == "herbivore":
        if me.eaten >= 3:
            me.going_home = True
        elif me.eaten == 2:
            # Push for 3rd only if time/energy allow; else go home
            if steps_required >= steps_left * 0.92:
                me.going_home = True
        elif me.eaten == 1:
            if steps_required >= steps_left * 0.90:
                me.going_home = True
        else:
            # eaten == 0: do NOT force step-based go-home; keep searching unless energy is critical
            pass
    else:
        if steps_required >= steps_left * 0.95:
            me.going_home = True

    # (B) Energy gate (applies to all)
    t_home = dist_home / max(eff_speed, 1e-6)
    move_cost  = Cmove  * (me.size ** 3) * (eff_speed ** 2) * t_home
    base_cost  = Csize  * (me.size ** 3) * t_home
    sense_cost = Csense * me.sense        * t_home
    need = (move_cost + base_cost + sense_cost) * float(BEHAV.return_energy_margin)
    if me.energy <= need:
        me.going_home = True

    # (C) Food-completion gates (non-herbivores keep original behavior)
    if diet != "herbivore":
        if me.eaten >= 2:
            me.going_home = True
    else:
        # already handled >=3 above; at 2 we may still search if safe
        pass

    # ---------- Flee predators ----------
    predator = None
    best_pd2 = r_pred * r_pred
    for o in others:
        if not o.alive or o.id == me.id:
            continue
        if o.size >= 1.1 * me.size:
            d2 = (o.x - me.x)**2 + (o.y - me.y)**2
            if d2 <= best_pd2:
                predator = o
                best_pd2 = d2
    if predator is not None:
        away = (me.x - predator.x, me.y - predator.y)
        return _mul(_unit(away), eff_speed)

    # ---------- Return home (strategic throttling) ----------
    if me.going_home:
        safety = 0.98
        if steps_left > 0:
            v_req = dist_home / max(steps_left * dt * safety, 1e-6)
            v_desired = min(eff_speed, v_req * 1.05)
        else:
            v_desired = eff_speed
        to_home = (me.home[0] - me.x, me.home[1] - me.y)
        return _mul(_unit(to_home), v_desired)


    # ---------- NEW: Predator density avoidance for PREY (herbivores) ----------
    if (diet == "herbivore") or (diet == "omnivore" and me.prey_kills_today == 0 and me.eaten == 0):
    # same avoidance logic
        # scan a bit wider than direct-flee radius
        scan_r = r_pred * AVOID_RADIUS_MULT
        scan_r2 = scan_r * scan_r
        cx = cy = 0.0
        cnt = 0
        for o in others:
            if not o.alive or o.id == me.id:
                continue
            od = o.species.diet.lower()
            if od in ("carnivore", "omnivore"):
                d2 = (o.x - me.x)**2 + (o.y - me.y)**2
                if d2 <= scan_r2:
                    cx += o.x; cy += o.y; cnt += 1
        if cnt >= AVOID_MIN_COUNT:
            cx /= cnt; cy /= cnt
            away = (me.x - cx, me.y - cy)
            ax, ay = _unit(away)
            # if we have a valid direction, move away from the predator cluster
            if ax != 0.0 or ay != 0.0:
                return _mul((ax, ay), eff_speed)

    # ---------- Foraging logic ----------
    if diet in ("herbivore", "omnivore"):
        # Home-biased plant foraging for herbivores after 1st (and possibly 2nd) food
        home_bias = 0.0
        if diet == "herbivore" and me.eaten >= 1:
            home_bias = 0.35 if me.eaten == 1 else 0.45

        f = world.nearest_food_within(me.x, me.y, r_food)
        if f is not None:
            to_food = _unit((f.x - me.x, f.y - me.y))
            if home_bias > 0.0:
                to_home = _unit((me.home[0] - me.x, me.home[1] - me.y))
                v = _unit(_add(_mul(to_food, 1.0 - home_bias), _mul(to_home, home_bias)))
                return _mul(v, eff_speed)
            else:
                return _mul(to_food, eff_speed)

    # ---------- Predator/omnivore hunting ----------
    if diet in ("carnivore", "omnivore"):
        want_hunt = (diet == "carnivore") or (me.species.aggression > 0.5 or me.eaten == 0)
        # Dynamic kill cap: 1 normally; 2 if hungry_streak >= 1
        max_kills_today = 2 if me.hungry_streak >= 1 else 1
        if me.prey_kills_today >= max_kills_today:
            want_hunt = False

        if want_hunt:
            candidate = None
            best_score = -1.0
            for o in others:
                if not o.alive or o.id == me.id:
                    continue
                if not can_eat(me, o):
                    continue
                p_kill = _kill_probability(me, o)
                d = math.hypot(o.x - me.x, o.y - me.y)
                if d <= r_prey:
                    score = p_kill / (1.0 + d)
                    if score > best_score:
                        best_score = score
                        candidate = o
            if candidate is not None and best_score >= 0.02:
                to_prey = (candidate.x - me.x, candidate.y - me.y)
                return _mul(_unit(to_prey), eff_speed)

    # ---------- Explore (wander) ----------
    drift = RNG.uniform(-BEHAV.wander_turn_rate, BEHAV.wander_turn_rate) * dt
    me.heading += drift
    vmag = BEHAV.wander_speed_fraction * eff_speed
    return (math.cos(me.heading) * vmag, math.sin(me.heading) * vmag)
