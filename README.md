# wiki-random

Turn any seed number into a real Wikipedia article through a **deterministic,
fully auditable** modular-hash pipeline. Same seed (plus the same live
page-ID ceiling) always lands on the same article, and every step of the
arithmetic is shown on screen so the result is checkable, not magic.

```
seed -> reduce mod m -> three mixing rounds -> sieve into the live ID range -> walk to nearest real article
```

The digit-count of the seed carries no information about the output: a 2-digit
seed and a 50-digit seed both spread across the whole encyclopedia. No RNG.

## What you get

This one repository ships the tool in several forms:

| Form | For | Install |
|------|-----|---------|
| **CLI / Python package** | terminals, scripts, any Python | `pip install wiki-random` then `wiki-random <seed>` |
| **Claude Code plugin** | Claude Code users (others) | `/plugin marketplace add potncoffee/wiki-random` then `/plugin install wiki-random@wiki-random` |
| **Personal skill** | your own Claude Code | symlink `skills/wiki-random` into `~/.claude/skills/` (gives `/wiki-random`) |
| **Portable Agent Skill** | other agent frameworks | point them at `skills/wiki-random/SKILL.md` (open [agentskills.io](https://agentskills.io) format) |
| **Browser app** | anyone, zero install | open [`webui/index.html`](webui/index.html) in a browser (runs entirely client-side) |
| **Hosted web app** | a shareable URL | deploy [`webui/`](webui/) to Hugging Face Spaces (Gradio) |
| **ChatGPT / Claude.ai** | chat-app users | upload the repo (or its zip) and the assistant follows [`AI_START_HERE.md`](AI_START_HERE.md) |

See [`webui/README.md`](webui/README.md) for the web builds and an honest note on
which web UIs can and cannot run the live Wikipedia lookup. The short version:
the code sandbox inside ChatGPT and Claude.ai has no internet, but those
assistants have a *separate* web-browsing tool that does. [`AI_START_HERE.md`](AI_START_HERE.md)
tells the assistant to run the math in its sandbox and do the Wikipedia lookups
through its browser, so the chat apps work after all.

## CLI usage

```
wiki-random <seed-integer>
wiki-random --verify <seed-integer>
```

Or without installing, run the engine directly:

```
python3 wiki_random/oracle.py 1729
```

It prints a labeled block: the **constants** (modulus `m`, multipliers `a1..a3`,
increments `c1..c3`), the per-run **inputs** (Input (seed), Wiki article ID
range), the full worked **computation**, and the **result** (Wiki article ID,
title, and `?curid=` URL).

### Verifiable output

`--verify` appends a self-contained, paste-and-run Python 3 snippet that
reproduces the hash and page id from the seed and the seven constants alone,
with the expected answers inline as comments. Anyone can run it cold to confirm
the math without trusting the tool. (The final article lookup queries live
Wikipedia and is confirmed by opening the URL.) The snippet pins the ceiling
used in that run, so a shared reading stays self-consistent even though a later
run with a grown ceiling lands on a different article.

## The math

- **Modulus** `m = 2^61 - 1` (a Mersenne prime), far larger than the page-ID
  range, so the final reduction is near-uniform.
- Three rounds of `x = (x * a + c) mod m`, a linear-congruential mixing chain.
  Each multiply is a bijection mod the prime, and each `+ c` breaks the linear
  rhythm so consecutive seeds land on unrelated articles (avalanche).
- The **sieve** maps the hash into `[1, ceiling]`, where `ceiling` is the live
  maximum Wikipedia page id (fetched per run; falls back to a constant offline).
- The **walk** queries a 50-ID window centered on the target and picks the
  nearest valid main-namespace, non-redirect article (ties -> lower id),
  widening if the center is empty.

Because the ceiling grows as Wikipedia grows, a seed slowly drifts to different
articles over time. The hash about the seed is permanent; only the live range
moves. This is intended: an oracle, not a permanent lookup.

## Install the personal skill

```
ln -s "$(pwd)/skills/wiki-random" ~/.claude/skills/wiki-random
```

Then `/wiki-random` is available in Claude Code. (Other people installing via
the plugin marketplace get the namespaced `/wiki-random:wiki-random`.)

## Tests

```
pytest -q
```

All tests are offline (the network is injected via a fake), so the suite is fast
and deterministic.

## License

MIT
