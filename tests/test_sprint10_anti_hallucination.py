"""Sprint 10 — anti-hallucination. Offline, no network, no API key.

- B (detection, agent_05.detect_unsourced_claims): a numeric claim without an
  allow-listed (.gov/canada.ca) citation in the same sentence is flagged; with a
  link it is not; a stat attributed to a named source without a link is the
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


# ---------------- detection (B) ----------------

def test_unsourced_stat_is_flagged():
    r = detect("Car insurance costs vary. On average drivers pay 15% more with no history.")
    assert len(r["unsourced_stats"]) == 1
    assert not r["unbacked_attributions"]


def test_sourced_stat_is_not_flagged():
    text = ("Premiums run about $1,800 per year for new drivers, per "
            "https://www.insurance.ca.gov/01-consumers/105-type/95-guides/01-auto/.")
    r = detect(text)
    assert r["unsourced_stats"] == [] and r["unbacked_attributions"] == []


def test_unbacked_named_attribution_is_flagged():
    r = detect("According to J.D. Power, 74% of foreign drivers overpay for coverage.")
    assert len(r["unbacked_attributions"]) == 1
    assert not r["unsourced_stats"]


def test_generic_reference_without_number_is_not_flagged():
    # Precision: an authority reference with NO number must never be flagged.
    r = detect("The IRS requires most residents to file an annual tax return.")
    assert r["unsourced_stats"] == [] and r["unbacked_attributions"] == []


def test_multiple_unsourced_stats_counted():
    text = ("Rates rose 25% last year. Roughly 60% of newcomers lack a US history. "
            "Deposits can reach $500 with some insurers.")
    r = detect(text)
    assert len(r["unsourced_stats"]) == 3


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
