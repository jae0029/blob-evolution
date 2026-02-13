# evo_sim/ui/csv_writer.py
from __future__ import annotations
import csv
import os
import uuid
from typing import Iterable, Dict, List, Optional
from ..sim.models import Creature


class DailyCsvLogger:
    """
    Append day-level UI stats to CSV files *when a day flips* in the UI.
    - overall_path:  runs/ui_daily.csv
    - species_path:  runs/ui_species_daily.csv  (optional)
    Each run gets its own session_id so you can combine logs safely later.

    Usage from UI loop:
        logger = DailyCsvLogger()
        ...
        if new_day_started:
            # If you keep a 'last_population_snapshot' of the day that just finished,
            # pass that here instead of live.population.
            logger.append_day(day=live.day - 1,
                              pop=live.last_population_snapshot or live.population,
                              food_per_day=int(WORLD.n_food),
                              day_steps=int(WORLD.day_steps))
    """
    def __init__(self,
                 overall_path: str = "runs/ui_daily.csv",
                 species_path: str = "runs/ui_species_daily.csv",
                 enable_species: bool = True):
        self.overall_path = overall_path
        self.species_path = species_path
        self.enable_species = enable_species
        self.session_id = uuid.uuid4().hex[:8]

        # Ensure folders exist
        if self.overall_path:
            os.makedirs(os.path.dirname(self.overall_path), exist_ok=True)
        if self.enable_species and self.species_path:
            os.makedirs(os.path.dirname(self.species_path), exist_ok=True)

        # Write headers if files are new
        self._overall_header = [
            "session_id","day","n","alive_end","ate0","ate1","ate2p",
            "avg_speed","avg_size","avg_sense","avg_metabolism",
            "speed_min","speed_q25","speed_median","speed_q75","speed_max",
            "food_per_day","day_steps","notes"
        ]
        if self.overall_path and not os.path.exists(self.overall_path):
            with open(self.overall_path, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=self._overall_header).writeheader()

        self._species_header = [
            "session_id","day","species_id","species_name",
            "n","alive_end","ate0","ate1","ate2p",
            "avg_speed","avg_size","avg_sense","metabolism"
        ]
        if self.enable_species and self.species_path and not os.path.exists(self.species_path):
            with open(self.species_path, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=self._species_header).writeheader()

    # ---------------- internal helpers ----------------
    @staticmethod
    def _avg(xs: List[float]) -> float:
        return (sum(xs) / len(xs)) if xs else float("nan")

    @staticmethod
    def _quantiles(xs: List[float]) -> Dict[str, float]:
        """
        Simple quantile helper (no numpy dependency).
        Returns q25, q50, q75 plus min/max.
        """
        if not xs:
            return dict(
                speed_min=float("nan"),
                speed_q25=float("nan"),
                speed_median=float("nan"),
                speed_q75=float("nan"),
                speed_max=float("nan"),
            )
        q = sorted(xs)
        n = len(q)
        def at(p: float) -> float:
            if n == 1:
                return q[0]
            # nearest-rank style index
            i = int(round(p * (n - 1)))
            return q[max(0, min(n - 1, i))]
        return dict(
            speed_min=q[0],
            speed_q25=at(0.25),
            speed_median=at(0.50),
            speed_q75=at(0.75),
            speed_max=q[-1],
        )

    def _overall_row(self, day: int, pop: Iterable[Creature], food_per_day: int, day_steps: int, notes: Optional[str]) -> Dict:
        pop = list(pop)
        n = len(pop)
        alive_end = sum(1 for c in pop if c.alive)
        ate0 = sum(1 for c in pop if c.eaten == 0)
        ate1 = sum(1 for c in pop if c.eaten == 1)
        ate2p = sum(1 for c in pop if c.eaten >= 2)

        speeds = [c.speed for c in pop]
        sizes  = [c.size for c in pop]
        senses = [c.sense for c in pop]
        mets   = [c.species.metabolism for c in pop]

        q = self._quantiles(speeds)

        row = dict(
            session_id=self.session_id,
            day=day,
            n=n,
            alive_end=alive_end,
            ate0=ate0,
            ate1=ate1,
            ate2p=ate2p,
            avg_speed=self._avg(speeds),
            avg_size=self._avg(sizes),
            avg_sense=self._avg(senses),
            avg_metabolism=self._avg(mets),
            speed_min=q["speed_min"],
            speed_q25=q["speed_q25"],
            speed_median=q["speed_median"],
            speed_q75=q["speed_q75"],
            speed_max=q["speed_max"],
            food_per_day=int(food_per_day),
            day_steps=int(day_steps),
            notes=(notes or "")
        )
        return row

    def _species_rows(self, day: int, pop: Iterable[Creature]) -> Iterable[Dict]:
        pop = list(pop)
        # group by species.id
        by_sp: Dict[int, List[Creature]] = {}
        for c in pop:
            by_sp.setdefault(c.species.id, []).append(c)

        for sid, members in by_sp.items():
            n = len(members)
            alive_end = sum(1 for c in members if c.alive)
            ate0 = sum(1 for c in members if c.eaten == 0)
            ate1 = sum(1 for c in members if c.eaten == 1)
            ate2p = sum(1 for c in members if c.eaten >= 2)
            row = dict(
                session_id=self.session_id, day=day,
                species_id=sid,
                species_name=members[0].species.name,
                n=n, alive_end=alive_end, ate0=ate0, ate1=ate1, ate2p=ate2p,
                avg_speed=self._avg([c.speed for c in members]),
                avg_size=self._avg([c.size for c in members]),
                avg_sense=self._avg([c.sense for c in members]),
                metabolism=members[0].species.metabolism,
            )
            yield row

    # ---------------- public API ----------------
    def append_day(self, day: int, pop: Iterable[Creature], food_per_day: int, day_steps: int, notes: Optional[str] = None):
        """Append one row (overall) and many rows (per species, if enabled)."""
        # Overall
        if self.overall_path:
            with open(self.overall_path, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=self._overall_header)
                w.writerow(self._overall_row(day, pop, food_per_day, day_steps, notes))

        # Per-species
        if self.enable_species and self.species_path:
            with open(self.species_path, "a", newline="") as f:
                w = csv.DictWriter(f, fieldnames=self._species_header)
                for r in self._species_rows(day, pop):
                    w.writerow(r)
