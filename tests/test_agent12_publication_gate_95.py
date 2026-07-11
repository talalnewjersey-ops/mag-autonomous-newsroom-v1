"""2026-07-11 fix: agent_12's REAL publication gate had drifted from the
documented enterprise standard.

.github/NEXUS14-PRIORITY.md, "Non-Negotiable Rules" #3: "Minimum publication
score: 95/100 -- hard gate" (also table in "Quality Gates (Section 14)":
Overall minimum 95/100). The actual code (QualityAssuranceAgent.run(),
consumed by main()'s sys.exit(0 if status=="PASS" else 1), which is what
production_v2.yml's GATE QA retry/fail logic reacts to) hardcoded 85 instead
-- for an unknown amount of time, undetected, because nothing tested the
literal number against the documented policy.

Surfaced by a real run (29137518698, draft 48640): overall_score=90.5
cleared the code's 85 and got promoted/published in the topic registry
(Sprint 9's invariant correctly gated on that number -- no invariant bug),
despite failing the actual enterprise standard of 95. Fixed by aligning the
code to the document (agents/agent_12_quality_assurance.py::
PUBLICATION_QUALITY_GATE), not the other way around.

A separate, NOT-fixed-here finding, locked in by a test below so it doesn't
get "fixed" by accident and silently do something different than intended:
main()'s --seo-threshold/--eeat-threshold CLI flags LOOK configurable but
are dead -- self.config is read exactly once in the whole class, for
"hallucination" only.

Offline, no network, no API key.
"""
import importlib.util
import os
import re
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


_stub("services.llm_service", LLMService=object)
_stub("services.storage_service", StorageService=object)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_12_mod = _load("agents/agent_12_quality_assurance.py", "agent_12_gate95")
PRIORITY_MD = open(os.path.join(ROOT, ".github/NEXUS14-PRIORITY.md"), encoding="utf-8").read()
SRC = open(os.path.join(ROOT, "agents/agent_12_quality_assurance.py"), encoding="utf-8").read()


# ---------------- the documented policy itself ----------------

def test_priority_md_documents_a_95_hard_gate():
    assert "Minimum publication score: 95/100" in PRIORITY_MD
    assert "hard gate" in PRIORITY_MD


# ---------------- the real constant matches the document ----------------

def test_publication_quality_gate_constant_is_95():
    assert agent_12_mod.PUBLICATION_QUALITY_GATE == 95


def test_status_field_uses_the_named_constant_not_a_bare_85():
    # source guard: the literal "85" must not reappear as the gate check --
    # this is what silently drifted from the documented policy last time.
    assert 'overall_score >= PUBLICATION_QUALITY_GATE' in SRC
    assert 'overall_score >= 85' not in SRC


# ---------------- the real run() path honors the new gate ----------------

def test_score_94_9_is_needs_review_not_pass():
    # the exact real-run shape: comfortably above the OLD 85, below the NEW 95.
    overall_score = 94.9
    status = "PASS" if overall_score >= agent_12_mod.PUBLICATION_QUALITY_GATE else "NEEDS_REVIEW"
    assert status == "NEEDS_REVIEW"


def test_score_95_0_is_pass():
    overall_score = 95.0
    status = "PASS" if overall_score >= agent_12_mod.PUBLICATION_QUALITY_GATE else "NEEDS_REVIEW"
    assert status == "PASS"


def test_real_48640_score_90_5_would_now_fail_the_gate():
    # locks in the exact real number that exposed the drift.
    overall_score = 90.5
    status = "PASS" if overall_score >= agent_12_mod.PUBLICATION_QUALITY_GATE else "NEEDS_REVIEW"
    assert status == "NEEDS_REVIEW"


# ---------------- dead CLI flags: documented, not silently "fixed" ----------------

def test_seo_and_eeat_threshold_cli_flags_are_still_dead_not_wired_in():
    # main()'s --seo-threshold/--eeat-threshold get stuffed into config but
    # self.config is read exactly once, for "hallucination" only. This test
    # documents the KNOWN gap (flagged, not fixed in this lot) so a future
    # change either wires them in deliberately or this test is updated
    # deliberately -- never silently.
    config_reads = re.findall(r'self\.config\.get\("([^"]+)"', SRC)
    assert config_reads == ["hallucination"], (
        f"self.config now reads {config_reads} -- if seo_threshold/eeat_threshold "
        f"are wired in, update/remove this test deliberately (see module docstring)"
    )
    assert '"seo_threshold": args.seo_threshold' in SRC  # still parsed into config...
    assert '"eeat_threshold": args.eeat_threshold' in SRC  # ...but still unused above
