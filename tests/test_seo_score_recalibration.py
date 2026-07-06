"""SEO SCORE RECALIBRATION (2026-07-06): every article that reached agent_12's
QA gate landed at exactly seo_score=70 -- arithmetic, not content variance
(100 - 15 keyword_density_ok - 15 word_count_ok = 70 every time). Both
criteria were structurally miscalibrated, not real content gaps:
  - word_count_ok required >= 5000 words, but agent_04's OWN tier word caps
    (PILLAR max=4200, STANDARD/OPPORTUNITY/GOLD max=4000) can never reach
    5000 -- a mathematical impossibility, not a content deficiency.
  - keyword_density_ok rewarded a density FLOOR (>=0.3%, first-3-words
    substring match) -- on a real 6-7 word long-tail keyword this floor is
    only reachable via ~13 literal repeats, i.e. old-style keyword-stuffing
    that contradicts this project's own EEAT/natural-writing goals.

User's decision (2026-07-06): word_count_ok becomes TIER-RELATIVE (+-10% of
the tier's own target_words, not an absolute number); keyword density is
NEVER rewarded again -- only an UNNATURALLY HIGH density (stuffing) can
subtract from the score. Weights redistributed to still sum to 100 for the
6 remaining positive criteria; the stuffing check is a separate, subtraction-
only penalty layered on top.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import importlib.util
_spec = importlib.util.spec_from_file_location("agent_12_recal_test", os.path.join(ROOT, "agents/agent_12_quality_assurance.py"))
agent_12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_12)

Agent = agent_12.QualityAssuranceAgent


def _agent():
    return Agent.__new__(Agent)


# ---------------------------------------------------------------- constants sanity

def test_tier_target_words_mirrors_agent_04():
    assert agent_12._TIER_TARGET_WORDS == {"PILLAR": 4200, "STANDARD": 4000, "OPPORTUNITY": 4000, "GOLD": 4000}


def test_seo_weights_still_sum_to_100():
    # keyword_in_title, has_good_structure, has_meta_description, has_tables,
    # has_internal_links, word_count_ok -- the 6 remaining positive criteria.
    a = _agent()
    all_true = {"keyword_in_title": True, "has_good_structure": True, "has_meta_description": True,
                "has_tables": True, "has_internal_links": True, "word_count_ok": True,
                "keyword_stuffing_detected": False}
    assert a._calculate_seo_score(all_true) == 100


# ---------------------------------------------------------------- word_count_ok: tier-relative +-10%

def _seo_checks_for(word_count, article_type="OPPORTUNITY", keyword="x", title="x", content_extra=""):
    import asyncio
    a = _agent()
    content = "## H2 One\n### H3 A\n### H3 B\n### H3 C\n### H3 D\n" + content_extra + (" word" * word_count)
    data = {"article_content": content, "keyword": keyword, "title": title,
            "meta_description": "d", "word_count": word_count, "article_type": article_type}
    return asyncio.run(a._audit_seo(data))


def test_word_count_at_exact_target_passes():
    checks = _seo_checks_for(4000, "OPPORTUNITY")
    assert checks["word_count_ok"] is True
    assert checks["tier_target_words"] == 4000


def test_word_count_within_10_percent_over_passes():
    checks = _seo_checks_for(4400, "OPPORTUNITY")  # +10.0% exactly
    assert checks["word_count_ok"] is True


def test_word_count_just_beyond_10_percent_over_fails():
    checks = _seo_checks_for(4450, "OPPORTUNITY")  # +11.25%
    assert checks["word_count_ok"] is False


def test_word_count_within_10_percent_under_passes():
    checks = _seo_checks_for(3600, "OPPORTUNITY")  # -10.0% exactly
    assert checks["word_count_ok"] is True


def test_word_count_the_old_impossible_5000_floor_is_gone():
    # 4000 words on an OPPORTUNITY article (the tier's own MAX per agent_04)
    # must now PASS -- the old >=5000 floor made this structurally impossible.
    checks = _seo_checks_for(4000, "OPPORTUNITY")
    assert checks["word_count_ok"] is True


def test_pillar_tier_uses_its_own_higher_target():
    checks_ok = _seo_checks_for(4200, "PILLAR")
    assert checks_ok["tier_target_words"] == 4200
    assert checks_ok["word_count_ok"] is True
    # the SAME 4200 words judged against OPPORTUNITY's target (4000) is +5% -- still ok
    # but confirms the target is genuinely tier-specific, not a global constant
    checks_opportunity = _seo_checks_for(4200, "OPPORTUNITY")
    assert checks_opportunity["tier_target_words"] == 4000


def test_unknown_article_type_falls_back_to_standard():
    checks = _seo_checks_for(4000, "SOME_UNKNOWN_TIER")
    assert checks["tier_target_words"] == 4000  # STANDARD's target


# ---------------------------------------------------------------- keyword density: never rewarded, only penalized when excessive

def test_low_natural_density_is_not_rewarded_or_penalized():
    a = _agent()
    import asyncio
    kw = "personal loans for immigrants no credit history"
    content = "## H2\n### H3 A\n### H3 B\n### H3 C\n### H3 D\n" + "personal loans for immigrants " + ("word " * 4000)
    data = {"article_content": content, "keyword": kw,
            "title": f"Best {kw.title()}", "meta_description": "d", "word_count": 4000, "article_type": "OPPORTUNITY"}
    checks = asyncio.run(a._audit_seo(data))
    assert "keyword_density_ok" not in checks, "the reward field must be gone entirely"
    assert checks["keyword_stuffing_detected"] is False
    assert checks["keyword_in_title"] is True and checks["word_count_ok"] is True
    score = a._calculate_seo_score({**checks, "has_good_structure": True, "has_meta_description": True,
                                     "has_tables": True, "has_internal_links": True})
    assert score == 100, "a normal, non-stuffed density must not cost or gain points"


def test_excessive_density_is_penalized():
    a = _agent()
    import asyncio
    # repeat the keyword phrase heavily relative to a short body -> high density
    kw = "best newcomer bank accounts"
    content = "## H2\n### H3 A\n### H3 B\n### H3 C\n### H3 D\n" + ((kw + " ") * 30) + ("word " * 500)
    data = {"article_content": content, "keyword": kw, "title": kw, "meta_description": "d",
            "word_count": 560, "article_type": "OPPORTUNITY"}
    checks = asyncio.run(a._audit_seo(data))
    assert checks["keyword_stuffing_detected"] is True
    assert checks["keyword_in_title"] is True
    # isolate the stuffing penalty alone: force every OTHER criterion to pass
    base = {**checks, "has_good_structure": True, "has_meta_description": True,
            "has_tables": True, "has_internal_links": True, "word_count_ok": True}
    score = a._calculate_seo_score(base)
    assert score == 80, "stuffing must subtract 20 points from an otherwise-perfect score"


def test_stuffing_penalty_never_makes_score_negative():
    a = _agent()
    score = a._calculate_seo_score({"keyword_stuffing_detected": True})  # nothing else scored
    assert score == 0


# ---------------------------------------------------------------- real control-run regression: the "70 plateau" is broken

def test_real_run6_canada_newcomer_case_no_longer_plateaus_at_70():
    # Real article (canada_newcomer, run 28778680469): word_count=4100,
    # density=0.122% on a 6-word keyword -- old score was exactly 70.
    a = _agent()
    checks = {
        "keyword_in_title": True, "has_good_structure": True, "has_meta_description": True,
        "has_tables": True, "has_internal_links": True,
        "word_count_ok": abs(4100 - 4000) <= 0.10 * 4000,  # True
        "keyword_stuffing_detected": False,
    }
    score = a._calculate_seo_score(checks)
    assert score == 100
    assert score != 70, "the old plateau must be gone for this real case"
