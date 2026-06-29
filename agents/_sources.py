"""Shared YMYL source classification (single source of truth).

Sprint 2 (fix-sources) introduced an "official external source" allow-list used
by the article writer's quality gate. Sprint 4 (fact-live-sources) makes the
fact checker block on official sources that are *not live*. Both agents must
agree on what "official" means, so the definition lives here and nowhere else.

An "official external source" is one whose URL HOSTNAME (via urlparse, never the
raw URL string) ends with one of the allow-listed suffixes:
    .gov     -> IRS, USCIS, FDIC, CFPB, HHS, CMS, healthcare.gov ...
    .gc.ca   -> CRA (cra-arc), IRCC, FINTRAC (fintrac-canafe), OSFI, FCAC
    canada.ca + subdomains
Anchoring on the hostname trailing labels avoids substring false positives
(craigslist.com, theirsite.com, irs.gov.attacker.com all correctly rejected).
Internal moneyabroadguide.com links are NEVER official sources.
"""
from urllib.parse import urlparse

OFFICIAL_SOURCE_SUFFIXES = (".gov", ".gc.ca", ".canada.ca")
_INTERNAL_HOST = "moneyabroadguide.com"


def classify_url(url: str) -> str:
    """Return 'internal', 'official' or 'offlist' for a single URL.
    Matching is done on the parsed HOSTNAME, not the raw URL string."""
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    if host == _INTERNAL_HOST or host.endswith("." + _INTERNAL_HOST):
        return "internal"
    if host == "canada.ca" or any(host.endswith(s) for s in OFFICIAL_SOURCE_SUFFIXES):
        return "official"
    return "offlist"


# Backwards-compatible alias (agent_04 historically used the underscore name).
_classify_url = classify_url
