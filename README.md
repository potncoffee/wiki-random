# wiki-random

Turn any seed number into a real Wikipedia article through a **deterministic,
fully auditable** modular-hash pipeline. Same seed (plus the same live page-ID
ceiling) always lands on the same article, and every step of the arithmetic is
shown so the result is checkable, not magic.

```
seed -> reduce mod m -> three mixing rounds -> sieve into the live ID range -> walk to nearest real article
```

The digit-count of the seed carries no information about the output: a 2-digit
seed and a 50-digit seed both spread across the whole encyclopedia. No random
number generator.

## Install

```
pip install wiki-random
```

Or just run the script directly (it is pure Python 3 standard library, no
dependencies):

```
python3 wiki_random/oracle.py 1729
```

## Two ways to use it

The tool has one job with two audiences, chosen by a flag.

### Default: generate an AI prompt

```
wiki-random 1729
```

This prints a complete, self-contained **prompt you can paste into any AI
assistant** (ChatGPT, Claude, anything). The prompt carries this run's labeled
math, a paste-and-run proof, the resolved article, and the full instructions for
how to present it (a who / what / where / when / why / how, disambiguation
handling, an honesty rule). The instructions travel *with* the data, so it works
in any assistant without installing anything.

It is adaptive about the network:

- **With internet**, the script resolves the article itself, and the prompt says
  "here is the article, here is the verified math, present it."
- **Without internet** (for example inside a network-isolated code sandbox), the
  script still does the deterministic math and the prompt *delegates* the lookup:
  it tells the assistant to fetch the live ceiling, finish the walk with its own
  web-browsing tool, and then present the result. So it never just fails.

### `--human`: a standalone reading

```
wiki-random --human 1729
```

This prints the reading for a person, not a prompt: the labeled math, the
constants, the target id, the article name, its link, and Wikipedia's own lead
summary. No AI in the loop. Because a human cannot delegate the lookup, this mode
**requires the internet** and exits with a clear message if it is offline.

Add `--verify` (either mode) to include a self-contained, paste-and-run Python 3
snippet that reproduces the hash and page id from the seed and the seven
constants alone. Anyone can run it cold to confirm the math without trusting the
tool.

```
wiki-random --human --verify 1729
```

## The math

- **Modulus** `m = 2^61 - 1` (a Mersenne prime), far larger than the page-ID
  range, so the final reduction is near-uniform.
- Three rounds of `x = (x * a + c) mod m`, a linear-congruential mixing chain.
  Each multiply is a bijection mod the prime, and each `+ c` breaks the linear
  rhythm so consecutive seeds land on unrelated articles (avalanche).
- The **sieve** maps the hash into `[1, ceiling]`, where `ceiling` is the live
  maximum Wikipedia page id (fetched per run; falls back to a constant offline).
- The **walk** queries a 50-ID window centered on the target and picks the
  nearest valid main-namespace, non-redirect article (ties go to the lower id),
  widening if the center is empty.

Because the ceiling grows as Wikipedia grows, a seed slowly drifts to different
articles over time. The hash about the seed is permanent; only the live range
moves. This is intended: an oracle, not a permanent lookup.

## Tests

```
pytest -q
```

All tests are offline (the network is injected via a fake), so the suite is fast
and deterministic.

## License

MIT
