"""Couche 3 -- G-Substance gate, revised to judge the CLEANED article (Option B).
Offline: no network, no API key.

Proves: OR/strict combination; tier-aware source floor; the Option B rule
(>= N=2 STABLE facts of the vertical actually cited); the documented edge case
(substantial + honest but only ONE cited STABLE fact -> FAIL, intended); the
soften-integrity residual check; and that the CLI BLOCKS (exit 1 on FAIL, 0 on
PASS) so a rejected article never proceeds toward WordPress.

LEVIER C PART 1 (2026-07-05): "cited" now means value-matched via
agents._fact_coverage.classify_claims, not mere source_url substring presence.
The NUMERIC case (utilization = 30%, the fact behind the real
proximity-false-sourced incident) is exercised separately below.

LEVIER C PART 2 (2026-07-05): _NUM_RE was extended to bare day/week/month/year/
bureau counts. This RECLASSIFIED "30 days" (dispute) and "7 years" (retention)
from qualitative (URL-presence credit) to numeric (value-match credit) -- both
still correctly cited below since GOOD states their exact engraved values.
It ALSO reclassified "Free credit reports" (FTC_FREE): its own engraved value
("... each of the 3 nationwide bureaus ...") now contains a bare-unit token
("bureau", 3.0), so the fact is no longer purely qualitative -- GOOD's Reports
line now states the bureau count explicitly so it is genuinely, not just
nominally, cited (a fixture stating "free report weekly" with the number
omitted would no longer count -- correct: G-Substance's whole point is that a
STABLE fact with a real citable figure must show that figure, not just its
link).
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.g_substance_gate import evaluate, resolve_gate_vertical

# us_credit STABLE-fact source URLs (from agents/_vertical_facts.py)
FTC_DISPUTE = "https://consumer.ftc.gov/articles/disputing-errors-your-credit-reports"
CFPB_7YR = "https://www.consumerfinance.gov/ask-cfpb/how-long-does-negative-information-remain-on-my-credit-report-en-323/"
FTC_FREE = "https://consumer.ftc.gov/articles/free-credit-reports"
IRS_ITIN = "https://www.irs.gov/individuals/individual-taxpayer-identification-number"

# STANDARD article citing 3 us_credit STABLE facts + IRS = 4 distinct sources, FAQ, 5 H2, no unsourced figures.
GOOD = f"""## Overview
Bureaus must investigate disputes within 30 days ([FTC]({FTC_DISPUTE})).

## Retention
Negative information stays 7 years ([CFPB]({CFPB_7YR})).

## Reports
You can pull a free report from each of the 3 nationwide bureaus every week ([FTC]({FTC_FREE})).

## ITIN
An ITIN works in place of an SSN ([IRS]({IRS_ITIN})).

## Frequently Asked Questions
### Do I need an SSN?
No, an ITIN can work.
"""


def V(market="USA", category="credit"):
    return resolve_gate_vertical(market, category)


def test_routing_us_credit():
    assert V() == "us_credit"


def test_good_article_passes():
    r = evaluate(GOOD, "STANDARD", V())
    assert r["verdict"] == "PASS" and r["reasons"] == []
    assert r["cited_stable_facts"] == 3 and r["distinct_sources"] == 4 and r["residual_unsourced"] == 0


def test_fail_when_too_few_sources():
    thin = GOOD.replace(f"([CFPB]({CFPB_7YR}))", "").replace(f"([IRS]({IRS_ITIN}))", "")
    r = evaluate(thin, "STANDARD", V())          # 2 distinct sources < 4
    assert r["verdict"] == "FAIL" and any("distinct official sources" in x for x in r["reasons"])


# ---- Option B edge case the user asked to document ----

def test_substantial_but_only_one_cited_stable_fact_fails():
    # Keep it substantial (4 distinct .gov sources, FAQ, H2) but cite only ONE STABLE
    # us_credit fact -> FAIL on criterion (2) alone. This is the intended Option B behaviour.
    one_fact = f"""## Overview
Bureaus must investigate disputes within 30 days ([FTC]({FTC_DISPUTE})).

## Rights
See the CFPB ([tools](https://www.consumerfinance.gov/consumer-tools/credit-reports-and-scores/)) and
the IRS ([ITIN]({IRS_ITIN})) and general FTC credit advice ([guide](https://consumer.ftc.gov/articles/understanding-your-credit)).

## Steps
Open an ITIN account and pay on time, every month.

## Frequently Asked Questions
### Do I need an SSN?
No.
"""
    r = evaluate(one_fact, "STANDARD", V())
    assert r["distinct_sources"] >= 4            # genuinely substantial sourcing
    assert r["cited_stable_facts"] == 1          # but only one STABLE fact cited
    assert r["verdict"] == "FAIL"
    assert r["reasons"] == ["only 1 STABLE facts cited (need >= 2)"]   # THIS reason only


def test_min_cited_facts_is_configurable():
    # Cites exactly ONE us_credit STABLE fact (FTC_DISPUTE) + 3 non-fact .gov sources.
    one = (f"## A\nDisputes within 30 days ([FTC]({FTC_DISPUTE})).\n"
           f"## B\nSee ([IRS]({IRS_ITIN})) and ([CFPB](https://www.consumerfinance.gov/consumer-tools/credit-cards/)) "
           f"and ([FTC2](https://consumer.ftc.gov/articles/understanding-your-credit)).\n"
           f"## FAQ\n### Q?\nA.\n")
    assert evaluate(one, "OPPORTUNITY", V(), min_cited_facts=2)["verdict"] == "FAIL"  # cited 1 < 2
    assert evaluate(one, "OPPORTUNITY", V(), min_cited_facts=1)["verdict"] == "PASS"  # cited 1 >= 1


# ---- structure + integrity ----

def test_fail_when_no_faq():
    r = evaluate(GOOD.replace("## Frequently Asked Questions", "## Notes"), "STANDARD", V())
    assert r["verdict"] == "FAIL" and "no FAQ section" in r["reasons"]


def test_h1_faq_is_recognized():
    # Piece 1: the writer often emits the FAQ as H1; it must still count as a FAQ.
    h1 = GOOD.replace("## Frequently Asked Questions", "# Frequently Asked Questions")
    r = evaluate(h1, "STANDARD", V())
    assert r["has_faq"] is True and "no FAQ section" not in r["reasons"]


def test_fail_when_unsourced_figure_survives():
    # A fabrication soften should have removed but didn't (integrity net).
    # Isolate the survivor well past the +-100 proximity window from any .gov link.
    filler = "This sentence carries no citation and only exists to add distance. " * 3
    survived = GOOD + "\n" + filler + "Roughly 45 million people are affected each year with no source.\n"
    r = evaluate(survived, "STANDARD", V())
    assert r["residual_unsourced"] >= 1
    assert r["verdict"] == "FAIL" and any("survived soften" in x for x in r["reasons"])


def test_tier_aware_source_floor():
    three = GOOD.replace(f"([IRS]({IRS_ITIN}))", "")   # 3 distinct sources
    assert evaluate(three, "OPPORTUNITY", V())["verdict"] == "PASS"   # floor 3, still 3 cited facts
    assert any("distinct official sources" in x for x in evaluate(three, "STANDARD", V())["reasons"])  # floor 4


# ---- blocking CLI + safe path ----

def test_cli_blocks_on_fail_and_passes_clean(tmp_path):
    gate = os.path.join(ROOT, "scripts", "g_substance_gate.py")
    good = tmp_path / "good.md"; good.write_text(GOOD, encoding="utf-8")
    ok = subprocess.run([sys.executable, gate, "--input", str(good), "--article-type", "STANDARD",
                         "--market", "USA", "--category", "credit"], capture_output=True, text=True)
    assert ok.returncode == 0                    # PASS -> proceeds

    # Only-one-cited-fact article -> FAIL -> exit 1 -> workflow `continue` -> never published.
    one = tmp_path / "one.md"
    one.write_text(f"## A\nDisputes within 30 days ([FTC]({FTC_DISPUTE})).\n## B\nx ([IRS]({IRS_ITIN})) "
                   f"([CFPB](https://www.consumerfinance.gov/consumer-tools/)) "
                   f"([FTC2](https://consumer.ftc.gov/articles/understanding-your-credit)).\n"
                   f"## FAQ\n### Q?\nA.\n", encoding="utf-8")
    out = tmp_path / "g.json"
    ko = subprocess.run([sys.executable, gate, "--input", str(one), "--article-type", "STANDARD",
                         "--market", "USA", "--category", "credit", "--output", str(out)],
                        capture_output=True, text=True)
    assert ko.returncode == 1                    # FAIL -> BLOCKS (never reaches WordPress)
    assert json.loads(out.read_text())["verdict"] == "FAIL"


# ---- LEVIER C: a NUMERIC STABLE fact must be value-matched, not just link-present ----

CFPB_UTIL = "https://www.consumerfinance.gov/ask-cfpb/how-do-i-get-and-keep-a-good-credit-score-en-318/"


def test_numeric_fact_correctly_cited_counts():
    # 30% is the utilization fact's EXACT engraved value, at its real source_url.
    good = (f"## Overview\nBureaus must investigate disputes within 30 days ([FTC]({FTC_DISPUTE})).\n"
            f"## Retention\nNegative information stays 7 years ([CFPB]({CFPB_7YR})).\n"
            f"## Utilization\nExperts advise keeping your credit use to no more than 30% of your "
            f"total credit limit ([CFPB]({CFPB_UTIL})).\n"
            f"## ITIN\nAn ITIN works in place of an SSN ([IRS]({IRS_ITIN})).\n"
            f"## Frequently Asked Questions\n### Do I need an SSN?\nNo.\n")
    r = evaluate(good, "STANDARD", V())
    assert r["verdict"] == "PASS"
    assert r["cited_stable_facts"] == 3   # dispute + retention (qualitative) + utilization (numeric, matched)


def test_wrong_number_next_to_the_real_link_does_not_count_as_cited():
    # The exact real-run bug (run 28731153809): "10%" sits near the genuine CFPB
    # en-318 link that supports 30%, but 30% itself is never stated -- the fact
    # must NOT be credited as cited by proximity to its own link alone.
    bad = (f"## Overview\nBureaus must investigate disputes within 30 days ([FTC]({FTC_DISPUTE})).\n"
           f"## Retention\nNegative information stays 7 years ([CFPB]({CFPB_7YR})).\n"
           f"## Utilization\nSome advisors recommend staying under 10% for an excellent score "
           f"([CFPB]({CFPB_UTIL})).\n"
           f"## ITIN\nAn ITIN works in place of an SSN ([IRS]({IRS_ITIN})).\n"
           f"## Frequently Asked Questions\n### Do I need an SSN?\nNo.\n")
    r = evaluate(bad, "STANDARD", V())
    assert r["cited_stable_facts"] == 2           # dispute + retention only -- NOT utilization
    assert r["residual_unsourced"] >= 1           # the fabricated "10%" survives as unsourced
    assert r["verdict"] == "FAIL"
