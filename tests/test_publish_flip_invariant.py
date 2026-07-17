"""2026-07-17: real auto-publish decision -- scripts/publish_if_qa_passed.py
is the ONLY code path in this repo that ever flips a WordPress post from
draft to publish.

THE NON-NEGOTIABLE ASSERTION (mirrors tests/test_sprint9_publish_invariant.py's
contract for the registry, but for the real WordPress post status): an
article that did not clear a REAL PASS at or above PUBLICATION_QUALITY_GATE
must NEVER be published, no matter what draft_only is set to. draft_only=false
is necessary but never sufficient on its own.

should_publish() is a pure function (no network, no filesystem beyond the
caller's json.load) -- exercised directly here, offline, no network, no API
key. The network-touching parts of the script (post_id fetch, the actual WP
POST call) are deliberately NOT exercised here; they are the same
challenge-retry-free, "refuse unless current status is draft" pattern already
covered informally by scripts/mark_qa_failed.py's own real-world usage.
"""
import importlib.util
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub(name, **attrs):
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m


# agent_12_quality_assurance.py (imported transitively for PUBLICATION_QUALITY_GATE)
# pulls in services.llm_service/services.storage_service -- same stub pattern as
# tests/test_agent12_publication_gate_95.py, so this stays offline/no-API-key.
_stub("services.llm_service", LLMService=object)
_stub("services.storage_service", StorageService=object)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_12_mod = _load("agents/agent_12_quality_assurance.py", "agent_12_publish_flip")
publish_mod = _load("scripts/publish_if_qa_passed.py", "publish_if_qa_passed_test")
SCRIPT_SRC = open(os.path.join(ROOT, "scripts", "publish_if_qa_passed.py"), encoding="utf-8").read()

should_publish = publish_mod.should_publish


def _qa(**over):
    base = {"status": "PASS", "overall_score": 100}
    base.update(over)
    return base


# ---------------- single source of truth: no second hardcoded copy of the gate ----------------

def test_gate_constant_is_imported_from_agent_12_not_copied():
    # source guard: this file must import the constant, never redefine its
    # own literal "95" -- a copy is exactly how GATE QA's own threshold
    # silently drifted (85 vs 95, AUDIT-LOG.md) before it was caught.
    assert "from agents.agent_12_quality_assurance import PUBLICATION_QUALITY_GATE" in SCRIPT_SRC
    assert publish_mod.PUBLICATION_QUALITY_GATE is agent_12_mod.PUBLICATION_QUALITY_GATE
    assert publish_mod.PUBLICATION_QUALITY_GATE == 95


# ===== NON-NEGOTIABLE: QA-FAILED can NEVER be published, regardless of draft_only =====

def test_qa_status_fail_never_publishes_even_with_draft_only_false():
    publish, _ = should_publish(_qa(status="FAIL", overall_score=100), "false")
    assert publish is False


def test_qa_status_needs_review_never_publishes_even_with_draft_only_false():
    publish, _ = should_publish(_qa(status="NEEDS_REVIEW", overall_score=94.9), "false")
    assert publish is False


def test_score_94_9_never_publishes_even_with_draft_only_false():
    # comfortably above the old drifted 85, still below the real 95 gate.
    publish, _ = should_publish(_qa(status="PASS", overall_score=94.9), "false")
    assert publish is False


def test_score_exactly_95_with_real_pass_publishes():
    publish, reason = should_publish(_qa(status="PASS", overall_score=95.0), "false")
    assert publish is True
    assert "publishing" in reason


def test_score_100_with_real_pass_publishes():
    publish, _ = should_publish(_qa(status="PASS", overall_score=100), "false")
    assert publish is True


# ===== NON-NEGOTIABLE: the heuristic fallback path can NEVER publish =====

def test_heuristic_mode_pass_never_publishes_even_with_draft_only_false():
    # agent_12's heuristic fallback caps overall_score at 75 (always < 95),
    # so the score check alone already blocks it -- this proves the explicit
    # "mode" check is real defense-in-depth, not dead code: it still refuses
    # even in the contrived case of a heuristic report claiming a 95+ score.
    publish, reason = should_publish(
        _qa(status="PASS", overall_score=99, mode="heuristic"), "false")
    assert publish is False
    assert "heuristic" in reason


def test_real_heuristic_shape_never_publishes():
    # the actual shape agent_12's main() heuristic branch writes.
    heuristic_report = {
        "status": "PASS", "overall_score": 75, "seo_score": 75, "eeat_score": 75,
        "mode": "heuristic",
    }
    publish, _ = should_publish(heuristic_report, "false")
    assert publish is False


# ===== NON-NEGOTIABLE: draft_only must be the literal "false", fail-safe otherwise =====

def test_draft_only_true_blocks_publish_even_with_a_perfect_score():
    publish, _ = should_publish(_qa(status="PASS", overall_score=100), "true")
    assert publish is False


def test_draft_only_empty_string_blocks_publish():
    # the real scheduled-run-without-override shape, if the workflow wiring
    # ever regressed back to not overriding schedule events.
    publish, _ = should_publish(_qa(status="PASS", overall_score=100), "")
    assert publish is False


def test_draft_only_garbage_value_blocks_publish():
    # same fail-safe contract as resolve_draft_only() in production_batch_loop.sh:
    # only the exact literal "false" is ever treated as real-publish mode.
    publish, _ = should_publish(_qa(status="PASS", overall_score=100), "FALSE")
    assert publish is False


# ===== combined matrix: draft_only=false is necessary but never sufficient =====

def test_draft_only_false_alone_does_not_publish_a_failing_score():
    publish, _ = should_publish(_qa(status="PASS", overall_score=50), "false")
    assert publish is False


def test_missing_overall_score_defaults_safe_and_does_not_publish():
    qa = {"status": "PASS"}  # no overall_score key at all
    publish, _ = should_publish(qa, "false")
    assert publish is False


def test_non_numeric_overall_score_does_not_publish():
    publish, _ = should_publish(_qa(status="PASS", overall_score="ninety-nine"), "false")
    assert publish is False
