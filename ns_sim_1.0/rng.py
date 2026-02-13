# Simple RNG wrapper
import random
class RNGClass:
    def __init__(self): self._r = random.Random()
    def seed(self, s): self._r.seed(s)
    def uniform(self, a, b): return self._r.uniform(a, b)
    def choice(self, seq): return self._r.choice(seq)
    def gauss(self, mu, sigma): return self._r.gauss(mu, sigma)
RNG = RNGClass()
