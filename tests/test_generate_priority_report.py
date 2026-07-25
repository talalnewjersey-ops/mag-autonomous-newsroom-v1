"""2026-07-25: the priority report is what the user now relies on to decide
which draft to review/publish first, since auto-publish is off. Two things
must never regress: (1) the gate-chain check reports the FIRST real blocker,
in the true pipeline order, not a later gate the article never reached; (2)
no search-volume/keyword-difficulty/AdSense number is ever printed --
agent_01's search_volume/keyword_difficulty are hardcoded placeholders
(1000/35) for every topic regardless of path, so surfacing them (even
labeled) would be indistinguishable from a real SEO measurement.

Offline: no network, no fixtures beyond in-memory dicts built to match the
real JSON shapes this session verified against downloaded artifacts.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_priority_report import (  # noqa: E402
    analyze_article, build_report, _gate_chain, _monetization_1_5, _pillar_1_5,
)


def _write(dir_, agent, name, data):
    p = dir_ / agent
    p.mkdir(parents=True, exist_ok=True)
    (p / name).write_text(json.dumps(data), encoding="utf-8")


def test_gate_chain_reports_g_substance_as_the_real_blocker():
    a04 = {"_g_substance": {"verdict": "FAIL", "reasons": ["only 0 STABLE facts cited (need >= 2)"]},
           "_length": {"over_ceiling": False}}
    publishable, reason = _gate_chain(a04, g3=None, wp=None, gate_d=None, qa=None)
    assert not publishable
    assert "G-SUBSTANCE FAIL" in reason
    assert "0 STABLE facts" in reason


def test_gate_chain_reports_gate_d_when_it_is_the_real_blocker():
    a04 = {"_g_substance": {"verdict": "PASS", "reasons": []}, "_length": {"over_ceiling": False}}
    g3 = {"passed": True, "decision": "PASS"}
    wp = {"post_id": 1, "title": "x", "keyword": "x"}
    gate_d = {"status": "FAIL", "body_findings": [{"type": "adjacent_connector_pair"}],
              "title_findings": [], "alt_text_findings": []}
    publishable, reason = _gate_chain(a04, g3, wp, gate_d, qa=None)
    assert not publishable
    assert "GATE D FAIL" in reason
    assert "adjacent_connector_pair" in reason


def test_gate_chain_does_not_blame_gate_d_when_article_never_reached_it():
    # G-Substance already failed -- GATE D was never even run. The reason
    # must name G-Substance, not silently fall through to a later check.
    a04 = {"_g_substance": {"verdict": "FAIL", "reasons": ["hollow"]}, "_length": {"over_ceiling": False}}
    gate_d = {"status": "FAIL"}  # would be wrong to report even if present
    publishable, reason = _gate_chain(a04, g3=None, wp=None, gate_d=gate_d, qa=None)
    assert not publishable
    assert "G-SUBSTANCE" in reason
    assert "GATE D" not in reason


def test_gate_chain_publishable_true_only_on_real_qa_pass():
    a04 = {"_g_substance": {"verdict": "PASS", "reasons": []}, "_length": {"over_ceiling": False}}
    g3 = {"passed": True, "decision": "PASS"}
    wp = {"post_id": 1}
    gate_d = {"status": "PASS", "body_findings": [], "title_findings": [], "alt_text_findings": []}
    qa = {"status": "PASS", "overall_score": 96.5}
    publishable, reason = _gate_chain(a04, g3, wp, gate_d, qa)
    assert publishable
    assert "96.5" in reason


def test_gate_chain_missing_wp_report_does_not_claim_gate_c_specifically():
    # RETRY-COMPLETENESS and similar upstream rejections don't write a JSON
    # report -- the reason must not overclaim which exact gate blocked it.
    a04 = {"_g_substance": {"verdict": "PASS", "reasons": []}, "_length": {"over_ceiling": False}}
    g3 = {"passed": True, "decision": "PASS"}
    publishable, reason = _gate_chain(a04, g3, wp=None, gate_d=None, qa=None)
    assert not publishable
    assert "voir le log" in reason.lower()


def test_monetization_rescale_is_clamped_1_to_5():
    assert _monetization_1_5({"revenue_score": 0}) == 1
    assert _monetization_1_5({"revenue_score": 100}) == 5
    assert _monetization_1_5({"revenue_score": 71}) == 4
    assert _monetization_1_5(None) is None


def test_pillar_heuristic_favors_short_generic_keywords():
    broad = _pillar_1_5("best bank account for immigrants")
    specific = _pillar_1_5("does applying for a credit card hurt your score as a new immigrant with an itin")
    assert broad > specific


def test_analyze_article_end_to_end_from_real_shaped_files(tmp_path):
    art = tmp_path / "article_1"
    _write(art, "agent_01", "topics.json", {"topics": [{"keyword": "how to open a us bank account without an ssn"}]})
    _write(art, "agent_04", "g_substance_report.json",
           {"verdict": "PASS", "reasons": [], "vertical": "us_banking", "cited_stable_facts": 4})
    _write(art, "agent_04", "length_report.json", {"over_ceiling": False, "word_count": 4000})
    _write(art, "agent_04", "g3_report.json", {"passed": True, "decision": "PASS"})
    _write(art, "agent_11", "wordpress_report.json",
           {"post_id": 49999, "title": "How to Open a US Bank Account Without an SSN", "keyword": "how to open a us bank account without an ssn"})
    _write(art, "agent_11", "placeholder_gate_report.json",
           {"status": "PASS", "body_findings": [], "title_findings": [], "alt_text_findings": []})
    _write(art, "agent_12", "qa_report.json", {"status": "PASS", "overall_score": 97.2})
    _write(art, "agent_17", "cannibalization_report.json",
           {"decision": "CREATE_NEW_ARTICLE", "observation": {"max_combined_score": 0.12}})
    _write(art, "agent_18", "revenue_score.json", {"revenue_score": 60})

    row = analyze_article(art)
    assert row["publishable"] is True
    assert row["score"] == 97.2
    assert row["vertical"] == "us_banking"
    assert row["cited_stable_facts"] == 4
    assert row["similarity_bucket"] == "neuf"
    assert row["post_id"] == 49999


def test_build_report_never_prints_a_seo_volume_or_adsense_number():
    rows = [{
        "dir": "article_1", "title": "T", "keyword": "k", "post_id": 1, "score": 96.0,
        "publishable": True, "reason": "ok", "vertical": "us_credit",
        "similarity_bucket": "neuf", "similarity_score": 0.1, "cited_stable_facts": 3,
        "monetization_1_5": 4, "pillar_1_5": 3,
    }]
    report = build_report(rows, "test-run")
    lowered = report.lower()
    for forbidden in ("search_volume", "keyword_difficulty", "1000", " 35 ", "adsense potential",
                       "cpc"):
        assert forbidden not in lowered, f"report must never surface {forbidden!r}"
    assert "estimation" in lowered
    assert "monétisation" in lowered and "(est" in lowered


def test_build_report_labels_every_heuristic_column_as_estimation():
    rows = [{
        "dir": "article_1", "title": "T", "keyword": "k", "post_id": 1, "score": 96.0,
        "publishable": True, "reason": "ok", "vertical": "us_credit",
        "similarity_bucket": "neuf", "similarity_score": 0.1, "cited_stable_facts": 3,
        "monetization_1_5": 4, "pillar_1_5": 3,
    }]
    report = build_report(rows, "test-run")
    assert "ESTIMATION" in report
    assert report.count("ESTIMATION") >= 2  # monetization + pillar disclaimers


def test_build_report_sorts_publishable_before_unpublishable_and_justifies_number_one():
    rows = [
        {"dir": "a", "title": "Bad", "keyword": "k", "post_id": None, "score": None,
         "publishable": False, "reason": "GATE D FAIL", "vertical": "us_credit",
         "similarity_bucket": "neuf", "similarity_score": 0.0, "cited_stable_facts": 1,
         "monetization_1_5": 5, "pillar_1_5": 5},
        {"dir": "b", "title": "Good", "keyword": "k", "post_id": 2, "score": 99.0,
         "publishable": True, "reason": "ok", "vertical": "us_banking",
         "similarity_bucket": "neuf", "similarity_score": 0.0, "cited_stable_facts": 4,
         "monetization_1_5": 3, "pillar_1_5": 2},
    ]
    report = build_report(rows, "test-run")
    assert report.index("Good") < report.index("Bad")
    assert "#1 : Good" in report
