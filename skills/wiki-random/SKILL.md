---
name: wiki-random
description: Turn a seed number into a random Wikipedia article through a deterministic, fully auditable modular-hash pipeline that shows its work on screen. Use when the user provides a "seed" number and wants a Wikipedia article, asks for a wiki-random or wiki oracle reading, or invokes /wiki-random. Can also emit a self-contained, paste-and-run proof of the math with --verify.
---

# wiki-random

Convert any integer "seed" into a real Wikipedia article. The mapping is
deterministic given the live page-ID ceiling, and every step of the arithmetic
is shown so the result is auditable, not magic.

## How it works (one sentence per stage)

1. **Reduce** the seed modulo `m = 2^61 - 1` (a Mersenne prime).
2. **Mix** through three rounds of `x = (x * a + c) mod m` (a linear-congruential
   chain) to a final hash. Input digit-count carries no information about the
   output, so a 2-digit and a 50-digit seed both spread across the whole range.
3. **Sieve** the hash into `[1, ceiling]`, where `ceiling` is Wikipedia's live
   maximum page id (fetched each run).
4. **Walk** to the nearest valid main-namespace, non-redirect article by page id
   (ties go to the lower id), widening the search window if needed.

Because the ceiling grows as Wikipedia grows, the same seed slowly drifts to
different articles over time. The hash about the seed never changes; only the
live range does. This is intended: it is an oracle, not a permanent lookup.

## Running it

The engine is `oracle.py`, sitting in this skill's own directory. It is pure
Python 3 standard library (no dependencies) and needs network access to reach
`en.wikipedia.org`.

- Plugin install:  `python3 "${CLAUDE_PLUGIN_ROOT}/skills/wiki-random/oracle.py" <seed>`
- Personal install: `python3 ~/.claude/skills/wiki-random/oracle.py <seed>`
- Add `--verify` before the seed to also print a self-contained proof snippet.

Example: `python3 ~/.claude/skills/wiki-random/oracle.py --verify 1729`

The script prints a labeled block: the constants (modulus, multipliers,
increments), the per-run inputs (Input (seed), Wiki article ID range), the full
worked computation, and the RESULT (Wiki article ID, title, URL).

## Presenting the result to the user

After running the script:

1. **Show the math.** The script already prints the labeled, worked arithmetic.
   Let it stand; do not hide it. If the user wants proof, run with `--verify` and
   point out that the printed snippet reproduces the hash and id from the seed
   and the seven constants alone (the article lookup, "the Walk", is confirmed by
   opening the `?curid=` URL).
2. **Link the article.** Always give the `https://en.wikipedia.org/?curid=<id>`
   URL from the RESULT block.
3. **Tell them what they landed on.** Fetch a short summary and give a
   who / what / where / when / why / how, and surface the genuinely odd details
   (Wikipedia logs strange facts plainly). Use the MediaWiki API, e.g.:
   `https://en.wikipedia.org/w/api.php?action=query&pageids=<id>&prop=extracts&explaintext=1&format=json`
   (add `&exintro=1` for just the lead).

## Disambiguation pages (special, richer handling)

The Walk can legitimately land on a disambiguation page (namespace 0, not a
redirect). When it does:

1. **Say plainly that it is a disambiguation page** — a signpost, not a subject.
2. **Mini-summarize each listed entry** (one line each).
3. **For each entry, give the reason it bears the name IF Wikipedia documents
   it — and explicitly say when it does not. Never invent a motive.** It is
   correct and expected to write "Wikipedia does not say" when the source is
   silent. If you offer a plausible guess, label it clearly as your inference,
   not as fact.
4. **For each "See also", give a short compare-and-contrast** against the
   headword (how is X different from the thing it points you toward?).

## Honesty rule (load-bearing)

Whenever you explain "why" something is named, classified, or connected, ground
it in what the linked Wikipedia articles actually state. When the reason is not
documented, say so rather than confabulating. This applies everywhere, not just
to disambiguation pages.

## Verifying / sharing a reading

`--verify` appends a ten-line, paste-and-run Python 3 block whose only
non-comment lines are the computation itself, with the expected `hash` and `id`
inline as comments. Anyone can run it cold to confirm the math up to the page id
without trusting this tool. The block pins the ceiling used in that run, so a
shared reading stays self-consistent even though a fresh run with a grown ceiling
would land on a different article.
