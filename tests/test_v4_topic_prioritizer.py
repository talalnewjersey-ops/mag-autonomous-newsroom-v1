"""
NEXUS-14 V4 - tests/test_v4_topic_prioritizer.py

Offline tests for the topic taxonomy + prioritizer (M7). No network, no live
data: these prove the scoring is deterministic, the weighting is well-formed,
and that absent live signals are handled honestly (never fabricated).
"""

import pytest

from services.topic_taxonomy import (
    NEWCOMER_TOPICS,
    Topic,
    all_topics,
    topics_for_region,
    topic_by_slug,
    slugs,
)
from services.topic_prioritizer import (
    WEIGHTS,
    LiveSignals,
    ScoredTopic,
    score_topic,
    prioritize,
    top_topic,
)


# --------------------------------------------------------------------------- #
# Taxonomy integrity
# --------------------------------------------------------------------------- #
def test_taxonomy_is_non_empty():
    assert len(NEWCOMER_TOPICS) >= 10


def test_all_scores_in_unit_interval():
    for t in NEWCOMER_TOPICS:
        for v in (t.newcomer_value, t.commercial_intent, t.evergreen):
            assert 0.0 <= v <= 1.0


def test_regions_are_valid():
    for t in NEWCOMER_TOPICS:
        assert t.region in ("US", "CA", "BOTH")


def test_slugs_are_unique():
    s = slugs()
    assert len(s) == len(set(s))


def test_topic_by_slug_roundtrip():
    for t in NEWCOMER_TOPICS:
        assert topic_by_slug(t.slug) is t


def test_topic_by_slug_missing_raises():
    with pytest.raises(KeyError):
        topic_by_slug("does-not-exist")


def test_invalid_score_rejected():
    with pytest.raises(ValueError):
        Topic("bad", "Bad", "US", 1.5, 0.5, 0.5)


def test_invalid_region_rejected():
    with pytest.raises(ValueError):
        Topic("bad", "Bad", "XX", 0.5, 0.5, 0.5)


def test_region_filter_us_includes_both():
    us = topics_for_region("US")
    assert all(t.region in ("US", "BOTH") for t in us)
    assert not any(t.region == "CA" for t in us)


def test_region_filter_ca_includes_both():
    ca = topics_for_region("CA")
    assert all(t.region in ("CA", "BOTH") for t in ca)
    assert not any(t.region == "US" for t in ca)


def test_region_filter_invalid_raises():
    with pytest.raises(ValueError):
        topics_for_region("XX")


# --------------------------------------------------------------------------- #
# Weighting
# --------------------------------------------------------------------------- #
def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9


def test_newcomer_value_is_highest_weight():
    assert WEIGHTS["newcomer_value"] == max(WEIGHTS.values())


# --------------------------------------------------------------------------- #
# Scoring: static-only
# --------------------------------------------------------------------------- #
def test_score_is_in_unit_interval():
    for t in NEWCOMER_TOPICS:
        st = score_topic(t)
        assert 0.0 <= st.score <= 1.0


def test_no_live_signals_means_none_used():
    t = NEWCOMER_TOPICS[0]
    st = score_topic(t)
    assert st.used_live_signals == []


def test_static_score_matches_manual():
    t = Topic("x", "X", "BOTH", 1.0, 1.0, 1.0)
    st = score_topic(t)
    expected = (
        WEIGHTS["newcomer_value"]
        + WEIGHTS["commercial_intent"]
        + WEIGHTS["evergreen"]
    )
    assert st.score == pytest.approx(round(expected, 6))


def test_zero_topic_scores_zero():
    t = Topic("z", "Z", "BOTH", 0.0, 0.0, 0.0)
    assert score_topic(t).score == 0.0


# --------------------------------------------------------------------------- #
# Scoring: with live signals (injected, not fabricated)
# --------------------------------------------------------------------------- #
def test_live_signal_increases_score_and_is_recorded():
    t = Topic("x", "X", "BOTH", 0.5, 0.5, 0.5)
    base = score_topic(t).score
    boosted = score_topic(t, LiveSignals(search_demand=1.0))
    assert boosted.score > base
    assert "search_demand" in boosted.used_live_signals


def test_partial_live_signals_record_only_supplied():
    t = Topic("x", "X", "BOTH", 0.5, 0.5, 0.5)
    st = score_topic(t, LiveSignals(trend=0.8))
    assert st.used_live_signals == ["trend"]


def test_live_values_are_clamped():
    t = Topic("x", "X", "BOTH", 0.0, 0.0, 0.0)
    st = score_topic(t, LiveSignals(search_demand=5.0))
    assert st.score <= 1.0


# --------------------------------------------------------------------------- #
# Prioritize / ranking
# --------------------------------------------------------------------------- #
def test_prioritize_sorted_descending():
    ranked = prioritize("BOTH")
    scores = [s.score for s in ranked]
    assert scores == sorted(scores, reverse=True)


def test_prioritize_returns_all_for_both():
    assert len(prioritize("BOTH")) == len(all_topics())


def test_prioritize_limit():
    ranked = prioritize("BOTH", limit=3)
    assert len(ranked) == 3


def test_prioritize_negative_limit_raises():
    with pytest.raises(ValueError):
        prioritize("BOTH", limit=-1)


def test_prioritize_is_deterministic():
    a = [s.slug for s in prioritize("BOTH")]
    b = [s.slug for s in prioritize("BOTH")]
    assert a == b


def test_top_topic_is_first_of_prioritize():
    assert top_topic("BOTH").slug == prioritize("BOTH")[0].slug


def test_top_topic_high_value():
    # Static-only sanity check: with no live signals, the top-ranked topic must
    # still be a strongly newcomer-critical one. The composite ceiling for a
    # static-only topic is ~0.70 (no live-signal weight contributes), so 0.65
    # is a meaningful floor that proves weighting favours newcomer value.
    assert top_topic("BOTH").score >= 0.65


class _StubProvider:
    """Test double standing in for a future authorised live source."""
    def __init__(self, mapping):
        self._mapping = mapping

    def signals_for(self, slug):
        return self._mapping.get(slug, LiveSignals())


def test_provider_signals_applied():
    target = NEWCOMER_TOPICS[-1].slug  # a lower-ranked topic
    provider = _StubProvider({target: LiveSignals(search_demand=1.0,
                                                  trend=1.0,
                                                  affiliate_demand=1.0)})
    ranked = {s.slug: s for s in prioritize("BOTH", provider=provider)}
    assert "search_demand" in ranked[target].used_live_signals
    assert "trend" in ranked[target].used_live_signals
    assert "affiliate_demand" in ranked[target].used_live_signals
