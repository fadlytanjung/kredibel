"""Seeded randomness (docs/18 SD-1): every draw comes from a named stream, never the wall clock.

A stream is keyed by the seed and a purpose ("2026-03/sales"), so adding a draw to one purpose never
shifts the values of another, and S2–S5 reuse S1's books exactly.
"""

import random
from datetime import date, timedelta
from decimal import Decimal


class Rng:
    def __init__(self, seed: int, *purpose: object) -> None:
        self.seed = seed
        self._random = random.Random("|".join(["kredibel-synth", str(seed), *map(str, purpose)]))

    def stream(self, *purpose: object) -> "Rng":
        return Rng(self.seed, *purpose)

    def chance(self, p: float) -> bool:
        return self._random.random() < p

    def between(self, lo: int, hi: int) -> int:
        return self._random.randint(lo, hi)

    def choice[T](self, items: list[T] | tuple[T, ...]) -> T:
        return items[self._random.randrange(len(items))]

    def sample[T](self, items: list[T], k: int) -> list[T]:
        return self._random.sample(items, k)

    def shuffle[T](self, items: list[T]) -> list[T]:
        out = list(items)
        self._random.shuffle(out)
        return out

    def amount(self, lo: int, hi: int, step: int = 1000) -> Decimal:
        """A whole amount in [lo, hi] on a grid of `step` (rupiah)."""
        return Decimal(self._random.randint(lo // step, hi // step) * step).quantize(
            Decimal("0.01")
        )

    def day(self, year: int, month: int, lo: int, hi: int) -> date:
        return date(year, month, self._random.randint(lo, hi))

    def jitter(self, d: date, lo: int, hi: int) -> date:
        return d + timedelta(days=self._random.randint(lo, hi))

    def uniform(self, lo: float, hi: float) -> float:
        return self._random.uniform(lo, hi)

    def bytes(self, n: int) -> bytes:
        return self._random.randbytes(n)
