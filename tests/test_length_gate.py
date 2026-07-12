"""GATE LENGTH (2026-07-11): symmetric ceiling counterpart to agent_04's
floor-only word-count expansion (_write_article_standalone only ever ADDS
words when under min_words -- nothing checks an overshoot at generation
time). agent_12's own tier-relative check catches an overshoot too, but
sits OUTSIDE production_v2.yml's retry loop (GATE QA/EDITOR are single-shot,
not retried) -- real finding: witness run 5, article 2
(us-send-money-to-india, STANDARD tier), 5232w vs a 4000w target (+30.8%),
had zero chance to self-correct before landing on that non-retriable gate.

Offline, no network, no API key.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import length_gate  # noqa: E402
import gate_feedback  # noqa: E402
import structure_completeness_gate as scg  # noqa: E402

WORKFLOW = open(os.path.join(ROOT, ".github/workflows/production_v2.yml"), encoding="utf-8").read()
# 2026-07-12: the batch loop's bash logic was extracted out of this YAML
# into its own script -- see tests/test_production_batch_loop.py for the
# extraction itself. Tests below that check bash CONTENT (not YAML wiring)
# now read the script instead.
BATCH_LOOP_SCRIPT = open(os.path.join(ROOT, "scripts", "production_batch_loop.sh"), encoding="utf-8").read()


# ---------------- evaluate(): tier-relative ceiling, same tolerance as agent_12 ----------------

def test_tolerance_matches_agent_12_exactly():
    src = open(os.path.join(ROOT, "agents/agent_12_quality_assurance.py"), encoding="utf-8").read()
    assert "_WORD_COUNT_TOLERANCE = 0.10" in src
    assert length_gate.WORD_COUNT_TOLERANCE == 0.10


def test_standard_tier_ceiling_is_4400():
    # STANDARD target_words=4000, +10% tolerance -> ceiling 4400.
    result = length_gate.evaluate(word_count=4400, article_type="STANDARD")
    assert result["ceiling_words"] == 4400
    assert result["over_ceiling"] is False


def test_real_run5_article2_case_5232w_standard_fails_the_gate():
    # the exact real numbers that exposed the gap: STANDARD tier, 5232w actual.
    result = length_gate.evaluate(word_count=5232, article_type="STANDARD")
    assert result["over_ceiling"] is True
    assert result["ceiling_words"] == 4400
    assert result["over_by_words"] == 5232 - 4400


def test_pillar_tier_ceiling_is_4620():
    # PILLAR target_words=4200, +10% -> 4620.
    result = length_gate.evaluate(word_count=4620, article_type="PILLAR")
    assert result["ceiling_words"] == 4620
    assert result["over_ceiling"] is False
    over = length_gate.evaluate(word_count=4621, article_type="PILLAR")
    assert over["over_ceiling"] is True


def test_at_exactly_the_ceiling_is_not_a_failure():
    result = length_gate.evaluate(word_count=4400, article_type="STANDARD")
    assert result["over_ceiling"] is False  # strictly greater-than, not >=


def test_reuses_agent_04s_own_tier_config_not_a_third_copy_of_the_numbers():
    from agents.agent_04_article_writer import _get_tier_config
    assert length_gate.evaluate(4000, "OPPORTUNITY")["target_words"] == _get_tier_config("OPPORTUNITY")["target_words"]


# ---------------- CLI: exit code + report file ----------------

def test_cli_exits_nonzero_and_writes_report_on_overshoot():
    with tempfile.TemporaryDirectory() as d:
        draft = os.path.join(d, "article_draft.md")
        report = os.path.join(d, "length_report.json")
        with open(draft, "w", encoding="utf-8") as f:
            f.write(" ".join(["word"] * 5232))
        sys.argv = ["length_gate.py", "--input", draft, "--article-type", "STANDARD", "--output", report]
        try:
            length_gate.main()
            assert False, "expected SystemExit"
        except SystemExit as e:
            assert e.code == 1
        data = json.load(open(report))
        assert data["over_ceiling"] is True
        assert data["word_count"] == 5232


def test_cli_exits_zero_when_under_ceiling():
    with tempfile.TemporaryDirectory() as d:
        draft = os.path.join(d, "article_draft.md")
        report = os.path.join(d, "length_report.json")
        with open(draft, "w", encoding="utf-8") as f:
            f.write(" ".join(["word"] * 4100))
        sys.argv = ["length_gate.py", "--input", draft, "--article-type", "STANDARD", "--output", report]
        try:
            length_gate.main()
        except SystemExit as e:
            assert e.code == 0


# ---------------- gate_feedback.length(): retry prompt text ----------------

def test_length_feedback_names_the_overshoot_and_protects_structure():
    report = {"word_count": 5232, "ceiling_words": 4400, "over_by_words": 832}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(report, f)
        path = f.name
    try:
        feedback = gate_feedback.build_feedback("length", path)
    finally:
        os.unlink(path)
    assert "5232w exceeds the ceiling of 4400w by 832w" in feedback
    assert "Do NOT" in feedback
    assert "FAQ section" in feedback
    assert "comparison table" in feedback


# ---------------- workflow wiring ----------------

def test_workflow_wires_length_gate_inside_the_retry_loop_before_g_substance():
    length_idx = BATCH_LOOP_SCRIPT.index("Phase 4.442: Length Gate")
    g_substance_idx = BATCH_LOOP_SCRIPT.index("Phase 4.45: G-Substance Gate")
    loop_start = BATCH_LOOP_SCRIPT.index("for RETRY_ATTEMPT in 0 1; do")
    loop_end = BATCH_LOOP_SCRIPT.index("\n  break\n  done")
    assert loop_start < length_idx < g_substance_idx < loop_end


def test_workflow_length_gate_retries_once_then_fails_hard():
    idx = BATCH_LOOP_SCRIPT.index("Phase 4.442: Length Gate")
    window = BATCH_LOOP_SCRIPT[idx:idx + 1200]
    assert 'GATE LENGTH FAIL (attempt 1/2)' in window
    assert 'GATE LENGTH FAIL (attempt 2/2, retry exhausted)' in window
    assert 'ARTICLES_FAILED=$((ARTICLES_FAILED+1)); continue 2' in window
    assert '--gate length --report' in window


def test_workflow_snapshots_before_length_gate_retry_like_the_other_gates():
    idx = BATCH_LOOP_SCRIPT.index("Phase 4.442: Length Gate")
    window = BATCH_LOOP_SCRIPT[idx:idx + 1200]
    assert 'structure_completeness_gate.py --input "$DRAFT" --snapshot' in window


def test_workflow_preserves_length_report_per_attempt():
    assert 'cp "${ARTICLE_DIR}/agent_04/length_report.json" "${ARTICLE_DIR}/agent_04/length_report_attempt0.json" || true' in BATCH_LOOP_SCRIPT


# ---------------- interaction with the retry structural-completeness check ----------------

def test_real_case_shortening_to_the_ceiling_is_not_flagged_as_a_regression():
    # 5232w -> under the 4400w ceiling is a ~16% drop -- must stay under the
    # structural-completeness gate's own 20% "worse" floor (see
    # test_retry_safety.py::test_g3_retry_can_legitimately_shorten_the_article
    # for the sibling case on G3).
    before = {"h2_count": 11, "has_faq": True, "word_count": 5232}
    after = {"h2_count": 11, "has_faq": True, "word_count": 4390}
    worse, reasons = scg.is_worse(before, after)
    drop_pct = (before["word_count"] - after["word_count"]) / before["word_count"]
    assert drop_pct < 0.20
    assert worse is False, f"a legitimate length-gate trim was flagged as a regression: {reasons}"
