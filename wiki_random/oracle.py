"""wiki-random: turn a seed number into a Wikipedia article.

A deterministic, fully auditable pipeline:

    seed -> modular-hash (mix) -> sieve into the live page-ID range -> walk to
    the nearest real article.

Same seed plus same live ceiling always yields the same article. The only
non-deterministic input is the live ceiling (Wikipedia's current maximum page
id), which grows over time, so a seed slowly drifts to new articles. The math
itself is pure and reproducible from the seven constants below.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "wiki-random/1.0 (https://github.com/potncoffee/wiki-random)"

# --- constants (fixed forever; reproducibility depends on these) -------------
# This is a linear-congruential mixing chain over a prime field:
#   m  = modulus (a Mersenne prime, far larger than the page-ID range)
#   aN = multipliers,  cN = increments  (one pair per round)
P  = (1 << 61) - 1                  # modulus m = 2**61 - 1
A1 = 1181783497276652981            # multiplier a1
C1 = 359334085968622831            # increment  c1
A2 = 1442695040888963407            # multiplier a2
C2 = 1013904242948204167           # increment  c2
A3 = 784637716923335289             # multiplier a3
C3 = 211888927362711809            # increment  c3

FALLBACK_CEILING = 83_407_206       # used only if the live ceiling fetch fails


def mix_steps(seed):
    """Return the labeled mixing steps as (name, value) pairs."""
    x = seed % P
    steps = [("Input (seed)", seed), ("Reduced input", x)]
    x = (x * A1 + C1) % P
    steps.append(("Round 1", x))
    x = (x * A2 + C2) % P
    steps.append(("Round 2", x))
    x = (x * A3 + C3) % P
    steps.append(("Mixed value (hash)", x))
    return steps


def mix(seed):
    """Deterministically hash an integer seed into [0, P)."""
    return mix_steps(seed)[-1][1]


def mix_trace(seed):
    """Full arithmetic trace of the mix: reduction details + per-round working.

    Returns the intermediate products (pre-modulo) and post-modulo results for
    each of the three rounds, so the output can show its work.
    """
    x = seed % P
    reduction = {"seed": seed, "wraps": seed // P, "remainder": x}
    rounds = []
    for mult, add in ((A1, C1), (A2, C2), (A3, C3)):
        product = x * mult + add
        result = product % P
        rounds.append({
            "prev": x,
            "mult": mult,
            "add": add,
            "product": product,
            "result": result,
        })
        x = result
    return {"reduction": reduction, "rounds": rounds, "final": x}


def sieve(x, ceiling):
    """Reduce a hash value into the inclusive page-ID range [1, ceiling]."""
    return (x % ceiling) + 1


def _api_get(params, timeout=20):
    """The only real-HTTP touchpoint. Returns parsed JSON as a dict."""
    params = dict(params)
    params.setdefault("format", "json")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_ceiling(fetch=_api_get):
    """Live maximum page id (the newest-created page). Falls back if offline."""
    try:
        data = fetch({
            "action": "query",
            "list": "recentchanges",
            "rctype": "new",
            "rclimit": 1,
            "rcprop": "ids|timestamp",
        })
        return int(data["query"]["recentchanges"][0]["pageid"])
    except Exception:
        return FALLBACK_CEILING


class OracleResolutionError(Exception):
    pass


class NetworkUnavailableError(OracleResolutionError):
    """Raised when the live article lookup cannot reach the network.

    A subclass of OracleResolutionError so existing callers that catch the base
    class keep working. It exists as its own type so a sandbox-only run (for
    example the ChatGPT or Claude.ai code tool, which has no internet) fails
    with actionable guidance instead of a raw urllib traceback.
    """


def _query_band(lo, hi, fetch):
    """Return valid main-namespace, non-redirect page objects in [lo, hi]."""
    lo = max(1, lo)
    ids = list(range(lo, hi + 1))
    candidates = []
    for i in range(0, len(ids), 50):           # MediaWiki: max 50 pageids/request
        chunk = ids[i:i + 50]
        try:
            data = fetch({
                "action": "query",
                "prop": "info",
                "pageids": "|".join(str(c) for c in chunk),
            })
        except (urllib.error.URLError, OSError) as exc:
            # Unlike fetch_ceiling (which can fall back to a constant), the walk
            # genuinely needs the network: there is no offline substitute for
            # "which page ids are real articles". Fail with guidance instead of
            # letting a raw urllib error escape.
            raise NetworkUnavailableError(
                "Could not reach Wikipedia to resolve the article (no network "
                "access). The article lookup needs the internet. In a "
                "network-isolated sandbox such as the ChatGPT or Claude.ai code "
                "tool, do not call oracle() directly. Follow AI_START_HERE.md: "
                "compute the math in the sandbox, then do the Wikipedia lookups "
                "with the assistant's browser."
            ) from exc
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if page.get("ns") == 0 and "missing" not in page and "redirect" not in page:
                candidates.append(page)
    return candidates


def _nearest(candidates, target):
    return min(candidates, key=lambda p: (abs(p["pageid"] - target), p["pageid"]))


def walk(target, fetch=_api_get, max_widenings=6):
    """Find the nearest valid article to `target` in either direction."""
    bands = [(target - 25, target + 24)]       # centered 50-ID window
    lower_edge = target - 25
    upper_edge = target + 24
    for _ in range(max_widenings + 1):
        found = []
        for lo, hi in bands:
            found.extend(_query_band(lo, hi, fetch))
        if found:
            page = _nearest(found, target)
            pid = page["pageid"]
            return {
                "pageid": pid,
                "title": page["title"],
                "url": f"https://en.wikipedia.org/?curid={pid}",
            }
        # next outer ring: the two adjacent 50-ID bands
        new_lower = (lower_edge - 50, lower_edge - 1)
        new_upper = (upper_edge + 1, upper_edge + 50)
        bands = [new_lower, new_upper]
        lower_edge -= 50
        upper_edge += 50
    raise OracleResolutionError(f"No article found near page id {target}")


def oracle(seed, fetch=_api_get):
    """Full reading: seed -> ceiling -> sieve -> walk -> article."""
    ceiling = fetch_ceiling(fetch)
    steps = mix_steps(seed)
    sieved_id = sieve(steps[-1][1], ceiling)
    article = walk(sieved_id, fetch)
    return {
        "seed": seed,
        "ceiling": ceiling,
        "steps": steps,
        "trace": mix_trace(seed),
        "sieved_id": sieved_id,
        "article": article,
    }


def format_ritual(result):
    a = result["article"]
    seed = result["seed"]
    ceiling = result["ceiling"]
    target = result["sieved_id"]
    width = 64
    bar = "=" * width
    L = [
        bar,
        "  WIKI-RANDOM",
        bar,
        "",
        "  CONSTANTS  (identical every run)",
        f"  Modulus      m  = {P:,}   (2^61 - 1, a Mersenne prime)",
        f"  Multiplier   a1 = {A1:,}",
        f"  Increment    c1 = {C1:,}",
        f"  Multiplier   a2 = {A2:,}",
        f"  Increment    c2 = {C2:,}",
        f"  Multiplier   a3 = {A3:,}",
        f"  Increment    c3 = {C3:,}",
        "",
        "  INPUTS  (this run)",
        f"  Input (seed)                  = {seed:,}",
        f"  Wiki article ID range (live)  = {ceiling:,}",
        "",
        "  COMPUTATION",
    ]
    trace = result.get("trace")
    if trace:
        r = trace["reduction"]
        L.append("  Reduce input into the field:  input mod m")
        L.append(f"      = {r['wraps']:,} whole wraps, remainder {r['remainder']:,}")
        syms = (("a1", "c1"), ("a2", "c2"), ("a3", "c3"))
        for i, rd in enumerate(trace["rounds"], start=1):
            am, cm = syms[i - 1]
            L.append(f"  Round {i}:  (previous * {am} + {cm}) mod m")
            L.append(f"      ({rd['prev']:,} * {rd['mult']:,} + {rd['add']:,})")
            L.append(f"      = {rd['product']:,}")
            L.append(f"      mod m = {rd['result']:,}")
        L.append(f"  Mixed value (hash)            = {trace['final']:,}")
    else:
        L.append(f"  Mixed value (hash)            = {result['steps'][-1][1]:,}")
    L.append("  Map hash into the ID range:  (hash mod range) + 1")
    L.append(f"      = {target:,}   (target Wiki article ID)")
    L.append(f"  Nearest live article to target  = {a['pageid']:,}   "
             f"(distance {abs(a['pageid'] - target)})")
    L += [
        "",
        "  RESULT",
        f"  Wiki article ID : {a['pageid']:,}",
        f"  Article         : {a['title']}",
        f"  URL             : {a['url']}",
        "",
        f"  Input {seed:,}  ->  Wiki article #{a['pageid']:,}",
        bar,
    ]
    return "\n".join(L)


def format_verify(result):
    """A self-contained, paste-and-run proof of the math up to the page id.

    The returned text is valid Python 3: the only non-comment lines are the
    computation itself, and the expected answers are inline as comments. Run it
    anywhere to confirm the hash and id independently of this tool.
    """
    seed = result["seed"]
    ceiling = result["ceiling"]
    expected_hash = result["steps"][-1][1]
    expected_id = result["sieved_id"]
    return "\n".join([
        "# -- verify: paste into any Python 3 --",
        "P = 2**61 - 1",
        f"A = [{A1}, {A2}, {A3}]",
        f"C = [{C1}, {C2}, {C3}]",
        f"x = {seed} % P",
        "for a, c in zip(A, C): x = (x*a + c) % P",
        "print('hash =', x)",
        f"print('id   =', (x % {ceiling}) + 1)",
        f"# expected -> hash = {expected_hash}",
        f"# expected -> id   = {expected_id}",
    ])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    verify = "--verify" in argv
    args = [a for a in argv if a != "--verify"]
    if not args:
        print("usage: wiki-random [--verify] <seed-integer>")
        return 1
    try:
        seed = int(args[0])
    except ValueError:
        print(f"seed must be an integer, got {args[0]!r}")
        return 1
    try:
        result = oracle(seed)
    except OracleResolutionError as exc:
        print(exc)
        return 1
    print(format_ritual(result))
    if verify:
        print(format_verify(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
