# AI, start here — running wiki-random inside ChatGPT or Claude.ai

You are a chat assistant (ChatGPT or Claude.ai) and a human has just handed you
this project. They want a **wiki-random reading**: give them a seed number, and
you turn it into a real Wikipedia article, showing all the math.

Read this whole file first. It tells you exactly how to run the tool here, where
the normal "just run the script" approach does **not** work, and how to present
the result.

## The one thing that will trip you up

Do **not** simply run `oracle(seed)` from `wiki_random/oracle.py`. In your code
sandbox it will crash. Your code sandbox has **no internet**, so the two network
steps inside `oracle()` fail:

- `fetch_ceiling()` silently falls back to a stale hardcoded number, and
- `walk()` raises `OracleResolutionError` because it cannot query Wikipedia.

You get the internet from a **different tool**: your own web browsing / web
search capability, which is separate from the code sandbox. So the job is split
across your two tools. The math runs in the sandbox; the lookups run through your
browser.

## The pipeline, split across your two tools

Run these four steps in order. Steps 1 and 3 use your **browsing** tool. Steps 2
and 4 use your **code** tool (the files in this repo are pure Python 3 standard
library, no installs needed).

### Step 1 — Browser: get the live ceiling

Fetch this URL with your browsing tool and read the newest page id:

```
https://en.wikipedia.org/w/api.php?action=query&list=recentchanges&rctype=new&rclimit=1&rcprop=ids|timestamp&format=json
```

The ceiling is `query.recentchanges[0].pageid`. Call it `ceiling`. (If your
browser genuinely cannot fetch it, and only then, fall back to the
`FALLBACK_CEILING` constant in `wiki_random/oracle.py`, and tell the user you
used a stale ceiling.)

### Step 2 — Code: compute the target page id (pure math, no network)

In your code tool, reuse the canonical functions so the math is identical to the
CLI:

```python
from wiki_random.oracle import mix_steps, mix_trace, sieve

seed = 1729                       # the user's seed, as an int
ceiling = 83414683                # from Step 1

steps = mix_steps(seed)           # labeled (name, value) pairs
trace = mix_trace(seed)           # full worked arithmetic, for showing your work
hash_value = steps[-1][1]
target_id = sieve(hash_value, ceiling)   # (hash % ceiling) + 1
print(target_id)
```

`target_id` is the ideal landing spot. The next step finds the nearest real
article to it.

### Step 3 — Browser: walk to the nearest real article

Real page ids have gaps (deleted pages, redirects, non-article namespaces), so
`target_id` itself may not be a valid article. Reproduce the "walk" by hand with
your browsing tool:

1. Query a 50-id window centered on the target, `[target_id - 25, target_id + 24]`.
   The API takes up to 50 page ids per request:

   ```
   https://en.wikipedia.org/w/api.php?action=query&prop=info&pageids=ID1|ID2|...&format=json
   ```

2. From `query.pages`, keep only pages that are **all** of: `ns == 0` (main
   article namespace), have no `missing` key, and have no `redirect` key.
3. Among the survivors, pick the one **nearest** to `target_id`. On a tie, pick
   the **lower** page id. That is your article.
4. If the window is empty, widen: query the next ring out on each side,
   `[lower_edge - 50, lower_edge - 1]` and `[upper_edge + 1, upper_edge + 50]`,
   moving the edges by 50 each time. Repeat up to ~6 times.

Record the winning page's `pageid` and `title`. Its URL is
`https://en.wikipedia.org/?curid=<pageid>`.

### Step 4 — Code: render the exact labeled output

Hand the pieces back to the canonical formatter so the on-screen math looks
exactly like the CLI's. `format_ritual` does no network; it only formats the dict
you give it:

```python
from wiki_random.oracle import format_ritual, format_verify

result = {
    "seed": seed,
    "ceiling": ceiling,
    "steps": steps,
    "trace": trace,
    "sieved_id": target_id,
    "article": {
        "pageid": 1234567,
        "title": "The article title from Step 3",
        "url": "https://en.wikipedia.org/?curid=1234567",
    },
}
print(format_ritual(result))
print(format_verify(result))   # optional paste-and-run proof of the math
```

Show that printed block to the user. It is the labeled, auditable arithmetic:
the constants, the inputs, the worked computation, and the result.

## Presenting the result

After you show the math block:

1. **Show the math, do not hide it.** The `format_ritual` block is the point. If
   the user wants proof, the `format_verify` block is ten lines of paste-and-run
   Python that reproduces the hash and id from the seed and the seven constants
   alone.
2. **Link the article.** Always give the `https://en.wikipedia.org/?curid=<id>`
   URL.
3. **Tell them what they landed on.** Fetch a short summary with your browser and
   give a who / what / where / when / why / how, and surface the genuinely odd
   details. Use:

   ```
   https://en.wikipedia.org/w/api.php?action=query&pageids=<id>&prop=extracts&exintro=1&explaintext=1&format=json
   ```

## Disambiguation pages (richer handling)

The walk can land on a disambiguation page (it is namespace 0 and not a
redirect, so it passes the filter). You can confirm it is one by adding
`&prop=pageprops&ppprop=disambiguation` to an info query: a disambiguation page
carries a `pageprops.disambiguation` marker. When you land on one:

1. **Say plainly that it is a disambiguation page** — a signpost, not a subject.
2. **Mini-summarize each listed entry**, one line each.
3. **For each entry, give the reason it bears the name only if Wikipedia
   documents it, and say so explicitly when it does not. Never invent a motive.**
   Writing "Wikipedia does not say" is correct and expected. If you offer a
   plausible guess, label it clearly as your inference, not as fact.
4. **For each "See also", give a short compare and contrast** against the
   headword.

## Honesty rule (load-bearing)

Whenever you explain why something is named, classified, or connected, ground it
in what the linked Wikipedia articles actually state. When the reason is not
documented, say so rather than confabulating. This holds everywhere, not just on
disambiguation pages.

## Why the seed's length does not matter

The seed is reduced modulo `m = 2^61 - 1` (a Mersenne prime) and pushed through
three rounds of `x = (x * a + c) mod m`. A 2-digit seed and a 50-digit seed both
spread across the whole encyclopedia, because the digit count is washed out by
the first reduction. No random number generator is involved: same seed plus same
ceiling always yields the same article. The ceiling grows as Wikipedia grows, so
a seed slowly drifts to new articles over time. That drift is intentional. This
is an oracle, not a permanent lookup.
