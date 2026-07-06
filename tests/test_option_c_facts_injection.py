"""Option C (2026-07-05): the Couche 1 facts + anti-fabrication rule must be injected
into EVERY content-generating writer call, not only the intro + body. draft 48438
proved the FAQ/Expert re-invented numbers because they never received the facts.

Source-inspection regression guard (agent_04 needs an API key, so it is not run
offline): assert each of the six previously-uncovered calls appends the facts, so a
future edit cannot silently drop the injection from one section again.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


def test_facts_and_rules_is_defined():
    # _facts_and_rules must combine the anti-fab rule and the Couche 1 facts (a de-dup
    # wording clause may sit between them; the facts must never be dropped). RETRY
    # MECHANISM (2026-07-06) may prepend an optional _retry_block ahead of _anti_fab.
    assert re.search(r"_facts_and_rules = (?:_retry_block \+ )?_anti_fab \+ .*_facts_block", SRC)


def test_comparison_gets_facts():
    assert "200-300w context.{_facts_and_rules}" in SRC


def test_expert_recommendation_gets_facts():
    assert "{_expert_links_instruction}{_facts_and_rules}" in SRC


def test_faq_gets_facts():
    assert re.search(r"ending with \?\{_facts_and_rules\}", SRC)


def test_faq_topup_gets_facts():
    assert "Answer 80-150w{facts_and_rules}" in SRC
    assert "target_faqs, _facts_and_rules)" in SRC          # passed at the call site
    assert "target_faqs, facts_and_rules=\"\")" in SRC       # accepted by _ensure_faq_count


def test_closing_gets_facts():
    # 2026-07-06: closing() no longer asks for an "About the Author" section
    # (100-150w) -- it now ends with the Disclaimer request; the bio is
    # fixed text (_AUTHOR_BIO_MD) appended separately, outside this call.
    assert "legal, affiliate disclosure){_facts_and_rules}" in SRC


def test_word_count_expansion_gets_facts():
    assert "Return ONLY new Markdown.{_facts_and_rules}" in SRC


def test_no_content_call_left_without_facts():
    # every _call_claude prompt in the file must reference a facts/rules/sources block
    # (intro/body use sourcing_block/section_sources_block; the six others use
    # _facts_and_rules/facts_and_rules). Guards against a NEW uncovered section.
    calls = [m.start() for m in re.finditer(r"await _call_claude\(", SRC)]
    for pos in calls:
        window = SRC[pos:pos + 600]
        assert re.search(r"_facts_and_rules|facts_and_rules|sourcing_block|section_sources_block", window), \
            f"a _call_claude near offset {pos} has no facts injection"
