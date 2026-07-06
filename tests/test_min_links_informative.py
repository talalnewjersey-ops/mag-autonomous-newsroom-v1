"""GATE MIN_LINKS (2026-07-06): the internal-link-count check in agent_04 must
be INFORMATIVE, never blocking -- a real control-run bug where the pre-existing
hard "internal_links >= tier min" gate silently relied on the (now-removed)
static INTERNAL_LINKS dict always supplying exactly the minimum. Once
_real_internal_links honestly returns fewer links for topics the site has
little content on, this hard gate directly contradicted "zero relevant = zero
links, accepted" (memory: nexus14-next-session-backlog.md).

Also covers: (a) the diagnose_relevance() companion used to log WHY a count
came up short (vertical/query/best-rejected-ratios), (b) the writer-prompt
guard against inventing a fake "(#)" links section when zero real candidates
are supplied (a real artifact found on the auto-insurance control-run draft).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import agents.agent_04_article_writer as agent_04
from agents._real_internal_links import diagnose_relevance


def test_internal_links_below_minimum_does_not_block():
    tier = agent_04._get_tier_config("OPPORTUNITY")  # min_links = 4
    article = (
        "Body. https://www.irs.gov/a https://cra-arc.gc.ca/b https://www.canada.ca/c "
        "https://fdic.gov/d https://www.canada.ca/e\n"
        "Internal: [only-one](https://moneyabroadguide.com/only-one)\n"
        "case study one. real-world example two.\n"
    )
    errors = agent_04._validate_tier_standard(article, word_count=99999, tier=tier)
    assert not [e for e in errors if "Internal links" in e], \
        "a short internal-link count must NOT be a blocking validation error"


def test_zero_internal_links_does_not_block():
    tier = agent_04._get_tier_config("OPPORTUNITY")
    article = (
        "Body. https://www.irs.gov/a https://cra-arc.gc.ca/b https://www.canada.ca/c "
        "https://fdic.gov/d https://www.canada.ca/e\n"
        "No internal links at all here.\n"
        "case study one. real-world example two.\n"
    )
    errors = agent_04._validate_tier_standard(article, word_count=99999, tier=tier)
    assert not [e for e in errors if "Internal links" in e]


def test_other_gates_still_block_when_internal_links_are_fine():
    # Non-regression: removing the internal-links block must not weaken the
    # OTHER gates (official sources still required).
    tier = agent_04._get_tier_config("OPPORTUNITY")
    article = (
        "Body with only offlist sources. https://www.rbc.com/x\n"
        "Internal: [a](https://moneyabroadguide.com/a) [b](https://moneyabroadguide.com/b) "
        "[c](https://moneyabroadguide.com/c) [d](https://moneyabroadguide.com/d)\n"
    )
    errors = agent_04._validate_tier_standard(article, word_count=99999, tier=tier)
    assert any("Distinct official sources" in e for e in errors), \
        "the official-sources gate must still block -- only min_links became informative"


# ---------------------------------------------------------------- diagnose_relevance()

REAL_POSTS = [
    {"title": "Best High-Interest Savings Accounts For International Students In Canada",
     "url": "https://moneyabroadguide.com/hisa-intl-students/"},
    {"title": "Best Banks For Canadian Newcomers International Students",
     "url": "https://moneyabroadguide.com/banks-intl-students/"},
    {"title": "Best Bank Accounts for Newcomers to Canada",
     "url": "https://moneyabroadguide.com/best-bank-accounts-newcomers-canada-2026/"},
]


def test_diagnose_relevance_reports_fetched_count_and_thresholds():
    diag = diagnose_relevance("car insurance foreign drivers international students", REAL_POSTS)
    assert diag["real_posts_fetched"] == 3
    assert diag["min_overlap"] == 2
    assert diag["min_ratio"] == 0.5


def test_diagnose_relevance_lists_best_rejected_candidates_by_ratio():
    diag = diagnose_relevance("car insurance foreign drivers international students", REAL_POSTS)
    # the 2 "international students" posts share 2 words but ratio 0.33 -- rejected,
    # and must be the TOP of the rejected list (best ratio among rejects).
    top = diag["top_rejected"][0]
    assert top["overlap"] == 2
    assert top["ratio"] == 0.33
    assert "International Students" in top["title"]


def test_diagnose_relevance_excludes_accepted_candidates_from_rejected_list():
    # A query where one real post clears both bars must NOT appear in top_rejected.
    diag = diagnose_relevance("best newcomer bank accounts in canada", REAL_POSTS)
    rejected_titles = {r["title"] for r in diag["top_rejected"]}
    assert "Best Bank Accounts for Newcomers to Canada" not in rejected_titles


# ---------------------------------------------------------------- writer prompt guard

SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


def test_no_links_instruction_defined_and_used_in_both_sections():
    assert "_NO_LINKS_INSTRUCTION" in SRC
    assert "Do NOT invent placeholder links" in SRC
    assert "_intro_links_instruction = f\"2-3 internal links:\\n{links_intro_block}\" if links_intro_block else _NO_LINKS_INSTRUCTION" in SRC
    assert "_expert_links_instruction = f\"2 internal links from:\\n{links_expert_block}\" if links_expert_block else _NO_LINKS_INSTRUCTION" in SRC


def test_diagnostic_warning_logged_when_links_come_up_short():
    assert "diagnose_relevance(f\"{keyword} {title}\", _real_posts)" in SRC
    assert "Best rejected candidates" in SRC
