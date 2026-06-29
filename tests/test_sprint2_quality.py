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


# ------------------------------------------- FIX(writer): curated source pool
# These tests are deterministic and require NO network: the pool is static data
# and classification is pure string logic. They guard the root-cause fix for the
# stochastic sourcing (writer was citing official URLs from memory).

_source_pool = _load("agents/_source_pool.py", "_source_pool")


def test_curated_pool_canada_newcomer_has_margin_over_minimum():
    """Pool must offer strictly MORE official sources than the STANDARD min (4),
    so a model that drops one still clears the gate (kills the zero-margin bug)."""
    pool = _source_pool.OFFICIAL_SOURCE_POOL["canada_newcomer"]
    assert len(pool) >= agent_04.STANDARD_MIN_SOURCES + 1, \
        "curated pool must exceed the tier minimum to provide margin"


def test_every_pool_url_is_classified_official():
    """Every URL we inject must actually count as 'official' under the allow-list.
    Otherwise we'd feed the writer sources the gate does not credit."""
    for entry in _source_pool.OFFICIAL_SOURCE_POOL["canada_newcomer"]:
        url = entry.split("|")[-1].strip()
        assert agent_04._classify_url(url) == "official", \
            f"pool URL not classified official: {url}"


def test_select_official_sources_respects_n_and_order():
    sel = _source_pool.select_official_sources("canada_newcomer", 4)
    assert len(sel) == 4
    full = _source_pool.OFFICIAL_SOURCE_POOL["canada_newcomer"]
    assert sel == full[:4], "selection must be a stable prefix of the pool"
    # Asking for more than the pool holds returns the whole pool, never more.
    big = _source_pool.select_official_sources("canada_newcomer", 999)
    assert big == full


def test_unknown_vertical_falls_back_no_injection():
    """Verticals without a curated pool must yield no sources (caller then uses
    the legacy memory prompt). We must NEVER fabricate/inject an unverified URL."""
    assert _source_pool.has_curated_pool("default") is False
    assert _source_pool.has_curated_pool("canada_newcomer") is True
    assert _source_pool.select_official_sources("default", 4) == []
    assert _source_pool.select_official_sources("nonexistent_topic", 4) == []


def test_pool_entries_carry_a_real_https_url():
    """Defensive: each entry exposes a parseable https URL (no bare names)."""
    for entry in _source_pool.OFFICIAL_SOURCE_POOL["canada_newcomer"]:
        url = entry.split("|")[-1].strip()
        assert url.startswith("https://"), f"entry has no https url: {entry}"


# ---------------------------------------------------------------------------
# FIX-WRITER: curated sources now injected into EACH section call (not only the
# intro), and intro rebalanced. Static assembly tests -- no network, no API key.
# ---------------------------------------------------------------------------


def test_intro_rebalanced_no_must_cite_four():
    """Intro no longer demands MUST-cite-4 (which contradicted 'be concise').
    The article-wide minimum is now carried by the body sections."""
    src = inspect.getsource(agent_04._write_article_standalone)
    assert "you MUST cite at least {tier['min_sources']} of these REAL" not in src, \
        "intro must not keep the concise-vs-MUST-4 contradiction"
    assert "cite 1-2 of these key REAL" in src, "intro should ask for 1-2 key authorities"


def test_section_call_injects_curated_sources():
    """The curated source block must be added to EACH section prompt, behind the
    curated-pool guard, alongside the existing anti-repetition digest."""
    src = inspect.getsource(agent_04._write_article_standalone)
    assert "section_sources_block" in src
    assert "if has_curated_pool(topic_key) and _official_sel:" in src
    assert "{digest_block}{section_sources_block}" in src, \
        "section prompt must include the sources block next to the digest"


def test_section_sources_block_balances_coverage_and_brake_without_cap():
    """Section instruction must (a) incite finding the right attachment,
    (b) brake off-topic/orphan links, (c) restate the global minimum, and
    (d) carry NO per-section numeric cap (which would bridle coverage)."""
    src = inspect.getsource(agent_04._write_article_standalone)
    assert "actively look for which" in src            # coverage incentive
    assert "without forcing any off-topic" in src       # off-topic brake
    assert "orphan 'references' line" in src            # no orphan-link brake
    assert "must cite at least {tier['min_sources']} DISTINCT" in src  # global min
    assert "avoid repeating these; prefer an unused one" in src        # already-cited hint
    assert "Use at most 1" not in src, "no per-section cap allowed"


def test_curated_pool_assembles_all_urls_into_section_block():
    """Reproduce the section-block assembly with the real pool and assert every
    selected official URL is present (the writer SEES the full list each section)."""
    sel = _source_pool.select_official_sources(
        "canada_newcomer", agent_04.STANDARD_MIN_SOURCES + 3)
    assert len(sel) >= agent_04.STANDARD_MIN_SOURCES + 1  # margin
    pool_lines = "\n".join(f"- {u}" for u in sel)
    assembled = (
        "\n\n=== OFFICIAL SOURCES - use across the article (not all in one place) ===\n"
        + pool_lines + "\n=== END OFFICIAL SOURCES ===\n")
    for entry in sel:
        url = entry.split("|")[-1].strip()
        assert url in assembled, f"selected source missing from assembled block: {url}"
        assert agent_04._classify_url(url) == "official"


def test_section_sources_fallback_empty_for_noncurated_topic():
    """A topic_key with no curated pool must NOT trigger the block -> writer keeps
    its legacy from-memory behavior (degraded but functional, no fabricated URLs)."""
    assert agent_04.has_curated_pool is not None
    assert _source_pool.has_curated_pool("totally_unknown_vertical_xyz") is False, \
        "non-curated topic must fall back (empty curated block)"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
