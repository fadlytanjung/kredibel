from functools import cache

from kredibel_synth.books import generate_books
from kredibel_synth.model import Books

SEEDS = range(1, 21)


@cache
def books_for(seed: int) -> Books:
    return generate_books(seed)
