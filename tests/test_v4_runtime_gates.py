"""
NEXUS-14 V4 - tests/test_v4_runtime_gates.py

Offline validation of the RUNTIME gates (Agent 22 performance / Agent 23
competitor) and their end-to-end integration with the authoritative Quality
Gate. These tests exercise the REAL agent logic against synthetic in-memory
fixtures: a synthetic Lighthouse JSON object and a synthetic competitor corpus.

They NEVER run Lighthouse against a live URL and NEVER call SERPAPI; the live
acquisition paths (run_lighthouse / fetch_competitors) remain documented runtime
integration points. No network / WordPress / OpenAI calls are made.

Key behaviours asserted:
  * Agent 22: good metrics -> PASS, bad metrics -> FAIL, no measurement -> PENDING
  * Agent 23: strong article -> PASS, weak info-gain -> FAIL, no corpus -> PENDING
  * Quality Gate: a clean article + PASS runtime reports -> READY_TO_PUBLISH
    (the runtime gates are the ONLY thing standing between clean + publishable)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("EMBEDDINGS_PROVIDER", "hashing")

from agents.agent_22_performance import run_performance_check, evaluate, parse_lighthouse
from agents.agent_23_competitor import run_competitor_check
import scripts.quality_gate_v4 as qg
from scripts.validate_v4_pipeline import CLEAN_ARTICLE, CLEAN_META, CLEAN_RENDERED


# --------------------------------------------------------------------------- #
# Synthetic Lighthouse JSON (shape matches what parse_lighthouse expects).      #
# --------------------------------------------------------------------------- #
def _lighthouse(seo, perf, a11y, bp, cls):
    return {
        "categories": {
            "seo": {"score": seo / 100.0},
            "performance": {"score": perf / 100.0},
            "accessibility": {"score": a11y / 100.0},
            "best-practices": {"score": bp / 100.0},
        },
        "audits": {
            "cumulative-layout-shift": {"numericValue": cls},
            "largest-contentful-paint": {"numericValue": 1800},
            "interaction-to-next-paint": {"numericValue": 120},
            "total-blocking-time": {"numericValue": 90},
            "speed-index": {"numericValue": 2200},
        },
    }


GOOD_LH = _lighthouse(98, 95, 98, 97, 0.03)
BAD_LH = _lighthouse(80, 60, 90, 90, 0.30)


# --------------------------------------------------------------------------- #
# Agent 22 - performance                                                        #
# --------------------------------------------------------------------------- #
def test_perf_parse_lighthouse_extracts_scores():
    m = parse_lighthouse(GOOD_LH)
    assert m["seo"] == 98
    assert m["performance"] == 95
    assert m["accessibility"] == 98
    assert m["best_practices"] == 97
    assert m["cls"] == 0.03


def test_perf_evaluate_good_metrics_pass():
    assert evaluate(parse_lighthouse(GOOD_LH)) is True


def test_perf_evaluate_bad_metrics_fail():
    assert evaluate(parse_lighthouse(BAD_LH)) is False


def test_perf_report_pass_when_lighthouse_supplied(tmp_path):
    lh_path = tmp_path / "lh.json"
    lh_path.write_text(json.dumps(GOOD_LH), encoding="utf-8")
    rep = run_performance_check(str(lh_path), None, str(tmp_path / "perf.json"))
    assert rep["status"] == "PASS"
    assert rep["passed"] is True


def test_perf_report_fail_on_bad_lighthouse(tmp_path):
    lh_path = tmp_path / "lh.json"
    lh_path.write_text(json.dumps(BAD_LH), encoding="utf-8")
    rep = run_performance_check(str(lh_path), None, str(tmp_path / "perf.json"))
    assert rep["status"] == "FAIL"
    assert rep["passed"] is False


def test_perf_report_pending_without_measurement(tmp_path):
    rep = run_performance_check(None, None, str(tmp_path / "perf.json"))
    assert rep["status"] == "PENDING"
    assert rep["passed"] is False


# --------------------------------------------------------------------------- #
# Agent 23 - competitor                                                         #
# --------------------------------------------------------------------------- #
# Agent 23 keeps tokens with len > 4 as "entities". The competitor entity set
# is therefore {money, transfer, abroad}. For PASS the article must:
#   * cover >= 70% of competitor entities (so include money/transfer/abroad), AND
#   * add >= 20% NEW entities (info gain), AND
#   * not be missing FAQ / table / example / official-reference that the
#     competitor has (our competitor text has none of those, so nothing missing).
COMPETITORS_THIN = [
    {"url": "https://x.test/a", "title": "transfer",
     "text": "money transfer abroad"},
]
STRONG_ARTICLE = (
    "Money transfer abroad explained.\n\n"
    "Remitly Wise Xoom corridor settlement intermediary compliance treasury "
    "liquidity hedging arbitrage remittance disbursement reconciliation "
    "beneficiary correspondent custodian regulatory jurisdiction.\n\n"
    "## Comparison\n| Provider | Fee |\n| --- | --- |\n| Wise | low |\n\n"
    "For example, a real-world case study of a transfer.\n\n"
    "Official guidance: https://www.irs.gov/businesses\n\n"
    "## Frequently Asked Questions\n### How long?\nOne day.\n"
)


def test_competitor_pass_with_strong_article(tmp_path):
    rep = run_competitor_check(STRONG_ARTICLE, COMPETITORS_THIN, "send money abroad",
                               str(tmp_path / "comp.json"))
    assert rep["status"] == "PASS", rep
    assert rep["passed"] is True
    assert rep["information_gain"] >= rep["thresholds"]["information_gain_min"]
    assert rep["entity_coverage"] >= rep["thresholds"]["entity_coverage_min"]


def test_competitor_fail_on_low_information_gain(tmp_path):
    # Article identical to the competitor text -> no new entities -> info gain 0.
    weak = COMPETITORS_THIN[0]["text"]
    rep = run_competitor_check(weak, COMPETITORS_THIN, "x", str(tmp_path / "comp.json"))
    assert rep["status"] == "FAIL"
    assert rep["passed"] is False


def test_competitor_pending_without_corpus(tmp_path):
    rep = run_competitor_check(STRONG_ARTICLE, None, "x", str(tmp_path / "comp.json"))
    assert rep["status"] == "PENDING"
    assert rep["passed"] is False


# --------------------------------------------------------------------------- #
# End-to-end: clean article + PASS runtime reports -> READY_TO_PUBLISH.         #
# This proves the runtime gates were the ONLY blockers offline; once supplied   #
# real (here: synthetic) PASS reports, the authoritative gate publishes.        #
# --------------------------------------------------------------------------- #
def _gate_args(tmp_path, perf_report=None, comp_report=None):
    art = tmp_path / "article.md"; art.write_text(CLEAN_ARTICLE, encoding="utf-8")
    ren = tmp_path / "rendered.html"; ren.write_text(CLEAN_RENDERED, encoding="utf-8")
    met = tmp_path / "meta.json"; met.write_text(json.dumps(CLEAN_META), encoding="utf-8")
    corpus_dir = tmp_path / "corpus"; corpus_dir.mkdir()
    out = tmp_path / "gate.json"

    class _A:
        pass
    a = _A()
    a.article = str(art)
    a.rendered = str(ren)
    a.meta = str(met)
    a.corpus_dir = str(corpus_dir)
    a.performance_report = perf_report
    a.competitor_report = comp_report
    a.output = str(out)
    return a


def _write_report(tmp_path, name, passed):
    p = tmp_path / name
    p.write_text(json.dumps({"passed": passed, "status": "PASS" if passed else "FAIL"}),
                 encoding="utf-8")
    return str(p)


def test_clean_article_blocked_without_runtime_reports(tmp_path):
    result = qg.run_gate(_gate_args(tmp_path))
    assert result["decision"] == "BLOCKED"
    assert set(result["failed_gates"]) == {"performance", "competitor"}


def test_clean_article_publishable_with_pass_runtime_reports(tmp_path):
    perf = _write_report(tmp_path, "perf.json", True)
    comp = _write_report(tmp_path, "comp.json", True)
    result = qg.run_gate(_gate_args(tmp_path, perf, comp))
    assert result["decision"] == "READY_TO_PUBLISH", result
    assert result["failed_gates"] == []


def test_clean_article_blocked_when_performance_fails(tmp_path):
    perf = _write_report(tmp_path, "perf.json", False)
    comp = _write_report(tmp_path, "comp.json", True)
    result = qg.run_gate(_gate_args(tmp_path, perf, comp))
    assert result["decision"] == "BLOCKED"
    assert "performance" in result["failed_gates"]
    assert "competitor" not in result["failed_gates"]
