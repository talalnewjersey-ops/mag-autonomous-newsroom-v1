"""scripts/production_batch_loop.sh extraction (2026-07-12).

The "Batch Loop -- 3 Articles Sequential" step's inline `run:` block hit
GitHub's ~21000-char single-expression limit TWICE: once at PR #73 (fixed by
trimming comments, ~650 chars margin), and again on 2026-07-11 when a
verbose comment pushed it to 20950 chars -- GitHub silently rejected the
ENTIRE workflow file as invalid and skipped that day's 06:00 UTC scheduled
run (see AUDIT-LOG.md). #73 considered extracting this to an external script
and deferred it ("not in a rush") -- two outages from the same limit is the
signal to stop deferring it.

This is a behavior-preserving MOVE, not a rewrite: the batch loop's actual
orchestration logic (agent calls, gate retries, tier assignment) is
unchanged, verbatim, just packaged as scripts/production_batch_loop.sh
instead of inline YAML. The one deliberate exception is a real bug fixed in
passing (see test_max_articles_resolution_no_longer_references_the_dead_
needs_detect_job below): the old inline expression referenced
`needs.detect.outputs.max_articles`, a job named "detect" that does not
exist (the job is "route-trigger"; "detect" is only its step id) -- so that
fallback was always empty, and every scheduled run silently used the
literal `3` default regardless of route-trigger's real per-slot output
(e.g. the `1` set for the rodage phase, 2026-07-11). Fixed by passing both
values in as separate env vars and resolving the fallback chain in bash.

`set -eo pipefail` at the top of the extracted script reproduces EXACTLY
what GitHub Actions was already doing implicitly for the inline `run:`
block (its default shell for a bash step is `bash --noprofile --norc -eo
pipefail {0}`) -- a bare `bash scripts/production_batch_loop.sh` invocation
does NOT inherit that from the parent step, so it has to be set explicitly
or unguarded commands would silently stop aborting on failure.

Three isolated, pure decision functions (resolve_draft_only,
resolve_max_articles, resolve_article_tier) were pulled out of the main
loop body specifically so they're unit-testable without running the full
agent pipeline -- source the script with PRODUCTION_BATCH_LOOP_SOURCE_ONLY=1
to get the functions without executing the loop below them.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SCRIPT_PATH = os.path.join(ROOT, "scripts", "production_batch_loop.sh")


def _run_bash(snippet, env_overrides=None):
    """Source the script in SOURCE_ONLY mode, then run `snippet`, returning
    (stdout, returncode). env_overrides are added on top of a minimal clean
    env so tests don't depend on the caller's shell state."""
    env = {"PATH": os.environ.get("PATH", ""), "PRODUCTION_BATCH_LOOP_SOURCE_ONLY": "1"}
    if env_overrides:
        env.update(env_overrides)
    script = f'source "{SCRIPT_PATH}"\n{snippet}\n'
    result = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


# ---------------------------------------------------------------- the script exists, is valid bash

def test_script_file_exists_and_is_executable():
    assert os.path.exists(SCRIPT_PATH)
    assert os.access(SCRIPT_PATH, os.X_OK), "scripts/production_batch_loop.sh must be executable (chmod +x)"


def test_script_has_valid_bash_syntax():
    result = subprocess.run(["bash", "-n", SCRIPT_PATH], capture_output=True, text=True)
    assert result.returncode == 0, f"bash -n failed: {result.stderr}"


def test_script_sets_eo_pipefail_to_match_githubs_implicit_default():
    with open(SCRIPT_PATH, encoding="utf-8") as f:
        src = f.read()
    assert "set -eo pipefail" in src


def test_sourcing_with_source_only_flag_does_not_run_the_batch_loop():
    # Without the flag being respected, sourcing this (no MAX_ARTICLES_INPUT/
    # MAX_ARTICLES_ROUTE/DRAFT_ONLY/FORCE_OPPORTUNITY_TIER/TOPIC_OVERRIDE set)
    # would attempt to invoke `python -m agents.agent_01_seo_research` for
    # real -- this proves the guard actually short-circuits before that.
    out, code = _run_bash("echo SOURCED_OK")
    assert code == 0
    assert out == "SOURCED_OK"


# ---------------------------------------------------------------- resolve_draft_only

def test_draft_only_empty_defaults_to_true():
    out, _ = _run_bash('resolve_draft_only ""')
    assert out == "true"


def test_draft_only_explicit_true_stays_true():
    out, _ = _run_bash('resolve_draft_only "true"')
    assert out == "true"


def test_draft_only_explicit_false_is_the_only_way_to_get_false():
    out, _ = _run_bash('resolve_draft_only "false"')
    assert out == "false"


def test_draft_only_garbage_value_defaults_to_true():
    # Anything but the literal "false" is draft-only -- a typo'd override
    # must fail SAFE, not fail open into a real publish.
    out, _ = _run_bash('resolve_draft_only "FALSE"')
    assert out == "true"


# ---------------------------------------------------------------- resolve_max_articles

def test_max_articles_input_takes_priority_over_route_output():
    out, _ = _run_bash('resolve_max_articles "3" "1"')
    assert out == "3"


def test_max_articles_falls_back_to_route_output_when_input_empty():
    # The real rodage case: a scheduled run has no workflow_dispatch input,
    # so this is what makes route-trigger's real per-slot value (1) actually
    # reach the batch loop.
    out, _ = _run_bash('resolve_max_articles "" "1"')
    assert out == "1"


def test_max_articles_falls_back_to_three_when_both_empty():
    out, _ = _run_bash('resolve_max_articles "" ""')
    assert out == "3"


def test_max_articles_clamped_above_three():
    out, _ = _run_bash('resolve_max_articles "99" ""')
    assert out == "3"


def test_max_articles_clamped_below_one():
    out, _ = _run_bash('resolve_max_articles "0" ""')
    assert out == "1"


def test_max_articles_non_numeric_input_falls_back_to_three():
    out, _ = _run_bash('resolve_max_articles "abc" ""')
    assert out == "3"


def test_max_articles_resolution_no_longer_references_the_dead_needs_detect_job():
    # Regression lock for the real bug found during extraction: the OLD
    # inline expression was `${{ github.event.inputs.max_articles ||
    # needs.detect.outputs.max_articles || 3 }}` -- "detect" is a STEP id,
    # not a job id (the job is "route-trigger"), so that fallback was
    # always empty and every scheduled run got the literal `3` regardless
    # of route-trigger's real output.
    # Both files' own comments may still MENTION the old broken reference
    # for context -- what must never reappear is the ACTIVE GH Actions
    # expression using it (i.e. inside a `${{ ... }}`), only possible in
    # the workflow YAML (a plain bash script has no such expression syntax).
    with open(os.path.join(ROOT, ".github/workflows/production_v2.yml"), encoding="utf-8") as f:
        workflow_src = f.read()
    assert "${{ needs.detect" not in workflow_src
    assert "needs.route-trigger.outputs.max_articles" in workflow_src


# ---------------------------------------------------------------- resolve_article_tier

def test_tier_high_score_is_pillar_when_force_disabled():
    out, _ = _run_bash('resolve_article_tier "90" "false"')
    assert out == "PILLAR"


def test_tier_mid_score_is_standard_when_force_disabled():
    out, _ = _run_bash('resolve_article_tier "75" "false"')
    assert out == "STANDARD"


def test_tier_low_score_is_opportunity_regardless_of_force():
    out, _ = _run_bash('resolve_article_tier "50" "false"')
    assert out == "OPPORTUNITY"


def test_tier_force_flag_overrides_a_high_score_to_opportunity():
    # The rodage safety behavior: STANDARD/PILLAR fail GATE LENGTH even
    # after retry (AUDIT-LOG.md) -- force_opportunity_tier pins everything
    # to OPPORTUNITY regardless of the real revenue score.
    out, _ = _run_bash('resolve_article_tier "90" ""')
    assert out == "OPPORTUNITY"


def test_tier_force_flag_empty_value_still_forces_opportunity():
    # Same safe-default pattern as DRAFT_ONLY: a scheduled run has no
    # workflow_dispatch inputs at all, so FORCE_OPPORTUNITY_TIER is empty --
    # must still force OPPORTUNITY, not silently fall through to the
    # revenue-score tier.
    out, _ = _run_bash('resolve_article_tier "90" "garbage"')
    assert out == "OPPORTUNITY"


# ---------------------------------------------------------------- workflow wiring

def test_workflow_invokes_the_extracted_script_with_a_short_run_block():
    import yaml
    with open(os.path.join(ROOT, ".github/workflows/production_v2.yml"), encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if step.get("name", "").startswith("Batch Loop"):
                assert step["run"].strip() == "bash scripts/production_batch_loop.sh"
                assert "MAX_ARTICLES_INPUT" in step.get("env", {})
                assert "MAX_ARTICLES_ROUTE" in step.get("env", {})
                return
    assert False, "could not find the 'Batch Loop' step in production_v2.yml"
