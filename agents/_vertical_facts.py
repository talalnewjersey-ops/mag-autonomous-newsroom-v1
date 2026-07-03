"""Couche 1 — per-vertical SOURCED FACTS injected into agent_04.

Purpose: give the writer REAL .gov figures to CITE so it stops inventing them
(the real-run 2026-07-03 proved the writer fabricates 20 stats + 10 attributions
when it has no supplied numbers). Consumed via the same market+category routing
as `_source_pool.py` (resolve_vertical), injected next to the _official_block.

GOLDEN RULE (anti-staleness — the "26M CFPB" lesson):
  - STABLE fact  -> carries a fixed `value` verified live on `last_reviewed`.
  - VOLATILE fact -> `value` is None (SOURCE-ONLY). Never hard-code a moving
    number; instruct the writer to cite the current figure from `source_url`.

Every entry:
  claim         short description of the fact
  value         the figure/text to cite, or None if VOLATILE (source-only)
  source_url    exact allow-listed .gov / .canada.ca URL (no NAIC/.org, no ssa/hhs)
  status        "STABLE" | "VOLATILE"
  last_reviewed ISO date the value was verified against the source
  note          optional qualitative framing (required for VOLATILE / qualitative)

All URLs below were verified live on 2026-07-03. Entries marked
`"url_confirm": True` had the FACT verified but the canonical URL still needs a
final check before code injection (flagged honestly, not silently shipped).
"""

VERTICAL_FACTS = {
    # ---------------------------------------------------------------- us_auto
    # 6 distinct facts — well above the >=4 sourced-claim floor.
    "us_auto": [
        {
            "claim": "Texas minimum liability (30/60/25)",
            "value": "$30,000 bodily injury per person / $60,000 per accident / "
                     "$25,000 property damage",
            "source_url": "https://www.tdi.texas.gov/pubs/consumer/cb020.html",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "New York minimum liability (25/50/10)",
            "value": "$25,000 per person / $50,000 per accident / $10,000 "
                     "property damage ($100,000 if death of 2+ persons); no-fault PIP",
            "source_url": "https://www.dfs.ny.gov/consumers/auto_insurance/minimum_auto_insurance_requirements",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Florida minimum coverage (no-fault)",
            "value": "$10,000 PIP + $10,000 PDL (PIP covers 80% of medical up to $10,000)",
            "source_url": "https://www.flhsmv.gov/insurance/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "California minimum liability",
            "value": None,  # SOURCE-ONLY: volatile
            "source_url": "https://www.insurance.ca.gov/01-consumers/105-type/9-compare-prem/auto-limits.cfm",
            "status": "VOLATILE",
            "last_reviewed": "2026-07-03",
            "note": "Raised to 30/60/25 on 2025-01-01, then CPI-indexed every 5 years "
                    "from 2026. Do NOT hard-code — state it qualitatively and cite the "
                    "current figure from the source.",
        },
        {
            "claim": "International student (F/M) driver's license timeline",
            "value": "Wait 10 days after US arrival (so the I-94 updates) AND at least "
                     "2 government business days after the SEVIS record is Active before "
                     "applying for a driver's license",
            "source_url": "https://studyinthestates.dhs.gov/students/study/driving-in-the-united-states",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Driving on a foreign license (qualitative)",
            "value": None,
            "source_url": "https://www.usa.gov/non-citizen-driving",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
            "note": "F/M students may drive but must obtain a state driver's license "
                    "(driving without one is illegal); not all states accept foreign licenses.",
        },
    ],

    # -------------------------------------------------------------- us_health
    # 3 distinct fact ENTRIES (J1 is rich: 4 sub-values). Thinnest sheet —
    # add >=1 more distinct fact for robustness (see status report).
    "us_health": [
        {
            "claim": "J-1 exchange visitor insurance minimums (22 CFR 62.14)",
            "value": "Medical benefits >= $100,000 per accident/illness; repatriation "
                     "of remains $25,000; medical evacuation $50,000; deductible <= $500 "
                     "per accident/illness",
            "source_url": "https://www.ecfr.gov/current/title-22/chapter-I/subchapter-G/part-62/subpart-A/section-62.14",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Marketplace Special Enrollment Period window",
            "value": "60 days from a qualifying life event to enroll in or change "
                     "Marketplace coverage",
            "source_url": "https://www.healthcare.gov/coverage-outside-open-enrollment/special-enrollment-period/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Lawfully present immigrants — Marketplace eligibility (qualitative)",
            "value": None,
            "source_url": "https://www.healthcare.gov/immigrants/lawfully-present-immigrants/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
            "note": "Lawfully present immigrants can get Marketplace coverage and may "
                    "qualify for savings; gaining eligible status can trigger an SEP.",
        },
        {
            "claim": "Medicaid/CHIP five-year waiting period for immigrants",
            "value": "Many lawfully present immigrants must wait 5 years from gaining "
                     "qualified status before full Medicaid/CHIP (refugees and asylees "
                     "are exempt); Marketplace coverage may be available during the wait",
            "source_url": "https://www.healthcare.gov/immigrants/lawfully-present-immigrants/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
            "note": "State option (CHIPRA 2009) lets some states drop the wait for "
                    "lawfully residing children/pregnant women — keep phrasing general.",
        },
    ],

    # -------------------------------------------------------------- us_credit
    # 3 exact-URL facts + free-weekly (canonical URL to confirm).
    "us_credit": [
        {
            "claim": "Credit report dispute investigation window",
            "value": "The credit bureau must investigate a dispute within 30 days "
                     "(up to 45 days in some cases)",
            "source_url": "https://consumer.ftc.gov/articles/disputing-errors-your-credit-reports",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Negative information retention",
            "value": "Most negative information stays on a credit report for 7 years",
            "source_url": "https://www.consumerfinance.gov/ask-cfpb/how-long-does-negative-information-remain-on-my-credit-report-en-323/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Bankruptcy retention",
            "value": "Bankruptcy can stay on a credit report for up to 10 years",
            "source_url": "https://www.consumerfinance.gov/ask-cfpb/how-long-does-a-bankruptcy-appear-on-credit-reports-en-325/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Free credit reports",
            "value": "One free credit report from each of the 3 nationwide bureaus every "
                     "week at AnnualCreditReport.com (program made permanent)",
            "source_url": "https://consumer.ftc.gov/articles/free-credit-reports",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
    ],

    # ------------------------------------------------------------ us_mortgage
    # 3 FHA facts (all answers.hud.gov) + HUD counseling (URL to confirm).
    "us_mortgage": [
        {
            "claim": "FHA minimum down payment",
            "value": "As low as 3.5% of the purchase price",
            "source_url": "https://answers.hud.gov/FHA/s/article/What-is-the-minimum-down-payment-requirement-for-FHA",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "FHA minimum credit score for 3.5% down",
            "value": "580 and above (lowest decision credit score for the 3.5% down option)",
            "source_url": "https://answers.hud.gov/FHA/s/article/Does-FHA-require-a-minimum-credit-score-and-how-is-it-determined",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "FHA qualifying ratios below 580 (manual underwriting)",
            "value": "Borrowers below 580 (or with non-traditional/insufficient credit) "
                     "may not exceed 31/43 qualifying ratios",
            "source_url": "https://answers.hud.gov/FHA/s/article/What-are-the-maximum-qualifying-ratio-requirements-for-manually-underwritten-loans",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "HUD-approved housing counseling (qualitative)",
            "value": None,
            "source_url": "https://www.hud.gov/findacounselor",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
            "note": "HUD-approved counselors give buyers independent advice, often at "
                    "little or no cost (HUD HCA Locator).",
        },
    ],

    # -------------------------------------------------------------- us_banking
    # 4 distinct .gov facts (2 core + Reg E + Reg CC), verified 2026-07-03.
    "us_banking": [
        {
            "claim": "FDIC deposit insurance limit",
            "value": "Up to $250,000 per depositor, per FDIC-insured bank, per "
                     "ownership category (coverage is automatic, no purchase needed)",
            "source_url": "https://www.fdic.gov/resources/deposit-insurance/understanding-deposit-insurance",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Opening an account without an SSN (qualitative)",
            "value": None,
            "source_url": "https://www.fdic.gov/getbanked",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
            "note": "Many banks let non-citizens open an account; ID may be an ITIN, a "
                    "foreign passport, or a consular ID instead of an SSN.",
        },
        {
            "claim": "Reporting an unauthorized transfer (Regulation E)",
            "value": "Report an unauthorized electronic fund transfer within 60 days of "
                     "the statement to avoid liability for later unauthorized transfers",
            "source_url": "https://www.consumerfinance.gov/rules-policy/regulations/1005/6/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Funds availability (Regulation CC)",
            "value": None,  # SOURCE-ONLY: threshold is inflation-adjusted ($225 -> $275 on 2025-07-01)
            "source_url": "https://www.federalreserve.gov/paymentsystems/regcc-about.htm",
            "status": "VOLATILE",
            "last_reviewed": "2026-07-03",
            "note": "Cash/certain check deposits get next-business-day availability, and a "
                    "set minimum of a check deposit must be available next business day; the "
                    "dollar threshold is inflation-adjusted every 5 years — cite it from the source.",
        },
    ],

    # ------------------------------------------------------------ us_transfers
    # 3 distinct CFPB Remittance-Rule facts.
    "us_transfers": [
        {
            "claim": "Right to cancel a remittance transfer",
            "value": "You can cancel for a full refund within 30 minutes of paying "
                     "(regardless of the provider's business hours)",
            "source_url": "https://www.consumerfinance.gov/rules-policy/regulations/1005/34/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Required upfront disclosures",
            "value": "The provider must disclose the fees, the exchange rate, and the "
                     "exact amount the recipient will receive before you pay",
            "source_url": "https://www.consumerfinance.gov/ask-cfpb/what-is-a-remittance-transfer-and-what-are-my-rights-en-1161/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Error-resolution window",
            "value": "You have 180 days to report a problem; the provider generally has "
                     "90 days to investigate and report results",
            "source_url": "https://www.consumerfinance.gov/rules-policy/regulations/1005/33/",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
    ],

    # -------------------------------------------------------------- us_housing
    # 3 federal Fair-Housing facts. NB: rent/security-deposit limits are STATE law
    # (offlist) so they are intentionally absent — this sheet is fair-housing only.
    "us_housing": [
        {
            "claim": "Fair Housing Act protected classes",
            "value": "It is illegal to discriminate based on race, color, religion, sex, "
                     "familial status, national origin, or disability (7 protected classes)",
            "source_url": "https://www.justice.gov/crt/fair-housing-act-1",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Deadline to file a housing-discrimination complaint",
            "value": "File within 1 year of the last alleged discrimination with HUD",
            "source_url": "https://www.hud.gov/fairhousing/fileacomplaint",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "How to enforce fair-housing rights (qualitative)",
            "value": None,
            "source_url": "https://www.hud.gov/helping-americans/fair-housing-act-overview",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
            "note": "Victims may file a complaint with HUD or bring their own lawsuit in "
                    "federal or state court.",
        },
    ],

    # ------------------------------------------------------------- us_students
    # 3 STABLE facts + I-901 fee as SOURCE-ONLY ($350 not confirmed this session).
    "us_students": [
        {
            "claim": "F-1 on-campus work limit",
            "value": "On-campus employment is limited to 20 hours per week while school "
                     "is in session",
            "source_url": "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Post-completion OPT duration",
            "value": "USCIS may authorize up to 12 months of Optional Practical Training "
                     "after completing a degree",
            "source_url": "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-opt-for-f-1-students",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "STEM OPT extension",
            "value": "Eligible STEM-degree students may apply for a 24-month extension "
                     "of post-completion OPT",
            "source_url": "https://www.uscis.gov/working-in-the-united-states/students-and-exchange-visitors/optional-practical-training-extension-for-stem-students-stem-opt",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "I-901 SEVIS fee",
            "value": None,  # SOURCE-ONLY: $350 not confirmed this session; fees change
            "source_url": "https://www.ice.gov/sevis/i901",
            "status": "VOLATILE",
            "last_reviewed": "2026-07-03",
            "note": "Congress-mandated fee that funds SEVP; do NOT hard-code an amount — "
                    "cite the current fee from the source.",
        },
    ],

    # -------------------------------------------------------- canada_newcomer
    # FEDERAL ONLY (allow-list = .gov/.gc.ca/.canada.ca). Provincial sources
    # (OHIP, RAMQ, provincial licences, provincial auto insurance) are OFFLIST
    # and intentionally excluded. 4 canada.ca facts.
    "canada_newcomer": [
        {
            "claim": "No-cost bank accounts for newcomers (FCAC)",
            "value": "Newcomers in their first year are eligible for $0/month bank "
                     "accounts under the FCAC commitment",
            "source_url": "https://www.canada.ca/en/financial-consumer-agency/services/industry/laws-regulations/low-cost-no-cost-accounts.html",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
            "note": "Included transaction counts were enhanced in 2025 — keep phrasing "
                    "general on the number of transactions.",
        },
        {
            "claim": "Right to open a personal bank account",
            "value": "You have the right to open a personal account even without a job, "
                     "without depositing money right away, or if you are unemployed",
            "source_url": "https://www.canada.ca/en/financial-consumer-agency/services/banking/opening-bank-account.html",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Social Insurance Number (SIN) and banking",
            "value": "A SIN is needed to work and access government services/benefits; "
                     "for a non-interest-bearing account you may decline to provide it as ID",
            "source_url": "https://www.canada.ca/en/financial-consumer-agency/services/banking/opening-bank-account.html",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
        },
        {
            "claim": "Newcomers and the CRA (taxes) (qualitative)",
            "value": None,
            "source_url": "https://www.canada.ca/en/revenue-agency/services/tax/international-non-residents/individuals-leaving-entering-canada-non-residents/newcomers-canada-immigrants.html",
            "status": "STABLE",
            "last_reviewed": "2026-07-03",
            "note": "Newcomers become residents for tax purposes on arrival and may need "
                    "to file a return; details on the CRA newcomers page.",
        },
    ],
}
