#!/usr/bin/env python3
"""
Offline tests for the M7 topic-selection bridge (services.topic_selection).

These tests verify the glue between the validated-topic dicts produced by
the pipeline and the deterministic newcomer US/CA prioritizer. They run
fully offline: no network, no live data, no fabricated metrics.

Known real taxonomy facts used as anchors (static weights only):
  * Highest static score: build-credit-score-newcomer (~0.6995)
  * Lowest static score:  driver-license-newcomer     (~0.5240)
  * open-bank-account-newcomer carries keyword "newcomer bank account"
"""
from __future__ import annotations

import pytest

from services.topic_selection import (
    prioritize_validated_topics,
    score_validated_topics,
    _build_score_index,
    _UNMATCHED_SCORE,
)


TOP_SLUG = "build-credit-score-newcomer"
LOW_SLUG = "driver-license-newcomer"


def _slugs(topics):
    return [t.get("slug") or t.get("keyword") for t in topics]


def test_index_contains_known_slugs_and_keywords():
    index = _build_score_index()
    assert TOP_SLUG in index
    assert LOW_SLUG in index
    # keyword handle is normalized (lowercased) and present
    assert "newcomer bank account" in index
    # every score is a clamped probability
    assert all(0.0 <= v <= 1.0 for v in index.values())


def test_top_slug_outscores_low_slug_in_index():
    index = _build_score_index()
    assert index[TOP_SLUG] > index[LOW_SLUG]


def test_score_validated_topics_annotates_without_mutating_input():
    original = [{"slug": TOP_SLUG, "keyword": "build credit newcomer"}]
    annotated = score_validated_topics(original)
    assert annotated[0]["m7_matched"] is True
    assert annotated[0]["m7_score"] > 0.0
    # original dict is untouched (no m7_* keys leaked back)
    assert "m7_score" not in original[0]


def test_unmatched_topic_is_flagged_but_kept():
    topics = [{"slug": "totally-unknown-topic-xyz", "keyword": "unknown xyz"}]
    annotated = score_validated_topics(topics)
    assert annotated[0]["m7_matched"] is False
    assert annotated[0]["m7_score"] == _UNMATCHED_SCORE


def test_prioritize_orders_high_value_first():
    topics = [
        {"slug": LOW_SLUG},
        {"slug": TOP_SLUG},
    ]
    ordered = prioritize_validated_topics(topics)
    assert _slugs(ordered) == [TOP_SLUG, LOW_SLUG]


def test_prioritize_matches_by_keyword_field():
    # No slug present; matching must fall back to the keyword text.
    topics = [
        {"keyword": "driver license newcomer"},
        {"keyword": "newcomer bank account"},
    ]
    ordered = prioritize_validated_topics(topics)
    # the bank-account topic (high score) must come before driver license
    assert ordered[0]["keyword"] == "newcomer bank account"


def test_unmatched_topics_sink_to_the_bottom_but_survive():
    topics = [
        {"slug": "unknown-a", "keyword": "zzz a"},
        {"slug": TOP_SLUG},
        {"slug": "unknown-b", "keyword": "zzz b"},
    ]
    ordered = prioritize_validated_topics(topics)
    assert ordered[0]["slug"] == TOP_SLUG
    # both unknowns are still present (never dropped)
    remaining = {t["slug"] for t in ordered[1:]}
    assert remaining == {"unknown-a", "unknown-b"}
    assert len(ordered) == 3


def test_unmatched_preserve_original_relative_order():
    topics = [
        {"slug": "unknown-first", "keyword": "u1"},
        {"slug": "unknown-second", "keyword": "u2"},
    ]
    ordered = prioritize_validated_topics(topics)
    assert [t["slug"] for t in ordered] == ["unknown-first", "unknown-second"]


def test_limit_returns_top_n_only():
    topics = [
        {"slug": LOW_SLUG},
        {"slug": TOP_SLUG},
        {"slug": "international-money-transfer"},
    ]
    ordered = prioritize_validated_topics(topics, limit=1)
    assert len(ordered) == 1
    assert ordered[0]["slug"] == TOP_SLUG


def test_non_positive_limit_yields_empty_list():
    topics = [{"slug": TOP_SLUG}]
    assert prioritize_validated_topics(topics, limit=0) == []
    assert prioritize_validated_topics(topics, limit=-3) == []


def test_empty_input_is_safe():
    assert prioritize_validated_topics([]) == []
    assert score_validated_topics([]) == []


def test_prioritize_is_deterministic_across_calls():
    topics = [
        {"slug": "newcomer-credit-cards"},
        {"slug": TOP_SLUG},
        {"slug": "health-insurance-newcomer"},
        {"slug": LOW_SLUG},
    ]
    first = _slugs(prioritize_validated_topics(topics))
    second = _slugs(prioritize_validated_topics(topics))
    assert first == second
    assert first[0] == TOP_SLUG


def test_output_length_matches_input_when_no_limit():
    topics = [
        {"slug": TOP_SLUG},
        {"slug": "unknown-x", "keyword": "x"},
        {"slug": LOW_SLUG},
    ]
    ordered = prioritize_validated_topics(topics)
    assert len(ordered) == len(topics
