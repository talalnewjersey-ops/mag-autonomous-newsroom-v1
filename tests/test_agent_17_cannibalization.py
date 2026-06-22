#!/usr/bin/env python3
"""
Unit tests for Agent 17 (HARDENED) deterministic duplicate prevention.
Run: pytest tests/test_agent_17_cannibalization.py -q

These tests exercise the deterministic layer in isolation. They do NOT call
WordPress or the Anthropic API; the AI pass is advisory and is not required for
deterministic verdicts.
"""

import importlib.util
import os
from pathlib import Path

import pytest

# Load the module by path so tests work without package installation.
MOD_PATH = Path(__file__).resolve().parents[1] / "agents" / "agent_17_cannibalization.py"
spec = importlib.util.spec_from_file_location("agent_17", MOD_PATH)
agent_17 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_17)


def _article(id, title, slug, status="publish"):
    return {"id": id, "title": title, "slug": slug, "status": status, "link": ""}


# ----------------------------------------------------------------------
# detect_country
# ----------------------------------------------------------------------
def test_detect_country_usa():
    assert agent_17.detect_country("Best Banks for ITIN Holders in the USA") == "USA"

def test_detect_country_canada():
    assert agent_17.detect_country("RRSP and TFSA guide for newcomers to Canada") == "CANADA"

def test_detect_country_unknown():
    assert agent_17.detect_country("How to budget your monthly expenses") == "UNKNOWN"


# ----------------------------------------------------------------------
# normalize_slug strips country qualifiers
# ----------------------------------------------------------------------
def test_normalize_slug_strips_country():
    a = agent_17.normalize_slug("best-banks-for-newcomers-usa")
    b = agent_17.normalize_slug("best-banks-for-newcomers-canada")
    assert a == b  # same core topic after stripping the country qualifier


# ----------------------------------------------------------------------
# evaluate_conflict — deterministic blocks
# ----------------------------------------------------------------------
def test_slug_duplicate_same_country_blocks():
    ev = agent_17.evaluate_conflict(
        "Best Bank Bonuses for Newcomers to the USA",
        agent_17.extract_keywords("Best Bank Bonuses for Newcomers to the USA"),
        "USA", "best-bank-bonuses-for-newcomers-usa",
        agent_17.primary_keyword("Best Bank Bonuses for Newcomers to the USA"),
        _article(101, "Best Bank Bonuses for Newcomers to the USA", "best-bank-bonuses-for-newcomers-usa"),
    )
    assert ev["blocking"] is True
    assert ev["slug_duplicate"] is True

def test_near_duplicate_title_same_country_blocks():
    new = "First 90 Days in the USA"
    ev = agent_17.evaluate_conflict(
        new, agent_17.extract_keywords(new), "USA", "first-90-days-in-the-usa",
        agent_17.primary_keyword(new),
        _article(102, "First 90 Days in USA", "first-90-days-in-usa"),
    )
    assert ev["blocking"] is True

def test_usa_vs_canada_variant_allowed():
    new = "Driver License Guide USA"
    ev = agent_17.evaluate_conflict(
        new, agent_17.extract_keywords(new), "USA", "driver-license-guide-usa",
        agent_17.primary_keyword(new),
        _article(103, "Driver License Guide Canada", "driver-license-guide-canada"),
    )
    assert ev["blocking"] is False
    assert ev["allowed_variant"] is True

def test_distinct_topic_no_block():
    new = "Best Credit Cards for ITIN Holders in the USA"
    ev = agent_17.evaluate_conflict(
        new, agent_17.extract_keywords(new), "USA", "best-credit-cards-itin-usa",
        agent_17.primary_keyword(new),
        _article(104, "How to Open a Bank Account as a Student in the USA", "open-bank-account-student-usa"),
    )
    assert ev["blocking"] is False
    assert ev["allowed_variant"] is False


# ----------------------------------------------------------------------
# Decision precedence: deterministic block beats advisory AI
# ----------------------------------------------------------------------
def test_ai_cannot_clear_deterministic_block(monkeypatch):
    # Force AI to say CREATE_NEW; deterministic slug-dup must still block.
    monkeypatch.setattr(agent_17, "ai_semantic_analysis",
                        lambda *a, **k: {"decision": agent_17.DECISIONS["CREATE_NEW"], "advisory": True})
    monkeypatch.setattr(agent_17, "fetch_wordpress_articles",
                        lambda status="any", per_page=100:
                            [_article(201, "Best Banks for Newcomers to the USA", "best-banks-for-newcomers-usa")]
                            if status == "publish" else [])
    out = "output/agent_17/_test_report.json"
    res = agent_17.run_cannibalization_check(
        "Best Banks for Newcomers to the USA",
        agent_17.extract_keywords("Best Banks for Newcomers to the USA"),
        target_country="USA", target_slug="best-banks-for-newcomers-usa",
        output_path=out,
    )
    assert res["blocking"] is True
    assert res["decision"] == agent_17.DECISIONS["REJECT"]
    assert res["deterministic_block"] is True
    if os.path.exists(out):
        os.remove(out)

def test_unknown_country_routes_to_manual_review(monkeypatch):
    monkeypatch.setattr(agent_17, "ai_semantic_analysis",
                        lambda *a, **k: {"decision": agent_17.DECISIONS["CREATE_NEW"], "advisory": True})
    monkeypatch.setattr(agent_17, "fetch_wordpress_articles",
                        lambda status="any", per_page=100: [])
    out = "output/agent_17/_test_report2.json"
    res = agent_17.run_cannibalization_check(
        "How to budget your monthly expenses", ["budget", "expenses"],
        output_path=out,
    )
    assert res["detected_country"] == "UNKNOWN"
    assert res["blocking"] is True
    if os.path.exists(out):
        os.remove(out)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
