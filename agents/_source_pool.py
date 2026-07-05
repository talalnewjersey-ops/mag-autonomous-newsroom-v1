"""Curated pool of REAL, verified official sources, organised by topic vertical.

Why this exists
---------------
Agent 04 used to ask the LLM to cite official sources "from memory". That is
stochastic: the model would sometimes produce fewer than the tier minimum (e.g.
3 of 4) or, worse, plausible-looking invented URLs. This module removes the
guesswork for known verticals by giving the writer a short list of *real* pages
on the official allow-list (.gov / .canada.ca) that it only has to cite and
integrate -- it never has to recall or fabricate a URL.

Design
------
- OFFICIAL_SOURCE_POOL maps a *source vertical* key to a list of
  "Authority name | https://url" entries.
- Verticals are resolved from the registry's market + category via
  CATEGORY_TO_VERTICAL / resolve_vertical(), NOT from fragile keyword guessing.
  Canada topics keep the legacy `canada_newcomer` vertical.
- Every URL was checked LIVE (HTTP 200, redirects followed) and is on the
  official allow-list. We deliberately provide 7 urls per US vertical -- one
  above the hardest tier floor (PILLAR = 6 sources) -- so a model that drops
  one, or a page that later 404s, still clears the gate.
- us_default is a generic US federal-financial pool used as a SAFETY NET for any
  US topic whose category is unmapped, so an automated run never dies for lack
  of sources.
- ssa.gov and hhs.gov are DELIBERATELY EXCLUDED: both return HTTP 403 to
  automated/datacenter requests, so the live-source gate (which fetches from
  GitHub Actions IPs) would count them broken. Their coverage (SSN, health) is
  replaced by usa.gov, USCIS, IRS, healthcare.gov and CMS.

Extending: add a new vertical = add a new key + a CATEGORY_TO_VERTICAL entry.
No code change required.
"""
from typing import List, Optional

# Each entry: "<Authority display name> | <full https URL>".
OFFICIAL_SOURCE_POOL = {
    # ---- Canada (unchanged) : banking / credit / settling-in for newcomers ----
    "canada_newcomer": [
        "Financial Consumer Agency of Canada | https://www.canada.ca/en/financial-consumer-agency.html",
        "FCAC - Credit reports and scores | https://www.canada.ca/en/financial-consumer-agency/services/credit-reports-score.html",
        "FCAC - Banking | https://www.canada.ca/en/financial-consumer-agency/services/banking.html",
        "Canada Revenue Agency (CRA) | https://www.canada.ca/en/revenue-agency.html",
        "Social Insurance Number (Service Canada) | https://www.canada.ca/en/employment-social-development/services/sin.html",
        "Immigration, Refugees and Citizenship Canada | https://www.canada.ca/en/immigration-refugees-citizenship.html",
        "FINTRAC | https://fintrac-canafe.canada.ca/intro-eng",
    ],

    # ---- USA : generic federal-financial safety net (unmapped US categories) ----
    "us_default": [
        "CFPB - Bank accounts | https://www.consumerfinance.gov/consumer-tools/bank-accounts/",
        "FDIC Consumer Resource Center | https://www.fdic.gov/consumer-resource-center",
        "OCC - HelpWithMyBank.gov | https://www.helpwithmybank.gov/",
        "FLEC - MyMoney.gov | https://www.mymoney.gov/",
        "USA.gov - Credit reports | https://www.usa.gov/credit-reports",
        "IRS - Individual Taxpayer Identification Number (ITIN) | https://www.irs.gov/individuals/individual-taxpayer-identification-number",
        "USA.gov - Social Security card | https://www.usa.gov/social-security-card",
    ],

    # ---- USA : banking + no-SSN account opening / documents ----
    "us_banking": [
        "CFPB - Bank accounts | https://www.consumerfinance.gov/consumer-tools/bank-accounts/",
        "FDIC Consumer Resource Center | https://www.fdic.gov/consumer-resource-center",
        "OCC - HelpWithMyBank.gov | https://www.helpwithmybank.gov/",
        "FLEC - MyMoney.gov | https://www.mymoney.gov/",
        "USA.gov - Social Security card | https://www.usa.gov/social-security-card",
        "USCIS - Working in the United States | https://www.uscis.gov/working-in-the-united-states",
        "IRS - Taxpayer Identification Numbers (TIN) | https://www.irs.gov/individuals/international-taxpayers/taxpayer-identification-numbers-tin",
    ],

    # ---- USA : credit cards, credit score, ITIN credit, credit-builder, loans ----
    "us_credit": [
        "CFPB - Credit reports and scores | https://www.consumerfinance.gov/consumer-tools/credit-reports-and-scores/",
        "CFPB - Credit cards | https://www.consumerfinance.gov/consumer-tools/credit-cards/",
        "IRS - Individual Taxpayer Identification Number (ITIN) | https://www.irs.gov/individuals/individual-taxpayer-identification-number",
        "USA.gov - Credit reports | https://www.usa.gov/credit-reports",
        "CFPB - Payday loans | https://www.consumerfinance.gov/ask-cfpb/category-payday-loans/",
        "FTC - Payday and car title loans | https://consumer.ftc.gov/articles/what-know-about-payday-and-car-title-loans",
        "FLEC - MyMoney.gov | https://www.mymoney.gov/",
    ],

    # ---- USA : international money transfers / remittances ----
    "us_transfers": [
        "CFPB - Sending money | https://www.consumerfinance.gov/consumer-tools/sending-money/",
        "CFPB - Money transfers Q&A | https://www.consumerfinance.gov/ask-cfpb/category-money-transfers/",
        "FDIC Consumer Resource Center | https://www.fdic.gov/consumer-resource-center",
        "CFPB - Bank accounts | https://www.consumerfinance.gov/consumer-tools/bank-accounts/",
        "FLEC - MyMoney.gov | https://www.mymoney.gov/",
        "USA.gov - Credit reports | https://www.usa.gov/credit-reports",
        "OCC - HelpWithMyBank.gov | https://www.helpwithmybank.gov/",
    ],

    # ---- USA : auto insurance + driver's license (state DOI / DMV) ----
    "us_auto": [
        "California DOI - Automobile insurance | https://www.insurance.ca.gov/01-consumers/105-type/95-guides/01-auto/",
        "New York DMV - Insurance requirements | https://dmv.ny.gov/insurance/insurance-requirements",
        "Florida FLHSMV - Insurance | https://www.flhsmv.gov/insurance/",
        "Texas DOI - Auto insurance | https://www.tdi.texas.gov/consumer/auto-insurance.html",
        "USA.gov - Motor vehicle services | https://www.usa.gov/motor-vehicle-services",
        "California DMV - Driver's licenses | https://www.dmv.ca.gov/portal/driver-licenses-identification-cards/",
        "Illinois Department of Insurance | https://insurance.illinois.gov/",
    ],

    # ---- USA : health insurance for immigrants / F1-J1 students ----
    "us_health": [
        "HealthCare.gov - Immigrants coverage | https://www.healthcare.gov/immigrants/coverage/",
        "HealthCare.gov - Lawfully present immigrants | https://www.healthcare.gov/immigrants/lawfully-present-immigrants/",
        "HealthCare.gov - Immigration status and coverage | https://www.healthcare.gov/immigrants/immigration-status/",
        "CMS - Health Insurance Marketplace | https://www.cms.gov/marketplace",
        "IRS - Affordable Care Act for individuals and families | https://www.irs.gov/affordable-care-act/individuals-and-families",
        "USA.gov - Health insurance | https://www.usa.gov/health-insurance",
        "DHS - Study in the States | https://studyinthestates.dhs.gov/",
    ],

    # ---- USA : renting + renters insurance ----
    "us_housing": [
        "HUD - Rental assistance | https://www.hud.gov/topics/rental_assistance",
        "HUD - Housing Choice Voucher (Section 8) | https://www.hud.gov/topics/housing_choice_voucher_program_section_8",
        "HUD - Fair Housing and Equal Opportunity | https://www.hud.gov/program_offices/fair_housing_equal_opp",
        "USA.gov - Housing help | https://www.usa.gov/housing-help",
        "USA.gov - Tenant rights | https://www.usa.gov/tenant-rights",
        "California DOI - Residential/renters insurance | https://www.insurance.ca.gov/01-consumers/105-type/95-guides/03-res/",
        "DOJ Civil Rights - Fair Housing Act | https://www.justice.gov/crt/fair-housing-act-1",
    ],

    # ---- USA : first-time home buyer mortgage ----
    "us_mortgage": [
        "CFPB - Owning a home | https://www.consumerfinance.gov/owning-a-home/",
        "CFPB - Mortgages | https://www.consumerfinance.gov/consumer-tools/mortgages/",
        "CFPB - Mortgages Q&A | https://www.consumerfinance.gov/ask-cfpb/category-mortgages/",
        "CFPB - Loan options | https://www.consumerfinance.gov/owning-a-home/loan-options/",
        "USA.gov - Buying a home | https://www.usa.gov/buying-home",
        "HUD - Buying a home | https://www.hud.gov/topics/buying_a_home",
        "FLEC - MyMoney.gov | https://www.mymoney.gov/",
    ],

    # ---- USA : international students money setup ----
    "us_students": [
        "DHS - Study in the States | https://studyinthestates.dhs.gov/",
        "IRS - Foreign students and scholars | https://www.irs.gov/individuals/international-taxpayers/foreign-students-and-scholars",
        "Federal Student Aid - Non-U.S. citizens | https://studentaid.gov/understand-aid/eligibility/requirements/non-us-citizens",
        "USA.gov - Social Security card | https://www.usa.gov/social-security-card",
        "FLEC - MyMoney.gov | https://www.mymoney.gov/",
        "USA.gov - Credit reports | https://www.usa.gov/credit-reports",
        "IRS - Taxpayer Identification Numbers (TIN) | https://www.irs.gov/individuals/international-taxpayers/taxpayer-identification-numbers-tin",
    ],
}

# Registry `category` (as stored in data/topic_registry.json) -> US source vertical.
# Categories are shared US/Canada, so this map is applied ONLY for US topics
# (see resolve_vertical); Canada keeps `canada_newcomer`.
CATEGORY_TO_VERTICAL = {
    "banques": "us_banking",
    "cartes": "us_credit",
    "credit": "us_credit",
    "credit builder": "us_credit",
    "credit conso": "us_credit",
    "transferts": "us_transfers",
    "assurance auto": "us_auto",
    "assurance sante": "us_health",
    "assur habitation": "us_housing",
    "credit immo": "us_mortgage",
    "banques cartes": "us_students",
}

_US_MARKETS = {"usa", "us", "united states", "u.s.", "u.s.a."}


def resolve_vertical(market: str, category: str) -> Optional[str]:
    """Resolve the source vertical from a registry topic's market + category.

    - US market: map the category to a us_* vertical, falling back to `us_default`
      (the generic federal-financial safety net) for unmapped/empty categories so
      an automated run is never left without a pool.
    - Non-US (Canada / unknown): return None so the caller keeps its legacy
      keyword-derived key (e.g. `canada_newcomer`), preserving current behaviour.
    """
    m = (market or "").strip().lower()
    if m in _US_MARKETS:
        c = (category or "").strip().lower()
        return CATEGORY_TO_VERTICAL.get(c, "us_default")
    return None


def resolve_gate_vertical(market: str, category: str) -> str:
    """Vertical for fact-citation gating (G-Substance, GATE A, Couche 2 soften).
    Relocated here from scripts/g_substance_gate.py (hygiene: it is vertical
    resolution, not gate logic) -- re-exported from there unchanged for existing
    callers/tests. Mirrors resolve_vertical's routing; Canada (resolve_vertical
    -> None) maps to canada_newcomer; unmapped US -> us_default (which has no
    fact sheet, so such articles fail the cited-facts floor by design)."""
    v = resolve_vertical(market, category)
    if v:
        return v
    return "canada_newcomer" if "canada" in (market or "").lower() else "us_default"


def has_curated_pool(vertical: str) -> bool:
    """True if we have a verified curated source list for this vertical."""
    return bool(OFFICIAL_SOURCE_POOL.get(vertical))


def select_official_sources(vertical: str, n: int) -> List[str]:
    """Return up to n curated 'name | url' entries for the vertical.

    Order is stable (definition order). Returns [] for verticals without a pool
    so callers can fall back to the legacy prompt. Never returns more than the
    pool holds.
    """
    pool = OFFICIAL_SOURCE_POOL.get(vertical) or []
    if n <= 0:
        return []
    return list(pool[:n])
