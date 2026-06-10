"""wiki-random: turn a seed number into a Wikipedia article, deterministically."""

# Bind the engine MODULE as `wiki_random.oracle` (do not shadow it with the
# function of the same name below).
from . import oracle
from .oracle import mix, mix_steps, mix_trace, sieve, walk, main

__version__ = "1.0.0"

__all__ = ["oracle", "mix", "mix_steps", "mix_trace", "sieve", "walk", "main", "__version__"]
