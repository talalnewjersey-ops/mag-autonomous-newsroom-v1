"""Single source of truth for the numeric-claim / attribution / URL regexes.

Shared by BOTH the Sprint 10 detection (agents/agent_05_fact_checker.py) and the
Couche 2 soften pass (scripts/soften_claims.py). One definition means detection
and softening can never drift apart: the soften pass must strip exactly what the
detector would flag. Pure regex, no dependencies.
"""
import re

# A "hard" numeric claim: a %, a $ / CAD amount, "N times/x", "N out of N",
# a magnitude count ("45 million"), or a score threshold ("650+"). The last two
# were added after a real run let "approximately 45 million ... credit invisible"
# and "650+ score" survive the soften pass (bare numbers _NUM_RE did not match).
_NUM_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s?%|\$\s?\d[\d,]*(?:\.\d+)?|\bCAD\s?\d[\d,]*|"
    r"\b\d+(?:\.\d+)?\s?(?:times|x)\b|\b\d+\s+out of\s+\d+\b|"
    r"\b\d[\d,]*(?:\.\d+)?\s?(?:million|billion|thousand)\b|"
    r"\b\d{2,}\+)", re.I)

# A named-source attribution cue (raises severity to "unbacked_attribution").
_ATTR_RE = re.compile(
    r"(?i)\b(?:according to|per|based on|reports?|survey|study|found by|data from|says?)\b|\([12]\d{3}\)")

# An inline URL (used to check for an allow-listed citation near a claim).
_URL_IN = re.compile(r"https?://[^\s\)\]>,;]+")
