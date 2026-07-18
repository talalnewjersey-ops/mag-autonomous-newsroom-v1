"""Anti-placeholder gate (2026-07-18, AUDIT-LOG.md).

The same bug class -- a dropped template variable leaving a dangling
preposition/connector, a fused sentence+link, or a broken-Title-Case
acronym -- shipped to production twice with no gate catching it before
agent_12 scoring: 48754 (2026-07-13, noted but not built) and 48854
(2026-07-18, published fully autonomous, scored 98.8/100, forced this).

Three layers tested here, matching the three places the fix actually lives:
  1. agents/_placeholder_scan.py -- the pure detectors (scan_body/scan_title).
  2. agents/agent_12_quality_assurance.py::placeholder_penalty -- the hard
     score cap wired into QA scoring itself (defense in depth).
  3. scripts/placeholder_gate.py -- the standalone pipeline gate (CLI,
     subprocess-tested) that runs after agent_11 (needed for real-title
     coverage agent_12 structurally cannot provide -- see that script's
     module docstring) and before agent_12.

Offline, no network, no API key -- same convention as
tests/test_agent12_publication_gate_95.py and
tests/test_sprint1_blocking_gates.py.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents._placeholder_scan import scan_body, scan_title  # noqa: E402


# ============================================================
# Layer 1: pure detectors, real verbatim bug fixtures from 48854
# ============================================================

REAL_48854_SENTENCES = {
    "adjacent_connector_pair": "The financial decisions you make in your first 60 to on campus will shape your ability to rent housing.",
    "missing_quantity_before_of_verb": "Post-graduation, USCIS may authorize of Optional Practical Training, extended by an additional 24 months for eligible STEM-degree holders.",
    "missing_quantity_before_of_noun": "For example, a newcomer on STEM OPT has a combined potential authorization window of U.S.-sourced employment income.",
    "fused_link_sentence": 'F-1 students may begin on-campus work as soon as they maintain valid status.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students).',
}

REAL_48733_SENTENCE = (
    "Most newcomer programs impose an enrollment deadline, typically within 3 "
    "to of first arriving in Canada, after which standard account pricing applies."
)


def test_catches_all_four_real_48854_body_bugs():
    for label, sentence in REAL_48854_SENTENCES.items():
        findings = scan_body(sentence)
        assert findings, f"missed real 48854 bug ({label}): {sentence!r}"


def test_catches_real_48733_bug_found_via_stress_testing():
    # Found by running the gate against 30 live published articles while
    # validating for false positives -- a genuine, previously undetected,
    # still-live instance of the same bug class on a THIRD article.
    findings = scan_body(REAL_48733_SENTENCE)
    assert any(f["type"] == "adjacent_connector_pair" for f in findings)


def test_catches_empty_image_src():
    findings = scan_body('<img src="" alt="broken">')
    assert any(f["type"] == "empty_image_src" for f in findings)


def test_fused_link_detector_does_not_flag_a_real_markdown_link():
    clean = 'See the USCIS OPT page (<a href="https://www.uscis.gov/foo">USCIS OPT page</a>) for details.'
    findings = scan_body(clean)
    assert not any(f["type"] == "fused_link_sentence" for f in findings)


# ============================================================
# Layer 1b: false-positive guards -- each of these killed a first-draft
# version of the detector when tested against 30 REAL published articles.
# Locked in here so a future regex tweak can't reintroduce them silently.
# ============================================================

FALSE_POSITIVE_FIXTURES = {
    "at_least": "Tax returns or IRS transcripts for at least the past two years.",
    "from_within": "Verified digital identity confirmation from within Canadian jurisdiction.",
    "on_time_compound": "Your first months of on-time payments go directly onto that report.",
    "at_fault_compound": "Minimum-only coverage leaves exposure in at-fault states like Texas.",
    "demonym_after_duration_noun": "The CRA expects a final-year tax filing covering the period of Canadian residency.",
    "quantity_already_present": "USCIS may authorize up to 12 months of Optional Practical Training.",
}


def test_no_false_positives_on_known_good_phrasing():
    for label, sentence in FALSE_POSITIVE_FIXTURES.items():
        findings = scan_body(sentence)
        assert not findings, f"false positive on {label!r}: {sentence!r} -> {findings}"


# ============================================================
# Layer 1c: title check
# ============================================================

def test_catches_broken_title_case_acronym():
    findings = scan_title("Best International Students Money Setup Checklist Usa: Complete Guide")
    assert any(f["type"] == "broken_title_case_acronym" and f["match"] == "Usa" for f in findings)


def test_title_check_does_not_flag_correct_acronym_case():
    findings = scan_title("Best International Students Money Setup Checklist USA: Complete Guide")
    assert not findings


def test_title_check_ignores_ordinary_words():
    findings = scan_title("Best Banks for Newcomers to Canada in 2026")
    assert not findings


# ============================================================
# Layer 2: agent_12's hard cap (offline stub-load, mirrors
# tests/test_agent12_publication_gate_95.py's pattern exactly)
# ============================================================

def _stub(name, **attrs):
    import types
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m


_stub("services.llm_service", LLMService=object)
_stub("services.storage_service", StorageService=object)


def _load_agent12():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "agent_12_placeholder_test", str(REPO_ROOT / "agents" / "agent_12_quality_assurance.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_placeholder_penalty_is_full_cap_not_graduated():
    mod = _load_agent12()
    assert mod.placeholder_penalty(0) == 0
    assert mod.placeholder_penalty(1) == mod.placeholder_penalty(5)  # not proportional -- zero tolerance
    assert mod.placeholder_penalty(1) >= mod.PUBLICATION_QUALITY_GATE  # a single finding alone zeroes any realistic score


def test_a_form_perfect_98_8_score_cannot_survive_one_placeholder_finding():
    # Locks in the exact real number from 48854: form_overall_score=98.8,
    # hallucination_penalty=0, yet it should NEVER have been able to reach
    # PUBLICATION_QUALITY_GATE (95) with placeholder artifacts present.
    mod = _load_agent12()
    form_overall_score = 98.8
    placeholder_findings_count = 4  # the real count found on 48854's body
    penalty = mod.placeholder_penalty(placeholder_findings_count)
    overall = max(0.0, round(form_overall_score - penalty, 1))
    assert overall < mod.PUBLICATION_QUALITY_GATE


def test_agent12_source_actually_calls_scan_body_and_applies_the_penalty():
    # Source guard (same style as test_agent12_publication_gate_95.py) --
    # proves the wiring exists in run(), not just that the pure function works.
    src = (REPO_ROOT / "agents" / "agent_12_quality_assurance.py").read_text(encoding="utf-8")
    assert "from agents._placeholder_scan import scan_body" in src
    assert "_placeholder_penalty = placeholder_penalty(" in src
    assert "overall_score - _halluc_penalty - _placeholder_penalty" in src


# ============================================================
# Layer 3: scripts/placeholder_gate.py, as a real subprocess (matches
# tests/test_sprint1_blocking_gates.py's convention)
# ============================================================

def _run_gate(article_path, wp_report_path, output_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    proc = subprocess.run(
        [sys.executable, "scripts/placeholder_gate.py",
         "--article", str(article_path),
         "--wordpress-report", str(wp_report_path),
         "--output", str(output_path)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_gate_cli_exits_1_on_broken_article(tmp_path):
    article = tmp_path / "draft.md"
    article.write_text(REAL_48854_SENTENCES["adjacent_connector_pair"], encoding="utf-8")
    wp_report = tmp_path / "wordpress_report.json"
    wp_report.write_text(json.dumps({"title": "Checklist Usa: A Broken Title"}), encoding="utf-8")
    output = tmp_path / "report.json"

    code, out = _run_gate(article, wp_report, output)
    assert code == 1, out
    report = json.loads(output.read_text())
    assert report["status"] == "FAIL"
    assert report["finding_count"] >= 2  # one body finding + one title finding


def test_gate_cli_exits_0_on_clean_article(tmp_path):
    article = tmp_path / "draft.md"
    article.write_text(
        "USCIS may authorize up to 12 months of Optional Practical Training, "
        "extended by an additional 24 months for eligible STEM-degree holders.",
        encoding="utf-8",
    )
    wp_report = tmp_path / "wordpress_report.json"
    wp_report.write_text(json.dumps({"title": "Best Banks for Newcomers to Canada 2026"}), encoding="utf-8")
    output = tmp_path / "report.json"

    code, out = _run_gate(article, wp_report, output)
    assert code == 0, out
    report = json.loads(output.read_text())
    assert report["status"] == "PASS"
    assert report["finding_count"] == 0


def test_gate_cli_missing_wordpress_report_does_not_crash(tmp_path):
    # agent_11 could conceivably fail to write the report file even though
    # this gate is only ever wired to run after a successful agent_11 --
    # must degrade to "no title check", not a stack trace that would mask
    # the real body findings.
    article = tmp_path / "draft.md"
    article.write_text("Clean sentence with no issues at all.", encoding="utf-8")
    output = tmp_path / "report.json"
    code, out = _run_gate(article, tmp_path / "does_not_exist.json", output)
    assert code == 0, out


# ============================================================
# Layer 4: production_batch_loop.sh wiring -- source guard, proves Phase
# 11.5 exists, runs after agent_11 / before agent_12, and is BLOCKING.
# ============================================================

def test_batch_loop_wires_gate_d_between_agent_11_and_agent_12():
    src = (REPO_ROOT / "scripts" / "production_batch_loop.sh").read_text(encoding="utf-8")
    gate_c_pos = src.index("Phase 11: WordPress Draft [GATE C]")
    gate_d_pos = src.index("Phase 11.5: Anti-Placeholder Gate [GATE D]")
    gate_qa_pos = src.index("Phase 12-13: QA + Chief Editor")
    assert gate_c_pos < gate_d_pos < gate_qa_pos
    assert "python scripts/placeholder_gate.py" in src
    assert "GATE D FAIL" in src
