"""
Sprint 1 — Regression tests proving RCA-005 is fixed.

These tests invoke the REAL agent CLIs (agents.agent_12_quality_assurance and
agents.agent_13_chief_editor) as subprocesses with ANTHROPIC_API_KEY unset, so
the deterministic heuristic decision path is exercised (no network, no API cost).

What we prove:
  * agent_12 exits 1 when QA fails (short / no FAQ / no image)  -> RCA-005
  * agent_12 exits 0 on a conformant article                    -> non-regression
  * agent_13 exits 1 (NEEDS_REVISION) when qa_report status=FAIL
  * agent_13 exits 0 (READY_TO_PUBLISH) when qa_report status=PASS + words OK
  * Two-tier word floor: ~1600 words PASS as STANDARD, FAIL as PILLAR (<3000),
    proving the hardcoded 5000 floor no longer gates the decision.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_agent(module, args, env_extra=None):
    """Run 'python -m <module> <args>' from the repo root, API key UNSET.
    Returns (returncode, stdout+stderr)."""
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)  # force deterministic heuristic path
    env["PYTHONPATH"] = str(REPO_ROOT)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode, (proc.stdout + proc.stderr)


def _write_article(path, words, faqs):
    """Build a Markdown article with a given word count and FAQ question count.
    FAQ questions are H3 lines ending in '?' (matches agent regex ^### .+\?)."""
    lines = ["title: Test Article", "", "# Test Article", ""]
    body_words = max(words - 4, 0)
    lines.append(" ".join(["word"] * body_words))
    lines.append("")
    if faqs > 0:
        lines.append("## Frequently Asked Questions")
        for i in range(faqs):
            lines.append("### Question number {} about banking?".format(i))
            lines.append("Answer text here.")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_image_validation(path, count):
    path.write_text(json.dumps({"images_produced": count}), encoding="utf-8")


# ---------------------------------------------------------------------------
# TEST 2 — RCA-005 proof: QA failure must produce a non-zero exit.
# ---------------------------------------------------------------------------
def test_agent12_blocks_on_failed_qa(tmp_path):
    article = tmp_path / "article_draft.md"
    _write_article(article, words=100, faqs=0)
    img = tmp_path / "image_validation_report.json"
    _write_image_validation(img, 0)
    out = tmp_path / "qa_report.json"

    code, log = _run_agent(
        "agents.agent_12_quality_assurance",
        ["--article", str(article),
         "--image-validation", str(img),
         "--output", str(out),
         "--article-type", "STANDARD"],
    )
    report = json.loads(out.read_text())
    assert report["status"] == "FAIL", "expected FAIL, got {}".format(report["status"])
    assert code == 1, "RCA-005 REGRESSION: agent_12 must exit 1 on QA fail, got {}\n{}".format(code, log)


# ---------------------------------------------------------------------------
# TEST 3 — Non-regression: a conformant article must pass and exit 0.
# ---------------------------------------------------------------------------
def test_agent12_passes_on_conformant_article(tmp_path):
    article = tmp_path / "article_draft.md"
    _write_article(article, words=1600, faqs=8)
    img = tmp_path / "image_validation_report.json"
    _write_image_validation(img, 5)
    out = tmp_path / "qa_report.json"

    code, log = _run_agent(
        "agents.agent_12_quality_assurance",
        ["--article", str(article),
         "--image-validation", str(img),
         "--output", str(out),
         "--article-type", "STANDARD"],
    )
    report = json.loads(out.read_text())
    assert report["status"] == "PASS", "expected PASS, got {}\n{}".format(report["status"], log)
    assert code == 0, "agent_12 should exit 0 on pass, got {}\n{}".format(code, log)


# ---------------------------------------------------------------------------
# TEST 4 — Two-tier word floor. Proves 5000 is no longer the floor.
# ---------------------------------------------------------------------------
def test_two_tier_word_floor(tmp_path):
    img = tmp_path / "image_validation_report.json"
    _write_image_validation(img, 5)

    art_std = tmp_path / "std.md"
    _write_article(art_std, words=1600, faqs=8)
    out_std = tmp_path / "qa_std.json"
    code_std, log_std = _run_agent(
        "agents.agent_12_quality_assurance",
        ["--article", str(art_std), "--image-validation", str(img),
         "--output", str(out_std), "--article-type", "STANDARD"],
    )
    assert code_std == 0, "1600w should PASS STANDARD, exit {}\n{}".format(code_std, log_std)

    out_pil = tmp_path / "qa_pil.json"
    code_pil, log_pil = _run_agent(
        "agents.agent_12_quality_assurance",
        ["--article", str(art_std), "--image-validation", str(img),
         "--output", str(out_pil), "--article-type", "PILLAR"],
    )
    assert code_pil == 1, "1600w should FAIL PILLAR (<3000), exit {}\n{}".format(code_pil, log_pil)
    assert code_std == 0 and code_pil == 1


# ---------------------------------------------------------------------------
# TEST 3b — agent_13 Chief Editor: blocks on QA=FAIL, approves on QA=PASS.
# ---------------------------------------------------------------------------
def test_agent13_blocks_on_qa_fail(tmp_path):
    article = tmp_path / "article_draft.md"
    _write_article(article, words=6000, faqs=8)
    qa = tmp_path / "qa_report.json"
    qa.write_text(json.dumps({"status": "FAIL", "overall_score": 40}), encoding="utf-8")
    out = tmp_path / "editor_report.json"

    code, log = _run_agent(
        "agents.agent_13_chief_editor",
        ["--qa-report", str(qa), "--article", str(article),
         "--output", str(out), "--article-type", "STANDARD"],
    )
    report = json.loads(out.read_text())
    assert report["decision"] == "NEEDS_REVISION", "got {}\n{}".format(report["decision"], log)
    assert report["approved_for_publication"] is False
    assert code == 1, "agent_13 must exit 1 when QA failed, got {}\n{}".format(code, log)


def test_agent13_approves_on_qa_pass(tmp_path):
    article = tmp_path / "article_draft.md"
    _write_article(article, words=1600, faqs=8)
    qa = tmp_path / "qa_report.json"
    qa.write_text(json.dumps({"status": "PASS", "overall_score": 80}), encoding="utf-8")
    out = tmp_path / "editor_report.json"

    code, log = _run_agent(
        "agents.agent_13_chief_editor",
        ["--qa-report", str(qa), "--article", str(article),
         "--output", str(out), "--article-type", "STANDARD"],
    )
    report = json.loads(out.read_text())
    assert report["decision"] == "READY_TO_PUBLISH", "got {}\n{}".format(report["decision"], log)
    assert report["approved_for_publication"] is True
    assert code == 0, "agent_13 should exit 0 on approve, got {}\n{}".format(code, log)
