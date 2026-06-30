"""Curated pool of REAL, verified official sources, organised by topic vertical.

Why this exists
---------------
Agent 04 used to ask the LLM to cite official sources "from memory". That is
stochastic: the model would sometimes produce fewer than the tier minimum (e.g.
3 of 4) or, worse, plausible-looking invented URLs. This module removes the
guesswork for known verticals by giving the writer a short list of *real* pages
on the official allow-list (.gov / .gc.ca / canada.ca) that it only has to cite
and integrate -- it never has to recall or fabricate a URL.

Design
------
- OFFICIAL_SOURCE_POOL maps a topic_key (same keys Agent 04 already uses for
  INTERNAL_LINKS) to a list of "Authority name | https://url" entries.
- Every URL in the pool was checked LIVE (HTTP 200, redirects followed) and is
  classified "official" by agents._sources.classify_url before being added.
- We deliberately provide MORE urls than the tier minimum (margin) so a model
  that drops one still clears the gate.
- Verticals not present here fall back to the legacy "from memory" prompt (see
  has_curated_pool). We never inject an unverified URL.

Extending: add a new vertical = add a new key. No code change required.
"""
from typing import List

# Each entry: "<Authority display name> | <full https URL>".
# canada_newcomer: banking / credit / settling-in for newcomers & immigrants.
OFFICIAL_SOURCE_POOL = {
    "canada_newcomer": [
        "Financial Consumer Agency of Canada | https://www.canada.ca/en/financial-consumer-agency.html",
        "FCAC - Credit reports and scores | https://www.canada.ca/en/financial-consumer-agency/services/credit-reports-score.html",
        "FCAC - Banking | https://www.canada.ca/en/financial-consumer-agency/services/banking.html",
        "Canada Revenue Agency (CRA) | https://www.canada.ca/en/revenue-agency.html",
        "Social Insurance Number (Service Canada) | https://www.canada.ca/en/employment-social-development/services/sin.html",
        "Immigration, Refugees and Citizenship Canada | https://www.canada.ca/en/immigration-refugees-citizenship.html",
        "FINTRAC | https://fintrac-canafe.canada.ca/intro-eng",
    ],
}


def has_curated_pool(topic_key: str) -> bool:
    """True if we have a verified curated source list for this vertical."""
    return bool(OFFICIAL_SOURCE_POOL.get(topic_key))


def select_official_sources(topic_key: str, n: int) -> List[str]:
    """Return up to n curated 'name | url' entries for topic_key.

    Order is stable (definition order). Returns [] for verticals without a pool
    so callers can fall back to the legacy prompt. Never returns more than the
    pool holds.
    """
    pool = OFFICIAL_SOURCE_POOL.get(topic_key) or []
    if n <= 0:
        return []
    return list(pool[:n])
