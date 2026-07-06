"""RETRY SAFETY (2026-07-06): the structural-completeness gate that stops a
retry from shipping something worse than the original rejected draft -- the
real control-run case was a retry that fixed G-Substance's sourcing
complaint but dropped the entire FAQ section (13 H2s -> 8).
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import structure_completeness_gate as scg  # noqa: E402


def _draft(h2_titles, faq=True, filler_words=500):
    body = " ".join(["word"] * filler_words)
    parts = [f"## {t}\n\n{body}\n" for t in h2_titles]
    if faq:
        parts.append("## FAQ\n\n### Is this a question?\nYes.\n")
    return "\n".join(parts)


def test_metrics_counts_h2_and_faq_and_words():
    text = _draft(["Intro", "Body"], faq=True, filler_words=10)
    m = scg._metrics(text)
    assert m["h2_count"] == 3  # Intro, Body, FAQ
    assert m["has_faq"] is True
    assert m["word_count"] > 0


def test_metrics_detects_missing_faq():
    text = _draft(["Intro", "Body"], faq=False, filler_words=10)
    m = scg._metrics(text)
    assert m["has_faq"] is False


def test_is_worse_flags_faq_regression():
    before = {"h2_count": 13, "has_faq": True, "word_count": 4500}
    after = {"h2_count": 8, "has_faq": False, "word_count": 4204}
    worse, reasons = scg.is_worse(before, after)
    assert worse
    assert any("FAQ" in r for r in reasons)
    assert any("h2_count" in r for r in reasons)


def test_is_worse_false_when_structure_preserved_or_improved():
    before = {"h2_count": 9, "has_faq": True, "word_count": 4000}
    after = {"h2_count": 10, "has_faq": True, "word_count": 4100}
    worse, reasons = scg.is_worse(before, after)
    assert not worse
    assert reasons == []


def test_is_worse_tolerates_word_count_within_20_percent():
    before = {"h2_count": 9, "has_faq": True, "word_count": 4000}
    after = {"h2_count": 9, "has_faq": True, "word_count": 3250}  # -18.75%
    worse, reasons = scg.is_worse(before, after)
    assert not worse


def test_is_worse_flags_word_count_drop_beyond_20_percent():
    before = {"h2_count": 9, "has_faq": True, "word_count": 4000}
    after = {"h2_count": 9, "has_faq": True, "word_count": 3000}  # -25%
    worse, reasons = scg.is_worse(before, after)
    assert worse
    assert any("word_count" in r for r in reasons)


def test_real_control_run_case_is_caught():
    # The actual numbers from the real regression: 13->8 H2s, FAQ lost.
    before = {"h2_count": 13, "has_faq": True, "word_count": 4855}
    after = {"h2_count": 8, "has_faq": False, "word_count": 4204}
    worse, reasons = scg.is_worse(before, after)
    assert worse


# ---------------------------------------------------------------- CLI end-to-end

def _run_cli(args):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts/structure_completeness_gate.py")] + args,
        capture_output=True, text=True,
    )


def test_cli_snapshot_then_compare_worse_exits_1(tmp_path):
    rejected = tmp_path / "rejected.md"
    rejected.write_text(_draft(["A", "B", "C", "D", "E"], faq=True, filler_words=200), encoding="utf-8")
    snap = tmp_path / "snapshot.json"
    r1 = _run_cli(["--input", str(rejected), "--snapshot", str(snap)])
    assert r1.returncode == 0
    assert json.loads(snap.read_text())["has_faq"] is True

    retry = tmp_path / "retry.md"
    retry.write_text(_draft(["A", "B"], faq=False, filler_words=200), encoding="utf-8")  # lost sections + FAQ
    r2 = _run_cli(["--input", str(retry), "--compare", str(snap)])
    assert r2.returncode == 1
    assert "RETRY REGRESSION" in r2.stdout


def test_cli_compare_ok_exits_0(tmp_path):
    rejected = tmp_path / "rejected.md"
    rejected.write_text(_draft(["A", "B"], faq=True, filler_words=200), encoding="utf-8")
    snap = tmp_path / "snapshot.json"
    _run_cli(["--input", str(rejected), "--snapshot", str(snap)])

    retry = tmp_path / "retry.md"
    retry.write_text(_draft(["A", "B", "C"], faq=True, filler_words=200), encoding="utf-8")  # improved
    r2 = _run_cli(["--input", str(retry), "--compare", str(snap)])
    assert r2.returncode == 0


def test_cli_compare_missing_snapshot_allows_through(tmp_path):
    retry = tmp_path / "retry.md"
    retry.write_text(_draft(["A"], faq=True, filler_words=50), encoding="utf-8")
    r = _run_cli(["--input", str(retry), "--compare", str(tmp_path / "does_not_exist.json")])
    assert r.returncode == 0
