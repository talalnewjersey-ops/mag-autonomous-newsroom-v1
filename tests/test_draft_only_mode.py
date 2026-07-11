"""2026-07-11: production_v2.yml gained a real draft-only workflow_dispatch
mode so manual witness/verification runs can no longer promote a topic to
"published" in data/topic_registry.json, no matter what the QA score is.

Previously the only thing standing between a witness run and a real
publish was the QA/editor/production-gate scores clearing whatever
threshold happened to be coded (see PUBLICATION_QUALITY_GATE fix,
agents/agent_12_quality_assurance.py) -- a high-scoring witness run could
still get promoted for real. draft_only defaults to true: PRODUCED.json
(the terminal marker the "Reconcile topic registry" step keys on) is
skipped entirely, so the existing rollback-to-candidate logic in
agent_01_seo_research --reconcile takes over unchanged. WordPress drafts
are still created either way -- this only gates the registry promotion.

Offline, no network, no API key.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = open(os.path.join(ROOT, ".github/workflows/production_v2.yml"), encoding="utf-8").read()


def test_draft_only_input_exists_and_defaults_to_true():
    idx = WORKFLOW.index("draft_only:")
    window = WORKFLOW[idx:idx + 300]
    assert "type: boolean" in window
    assert "default: true" in window


def test_draft_only_env_wired_from_the_dispatch_input():
    assert "DRAFT_ONLY: ${{ github.event.inputs.draft_only }}" in WORKFLOW


def test_only_the_explicit_literal_false_turns_off_draft_only():
    # covers scheduled runs too: no workflow_dispatch inputs at all means
    # DRAFT_ONLY is empty, which must NOT be treated as "false".
    idx = WORKFLOW.index('if [ "$DRAFT_ONLY" = "false" ]; then')
    window = WORKFLOW[idx:idx + 150]
    assert 'DRAFT_ONLY="false"' in window
    assert 'DRAFT_ONLY="true"' in window


def test_produced_json_write_is_skipped_in_draft_only_mode():
    idx = WORKFLOW.index("PRODUCED.json for article")
    window = WORKFLOW[max(0, idx - 400):idx + 400]
    assert 'if [ "$DRAFT_ONLY" = "true" ]; then' in window
    assert "SPRINT 9 publish-invariant: terminal marker written ONLY after QA+editor+gate all pass." in window
    assert "json.dump({'post_id': '${POST_ID}', 'article': ${ARTICLE_NUM}, 'produced': True}" in window


def test_articles_produced_counter_still_increments_regardless_of_draft_only():
    # draft-only must not make a genuinely successful article look like a
    # failure -- it only withholds the registry-promotion marker.
    gate_idx = WORKFLOW.index('--output "${ARTICLE_DIR}/production_gate_result.json" && {')
    draft_only_idx = WORKFLOW.index('if [ "$DRAFT_ONLY" = "true" ]; then', gate_idx)
    counter_idx = WORKFLOW.index("ARTICLES_PRODUCED=$((ARTICLES_PRODUCED+1))", gate_idx)
    assert gate_idx < counter_idx < draft_only_idx


def test_reconcile_rollback_logic_is_untouched():
    # the existing reconcile step already rolls a topic back to candidate
    # when PRODUCED.json is absent -- draft_only relies on this unchanged.
    assert "Reconcile topic registry (published on success, rollback on failure)" in WORKFLOW
    assert "PYTHONPATH=. python -m agents.agent_01_seo_research --reconcile --output-dir output" in WORKFLOW
