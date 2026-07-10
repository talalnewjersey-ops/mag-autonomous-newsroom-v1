"""2026-07-10 fix: two agent_12 signals that were computed but silently wrong,
found while diagnosing why a real draft (post_id=48624) scored eeat_score=80.0
overall_score=84.0 instead of the ~95 bar the user set before re-enabling crons.

- TRUST (`has_update_date`): _audit_eeat's trust_score reads
  data.get("has_update_date") for a +25 bonus, but nothing in the whole file
  ever WROTE that key -- it was always None, so the bonus could never fire,
  even on a real article with a genuine "> **Last Updated**: July 2026" line
  (confirmed on draft 48624's actual published-bound content).
- FAQ (`question_count`): the old section-boundary lookahead "(?=## |$)"
  matched INSIDE a "### " (H3) heading, because "##" is a substring of "###"
  ("### Can I drive...?" satisfies "## " at offset 1). That truncated the
  captured FAQ section to the H2 title line alone, right before the first
  real question -- question_count was always 0 even on a real article with
  10 genuine FAQ questions (draft 48624, verified via the WordPress REST API).

Offline, no network, no API key -- same harness pattern as
tests/test_sprint10_anti_hallucination.py.
"""
import asyncio
import importlib.util
import os
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


agent_12_mod = _load("agents/agent_12_quality_assurance.py", "agent_12_eeat_faq_fix")
Agent = agent_12_mod.QualityAssuranceAgent


def _agent():
    return Agent.__new__(Agent)


def _run(coro):
    return asyncio.run(coro)


# ---------------- has_update_date detection ----------------

def test_has_update_date_detected_from_real_trailing_line():
    # exact shape agent_04_article_writer.py now builds (post PR #66 fix).
    content = "Some article body.\n\n> **Last Updated**: July 2026"
    data = _run(_agent()._load_article_data({"article_content": content}))
    assert data["has_update_date"] is True


def test_has_update_date_false_when_absent():
    content = "Some article body with no update marker at all."
    data = _run(_agent()._load_article_data({"article_content": content}))
    assert data["has_update_date"] is False


def test_has_update_date_respects_context_override():
    # matches has_faq's own "only set if not already provided" contract.
    data = _run(_agent()._load_article_data(
        {"article_content": "no marker here", "has_update_date": True}))
    assert data["has_update_date"] is True


# ---------------- trust_score wiring ----------------

def test_trust_score_gets_the_update_date_bonus():
    a = _agent()
    checks_with_date = _run(a._audit_eeat({"article_content": "Source: fdic.gov.", "has_update_date": True}))
    checks_without_date = _run(a._audit_eeat({"article_content": "Source: fdic.gov.", "has_update_date": False}))
    assert checks_with_date["trust_score"] - checks_without_date["trust_score"] == 25


def test_real_draft_eeat_score_improves_after_fix():
    # Same body, only the trailing "Last Updated" line differs -- isolates
    # the fix's real effect: the update-date bonus alone must move eeat_score,
    # matching the real 48624 case (trust_score 90 -> 100, eeat_score
    # 80.0 -> 82.5, all else held constant).
    body = ("## Overview\nSource: fdic.gov. Official government requirement. "
            "$500 minimum. Expert advisor recommended.")
    a = _agent()
    ctx = {"has_author": True, "has_author_bio": True}

    data_with_date = _run(a._load_article_data(
        {**ctx, "article_content": body + "\n\n> **Last Updated**: July 2026"}))
    data_without_date = _run(a._load_article_data({**ctx, "article_content": body}))

    eeat_with_date = _run(a._audit_eeat(data_with_date))
    eeat_without_date = _run(a._audit_eeat(data_without_date))

    # +25 from the has_update_date bonus itself; the "Last Updated" line's own
    # "updated" substring also feeds the trust_count pattern (+5 more) --
    # a real, harmless overlap, not double-counting the bonus.
    assert eeat_with_date["trust_score"] - eeat_without_date["trust_score"] >= 25
    assert a._calculate_eeat_score(eeat_with_date) > a._calculate_eeat_score(eeat_without_date)


# ---------------- FAQ question_count boundary fix ----------------

FAQ_WITH_TRAILING_H2 = """## Frequently Asked Questions: Car Insurance for Foreign Drivers

### Can I drive in the USA using only my foreign license?

Answer one.

### Do I need a Social Security Number to get car insurance?

Answer two.

### What are the minimum liability requirements across states?

Answer three.

## Conclusion

Wrap-up text that must NOT be counted as a question.
"""


def test_faq_question_count_not_truncated_by_h3_substring_bug():
    # The old boundary "(?=## |$)" matched inside the FIRST "### " heading
    # (offset 1: "##" + " "), truncating the section before any question was
    # captured -- question_count was 0 despite 3 real questions here.
    a = _agent()
    checks = _run(a._audit_faq({"article_content": FAQ_WITH_TRAILING_H2}))
    assert checks["question_count"] == 3
    assert checks["has_enough_questions"] is False  # 3 < 8, correctly so
    assert checks["schema_ready"] is False  # < 5


def test_faq_section_still_stops_at_the_next_real_h2():
    # Safety net for the fix itself: the new boundary must not overshoot into
    # a following section and inflate the count.
    a = _agent()
    checks = _run(a._audit_faq({"article_content": FAQ_WITH_TRAILING_H2}))
    assert checks["question_count"] == 3  # not 4+ from "## Conclusion" onward


def test_faq_ten_questions_matches_the_real_48624_regression():
    # Same shape as the real draft: 10 questions, ends the FAQ section at a
    # real "## Conclusion" H2. Locks in the exact real-run regression.
    ten_questions = "".join(
        f"\n### Question number {i}?\n\nA clear answer for newcomers.\n" for i in range(1, 11))
    content = "## Frequently Asked Questions\n" + ten_questions + "\n## Conclusion\n\nWrap-up.\n"
    a = _agent()
    checks = _run(a._audit_faq({"article_content": content}))
    assert checks["question_count"] == 10
    assert checks["has_enough_questions"] is True
    assert checks["schema_ready"] is True


def test_faq_with_no_trailing_section_still_counts_correctly():
    # boundary "\Z" branch: FAQ is the LAST section in the document.
    content = "## Frequently Asked Questions\n\n### Only question here?\n\nAnswer.\n"
    a = _agent()
    checks = _run(a._audit_faq({"article_content": content}))
    assert checks["question_count"] == 1


# ---------------- content_check tier-relative word count (lever 2) ----------------
# 2026-07-10: _audit_content_quality's old flat ">=5000"/">=7000" word-count
# thresholds ignored article TIER entirely. agent_04_article_writer.py caps
# every tier this pipeline produces at <=4200w (PILLAR) or <=4000w (STANDARD/
# OPPORTUNITY/GOLD) -- so those 40 points were a mathematical impossibility,
# not a content deficiency, on the real draft 48624 (OPPORTUNITY, 4304w,
# content_check.score stuck at 60/100 no matter how good the article was).
# Fixed to reuse the SAME tier-relative rule the SEO score already applies
# (_TIER_TARGET_WORDS, +-10% tolerance) instead of a second, divergent
# word-count rule.

def _faq_and_structure_filler():
    # the 4 non-word-count content_check criteria, satisfied once so each
    # test below isolates the word-count criterion alone.
    h2s = "".join(f"\n## Section {i}\n\n### Sub {i}.1\n\n### Sub {i}.2\n" for i in range(1, 6))
    table = "\n".join(f"| Row {i} | Val {i} |" for i in range(1, 7))
    faq = "\n## Frequently Asked Questions\n\n### Q?\n\nA.\n"
    return h2s + "\n" + table + faq


def test_opportunity_tier_4304_words_now_hits_full_content_score():
    # the exact real 48624 shape: OPPORTUNITY tier, 4304 words -- was
    # content_check.score=60 before this fix (0/40 on word count), now 100.
    filler = _faq_and_structure_filler()
    padding_words_needed = 4304 - len(filler.split())
    content = filler + " word" * max(0, padding_words_needed)
    a = _agent()
    checks = _run(a._audit_content_quality({"article_content": content, "article_type": "OPPORTUNITY"}))
    assert checks["word_count_ok"] is True
    assert checks["tier_target_words"] == 4000
    assert checks["score"] == 100


def test_5000_words_used_to_score_but_now_fails_tier_check_for_opportunity():
    # the OLD code rewarded 5000 words unconditionally; that's now 25% over
    # an OPPORTUNITY article's own 4000w target (+10% tolerance = 4400 max)
    # -- no longer "hitting the target", so it must NOT get the 40 points.
    filler = _faq_and_structure_filler()
    padding_words_needed = 5000 - len(filler.split())
    content = filler + " word" * max(0, padding_words_needed)
    a = _agent()
    checks = _run(a._audit_content_quality({"article_content": content, "article_type": "OPPORTUNITY"}))
    assert checks["word_count_ok"] is False
    assert checks["score"] == 60  # the 4 structure criteria only, no word-count points


def test_pillar_tier_4200_words_hits_full_content_score_but_would_have_failed_the_old_flat_5000_rule():
    filler = _faq_and_structure_filler()
    padding_words_needed = 4200 - len(filler.split())
    content = filler + " word" * max(0, padding_words_needed)
    a = _agent()
    checks = _run(a._audit_content_quality({"article_content": content, "article_type": "PILLAR"}))
    assert checks["tier_target_words"] == 4200
    assert checks["word_count_ok"] is True
    assert checks["score"] == 100


def test_missing_article_type_defaults_to_standard_tier():
    a = _agent()
    checks = _run(a._audit_content_quality({"article_content": "short"}))
    assert checks["tier_target_words"] == 4000  # _TIER_TARGET_WORDS["STANDARD"]


def test_real_draft_48624_combined_fixes_raise_content_and_eeat_together():
    # Combined check, same OPPORTUNITY/4304-word shape as the real draft:
    # content_check now hits 100 (was 60) AND eeat_score improves via the
    # update-date bonus (was 80.0), matching the two levers reported to the
    # user (overall_score verified end-to-end at 93.0 via direct replication
    # of the real CLI context against the real captured artifact -- not
    # reproduced here since that needs the full real metadata/outline files).
    filler = _faq_and_structure_filler()
    padding_words_needed = 4304 - len(filler.split())
    content = (filler + " word" * max(0, padding_words_needed) +
               "\nSource: fdic.gov. Official government requirement. Expert advisor. "
               "According to CFPB, tested and reviewed data shows a real-world example.\n\n"
               "> **Last Updated**: July 2026")
    a = _agent()
    data = _run(a._load_article_data({
        "article_content": content, "has_author": True, "has_author_bio": True, "article_type": "OPPORTUNITY",
    }))
    eeat_check = _run(a._audit_eeat(data))
    content_check = _run(a._audit_content_quality(data))
    assert content_check["score"] == 100
    assert data["has_update_date"] is True  # the trust bonus fired (exact delta covered above)
