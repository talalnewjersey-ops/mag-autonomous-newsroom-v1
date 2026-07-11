"""Single source of truth for EEAT (Experience/Expertise/Authority/Trust)
scoring (2026-07-11, PR unifying agent_06/agent_12).

Real finding: witness run 9's article 1 scored EEAT=98.3 from GATE B
(agent_06_eeat_validator.py) and EEAT=81.2 from GATE QA (agent_12_quality_
assurance.py) minutes later, on the EXACT SAME article -- a 17-point gap on
what is supposed to be one well-defined metric. Root cause, verified against
the real article text (not guessed): two completely independent
implementations that had already diverged. agent_12's WAS the one actively
maintained -- the 2026-07-10 fixes (PR #68's firsthand-experience bio
recognition, PR #70's illustrative-scenario recognition) live in agent_12's
`experience_patterns`, not agent_06's `EEAT_SIGNALS`, which was never touched
by that work. Concretely, on the real article:
  - Experience: agent_12 correctly counts all 5 real signals present
    (2 "based on"/"according to", 3 "scenario", 1 "firsthand experience", 1
    "built ... from scratch") = 10 matches -> 50/100 (linear x5, capped at
    100 -- needs 20 matches to max out). agent_06's broader, independent
    first-person-narrative/step-by-step/date patterns hit 100/100 on the same
    text -- a different (looser) measure of the same underlying signal, not a
    bug in either taken alone, but a real inconsistency between the two.
  - Authority: agent_06's "author_credentials" signal matched generically on
    the word "licensed" appearing SIX times in the article body -- every
    single occurrence describes third-party insurers/agents ("insurers
    licensed in those states", "licensed insurance professional"), NEVER the
    article's own author. That's a false positive, not a real credential
    signal, and it inflated agent_06's authority score to 93.3. agent_12's
    narrower has_credentials check (CPA/CFA/CFP/attorney/lawyer/advisor)
    correctly returns False here: the real author bio
    (agents/agent_04_article_writer.py::_AUTHOR_BIO_MD) deliberately does NOT
    claim a professional credential -- the founder's real background is
    retail banking, not a licensed advisor (Sprint 8's anti-fabrication
    decision). agent_12's False is the honest read; agent_06's True was a
    keyword collision, not evidence of anything about the author.

This module is agent_12's `_audit_eeat`/`_calculate_eeat_score` logic,
extracted VERBATIM (same patterns, same weights, same formulas -- a
migration, not a rewrite) so both agent_06 (GATE B) and agent_12 (GATE QA)
score EEAT identically. agent_06 is no longer a second, drifting
implementation of the same metric.
"""
import re


def audit_eeat(content: str, has_author: bool = False, has_author_bio: bool = False,
                has_update_date: bool = None) -> dict:
    """Audit Experience, Expertise, Authority, Trust signals in article text.
    has_author/has_author_bio/has_update_date are booleans the caller may
    already know (e.g. from upstream pipeline data); a caller with only the
    raw text (no separate flags) should derive them from content first --
    see agent_06_eeat_validator.py's own derivation for the reference
    approach (checks for the deterministic "## About the Author" section and
    a "Last Updated" line, both of which agent_04_article_writer.py always
    appends to every article this pipeline produces)."""
    checks = {}

    # Experience signals
    experience_patterns = [
        r'(?:based on|according to|our experience|we found|in practice)',
        r'(?:real-world|case study|example|scenario)',
        r'(?:tested|reviewed|analyzed|compared)',
        # 2026-07-10: recognizes genuine firsthand-experience language
        # already present in the deterministic author bio (agent_04_
        # article_writer.py _AUTHOR_BIO_MD) -- "he draws on that
        # firsthand experience", "built his own credit history and
        # banking relationships from scratch". Not a new signal source
        # or a bio rewrite -- the bio's true content was simply
        # invisible to this scorer before. Scoped tight (not a bare
        # "experience") so it can't be gamed by unrelated prose.
        r'firsthand experience',
        r'built (?:his|her|their|our) own .{0,60}from scratch',
    ]
    experience_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in experience_patterns)
    checks["experience_signals"] = experience_count
    checks["experience_score"] = min(100, experience_count * 5)

    # Expertise signals
    expertise_patterns = [
        r'(?:expert|professional|specialist|certified)',
        r'(?:according to|research shows|studies indicate|data from)',
        r'(?:official|government|regulation|requirement)',
        r'(?:\$|USD|CAD|€|percent|%|annual|monthly)'
    ]
    expertise_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in expertise_patterns)
    checks["expertise_signals"] = expertise_count
    checks["expertise_score"] = min(100, expertise_count * 3)

    # Authority signals
    checks["has_author"] = has_author
    checks["has_author_bio"] = has_author_bio
    checks["has_credentials"] = bool(re.search(r'(?:CPA|CFA|CFP|attorney|lawyer|advisor)', content, re.IGNORECASE))
    checks["authority_score"] = (
        (25 if checks["has_author"] else 0) +
        (25 if checks["has_author_bio"] else 0) +
        (25 if checks["has_credentials"] else 0) +
        (25 if expertise_count > 10 else 0)
    )

    # Trust signals
    trust_patterns = [
        r'(?:updated|last reviewed|fact.checked)',
        r'(?:source:|citation|reference)',
        r'(?:FDIC|CFPB|CRA|IRS|government|official)',
        r'(?:privacy|security|encrypted|SSL)'
    ]
    trust_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in trust_patterns)
    checks["trust_signals"] = trust_count
    checks["trust_score"] = min(100, trust_count * 5 + (25 if has_update_date else 0))

    return checks


def calculate_eeat_score(eeat_check: dict) -> float:
    """Overall EEAT score: equal 25% weight per dimension."""
    exp = eeat_check.get("experience_score", 0)
    exp_score = eeat_check.get("expertise_score", 0)
    auth = eeat_check.get("authority_score", 0)
    trust = eeat_check.get("trust_score", 0)
    return round((exp * 0.25 + exp_score * 0.25 + auth * 0.25 + trust * 0.25), 1)


def derive_flags_from_content(content: str) -> dict:
    """Best-effort has_author/has_author_bio/has_update_date derivation from
    raw article text alone, for a caller (like agent_06) with no separate
    upstream pipeline data. agent_04_article_writer.py always appends a
    deterministic "## About the Author" section and a "> **Last Updated**:"
    line to every article this pipeline produces, so both are reliable,
    self-contained signals straight from the text."""
    has_author = bool(re.search(r'##\s+About the Author', content, re.IGNORECASE))
    return {
        "has_author": has_author,
        "has_author_bio": has_author,
        "has_update_date": bool(re.search(r'Last Updated', content, re.IGNORECASE)),
    }
