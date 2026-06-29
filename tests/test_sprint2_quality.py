"""
NEXUS-14 Sprint 2 regression tests.

Covers the four sprint guarantees:
  1. G3 anti-repetition gate: PASS on a clean article, FAIL on duplicated
     phrases and on near-identical sections.
  2. DRI metric: detects diffuse trigram repetition; clean text scores ~0.
  3. Writer model: agent_04 sends "claude-sonnet-4-6" by default (RCA-003)
     and remains env-overridable.
  4. Digest: _build_digest is bounded (<= cap) and is actually injected into
     the section prompt, surfacing entities AND figures (RCA-004).

All tests are deterministic and require no network / no API key.
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


g3 = _load("scripts/g3_repetition_gate.py", "g3_repetition_gate")
dri = _load("scripts/dri_metric.py", "dri_metric")
agent_04 = _load("agents/agent_04_article_writer.py", "agent_04_article_writer")


# ---------------------------------------------------------------- G3 gate

_CLEAN_ARTICLE = """---
title: "x"
---
# Title

## Opening Your First Account
Newcomers should visit a branch within their first week. Bring a passport and a
secondary document. Direct deposit lets employers pay your salary electronically.

## Building a Credit History
A strong credit score takes time. Use a secured card responsibly and pay the
balance in full each month to demonstrate reliability to lenders over time.

## Avoiding Common Fees
Monthly maintenance charges add up. Compare providers and pick a plan that waives
fees for the first year, then reassess once the promotional window closes.
"""

_DUP_ARTICLE = """---
title: "x"
---
# Title

## Section One
You must present two pieces of identification to open a basic chequing account
quickly and without unnecessary delays at any major branch location nationwide.

## Section Two
You must present two pieces of identification to open a basic chequing account
quickly and without unnecessary delays at any major branch location nationwide.
"""


def test_g3_passes_clean_article():
    res = g3.evaluate(_CLEAN_ARTICLE)
    assert res["passed"] is True
    assert res["decision"] == "PASS"
    assert res["max_pairwise_cosine"] < g3.COSINE_THRESHOLD


def test_g3_blocks_duplicate_phrases():
    res = g3.evaluate(_DUP_ARTICLE)
    assert res["passed"] is False
    assert res["decision"] == "FAIL"
    # Either the duplicate-phrase check or the cosine check (or both) must fire.
    assert res["duplicate_phrases"] or res["over_threshold_pairs"]


def test_g3_thresholds_are_frozen():
    # Calibration-frozen values must not drift.
    assert g3.COSINE_THRESHOLD == 0.80
    assert g3.MIN_DUP_WORDS == 8


# ---------------------------------------------------------------- DRI metric

def test_dri_zero_on_varied_text():
    res = dri.compute_dri(_CLEAN_ARTICLE)
    assert res["dri"] == 0
    assert res["excess_dispersion"] == 0


def test_dri_detects_diffuse_repetition():
    # Same content trigram planted in three distinct sections.
    phrase = "provincial health authority"
    md = "---\ntitle: x\n---\n# T\n"
    for i in range(3):
        md += "\n## Section %d\nRegister with the %s promptly after arrival to " \
              "secure coverage details and timelines.\n" % (i, phrase)
    res = dri.compute_dri(md)
    assert res["dri"] >= 1
    assert any("provincial health authority" in t["trigram"]
               for t in res["top_diffuse_trigrams"])


def test_dri_metric_params_default():
    assert dri.MIN_SECTIONS == 3
    assert dri.NGRAM == 3


# --------------------------------------------------------------- writer model

def test_writer_default_model_is_sonnet_4_6(monkeypatch):
    # No explicit model + no env override -> the frozen Sonnet version.
    monkeypatch.delenv("ARTICLE_WRITER_MODEL", raising=False)
    captured = {}

    async def fake_urlopen(*args, **kwargs):  # pragma: no cover - not reached
        raise AssertionError("network must not be called")

    # Inspect the source-level default rather than making a request.
    import inspect
    src = inspect.getsource(agent_04._call_claude)
    assert "claude-sonnet-4-6" in src
    assert "ARTICLE_WRITER_MODEL" in src
    # Must NOT silently fall back to haiku for the writer.
    assert "claude-haiku" not in src


def test_writer_model_env_overridable(monkeypatch):
    import inspect
    src = inspect.getsource(agent_04._call_claude)
    # The default is read from the environment variable, allowing override.
    assert 'os.getenv("ARTICLE_WRITER_MODEL"' in src


# ------------------------------------------------------------------- digest

_S1 = "## Opening an Account\nThe Financial Consumer Agency of Canada confirms " \
      "you may open an account with 2 pieces of ID within 5 business days. RBC " \
      "and Scotiabank offer free packages for 12 months."
_S2 = "## Required Documents\nA Permanent Resident Card works as primary ID. " \
      "The Financial Consumer Agency of Canada notes a SIN is optional."


def test_digest_lists_entities_and_numbers():
    d = agent_04._build_digest([_S1, _S2])
    # Entities present.
    assert "Financial Consumer Agency" in d or "RBC" in d
    # Figures present (not just titles).
    assert "5 business days" in d or "12 months" in d or "2 pieces of id" in d.lower()


def test_digest_is_bounded():
    big = "## S%d\nThe Financial Consumer Agency of Canada cited 5 business days " \
          "and 12 months at RBC, Scotiabank, and TD Bank repeatedly. "
    sections = [big % i for i in range(40)]
    d = agent_04._build_digest(sections)
    assert len(d) <= agent_04._DIGEST_MAX_TOTAL_CHARS


def test_digest_empty_when_no_sections():
    assert agent_04._build_digest([]) == ""


def test_digest_injected_into_section_prompt():
    # The section loop must build the digest from intro + prior sections and
    # append it to the section prompt.
    import inspect
    src = inspect.getsource(agent_04._write_article_standalone)
    assert "_build_digest([intro] + written_sections)" in src
    assert "digest_block" in src


# --- Sprint 2 fix-sources: official-source allow-list ----------------------

def test_url_classifier_official_and_attacks():
    c = agent_04._classify_url
    # legitimate official sources count
    assert c("https://www.irs.gov/forms") == "official"
    assert c("https://cra-arc.gc.ca/charts") == "official"
    assert c("https://fintrac-canafe.gc.ca/intel") == "official"
    assert c("https://www.canada.ca/en/services.html") == "official"
    assert c("https://canada.ca") == "official"
    # internal is never official
    assert c("https://moneyabroadguide.com/blog/irs-guide") == "internal"
    # off-list legitimate-but-not-official does not count
    assert c("https://www.rbc.com/accounts") == "offlist"
    # ATTACK / false-positive cases MUST be rejected (offlist, never official)
    assert c("https://craigslist.com") == "offlist"
    assert c("https://theirsite.com") == "offlist"
    assert c("https://irs.gov.attacker.com/phish") == "offlist"
    assert c("https://mygov.com.attacker.net") == "offlist"
    assert c("https://notgov.com") == "offlist"


def test_gate_fails_with_internal_links_but_no_official_source():
    # *** DECISIVE TEST: 4 internal links + 0 official external -> MUST FAIL ***
    tier = agent_04._get_tier_config("STANDARD")  # min_sources = 4
    article = (
        "Body. https://moneyabroadguide.com/a https://moneyabroadguide.com/b "
        "https://moneyabroadguide.com/c https://moneyabroadguide.com/d "
        "https://www.rbc.com/x"  # off-list, must not count
    )
    errors = agent_04._validate_tier_standard(article, word_count=99999, tier=tier)
    src_errs = [e for e in errors if "Official external sources" in e]
    assert src_errs, "Gate MUST flag missing official sources (0 official < 4)"
    assert "do NOT count" in src_errs[0]  # pedagogical message present


def test_gate_passes_source_check_with_four_official_sources():
    tier = agent_04._get_tier_config("STANDARD")
    article = (
        "Body. https://www.irs.gov/a https://cra-arc.gc.ca/b "
        "https://www.canada.ca/c https://fdic.gov/d "
        "https://moneyabroadguide.com/internal https://www.rbc.com/offlist"
    )
    errors = agent_04._validate_tier_standard(article, word_count=99999, tier=tier)
    assert not [e for e in errors if "Official external sources" in e], \
        "4 official sources must satisfy the source minimum"


# ---------------------------------------------------------------- Sprint 4: live-source gate
# agent_05 imports aiohttp at module top; CI does not install it, so we stub a
# minimal aiohttp before loading the module. All network is mocked: zero real I/O.
import asyncio as _asyncio
import types as _types

if "aiohttp" not in sys.modules:
    _aio = _types.ModuleType("aiohttp")
    class _ClientTimeout:
        def __init__(self, *a, **k):
            pass
    class _ClientSession:
        pass
    class _ClientError(Exception):
        pass
    _aio.ClientTimeout = _ClientTimeout
    _aio.ClientSession = _ClientSession
    _aio.ClientError = _ClientError
    sys.modules["aiohttp"] = _aio

agent_05 = _load("agents/agent_05_fact_checker.py", "agent_05_fact_checker")
_sources = _load("agents/_sources.py", "agent_sources")


class _StubSelf:
    """Minimal self for calling _build_report without constructing the agent."""
    def _generate_recommendations(self, *a, **k):
        return []


def _report(broken):
    """Build a fact-check report from a list of broken-url dicts (no network)."""
    url_results = {"live": [], "broken": list(broken), "redirected": [], "untrusted": []}
    from datetime import datetime as _dt
    return agent_05.FactCheckerAgent._build_report(
        _StubSelf(), verified=[], url_results=url_results, stats={}, start_time=_dt.now()
    )


def test_sources_module_is_single_source_of_truth():
    # agent_04's classifier is imported from the shared module (agents._sources),
    # not a local copy. In production there is exactly one agents._sources, so
    # both agents share one definition. (The test loader imports the file twice
    # under different module names, so we assert provenance + behavior, not
    # object identity.)
    assert agent_04._classify_url.__module__ == "agents._sources"
    for url, expected in [
        ("https://www.canada.ca/x", "official"),
        ("https://cra-arc.gc.ca/x", "official"),
        ("https://example.com/x", "offlist"),
        ("https://www.moneyabroadguide.com/x", "internal"),
    ]:
        assert agent_04._classify_url(url) == expected
        assert _sources.classify_url(url) == expected


def test_official_404_is_hard_fail():
    # 1. Official source with a definite HTTP error -> blocking FAIL.
    rep = _report([{"url": "https://www.canada.ca/nope", "status_code": 404, "reason": "http"}])
    assert rep["summary"]["broken_official_hard"] == 1
    assert rep["verdict"] == "FAIL"


def test_offlist_404_is_warning_not_fail():
    # 2. Off-list source 404 -> not hard, single issue -> PASS_WITH_WARNINGS.
    rep = _report([{"url": "https://somebank.com/nope", "status_code": 404, "reason": "http"}])
    assert rep["summary"]["broken_official_hard"] == 0
    assert rep["verdict"] == "PASS_WITH_WARNINGS"


def test_official_redirect_is_not_broken():
    # 3. A followed redirect ends up in 'redirected'/'live', never in 'broken'.
    url_results = {"live": [{"url": "https://www.canada.ca/x", "status_code": 200}],
                   "broken": [], "redirected": [], "untrusted": []}
    from datetime import datetime as _dt
    rep = agent_05.FactCheckerAgent._build_report(
        _StubSelf(), verified=[], url_results=url_results, stats={}, start_time=_dt.now())
    assert rep["summary"]["broken_official_hard"] == 0
    assert rep["verdict"] == "PASS"


def test_official_live_passes():
    # 5. Official source 200 and nothing else wrong -> PASS.
    rep = _report([])
    assert rep["summary"]["broken_official_hard"] == 0
    assert rep["verdict"] == "PASS"


def test_official_systematic_timeout_is_soft_warning_with_visible_log(caplog):
    # 6. Official source unreachable after retries -> soft, NOT a FAIL, but a
    #    loud 'human review needed' WARNING is emitted for the draft reviewer.
    import logging as _logging
    with caplog.at_level(_logging.WARNING):
        rep = _report([{"url": "https://www.canada.ca/ghost", "error": "timeout",
                        "trusted": False, "reason": "transport"}])
    assert rep["summary"]["broken_official_hard"] == 0
    assert rep["summary"]["broken_official_soft"] == 1
    assert rep["verdict"] != "FAIL"  # never blocks prod on transport error
    assert any("human review needed" in r.getMessage() for r in caplog.records)


def test_check_one_retries_transport_then_succeeds():
    # 4. A transient transport error on the first HEAD, then a 200 -> 'live',
    #    no broken entry (retry recovers). Fully mocked session, no real I/O.
    class _Resp:
        def __init__(self, status, url):
            self.status = status
            self.url = url
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    class _FlakySession:
        def __init__(self):
            self.calls = 0
        def head(self, url, **k):
            self.calls += 1
            if self.calls == 1:
                raise sys.modules["aiohttp"].ClientError("boom")
            return _Resp(200, url)
        def get(self, url, **k):
            return _Resp(200, url)

    fc = agent_05.FactCheckerAgent.__new__(agent_05.FactCheckerAgent)
    fc.session = _FlakySession()
    out = _asyncio.run(fc._check_urls(["https://www.canada.ca/ok"]))
    assert len(out["live"]) == 1
    assert out["broken"] == []
    assert fc.session.calls == 2  # 1 failure + 1 retry success


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
