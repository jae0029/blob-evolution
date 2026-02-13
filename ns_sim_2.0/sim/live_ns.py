
from __future__ import annotations
from typing import List
import math

from evo_sim.sim.config import WORLD
from evo_sim.sim.world import World
from evo_sim.sim.models import Creature as EvoCreature, Species
from .engine_ns import end_of_day_selection, _clamp_speed, _apply_energy, _apply_motion, _consume_food_if_reached, _consume_prey_if_reached
from .behaviors_ns import step_behavior
from .lineage_stub import LineageStub

class LiveSimNS:
    def __init__(self, population: List[EvoCreature], seed: int = 42, lineage=None):
        from evo_sim.sim.rng import RNG
        RNG.seed(seed)
        self.world = World()
        self.population: List[EvoCreature] = population
        self.day: int = 1
        self.step_in_day: int = 0
        self._next_id = max((c.id for c in population), default=0) + 1
        self.mutate_speed = True
        self.mutate_size  = True
        self.mutate_sense = True
        self.lineage = lineage if lineage is not None else LineageStub()
        self.last_population_snapshot = None
        self.start_new_day()

    def start_new_day(self):
        self.world.spawn_food_uniform(int(WORLD.n_food))
        self.world.spawn_creatures_at_edges(self.population)
        self.step_in_day = 0

    def _step_once(self):
        dt = WORLD.dt
        pop = self.population
        steps_left = int(WORLD.day_steps) - self.step_in_day
        velocities = []
        for me in pop:
            if not me.alive:
                velocities.append((me.id, 0.0, 0.0)); continue
            vx, vy = step_behavior(self.world, me, pop, dt, steps_left)
            vx, vy = _clamp_speed(vx, vy, me.effective_speed())
            velocities.append((me.id, vx, vy))
        idmap = {c.id: c for c in pop}
        for cid, vx, vy in velocities:
            me = idmap[cid]
            if not me.alive:
                continue
            spd = math.hypot(vx, vy)
            _apply_energy(me, spd, dt)
            if not me.alive:
                continue
            _apply_motion(self.world, me, vx, vy, dt)
        for me in pop:
            if not me.alive:
                continue
            _consume_prey_if_reached(me, pop)
            _consume_food_if_reached(self.world, me)
        self.step_in_day += 1

    def step(self) -> bool:
        if len(self.population) == 0:
            sp = Species(1, "NS", (120,160,240), aggression=0.0, bravery=0.0, metabolism=1.0, diet="omnivore")
            for i in range(16):
                self.population.append(EvoCreature(
                    id=self._next_id+i, species=sp, speed=2.2, size=1.0, sense=30.0,
                    x=0.0,y=0.0, home=(0.0,0.0), energy=0.0
                ))
            self._next_id += 16
            self.start_new_day()
            return True
        self._step_once()
        if self.step_in_day < int(WORLD.day_steps):
            return False
        survivors, repro_orders = end_of_day_selection(self.population)
        self.last_population_snapshot = list(self.population)
        new_pop: List[EvoCreature] = []
        for s in survivors:
            new_pop.append(EvoCreature(id=s.id, species=s.species, speed=s.speed, size=s.size, sense=s.sense,
                                       x=0.0,y=0.0, home=(0.0,0.0), energy=0.0))
        for p in repro_orders:
            new_pop.append(EvoCreature(id=self._next_id, species=p.species, speed=p.speed, size=p.size, sense=p.sense,
                                       x=0.0,y=0.0, home=(0.0,0.0), energy=0.0))
            self._next_id += 1
        self.population = new_pop
        self.day += 1
        self.start_new_day()
        return True

    def food_positions(self):
        return [(f.x, f.y) for f in self.world.food]

    def stat_means(self):
        n = len(self.population)
        if n == 0:
            return dict(n=0, mean_speed=float('nan'), mean_size=float('nan'), mean_sense=float('nan'))
        return dict(n=n,
                    mean_speed=sum(c.speed for c in self.population)/n,
                    mean_size=sum(c.size for c in self.population)/n,
                    mean_sense=sum(c.sense for c in self.population)/n)
