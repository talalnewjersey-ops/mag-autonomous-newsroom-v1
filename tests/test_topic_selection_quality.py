#!/usr/bin/env python3
"""Unit tests for topic_selection_quality (Priority 3).

Run: python -m pytest tests/test_topic_selection_quality.py -q
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import topic_selection_quality as tsq  # noqa: E402


ALL_PASS = {g: True for g in tsq.REQUIRED_GATES}


def _cand(topic, cluster, atype="STANDARD", gates=None, **scores):
    base = dict(user_value=80, commercial_intent=70, search_demand=60,
                affiliate_opportunity=50, strategic_authority=50)
    base.update(scores)
    return tsq.TopicCandidate(
        topic=topic, cluster=cluster, article_type=atype,
        gates=dict(ALL_PASS if gates is None else gates), **base
    )


def test_balanced_score_weights():
    c = _cand("t", "banking", user_value=100, commercial_intent=100,
              search_demand=100, affiliate_opportunity=100, strategic_authority=100)
    assert round(c.balanced_score(), 2) == 100.0


def test_failed_gate_makes_ineligible():
    bad = dict(ALL_PASS)
    bad["eeat_pass"] = False
    c = _cand("t", "banking", gates=bad)
    assert c.is_eligible() is False
    assert "eeat_pass" in c.failed_gates()


def test_ceiling_never_exceeded():
    cands = [_cand("t%d" % i, "banking") for i in range(10)]
    res = tsq.select(cands)
    assert res["counts"]["selected"] == tsq.MAX_ARTICLES_PER_DAY
    assert len(res["selected"]) == 6


def test_no_filler_when_few_eligible():
    # Only 2 eligible; the rest fail a gate. Must select exactly 2 (no padding).
    good = [_cand("g%d" % i, "banking") for i in range(2)]
    bad_gates = dict(ALL_PASS); bad_gates["seo_pass"] = False
    bad = [_cand("b%d" % i, "banking", gates=bad_gates) for i in range(5)]
    res = tsq.select(good + bad)
    assert res["counts"]["selected"] == 2
    assert res["counts"]["unused_slots"] == 4
    assert res["counts"]["rejected"] == 5


def test_priority_cluster_ordering():
    # A low-score car_insurance topic should outrank a high-score off-cluster one.
    car = _cand("car", "car_insurance", user_value=10, commercial_intent=10,
                search_demand=10, affiliate_opportunity=10, strategic_authority=10)
    other = _cand("misc", "gardening", user_value=100, commercial_intent=100,
                  search_demand=100, affiliate_opportunity=100, strategic_authority=100)
    res = tsq.select([other, car])
    assert res["selected"][0]["topic"] == "car"


def test_pillar_subcap_enforced():
    pillars = [_cand("p%d" % i, "banking", atype="PILLAR") for i in range(5)]
    res = tsq.select(pillars)
    pillar_selected = [s for s in res["selected"] if s["article_type"] == "PILLAR"]
    assert len(pillar_selected) <= tsq.MAX_PILLAR_PER_DAY


def test_rejected_lists_failed_gates():
    bad_gates = dict(ALL_PASS); bad_gates["originality_pass"] = False
    res = tsq.select([_cand("x", "taxes", gates=bad_gates)])
    assert res["counts"]["selected"] == 0
    assert res["rejected"][0]["failed_gates"] == ["originality_pass"]


def test_deterministic_repeatable():
    cands = [_cand("t%d" % i, "banking") for i in range(8)]
    assert tsq.select(cands) == tsq.select(cands)


def test_policy_flags_present():
    res = tsq.select([_cand("t", "banking")])
    pol = res["policy"]
    assert pol["ceiling_not_quota"] is True
    assert pol["no_filler"] is True
    assert pol["no_gate_bypass"] is True
    assert pol["max_articles_per_day"] == 6


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
