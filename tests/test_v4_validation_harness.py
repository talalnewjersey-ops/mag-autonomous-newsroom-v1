"""
NEXUS-14 V4 - tests/test_v4_validation_harness.py

Structured pytest regression suite for the V4 decision core. Each Agent 17 /
19 / 20 and Quality Gate decision is asserted as a discrete, named test so a
failure is isolated and self-describing. These reuse the SAME real code paths
and deterministic fixtures as scripts/validate_v4_pipeline.py (the offline
harness validated under CI run #2), and make NO network / WordPress / OpenAI
calls (EMBEDDINGS_PROVIDER=hashing).

Run:  pytest -q tests/test_v4_validation_harness.py
"""
from __future__ import annotations

import os

import pytest

# Deterministic offline embeddings BEFORE importing any agent/service.
os.environ.setdefault("EMBEDDINGS_PROVIDER", "hashing")

from agents.agent_19_originality import run_originality_check
from agents.agent_20_ymyl_validator import run_ymyl_validation
from agents import agent_17_cannibalization as a17

# Reuse the proven offline drivers + fixtures from the validation harness so the
# tests and the harness can never drift apart.
from scripts.validate_v4_pipeline import (
    RUNTIME_GATES,
    CLEAN_ARTICLE,
    CLEAN_META,
    CLEAN_RENDERED,
    DUP_CORPUS_POSTS,
    BAD_ARTICLE,
    BAD_META,
    BAD_RENDERED,
    run_cannibalization_offline,
    run_quality_gate_offline,
)


# --------------------------------------------------------------------------- #
# Fixtures (computed once; the agents are pure given the hashing backend).      #
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def gate_clean(tmp_path_factory):
    return run_quality_gate_offline(CLEAN_ARTICLE, CLEAN_RENDERED, CLEAN_META, [])


@pytest.fixture(scope="module")
def gate_bad(tmp_path_factory):
    return run_quality_gate_offline(BAD_ARTICLE, BAD_RENDERED, BAD_META, [])


def _content_failures(gate_result):
    return [g for g in gate_result["failed_gates"] if g not in RUNTIME_GATES]


# --------------------------------------------------------------------------- #
# Agent 19 - Originality                                                        #
# --------------------------------------------------------------------------- #
def test_agent19_clean_article_passes(tmp_path):
    rep = run_originality_check(CLEAN_ARTICLE, [], str(tmp_path / "o.json"))
    assert rep["passed"] is True
    assert rep["originality_score"] >= 80.0
    assert rep["regenerate_sections"] == []
    assert rep["violations"] == []


def test_agent19_bad_article_fails_on_patterns(tmp_path):
    rep = run_originality_check(BAD_ARTICLE, [], str(tmp_path / "o.json"))
    assert rep["passed"] is False
    vtypes = {v["type"] for v in rep["violations"]}
    # BAD_ARTICLE opens with a banned opener and uses an emoji heading.
    assert "banned_opener" in vtypes
    assert "emoji_heading" in vtypes


# --------------------------------------------------------------------------- #
# Agent 17 - Cannibalization (decision bands + offline corpus driver)           #
# --------------------------------------------------------------------------- #
def test_agent17_empty_corpus_allows():
    res = run_cannibalization_offline(
        CLEAN_META["title"], CLEAN_META["keywords"], CLEAN_META["slug"], [])
    assert res["decision"] == "ALLOW"
    assert res["blocking"] is False
    assert res["max_composite"] == 0.0


def test_agent17_near_duplicate_blocks():
    res = run_cannibalization_offline(
        CLEAN_META["title"], CLEAN_META["keywords"], CLEAN_META["slug"],
        DUP_CORPUS_POSTS)
    assert res["decision"] != "ALLOW"
    assert res["blocking"] is True
    assert res["max_composite"] > a17.BAND_ALLOW


@pytest.mark.parametrize("composite,expected", [
    (0.00, "ALLOW"),
    (0.54, "ALLOW"),
    (0.55, "HUMAN_REVIEW"),
    (0.71, "HUMAN_REVIEW"),
    (0.72, "MERGE"),
    (0.84, "MERGE"),
    (0.85, "BLOCK"),
    (0.99, "BLOCK"),
])
def test_agent17_decision_bands(composite, expected):
    a17._load_thresholds()
    assert a17.decide(composite) == expected


# --------------------------------------------------------------------------- #
# Agent 20 - YMYL                                                               #
# --------------------------------------------------------------------------- #
def test_agent20_clean_article_passes(tmp_path):
    rep = run_ymyl_validation(CLEAN_ARTICLE, output_path=str(tmp_path / "y.json"))
    assert rep["status"] == "PASS"
    assert rep["summary"]["contradicted"] == 0


def test_agent20_contradicted_value_fails(tmp_path):
    rep = run_ymyl_validation(
        "The TFSA contribution limit is $99,999 for 2025.",
        output_path=str(tmp_path / "y.json"))
    assert rep["status"] == "FAIL"
    assert rep["summary"]["contradicted"] >= 1


# --------------------------------------------------------------------------- #
# Quality Gate V4 - authoritative decision                                      #
# --------------------------------------------------------------------------- #
def test_gate_clean_passes_all_content_gates(gate_clean):
    # Every CONTENT gate passes; the article is clean.
    assert _content_failures(gate_clean) == []


def test_gate_clean_blocked_only_by_runtime_gates(gate_clean):
    # Offline, performance + competitor reports are absent (honest PENDING
    # design): the gate is BLOCKED but ONLY by the runtime gates.
    assert gate_clean["decision"] == "BLOCKED"
    assert set(gate_clean["failed_gates"]) <= RUNTIME_GATES
    assert set(gate_clean["failed_gates"]) == RUNTIME_GATES


def test_gate_bad_blocked_on_content(gate_bad):
    assert gate_bad["decision"] == "BLOCKED"
    failures = _content_failures(gate_bad)
    assert len(failures) >= 1
    # The bad article has body JSON-LD (schema), missing EEAT, emoji heading
    # (formatting) and too few internal links.
    assert "schema" in failures
    assert "eeat" in failures
    assert "internal_links" in failures


def test_no_external_io_markers(gate_clean):
    # Sanity: the offline drivers never set WP/OpenAI flags. The harness report
    # asserts wordpress_contacted/openai_contacted False; here we assert the
    # gate result carries the expected authoritative shape and nothing more.
    assert gate_clean["gate"] == "quality_gate_v4"
    assert "checks" in gate_clean and isinstance(gate_clean["checks"], list)
