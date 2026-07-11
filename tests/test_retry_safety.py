"""RETRY SAFETY (2026-07-06): the retry mechanism must never ship an article
worse than the one it replaced. Real control-run finding: a retry that fixed
G-Substance's sourcing complaint also silently dropped the entire FAQ section
(13 H2s -> 8). Two fixes, both covered here:
  (a) the writer's retry prompt demands a TARGETED fix that preserves
      everything else (structure, FAQ) -- see 2026-07-11 note below.
  (b) production_v2.yml snapshots the rejected draft's structure before each
      retry and compares after -- a regression is treated as a full failure,
      never falling back to publishing either version.

RECALIBRATED (2026-07-11, AUDIT-LOG.md): the original retry prompt ALSO
forbade shortening anything at all ("the overall length must all still be
present... a fix that removes content elsewhere is WORSE than the
original"). Combined with structure_completeness_gate.py's word-count floor
(>20% drop only, NO ceiling -- "more words is always fine"), every retry was
a one-way ratchet toward MORE words. Confirmed directly via a real retry's
own pre_retry_snapshot.json: a G3 (anti-repetition) retry took a 4412w
rejected draft to a 4486w accepted one -- fixing a DUPLICATE made the
article LONGER. The real incident this guards against was losing a WHOLE
SECTION (FAQ gone), not general length -- the prompt now narrows the
protection to that actual incident and explicitly allows trimming/merging
the specific flagged duplicate. The structure gate itself already tolerated
this (word_count within 20%, h2_count/FAQ preserved) -- only the prompt
wording was overly broad; see test_g3_retry_can_legitimately_shorten_the_
article below.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import gate_feedback  # noqa: E402
import structure_completeness_gate as scg  # noqa: E402

SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()
WORKFLOW = open(os.path.join(ROOT, ".github/workflows/production_v2.yml"), encoding="utf-8").read()


def test_retry_prompt_demands_targeted_fix_not_blind_regeneration():
    assert "FIX THIS SPECIFICALLY" in SRC
    assert "SMALLEST possible change" in SRC
    assert "FAQ section" in SRC
    assert "Only dropping an entire section" in SRC


def test_retry_prompt_no_longer_forbids_shortening_generally():
    # the 2026-07-11 real-run finding: this exact wording made every retry
    # grow, never shrink -- must not regress.
    assert "the overall length must all" not in SRC
    assert "removes content elsewhere is WORSE than the original" not in SRC


def test_retry_prompt_explicitly_allows_merging_a_duplicate():
    assert "the correct fix is to MERGE or" in SRC
    assert "SHORTEN that passage" in SRC
    assert "removing a duplicate is a valid fix, not a regression" in SRC


def test_workflow_snapshots_before_every_content_gate_retry():
    # one snapshot call per gate that can trigger a retry (G-Substance, G3, A, B)
    assert WORKFLOW.count(
        'structure_completeness_gate.py --input "${ARTICLE_DIR}/agent_04/article_draft.md" --snapshot'
    ) == 4


# ---------------- G3 feedback: merge/remove is now offered as a valid fix ----------------

def test_g3_feedback_offers_removal_as_a_valid_fix_not_only_reword():
    import json
    import tempfile
    report = {"duplicate_phrases": [{"phrase": "same driving history claim repeated", "blocking": True}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(report, f)
        path = f.name
    try:
        feedback = gate_feedback.g3(path)
    finally:
        os.unlink(path)
    assert "removing/merging the duplicate" in feedback
    assert "valid, preferred fix, not a regression" in feedback


# ---------------- THE REQUESTED TEST: a G3 retry CAN legitimately shorten ----------------

def test_g3_retry_can_legitimately_shorten_the_article():
    # Simulates the real scenario: a rejected draft has a duplicated passage
    # across two sections (G3 blocking). The retry's fix is to MERGE/REMOVE
    # the duplicate -- the result is shorter, but no section is lost and the
    # drop is well within the gate's own 20% tolerance. Must NOT be flagged
    # as a regression.
    rejected_word_count = 4412  # real number from pre_retry_snapshot.json, run 29134940191
    duplicate_passage_word_count = 80  # a realistic repeated paragraph
    before = {"h2_count": 10, "has_faq": True, "word_count": rejected_word_count}
    after = {
        "h2_count": 10,  # same sections, none dropped
        "has_faq": True,  # FAQ still present
        "word_count": rejected_word_count - duplicate_passage_word_count,  # SHORTER than the input
    }
    worse, reasons = scg.is_worse(before, after)
    assert after["word_count"] < before["word_count"], "the fix must genuinely be shorter than the input"
    assert worse is False, f"a legitimate duplicate-trim was flagged as a regression: {reasons}"
    assert reasons == []


def test_g3_retry_growing_instead_of_shrinking_still_passes_too():
    # the gate must not swing the other way and start punishing growth --
    # "more words is always fine" stays true; only the PROMPT no longer
    # forces growth as the only safe option.
    before = {"h2_count": 10, "has_faq": True, "word_count": 4412}
    after = {"h2_count": 10, "has_faq": True, "word_count": 4486}  # the real, previously-forced outcome
    worse, reasons = scg.is_worse(before, after)
    assert worse is False


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


# ---------------- gate report preservation per attempt (2026-07-11) ----------------
# Without this, the attempt-0 report that actually TRIGGERED a retry is
# overwritten by attempt 1 and lost from the uploaded artifact -- the next
# investigation of this kind would be back to inferring from word-count
# deltas instead of reading the real flagged content (e.g. G3's
# duplicate_phrases). One preserved copy per gate that can trigger a retry.

def test_workflow_preserves_g_substance_report_per_attempt():
    assert 'cp "${ARTICLE_DIR}/agent_04/g_substance_report.json" "${ARTICLE_DIR}/agent_04/g_substance_report_attempt0.json"' in WORKFLOW


def test_workflow_preserves_g3_report_per_attempt():
    assert 'cp "${ARTICLE_DIR}/agent_04/g3_report.json" "${ARTICLE_DIR}/agent_04/g3_report_attempt0.json"' in WORKFLOW


def test_workflow_preserves_fact_check_report_per_attempt():
    assert 'cp "${ARTICLE_DIR}/agent_05/fact_check_report.json" "${ARTICLE_DIR}/agent_05/fact_check_report_attempt0.json"' in WORKFLOW


def test_workflow_preserves_eeat_report_per_attempt():
    assert 'cp "${ARTICLE_DIR}/agent_06/eeat_report.json" "${ARTICLE_DIR}/agent_06/eeat_report_attempt0.json"' in WORKFLOW


def test_all_four_report_preservation_copies_are_fail_soft():
    # "|| true" -- a missing report (e.g. gate never ran) must never break the retry loop.
    for line in [
        'cp "${ARTICLE_DIR}/agent_04/g_substance_report.json" "${ARTICLE_DIR}/agent_04/g_substance_report_attempt0.json" || true',
        'cp "${ARTICLE_DIR}/agent_04/g3_report.json" "${ARTICLE_DIR}/agent_04/g3_report_attempt0.json" || true',
        'cp "${ARTICLE_DIR}/agent_05/fact_check_report.json" "${ARTICLE_DIR}/agent_05/fact_check_report_attempt0.json" || true',
        'cp "${ARTICLE_DIR}/agent_06/eeat_report.json" "${ARTICLE_DIR}/agent_06/eeat_report_attempt0.json" || true',
    ]:
        assert line in WORKFLOW


def test_report_preservation_copy_happens_before_continue():
    # each cp must run BEFORE the "continue" that restarts the loop for attempt 1
    # (the source file must still exist -- attempt 1 hasn't started writing yet).
    for report_var, cp_snippet, gate_label in [
        ("g_substance_report.json", 'cp "${ARTICLE_DIR}/agent_04/g_substance_report.json"', "GATE G-SUBSTANCE FAIL (attempt 1/2)"),
        ("g3_report.json", 'cp "${ARTICLE_DIR}/agent_04/g3_report.json"', "GATE G3 FAIL (attempt 1/2)"),
        ("fact_check_report.json", 'cp "${ARTICLE_DIR}/agent_05/fact_check_report.json"', "GATE A FAIL (attempt 1/2)"),
        ("eeat_report.json", 'cp "${ARTICLE_DIR}/agent_06/eeat_report.json"', "GATE B FAIL (attempt 1/2)"),
    ]:
        fail_idx = WORKFLOW.index(gate_label)
        cp_idx = WORKFLOW.index(cp_snippet, fail_idx)
        continue_idx = WORKFLOW.index("\n                continue", cp_idx)
        assert fail_idx < cp_idx < continue_idx, report_var


def test_upload_step_captures_the_whole_article_dir_including_attempt0_files():
    # the attempt0-suffixed files need no separate upload wiring -- the
    # existing step already globs the whole per-article output directory.
    assert "output/article_1/\n" in WORKFLOW
    upload_idx = WORKFLOW.index("Upload article reports")
    path_idx = WORKFLOW.index("output/article_1/", upload_idx)
    assert path_idx - upload_idx < 400  # the path line is right there, not some unrelated later match
