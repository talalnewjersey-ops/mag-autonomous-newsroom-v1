import json

from orchestrator.orchestrator import evaluate_performance_gate


def _lh(perf=None, a11y=None, bp=None, seo=None):
    """Build a minimal Lighthouse-shaped report with the given category scores."""
    cats = {}
    if perf is not None:
        cats["performance"] = {"score": perf}
    if a11y is not None:
        cats["accessibility"] = {"score": a11y}
    if bp is not None:
        cats["best-practices"] = {"score": bp}
    if seo is not None:
        cats["seo"] = {"score": seo}
    return {"categories": cats}


def test_disabled_by_default_is_noop():
    gate = evaluate_performance_gate(_lh(perf=0.1))
    assert gate["enabled"] is False
    assert gate["passed"] is True
    assert gate["blocking"] is False
    assert gate["categories"] == {}
    assert gate["failed_categories"] == []
    assert gate["serp"] is None
    assert gate["serp_passed"] is None


def test_schema_is_stable():
    gate = evaluate_performance_gate(_lh(perf=0.95), enabled=True)
    assert gate["schema"] == "nexus14.performance_gate.v1"


def test_all_pass_above_thresholds():
    gate = evaluate_performance_gate(
        _lh(perf=0.95, a11y=0.99, bp=0.92, seo=1.0), enabled=True
    )
    assert gate["passed"] is True
    assert gate["failed_categories"] == []
    assert gate["categories"]["performance"]["passed"] is True
    assert gate["categories"]["performance"]["score"] == 0.95
    assert gate["categories"]["performance"]["threshold"] == 0.9


def test_failing_categories_are_flagged_and_sorted():
    gate = evaluate_performance_gate(
        _lh(perf=0.5, a11y=0.5, bp=0.95, seo=0.5), enabled=True
    )
    assert gate["passed"] is False
    # sorted alphabetically
    assert gate["failed_categories"] == ["accessibility", "performance", "seo"]


def test_score_equal_to_threshold_passes():
    gate = evaluate_performance_gate(_lh(perf=0.9), enabled=True)
    assert gate["categories"]["performance"]["passed"] is True
    assert gate["failed_categories"] == []


def test_custom_thresholds_override():
    gate = evaluate_performance_gate(
        _lh(perf=0.7), enabled=True, thresholds={"performance": 0.6}
    )
    assert gate["categories"]["performance"]["passed"] is True
    gate2 = evaluate_performance_gate(
        _lh(perf=0.7), enabled=True, thresholds={"performance": 0.8}
    )
    assert gate2["categories"]["performance"]["passed"] is False


def test_missing_categories_are_ignored():
    gate = evaluate_performance_gate(_lh(perf=0.95), enabled=True)
    assert "accessibility" not in gate["categories"]
    assert "seo" not in gate["categories"]
    assert gate["passed"] is True


def test_serp_rank_within_limit_passes():
    gate = evaluate_performance_gate(
        _lh(perf=0.95), serp={"rank": 3, "query": "best banks", "url": "https://x"},
        enabled=True,
    )
    assert gate["serp_passed"] is True
    assert gate["serp"]["rank"] == 3
    assert gate["serp"]["max_rank"] == 10
    assert gate["serp"]["query"] == "best banks"
    assert gate["passed"] is True


def test_serp_rank_beyond_limit_fails_overall():
    gate = evaluate_performance_gate(
        _lh(perf=0.95), serp={"rank": 25}, enabled=True
    )
    assert gate["serp_passed"] is False
    assert gate["passed"] is False


def test_serp_custom_max_rank():
    gate = evaluate_performance_gate(
        _lh(perf=0.95), serp={"rank": 5}, enabled=True,
        thresholds={"serp_max_rank": 3},
    )
    assert gate["serp_passed"] is False


def test_no_serp_means_serp_passed_none_and_does_not_fail():
    gate = evaluate_performance_gate(_lh(perf=0.95), enabled=True)
    assert gate["serp_passed"] is None
    assert gate["passed"] is True


def test_does_not_mutate_inputs():
    lh = _lh(perf=0.95)
    serp = {"rank": 2}
    before_lh = json.dumps(lh, sort_keys=True)
    before_serp = json.dumps(serp, sort_keys=True)
    evaluate_performance_gate(lh, serp=serp, enabled=True)
    assert json.dumps(lh, sort_keys=True) == before_lh
    assert json.dumps(serp, sort_keys=True) == before_serp


def test_never_raises_on_garbage_input():
    for bad in (None, 42, "str", [], {"categories": "nope"}, {"categories": {"performance": "x"}}):
        gate = evaluate_performance_gate(bad, enabled=True)
        assert gate["schema"] == "nexus14.performance_gate.v1"
        assert gate["blocking"] is False


def test_garbage_serp_does_not_raise():
    gate = evaluate_performance_gate(_lh(perf=0.95), serp="notadict", enabled=True)
    assert gate["passed"] is True
    assert gate["serp_passed"] is None


def test_non_numeric_score_is_skipped():
    report = {"categories": {"performance": {"score": None}, "seo": {"score": 0.95}}}
    gate = evaluate_performance_gate(report, enabled=True)
    assert "performance" not in gate["categories"]
    assert gate["categories"]["seo"]["passed"] is True
