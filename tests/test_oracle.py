from wiki_random import oracle


# --- mix (pure modular hash) ------------------------------------------------

def test_mix_is_deterministic():
    assert oracle.mix(12345) == oracle.mix(12345)


def test_mix_is_in_range():
    for s in [0, 1, 2, 99, 100000000, -7]:
        assert 0 <= oracle.mix(s) < oracle.P


def test_mix_is_injective_on_small_range():
    # mix is a composition of bijections mod the prime P, so distinct
    # inputs must give distinct outputs.
    values = {oracle.mix(s) for s in range(1000)}
    assert len(values) == 1000


def test_mix_handles_zero_and_negative():
    assert isinstance(oracle.mix(0), int)
    assert isinstance(oracle.mix(-123456789), int)


def test_mix_steps_last_equals_mix():
    steps = oracle.mix_steps(777)
    assert steps[-1][1] == oracle.mix(777)
    assert all(isinstance(n, str) and isinstance(v, int) for n, v in steps)
    assert steps[0][0] == "Input (seed)"


# --- sieve ------------------------------------------------------------------

def test_sieve_lower_bound():
    assert oracle.sieve(0, 100) == 1


def test_sieve_upper_bound():
    assert oracle.sieve(99, 100) == 100


def test_sieve_wraps():
    assert oracle.sieve(100, 100) == 1


def test_sieve_always_in_range():
    ceiling = 83_407_206
    for s in [0, 1, 42, 999999, 100000000, -55]:
        sid = oracle.sieve(oracle.mix(s), ceiling)
        assert 1 <= sid <= ceiling


# --- the two behaviours that matter -----------------------------------------

TEST_CEILING = 83_407_206


def _ids(seeds):
    return [oracle.sieve(oracle.mix(s), TEST_CEILING) for s in seeds]


def test_digit_count_independence():
    two_digit = _ids(range(10, 100))
    nine_digit = _ids(range(100_000_000, 100_000_090))

    def deciles(ids):
        return {min(9, (v - 1) * 10 // TEST_CEILING) for v in ids}

    assert len(deciles(two_digit)) >= 6
    assert len(deciles(nine_digit)) >= 6

    mean_two = sum(two_digit) / len(two_digit)
    mean_nine = sum(nine_digit) / len(nine_digit)
    assert abs(mean_two - mean_nine) < 0.20 * TEST_CEILING


def test_avalanche_consecutive_seeds_are_unrelated():
    ids = _ids(range(1, 2001))
    gaps = [abs(ids[i + 1] - ids[i]) for i in range(len(ids) - 1)]
    mean_gap = sum(gaps) / len(gaps)
    assert mean_gap > 0.20 * TEST_CEILING
    near = sum(1 for g in gaps if g < TEST_CEILING / 1000)
    assert near / len(gaps) < 0.05


# --- fetch_ceiling (injectable network) -------------------------------------

def test_fetch_ceiling_reads_newest_pageid():
    def fake_fetch(params):
        assert params["list"] == "recentchanges"
        return {"query": {"recentchanges": [{"pageid": 83_407_206}]}}

    assert oracle.fetch_ceiling(fetch=fake_fetch) == 83_407_206


def test_fetch_ceiling_falls_back_on_error():
    def boom(params):
        raise RuntimeError("network down")

    assert oracle.fetch_ceiling(fetch=boom) == oracle.FALLBACK_CEILING


def test_fetch_ceiling_falls_back_on_bad_shape():
    def weird(params):
        return {"unexpected": True}

    assert oracle.fetch_ceiling(fetch=weird) == oracle.FALLBACK_CEILING


# --- walk (the resolver) ----------------------------------------------------

class FakeWiki:
    """Serves prop=info pageids requests from a fixed {pageid: page} map."""

    def __init__(self, pages):
        self.pages = pages

    def __call__(self, params):
        ids = [int(x) for x in params["pageids"].split("|")]
        out = {}
        for pid in ids:
            if pid in self.pages:
                out[str(pid)] = dict(self.pages[pid], pageid=pid)
            else:
                out[str(pid)] = {"pageid": pid, "ns": 0, "missing": ""}
        return {"query": {"pages": out}}


def test_walk_returns_nearest_valid_article():
    target = 1000
    pages = {
        995: {"ns": 0, "title": "Far Left"},
        1003: {"ns": 0, "title": "Closest Right"},
        1000: {"ns": 1, "title": "Talk:Not An Article"},
        1001: {"ns": 0, "title": "Redirect Page", "redirect": ""},
    }
    result = oracle.walk(target, fetch=FakeWiki(pages))
    assert result["title"] == "Closest Right"
    assert result["pageid"] == 1003
    assert result["url"] == "https://en.wikipedia.org/?curid=1003"


def test_walk_tie_breaks_toward_lower_id():
    target = 1000
    pages = {
        998: {"ns": 0, "title": "Lower"},
        1002: {"ns": 0, "title": "Higher"},
    }
    result = oracle.walk(target, fetch=FakeWiki(pages))
    assert result["pageid"] == 998


def test_walk_widens_when_center_is_empty():
    target = 5000
    pages = {5060: {"ns": 0, "title": "Found After Widening"}}
    result = oracle.walk(target, fetch=FakeWiki(pages))
    assert result["pageid"] == 5060
    assert result["title"] == "Found After Widening"


def test_walk_raises_when_exhausted():
    import pytest
    with pytest.raises(oracle.OracleResolutionError):
        oracle.walk(5000, fetch=FakeWiki({}), max_widenings=1)


# --- oracle orchestration ---------------------------------------------------

def test_oracle_end_to_end_with_mock():
    def fake_fetch(params):
        if params.get("list") == "recentchanges":
            return {"query": {"recentchanges": [{"pageid": 1000}]}}
        return FakeWiki({1: {"ns": 0, "title": "An Article"}})(params)

    result = oracle.oracle(7, fetch=fake_fetch)
    assert result["ceiling"] == 1000
    assert 1 <= result["sieved_id"] <= 1000
    assert result["article"]["title"] == "An Article"
    assert result["seed"] == 7
    assert result["steps"][0] == ("Input (seed)", 7)


# --- mix_trace --------------------------------------------------------------

def test_mix_trace_matches_mix():
    trace = oracle.mix_trace(12345)
    assert trace["final"] == oracle.mix(12345)
    assert trace["reduction"]["remainder"] == 12345 % oracle.P
    assert len(trace["rounds"]) == 3
    for rd in trace["rounds"]:
        assert rd["prev"] * rd["mult"] + rd["add"] == rd["product"]
        assert rd["product"] % oracle.P == rd["result"]
    assert trace["rounds"][1]["prev"] == trace["rounds"][0]["result"]
    assert trace["rounds"][2]["prev"] == trace["rounds"][1]["result"]


# --- presentation -----------------------------------------------------------

def test_format_ritual_labels_numbers_and_links():
    result = {
        "seed": 7,
        "ceiling": 1000,
        "steps": oracle.mix_steps(7),
        "trace": oracle.mix_trace(7),
        "sieved_id": 42,
        "article": {"pageid": 1, "title": "An Article",
                     "url": "https://en.wikipedia.org/?curid=1"},
    }
    text = oracle.format_ritual(result)
    assert "Modulus" in text
    assert "Multiplier" in text
    assert "Increment" in text
    assert "Input (seed)" in text
    assert "Wiki article ID range (live)" in text
    assert "Wiki article ID" in text
    assert "An Article" in text
    assert "https://en.wikipedia.org/?curid=1" in text
    assert "1,000" in text


def test_format_ritual_shows_computation_when_trace_present():
    result = {
        "seed": 7,
        "ceiling": 1000,
        "steps": oracle.mix_steps(7),
        "trace": oracle.mix_trace(7),
        "sieved_id": 42,
        "article": {"pageid": 1, "title": "An Article",
                     "url": "https://en.wikipedia.org/?curid=1"},
    }
    text = oracle.format_ritual(result)
    assert "COMPUTATION" in text
    assert "mod m" in text
    product = oracle.mix_trace(7)["rounds"][0]["product"]
    assert f"{product:,}" in text


def test_format_ritual_shows_input_at_top_and_tied_to_article():
    result = {
        "seed": 123456789,
        "ceiling": 1000,
        "steps": oracle.mix_steps(123456789),
        "trace": oracle.mix_trace(123456789),
        "sieved_id": 42,
        "article": {"pageid": 5, "title": "An Article",
                     "url": "https://en.wikipedia.org/?curid=5"},
    }
    text = oracle.format_ritual(result)
    assert "Input (seed)                  = 123,456,789" in text
    assert "Input 123,456,789  ->  Wiki article #5" in text


def test_format_verify_snippet_runs_and_matches():
    res = {
        "seed": 7,
        "ceiling": 1000,
        "steps": oracle.mix_steps(7),
        "sieved_id": oracle.sieve(oracle.mix(7), 1000),
        "article": {"pageid": 1, "title": "x", "url": "u"},
    }
    snippet = oracle.format_verify(res)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(snippet, {})
    out = buf.getvalue()
    assert f"hash = {oracle.mix(7)}" in out
    assert f"id   = {oracle.sieve(oracle.mix(7), 1000)}" in out


def test_main_verify_flag_appends_snippet(capsys, monkeypatch):
    fake = {
        "seed": 7,
        "ceiling": 1000,
        "steps": oracle.mix_steps(7),
        "sieved_id": 42,
        "article": {"pageid": 1, "title": "An Article",
                     "url": "https://en.wikipedia.org/?curid=1"},
    }
    monkeypatch.setattr(oracle, "oracle", lambda seed: fake)
    code = oracle.main(["--verify", "7"])
    out = capsys.readouterr().out
    assert code == 0
    assert "verify" in out
    assert "P = 2**61 - 1" in out


def test_main_rejects_non_integer(capsys):
    code = oracle.main(["banana"])
    assert code == 1
    assert "integer" in capsys.readouterr().out.lower()


def test_main_requires_an_argument(capsys):
    code = oracle.main([])
    assert code == 1
    assert "usage" in capsys.readouterr().out.lower()
