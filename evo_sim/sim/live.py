# evo_sim/sim/live.py
from __future__ import annotations
from typing import List
import math

from .models import Creature, Species
from .world import World
from .behaviors import step_behavior
from .config import WORLD, ENERGY
from .engine import end_of_day_selection, _consume_prey_if_reached, _consume_food_if_reached
from .rng import RNG
from .genetics import reproduce_N_children
from .lineage import LineageTracker

class LiveSim:
    """
    Step-by-step wrapper for UI with species + phylogeny.
    Uses variable offspring counts (e.g., herbivores with eaten>=3 -> 2 babies).
    """
    def __init__(self, population: List[Creature], seed: int = 42, lineage: LineageTracker | None = None):
        RNG.seed(seed)
        self.world = World()
        self.population: List[Creature] = population
        self.day: int = 1
        self.step_in_day: int = 0

        self._next_id = max((c.id for c in population), default=0) + 1
        self._next_species_id = max((c.species.id for c in population), default=0) + 1

        # UI mutation toggles
        self.mutate_speed = True
        self.mutate_size  = True
        self.mutate_sense = True

        # lineage tracker
        self.lineage = lineage if lineage is not None else LineageTracker()
        if not self.lineage.has_data():
            seen = set()
            for c in population:
                if c.species.id not in seen:
                    self.lineage.register_root_species(c.species, birth_day=self.day)
                    seen.add(c.species.id)

        # for UI CSV (optional)
        self.last_population_snapshot = None

        self.start_new_day()

    def start_new_day(self):
        self.world.spawn_food_uniform(int(WORLD.n_food))
        self.world.spawn_creatures_at_edges(self.population)
        self.step_in_day = 0

    def _apply_energy(self, me: Creature, move_speed: float, dt: float):
        from .config import RISK
        base = ENERGY.C_size * (me.size ** 3) + ENERGY.C_sense * me.sense
        move = ENERGY.C_move * (me.size ** 3) * (move_speed ** 2)
        leak = RISK.injury_energy_leak_per_time if me.injury_days_left > 0 else 0.0
        mult = me.species.metabolism
        me.energy -= ((base + move) * mult + leak) * dt
        if me.energy <= 0:
            me.alive = False

    def _step_once(self):
        dt = WORLD.dt
        pop = self.population
        steps_left = int(WORLD.day_steps) - self.step_in_day

        # velocities
        velocities = []
        for me in pop:
            if not me.alive:
                velocities.append((me.id, 0.0, 0.0))
                continue
            vx, vy = step_behavior(self.world, me, pop, dt, steps_left)
            spd = math.hypot(vx, vy)
            vmax = me.effective_speed()
            if spd > vmax and spd > 1e-12:
                s = vmax / spd
                vx *= s; vy *= s
            velocities.append((me.id, vx, vy))

        # energy + motion
        id2 = {c.id: c for c in pop}
        for cid, vx, vy in velocities:
            me = id2[cid]
            if not me.alive:
                continue
            move_speed = math.hypot(vx, vy)
            self._apply_energy(me, move_speed, dt)
            if not me.alive:
                continue
            me.x += vx * dt
            me.y += vy * dt
            me.x, me.y = self.world.clamp_inside(me.x, me.y)

        # interactions
        for me in pop:
            if not me.alive:
                continue
            _consume_prey_if_reached(me, pop)
            _consume_food_if_reached(self.world, me)

        self.step_in_day += 1

    def step(self) -> bool:
        # repopulate if extinct (minimal reseed)
        if len(self.population) == 0:
            seed_sp = [
                Species(1, "A", (70,140,240), aggression=0.3, bravery=0.5, metabolism=1.0, diet="omnivore"),
                Species(2, "B", (240,160,60), aggression=0.1, bravery=0.8, metabolism=0.9, diet="herbivore"),
            ]
            self._next_species_id = 3
            self.population = [
                Creature(
                    id=i+1, species=seed_sp[i % len(seed_sp)],
                    speed=2.2, size=1.0, sense=30.0,
                    x=0.0, y=0.0, home=(0.0,0.0), energy=0.0
                ) for i in range(16)
            ]
            self._next_id = max(c.id for c in self.population) + 1
            self.lineage = LineageTracker()
            for sp in seed_sp:
                self.lineage.register_root_species(sp, birth_day=self.day)
            self.start_new_day()
            return True

        self._step_once()

        # fixed length day
        if self.step_in_day < int(WORLD.day_steps):
            return False

        # end of day
        survivors, repro_orders = end_of_day_selection(self.population)

        # keep snapshot for UI CSV, if needed
        self.last_population_snapshot = list(self.population)

        # rebuild next population
        new_pop: List[Creature] = []
        for s in survivors:
            new_pop.append(Creature(
                id=s.id, species=s.species,
                speed=s.speed, size=s.size, sense=s.sense,
                x=0.0, y=0.0, home=(0.0,0.0), energy=0.0,
                hungry_streak=s.hungry_streak
            ))

        # variable offspring counts
        for parent, num_kids in repro_orders:
            kids, self._next_id, self._next_species_id, events = reproduce_N_children(
                parent=parent, n_offspring=num_kids,
                next_creature_id=self._next_id, next_species_id=self._next_species_id,
                mutate_speed=self.mutate_speed, mutate_size=self.mutate_size, mutate_sense=self.mutate_sense
            )
            for psp, csp in events:
                self.lineage.register_speciation(psp, csp, birth_day=self.day + 1)
            new_pop.extend(kids)

        self.population = new_pop
        self.day += 1
        self.lineage.update_from_population(self.population, self.day)
        self.start_new_day()
        return True

    # UI helpers
    def food_positions(self):
        return [(f.x, f.y) for f in self.world.food]

    def stat_means(self):
        n = len(self.population)
        if n == 0:
            return dict(n=0, mean_speed=float('nan'), mean_size=float('nan'), mean_sense=float('nan'))
        return dict(
            n=n,
            mean_speed=sum(c.speed for c in self.population)/n,
            mean_size=sum(c.size for c in self.population)/n,
            mean_sense=sum(c.sense for c in self.population)/n,
        )