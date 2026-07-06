"""RETRY SAFETY (2026-07-06): the retry mechanism must never ship an article
worse than the one it replaced. Real control-run finding: a retry that fixed
G-Substance's sourcing complaint also silently dropped the entire FAQ section
(13 H2s -> 8). Two fixes, both covered here:
  (a) the writer's retry prompt now explicitly demands a TARGETED fix that
      preserves everything else (structure, FAQ, length).
  (b) production_v2.yml snapshots the rejected draft's structure before each
      retry and compares after -- a regression is treated as a full failure,
      never falling back to publishing either version.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()
WORKFLOW = open(os.path.join(ROOT, ".github/workflows/production_v2.yml"), encoding="utf-8").read()


def test_retry_prompt_demands_targeted_fix_not_blind_regeneration():
    assert "CHANGE NOTHING ELSE" in SRC
    assert "SMALLEST possible change" in SRC
    assert "FAQ section" in SRC
    assert "removes content elsewhere is WORSE than the original" in SRC


def test_workflow_snapshots_before_every_content_gate_retry():
    # one snapshot call per gate that can trigger a retry (G-Substance, G3, A, B)
    assert WORKFLOW.count(
        'structure_completeness_gate.py --input "${ARTICLE_DIR}/agent_04/article_draft.md" --snapshot'
    ) == 4


def test_workflow_compares_only_after_a_retry_succeeded():
    assert 'if [ "$RETRY_ATTEMPT" -eq 1 ] && [ -f "${ARTICLE_DIR}/agent_04/pre_retry_snapshot.json" ]' in WORKFLOW
    assert "--compare" in WORKFLOW


def test_workflow_regression_is_treated_as_full_failure_not_a_fallback():
    # must count as failed + move to next article (continue 2) -- never breaks
    # through to WordPress with either version.
    idx = WORKFLOW.index("GATE RETRY-COMPLETENESS FAIL")
    window = WORKFLOW[idx:idx + 200]
    assert "ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2" in window


def test_completeness_check_happens_before_break_not_after():
    compare_idx = WORKFLOW.index("Retry structural-completeness check")
    break_idx = WORKFLOW.index("\n            break\n            done")
    assert compare_idx < break_idx
