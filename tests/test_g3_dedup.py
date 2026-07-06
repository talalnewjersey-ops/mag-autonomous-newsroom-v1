"""G3 de-dup (2026-07-05): universal fact injection made the writer parrot a fact's
exact sentence into every section -> the anti-repetition gate (G3) tripped. Fix
WITHOUT re-opening invention: keep every fact AVAILABLE in every section, only ask
for varied wording + pass a digest so trailing sections don't re-explain at length.

Source-inspection guard (agent_04 needs an API key, not run offline).
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


def test_dedup_wording_defined_and_in_facts_and_rules():
    assert "_dedup_wording = (" in SRC
    # RETRY MECHANISM (2026-07-06) prepends an optional _retry_block ahead of
    # the existing anti-fab + dedup + facts chain -- never removes any of it.
    assert "_facts_and_rules = _retry_block + _anti_fab + _dedup_wording + _facts_block" in SRC


def test_facts_are_never_removed_veracity_preserved():
    # the fix must NOT strip _facts_block from the injection -- the fact stays available
    # in every section (universal availability). This is the veracity non-regression.
    assert "_facts_block" in SRC.split("_facts_and_rules = ")[1].split("\n")[0]


def test_dedup_digest_built_from_body():
    assert "_dedup_digest = (" in SRC
    assert "_covered = _build_digest([intro] + written_sections)" in SRC


def test_dedup_digest_appended_to_all_trailing_sections():
    # 2026-07-06: closing()'s marker updated -- it no longer asks for an
    # "About the Author" section at all (the bio is now fixed text,
    # _AUTHOR_BIO_MD, appended separately -- see tests/test_end_section_dedup.py).
    # closing() still ends with the Disclaimer request, still carrying facts
    # + dedup digest exactly as before.
    for marker in ["200-300w context.{_facts_and_rules}{_dedup_digest}",       # comparison
                   "{_expert_links_instruction}{_facts_and_rules}{_dedup_digest}",     # Expert
                   "ending with ?{_facts_and_rules}{_dedup_digest}",            # FAQ
                   "legal, affiliate disclosure){_facts_and_rules}{_dedup_digest}",  # closing
                   "Return ONLY new Markdown.{_facts_and_rules}{_dedup_digest}"]:  # expansion
        assert marker in SRC, f"missing dedup digest on: {marker}"


def test_no_generation_call_left_without_facts():
    # unchanged guard: EVERY _call_claude still carries a facts/sources block
    for pos in (m.start() for m in re.finditer(r"await _call_claude\(", SRC)):
        window = SRC[pos:pos + 700]
        assert re.search(r"_facts_and_rules|facts_and_rules|sourcing_block|section_sources_block", window)


def test_wording_rule_keeps_the_citation():
    # the anti-repetition rule must ask to VARY WORDING, never to drop the citation
    assert "vary the wording, keep the citation" in SRC
    assert "remain available in every section" in SRC
