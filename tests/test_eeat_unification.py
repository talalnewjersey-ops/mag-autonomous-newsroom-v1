"""EEAT scoring unification (2026-07-11) -- GATE B (agent_06_eeat_validator.py)
and GATE QA (agent_12_quality_assurance.py) used to run two completely
independent EEAT implementations. Real finding, witness run 9: the SAME
article 1 scored EEAT=98.3 from GATE B and EEAT=81.2 from GATE QA minutes
later -- a 17-point gap on one supposedly well-defined metric.

Root cause (verified against the real article text, not guessed):
  - agent_12 received the 2026-07-10 EEAT fixes (PR #68 firsthand-experience
    recognition, PR #70 illustrative-scenario recognition); agent_06 never did.
  - agent_06's OWN "author_credentials" signal matched generically on the word
    "licensed" appearing 6 times in the real article body -- every occurrence
    described THIRD-PARTY insurers/agents ("insurers licensed in California"),
    never the article's own author. A false positive, not a real signal.

Both agents now delegate to agents/_eeat_scoring.py -- this file proves they
score identically, and locks in the two specific findings above as regression
tests so neither implementation can silently re-diverge.

Offline: no network, no API key.
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _stub(name, **attrs):
    import types
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


eeat_scoring = _load("agents/_eeat_scoring.py", "eeat_scoring_test")
agent_06 = _load("agents/agent_06_eeat_validator.py", "agent_06_unification_test")
agent_12_mod = _load("agents/agent_12_quality_assurance.py", "agent_12_unification_test")
Agent12 = agent_12_mod.QualityAssuranceAgent


def _agent12():
    return Agent12.__new__(Agent12)


def _run(coro):
    import asyncio
    return asyncio.run(coro)


# ---------------------------------------------------------------- the core proof: identical scores

REAL_SHAPE_ARTICLE = (
    "## About the Author\n\n"
    "Talal Eddaouahiri is the founder of MoneyAbroadGuide.com. Originally from Morocco, "
    "he settled in the U.S. in 2015 and built his own credit history and banking relationships "
    "from scratch in both countries. His background is in retail banking and customer relations, "
    "and he draws on that firsthand experience to write independent, source-based guides.\n\n"
    "## Eligibility\n\n"
    "According to state DMV records, insurers licensed in California, Texas, and New York must "
    "quote all drivers regardless of citizenship. State insurance regulators require licensed "
    "agents to manually review foreign records, and a licensed insurance professional can help "
    "compare options. Consult your state's department of insurance or a licensed insurance "
    "professional before purchasing. Based on official government requirements, expect to need "
    "an ITIN or SSN for verification purposes in most states as of 2026.\n\n"
    "## Illustrative Scenarios\n\n"
    "### Illustrative Scenario: International Student, Graduate Program (Ohio)\n\n"
    "An F-1 visa holder relocating from abroad for a two-year program needs liability coverage "
    "before driving to campus, illustrating one common scenario newcomers face.\n\n"
    "## Sources\n\n"
    "Source: FDIC and CFPB regulatory guidance. Government references are cited throughout, "
    "with privacy and security disclosures available upon request.\n\n"
    "> **Last Updated**: July 2026\n"
)


def test_agent06_and_agent12_score_the_same_article_identically():
    flags = eeat_scoring.derive_flags_from_content(REAL_SHAPE_ARTICLE)
    checks_via_shared = eeat_scoring.audit_eeat(REAL_SHAPE_ARTICLE, **flags)
    score_via_shared = eeat_scoring.calculate_eeat_score(checks_via_shared)

    checks_via_agent12 = _run(_agent12()._audit_eeat({
        "article_content": REAL_SHAPE_ARTICLE, **flags,
    }))
    score_via_agent12 = _agent12()._calculate_eeat_score(checks_via_agent12)

    assert checks_via_shared == checks_via_agent12
    assert score_via_shared == score_via_agent12


def test_agent06_cli_report_matches_agent12_dimension_scores(tmp_path):
    article_path = tmp_path / "article_draft.md"
    article_path.write_text(REAL_SHAPE_ARTICLE, encoding="utf-8")

    report = agent_06.run_eeat_validation(str(article_path), str(tmp_path / "out"), threshold=85)

    flags = eeat_scoring.derive_flags_from_content(REAL_SHAPE_ARTICLE)
    agent12_checks = _run(_agent12()._audit_eeat({"article_content": REAL_SHAPE_ARTICLE, **flags}))
    agent12_score = _agent12()._calculate_eeat_score(agent12_checks)

    assert report["total_eeat_score"] == agent12_score
    assert report["dimension_scores"]["experience"] == agent12_checks["experience_score"]
    assert report["dimension_scores"]["expertise"] == agent12_checks["expertise_score"]
    assert report["dimension_scores"]["authority"] == agent12_checks["authority_score"]
    assert report["dimension_scores"]["trust"] == agent12_checks["trust_score"]


# ---------------------------------------------------------------- regression: the "licensed" false positive

def test_licensed_describing_third_parties_does_not_grant_credentials():
    # the EXACT real-world shape that inflated the old agent_06's authority to
    # 93.3: "licensed" appears repeatedly, but only ever describing insurers/
    # agents -- never the article's own author.
    content = (
        "Insurers licensed in California, Texas, and New York must quote all drivers. "
        "Licensed agents can manually review foreign records. A licensed insurance "
        "professional can help compare options."
    )
    checks = eeat_scoring.audit_eeat(content)
    assert checks["has_credentials"] is False


def test_a_real_credential_word_is_still_recognized():
    # the narrower check is intentionally strict, not broken -- a genuine
    # credential claim (CPA/CFA/CFP/attorney/lawyer/advisor) still counts.
    assert eeat_scoring.audit_eeat("Our author is a licensed CFP with 15 years of practice.")["has_credentials"] is True
    assert eeat_scoring.audit_eeat("Reviewed by an attorney specializing in immigration finance.")["has_credentials"] is True


def test_generic_by_or_author_words_alone_no_longer_fabricate_authority():
    # the OLD agent_06 pattern matched bare "by"/"author"/"written by"/"expert"
    # ANYWHERE (min_count=1) -- trivially satisfied by boilerplate like a
    # "Written by the editorial team" byline or an "Expert Recommendation"
    # section heading, regardless of any real credential. The unified check
    # requires an ACTUAL credential word.
    content = "Written by the editorial team.\n\n## Expert Recommendation\n\nOur top picks below."
    assert eeat_scoring.audit_eeat(content)["has_credentials"] is False


# ---------------------------------------------------------------- regression: #68/#70 signals still recognized

def test_firsthand_experience_and_scenario_signals_still_count_toward_experience():
    checks = eeat_scoring.audit_eeat(
        "He draws on that firsthand experience. He built his own credit history from scratch. "
        "### Illustrative Scenario: a generic scenario for newcomers."
    )
    assert checks["experience_signals"] >= 3  # firsthand + built-from-scratch + scenario, at minimum


# ---------------------------------------------------------------- derive_flags_from_content

def test_derive_flags_detects_the_deterministic_author_section_and_update_line():
    flags = eeat_scoring.derive_flags_from_content(REAL_SHAPE_ARTICLE)
    assert flags["has_author"] is True
    assert flags["has_author_bio"] is True
    assert flags["has_update_date"] is True


def test_derive_flags_false_when_sections_absent():
    flags = eeat_scoring.derive_flags_from_content("Just some article body with no special sections.")
    assert flags["has_author"] is False
    assert flags["has_author_bio"] is False
    assert flags["has_update_date"] is False
