# evo_sim/sim/rng.py
import random

class RNG:
    _rng = random.Random()

    @classmethod
    def seed(cls, s: int):
        cls._rng.seed(s)

    @classmethod
    def uniform(cls, a: float, b: float) -> float:
        return cls._rng.uniform(a, b)

    @classmethod
    def choice(cls, seq):
        return cls._rng.choice(seq)

    @classmethod
    def gauss(cls, mu: float, sigma: float) -> float:
        return cls._rng.gauss(mu, sigma)
