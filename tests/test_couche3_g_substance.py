"""Couche 3 -- G-Substance blocking gate. Offline: no network, no API key.

Proves the OR/strict combination (any one criterion -> FAIL), the tier-aware
source floor (3/4/6), the configurable strip-ratio, the structure checks
(FAQ + H2), the divide-by-zero guard, and that the CLI BLOCKS (exit 1 on FAIL,
0 on PASS) so a rejected article never proceeds toward WordPress.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.g_substance_gate import evaluate

# A well-formed STANDARD article: 4 distinct .gov sources, FAQ, 5 H2 sections.
GOOD = """## Overview
Newcomers face many choices. See https://www.irs.gov/itin and https://www.fdic.gov/getbanked .

## Requirements
Details at https://www.consumerfinance.gov/rules and https://www.hud.gov/fha .

## Steps
Follow the plan carefully and in order.

## Costs
Budget ahead for the essentials you will need.

## Frequently Asked Questions
### Do I need an SSN?
No, an ITIN can work.
"""
LOW_STRIP = {"numeric_claims_total": 8, "unsourced_found": 1}   # 12.5%


def test_good_article_passes():
    r = evaluate(GOOD, LOW_STRIP, "STANDARD")
    assert r["verdict"] == "PASS" and r["reasons"] == []
    assert r["distinct_sources"] == 4 and r["has_faq"] and r["h2_count"] == 5


def test_fail_when_too_few_sources():
    only_two = GOOD.replace("https://www.consumerfinance.gov/rules", "https://example.com/x") \
                   .replace("https://www.hud.gov/fha", "https://example.com/y")
    r = evaluate(only_two, LOW_STRIP, "STANDARD")
    assert r["verdict"] == "FAIL" and any("distinct official sources" in x for x in r["reasons"])


def test_tier_aware_floor_opportunity_vs_standard():
    three = GOOD.replace("https://www.hud.gov/fha", "https://example.com/y")  # 3 .gov left
    assert evaluate(three, LOW_STRIP, "OPPORTUNITY")["verdict"] == "PASS"   # floor 3
    assert evaluate(three, LOW_STRIP, "STANDARD")["verdict"] == "FAIL"      # floor 4


def test_fail_when_strip_ratio_above_threshold():
    r = evaluate(GOOD, {"numeric_claims_total": 10, "unsourced_found": 6}, "STANDARD")  # 60%
    assert r["verdict"] == "FAIL" and any("strip-ratio" in x for x in r["reasons"])


def test_strip_ratio_threshold_is_configurable():
    rep = {"numeric_claims_total": 10, "unsourced_found": 6}  # 60%
    assert evaluate(GOOD, rep, "STANDARD", max_strip_ratio=0.50)["verdict"] == "FAIL"
    assert evaluate(GOOD, rep, "STANDARD", max_strip_ratio=0.70)["verdict"] == "PASS"


def test_divide_by_zero_guard_no_false_fail():
    r = evaluate(GOOD, {"numeric_claims_total": 0, "unsourced_found": 0}, "STANDARD")
    assert r["strip_ratio"] == 0.0 and r["verdict"] == "PASS"


def test_fail_when_no_faq():
    no_faq = GOOD.replace("## Frequently Asked Questions", "## More Notes")
    r = evaluate(no_faq, LOW_STRIP, "STANDARD")
    assert r["verdict"] == "FAIL" and "no FAQ section" in r["reasons"]


def test_fail_when_too_few_h2():
    thin = "## Only One\nText with https://www.irs.gov/a https://www.fdic.gov/b " \
           "https://www.hud.gov/c https://www.consumerfinance.gov/d .\n## FAQ\n### Q?\nA.\n"
    r = evaluate(thin, LOW_STRIP, "STANDARD")   # 2 H2 < 4
    assert r["verdict"] == "FAIL" and any("H2 sections" in x for x in r["reasons"])


def test_or_gate_accumulates_all_reasons():
    bad = "## One\nNo sources here.\n"  # few sources + no FAQ + few H2
    r = evaluate(bad, {"numeric_claims_total": 10, "unsourced_found": 9}, "STANDARD")
    assert r["verdict"] == "FAIL" and len(r["reasons"]) >= 3   # strict OR: every miss listed


def test_cli_blocks_on_fail_and_passes_clean(tmp_path):
    gate = os.path.join(ROOT, "scripts", "g_substance_gate.py")
    good = tmp_path / "good.md"; good.write_text(GOOD, encoding="utf-8")
    rep = tmp_path / "soften.json"; rep.write_text(json.dumps(LOW_STRIP), encoding="utf-8")
    ok = subprocess.run([sys.executable, gate, "--input", str(good),
                         "--soften-report", str(rep), "--article-type", "STANDARD"],
                        capture_output=True, text=True)
    assert ok.returncode == 0                       # PASS -> proceeds

    bad = tmp_path / "bad.md"; bad.write_text("## One\nNo sources.\n", encoding="utf-8")
    out = tmp_path / "g.json"
    ko = subprocess.run([sys.executable, gate, "--input", str(bad),
                         "--soften-report", str(rep), "--article-type", "STANDARD",
                         "--output", str(out)], capture_output=True, text=True)
    assert ko.returncode == 1                       # FAIL -> BLOCKS (workflow continues, no WP)
    assert json.loads(out.read_text())["verdict"] == "FAIL"
