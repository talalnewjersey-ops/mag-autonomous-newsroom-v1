"""Sprint 10 — anti-hallucination. Offline, no network, no API key.

- B (detection, agent_05.detect_unsourced_claims): a numeric claim not COVERED by
  an engraved Couche 1 STABLE fact of the given vertical is flagged (LEVIER C,
  2026-07-05: a nearby allow-listed link is no longer sufficient by itself --
  the number must match that fact's exact engraved value, agents/_fact_coverage.py);
  a stat attributed to a named source without a covering fact is the
  higher-severity `unbacked_attribution`; a sentence with NO number is never
  flagged (precision -> no false positives).
- Barème (agent_12.hallucination_penalty): -8 per unsourced stat, -15 per
  unbacked attribution, capped at 40. Two documented behaviours the user asked
  for: a SINGLE unsourced stat drops a form-clean 90 to 82 (< 85 -> recalibrated,
  zero tolerance on YMYL); a MASSIVE mix (5 stats + 1 attribution) stays below 85
  despite the cap. Plus the anti-false-positive: all-sourced -> 0 penalty -> pass.
"""
import importlib.util
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub(name, **attrs):
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m


if "aiohttp" not in sys.modules:
    aio = types.ModuleType("aiohttp")
    aio.ClientTimeout = lambda *a, **k: None
    aio.ClientSession = object
    aio.ClientError = Exception
    sys.modules["aiohttp"] = aio
_stub("services.llm_service", LLMService=object)
_stub("services.storage_service", StorageService=object)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_05 = _load("agents/agent_05_fact_checker.py", "agent_05_s10")
agent_12 = _load("agents/agent_12_quality_assurance.py", "agent_12_s10")
detect = agent_05.detect_unsourced_claims
penalty = agent_12.hallucination_penalty

PASS_GATE = 85
V = "us_auto"
# Real us_auto STABLE fact (agents/_vertical_facts.py): Texas minimum liability.
TX_URL = "https://www.tdi.texas.gov/pubs/consumer/cb020.html"


# ---------------- detection (B) ----------------

def test_unsourced_stat_is_flagged():
    r = detect("Car insurance costs vary. On average drivers pay 15% more with no history.", V)
    assert len(r["unsourced_stats"]) == 1
    assert not r["unbacked_attributions"]


def test_sourced_stat_is_not_flagged():
    # $30,000 is the TX fact's engraved bodily-injury-per-person value, cited at
    # its REAL source_url -- genuinely covered, not flagged.
    text = f"Texas requires $30,000 of bodily-injury coverage per person ({TX_URL})."
    r = detect(text, V)
    assert r["unsourced_stats"] == [] and r["unbacked_attributions"] == []


def test_generic_official_link_no_longer_shelters_an_uncovered_number():
    # LEVIER C: a real, live .gov link is NOT enough on its own -- $1,800 matches
    # no engraved us_auto fact, so it IS flagged despite the official citation.
    # ("per" before the URL is itself an attribution cue -> higher-severity bucket.)
    text = ("Premiums run about $1,800 per year for new drivers, per "
            "https://www.insurance.ca.gov/01-consumers/105-type/95-guides/01-auto/.")
    r = detect(text, V)
    assert len(r["unsourced_stats"]) + len(r["unbacked_attributions"]) == 1


def test_unbacked_named_attribution_is_flagged():
    r = detect("According to J.D. Power, 74% of foreign drivers overpay for coverage.", V)
    assert len(r["unbacked_attributions"]) == 1
    assert not r["unsourced_stats"]


def test_generic_reference_without_number_is_not_flagged():
    # Precision: an authority reference with NO number must never be flagged.
    r = detect("The IRS requires most residents to file an annual tax return.", V)
    assert r["unsourced_stats"] == [] and r["unbacked_attributions"] == []


def test_multiple_unsourced_stats_counted():
    text = ("Rates rose 25% last year. Roughly 60% of newcomers lack a US history. "
            "Deposits can reach $500 with some insurers.")
    r = detect(text, V)
    assert len(r["unsourced_stats"]) == 3


# ---------------- LEVIER C: proximity-false-sourced (the "under 10%" incident) ----------------
# Real incident, run 28731153809: the writer kept "under 10%" because the CFPB
# en-318 link (which supports the engraved 30% utilization rule) sat nearby.

CFPB_UTIL = "https://www.consumerfinance.gov/ask-cfpb/how-do-i-get-and-keep-a-good-credit-score-en-318/"


def test_covered_number_next_to_its_real_fact_link_is_not_flagged():
    text = (f"Experts advise keeping your credit use to no more than 30% of your "
            f"total credit limit ([CFPB]({CFPB_UTIL})).")
    r = detect(text, "us_credit")
    assert r["unsourced_stats"] == [] and r["unbacked_attributions"] == []


def test_uncovered_number_next_to_the_SAME_real_link_is_flagged():
    # The exact real-run bug: a different, fabricated figure sits near the same
    # genuine CFPB link that supports 30% -- the link's presence must not launder it.
    text = (f"Experts advise keeping your credit use to no more than 30% of your "
            f"total credit limit ([CFPB]({CFPB_UTIL})). Some advisors even recommend "
            f"staying under 10% for an excellent score.")
    r = detect(text, "us_credit")
    assert len(r["unsourced_stats"]) == 1
    assert "10%" in r["unsourced_stats"][0]


# ---------------- LEVIER C: qualitative-fact guard ----------------
# usa.gov/credit-score engraves the 5 FICO-report factors with NO percentage/
# ranking (PR #44). A number sitting next to that link is never covered by it.

USAGOV_FACTORS = "https://www.usa.gov/credit-score"


def test_qualitative_fact_cited_with_no_number_is_untouched():
    text = (f"Your credit score is shaped by five factors, including payment history "
            f"and length of credit history ([USA.gov]({USAGOV_FACTORS})).")
    r = detect(text, "us_credit")
    assert r["unsourced_stats"] == [] and r["unbacked_attributions"] == []


def test_number_next_to_a_qualitative_facts_link_is_flagged():
    # The FICO-weighting fabrication pattern (memory: draft 48438) -- a fabricated
    # percentage sits beside the "5 factors, no %" fact's own link. Must NOT be
    # laundered by that link: the fact's tokens are empty, so it cannot cover it.
    text = (f"Payment history represents 35% of your score, according to "
            f"[USA.gov]({USAGOV_FACTORS}).")
    r = detect(text, "us_credit")
    assert len(r["unbacked_attributions"]) == 1 or len(r["unsourced_stats"]) == 1


# ---------------- barème (QA penalty) ----------------

def test_penalty_single_unsourced_stat_is_8():
    assert penalty(1, 0) == 8


def test_attribution_is_penalised_more_than_a_bare_stat():
    assert penalty(0, 1) == 15 > penalty(1, 0) == 8


def test_penalty_is_capped_at_40():
    assert penalty(5, 1) == 40           # 40 + 15 -> capped
    assert penalty(100, 100) == 40


def test_single_stat_drops_form_clean_article_below_gate():
    # Documented zero-tolerance behaviour: a form-perfect 90 minus one -8 = 82 < 85.
    assert 90 - penalty(1, 0) == 82
    assert (90 - penalty(1, 0)) < PASS_GATE


def test_massive_hallucination_below_gate_despite_cap():
    # Even a form-perfect 100 minus the -40 cap = 60, well under 85.
    assert (100 - penalty(5, 1)) == 60
    assert (100 - penalty(5, 1)) < PASS_GATE


def test_all_sourced_article_has_no_penalty_and_passes():
    # Anti-false-positive: no hallucination -> 0 penalty -> a >=85 article still passes.
    assert penalty(0, 0) == 0
    assert (90 - penalty(0, 0)) >= PASS_GATE
