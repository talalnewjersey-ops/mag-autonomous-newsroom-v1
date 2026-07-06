"""gate_feedback.py (2026-07-06): builds the writer-facing retry feedback
string from each gate's own JSON report. Extracted out of production_v2.yml's
YAML (a multi-line `python3 -c "..."` embedded in a YAML block scalar is
fragile -- every line must satisfy both YAML's block-indentation rule and
Python's column-0 module-level rule, which conflict) into a real, testable
script.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import gate_feedback as gf  # noqa: E402


def _write_json(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_g_substance_uses_real_reasons(tmp_path):
    path = _write_json(tmp_path, "g_substance_report.json",
                        {"reasons": ["2 unsourced figure(s) survived soften"]})
    msg = gf.g_substance(path)
    assert "2 unsourced figure(s) survived soften" in msg
    assert "GATE G-SUBSTANCE" in msg


def test_g_substance_falls_back_on_missing_file(tmp_path):
    msg = gf.g_substance(str(tmp_path / "does_not_exist.json"))
    assert "hollow article" in msg


def test_g3_lists_blocking_phrases_only(tmp_path):
    path = _write_json(tmp_path, "g3_report.json", {
        "duplicate_phrases": [
            {"phrase": "have the right to open a personal bank account", "blocking": True},
            {"phrase": "some tolerated synthesis overlap", "blocking": False},
        ]
    })
    msg = gf.g3(path)
    assert "have the right to open a personal bank account" in msg
    assert "some tolerated synthesis overlap" not in msg


def test_g3_falls_back_when_no_blocking_phrases(tmp_path):
    path = _write_json(tmp_path, "g3_report.json", {"duplicate_phrases": []})
    msg = gf.g3(path)
    assert "repetition detected" in msg


def test_gate_a_reads_summary_counts(tmp_path):
    path = _write_json(tmp_path, "fact_check_report.json", {
        "summary": {"broken_official_hard": 2, "unsourced_stat_count": 1, "unbacked_attribution_count": 0}
    })
    msg = gf.gate_a(path)
    assert "broken_official_hard=2" in msg
    assert "unsourced_stat_count=1" in msg


def test_gate_b_reads_dimension_scores(tmp_path):
    path = _write_json(tmp_path, "eeat_report.json", {
        "total_eeat_score": 69.8, "minimum_required": 85,
        "dimension_scores": {"experience": 20, "expertise": 78, "authority": 100, "trust": 100},
    })
    msg = gf.gate_b(path)
    assert "score=69.8" in msg
    assert "minimum=85" in msg
    assert "experience=20" in msg


def test_build_feedback_dispatches_by_gate_name(tmp_path):
    path = _write_json(tmp_path, "g_substance_report.json", {"reasons": ["x"]})
    assert gf.build_feedback("g_substance", path) == gf.g_substance(path)


def test_cli_never_raises_on_malformed_json(tmp_path, capsys):
    import subprocess
    bad = tmp_path / "broken.json"
    bad.write_text("not valid json{{{", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts/gate_feedback.py"),
         "--gate", "g3", "--report", str(bad)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "repetition detected" in result.stdout
