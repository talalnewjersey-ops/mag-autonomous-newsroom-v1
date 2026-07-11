"""Illustrative Scenarios -- Sprint 8 anti-fabrication guardrail, enforced in
CODE, not just prompt wording (2026-07-10, lever "a" of the 48624 EEAT
diagnosis).

Sprint 8 (2026-07-05) removed the old free-form "case studies" section
entirely: it prompted for specific personas and figures with no sourcing,
a real Helpful-Content/AdSense liability. That decision is NOT reversed
here. This module lets agent_04 reintroduce a STRICT, different, validated
format instead -- "Illustrative Scenarios" -- the exact shape already live
on article 48384 (found during the content audit): 1-2 GENERIC personas by
role/status (never a named individual), explicitly labeled non-testimonial,
grounded ONLY in numbers already covered by an engraved Couche 1 STABLE
fact (agents/_vertical_facts.py), via the SAME LEVIER C predicate agent_05
uses (agents/_fact_coverage.py).

Belt-and-suspenders, same philosophy as agent_04's own
_dedupe_reserved_end_sections: the prompt asks the LLM to follow the rules,
but this module NEVER trusts that alone -- validate_scenario_block()
deterministically checks the LLM's actual output and the caller must strip
the whole scenario block (never publish a partial/edited one that could
still look like a real testimonial) if either check fails.
"""
import re

from agents._fact_coverage import classify_claims

SCENARIO_HEADING = "## Illustrative Scenarios"

SCENARIO_DISCLAIMER = (
    "*The following are illustrative scenarios, not real testimonials or case "
    "studies of specific individuals.*"
)

# Best-effort, curated list -- deliberately NOT NLP/named-entity recognition,
# consistent with this project's existing regex/list-based detection style
# (TRUSTED_DOMAINS, CATEGORY_TO_VERTICAL). Deliberately diverse: the real
# incident this guards against used "Priya"/"Carlos" (AUDIT-LOG.md, article
# 47510's anonymization work) -- an anglo-only list would have missed it.
# Not exhaustive by construction (no first-name list can be); this is one
# layer of a defense-in-depth guard, not a claim of completeness.
COMMON_FIRST_NAMES = frozenset({
    # anglo
    "sarah", "john", "mary", "michael", "jennifer", "david", "linda", "robert",
    "patricia", "james", "emily", "jessica", "daniel", "laura", "mark", "susan",
    "paul", "karen", "steven", "nancy", "andrew", "emma", "kevin", "amy",
    # south asian
    "priya", "raj", "arjun", "meera", "anjali", "ravi", "deepa", "sanjay",
    "kavita", "vikram", "neha", "amit",
    # east/southeast asian
    "wei", "li", "chen", "yuki", "hiroshi", "mei", "jun", "linh", "nguyen",
    "kim", "min", "jin",
    # arabic/middle-eastern
    "ahmed", "fatima", "mohammed", "aisha", "hassan", "layla", "omar", "yasmin",
    "khalid", "noor",
    # hispanic/latino
    "carlos", "maria", "diego", "sofia", "ana", "juan", "luis", "camila",
    "javier", "valentina", "miguel", "lucia",
    # west/east african
    "kwame", "ngozi", "chidi", "amara", "kofi", "zainab", "tunde", "adaeze",
    # eastern european
    "olga", "ivan", "natasha", "dmitri", "elena", "sergei",
})

_CAP_WORD_RE = re.compile(r"\b[A-Z][a-z]+\b")


def find_invented_names(text):
    """Capitalized words matching a common first name in `text`. Best-effort
    detection, not NLP -- deliberately over-broad rather than under-broad
    (a false-positive strips a scenario that was probably fine; a false
    negative would publish an invented identity -- the asymmetry that
    matters for a YMYL anti-fabrication guard)."""
    return [m.group(0) for m in _CAP_WORD_RE.finditer(text or "")
            if m.group(0).lower() in COMMON_FIRST_NAMES]


def find_uncovered_numeric_claims(text, vertical):
    """Numeric claims in `text` not covered by an engraved Couche 1 STABLE
    fact of `vertical` -- the SAME LEVIER C predicate agent_05 uses on the
    full article (agents/_fact_coverage.py::classify_claims). Applied here
    at generation time, specifically to the scenario block, as a
    belt-and-suspenders check: agent_05 will also catch an uncovered number
    downstream on the assembled article, but this stops it before the
    scenario is even included in the draft."""
    return [c for c in classify_claims(text or "", vertical) if c["fact"] is None]


def validate_scenario_block(text, vertical):
    """(is_clean, reasons). is_clean is True only if `text` contains NEITHER
    an invented first name NOR an uncovered numeric claim. `reasons` is a
    human-readable list for the caller to log -- the caller must DROP the
    entire block on failure (never publish a partially-fixed version)."""
    names = find_invented_names(text)
    claims = find_uncovered_numeric_claims(text, vertical)
    if not names and not claims:
        return True, []
    reasons = []
    if names:
        reasons.append(f"invented name(s): {sorted(set(names))}")
    if claims:
        reasons.append(f"{len(claims)} uncovered numeric claim(s)")
    return False, reasons


def build_scenario_block(scenario_body, vertical):
    """Assemble the full section (deterministic heading + deterministic
    disclaimer + validated LLM body) if `scenario_body` passes validation,
    else "" -- never a partial/edited scenario, only whole-block accept or
    reject. Returns (block_or_empty_string, is_clean, reasons)."""
    is_clean, reasons = validate_scenario_block(scenario_body, vertical)
    if not is_clean or not (scenario_body or "").strip():
        return "", is_clean, reasons
    block = "\n\n".join([SCENARIO_HEADING, SCENARIO_DISCLAIMER, scenario_body.strip()])
    return block, is_clean, reasons
