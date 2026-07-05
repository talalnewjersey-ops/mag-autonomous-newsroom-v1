"""URL normalization pass. Offline: no network, no API key.

Proves: a mutated .gov URL is RESTORED to the canonical engraved-fact URL (not a
guessed one); exact supplied URLs (facts + source pool) are kept; a fully-invented
.gov URL is removed (anchor text kept); an AMBIGUOUS near-miss is NOT restored
(never guessed to a wrong page); internal / off-list links are untouched.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.normalize_urls import normalize, _canonical_urls

FTC_DISPUTE = "https://consumer.ftc.gov/articles/disputing-errors-your-credit-reports"


def test_real_mutation_restored_to_the_engraved_fact_url():
    fact_urls, known = _canonical_urls("USA", "credit")   # -> us_credit
    txt = "[dispute](https://consumer.ftc.gov/articles/disputing-errors-on-your-credit-reports)"
    out, rep = normalize(txt, fact_urls, known)
    assert rep["restored"] and rep["restored"][0]["to"] == FTC_DISPUTE
    assert rep["restored"][0]["to"] in fact_urls          # restored ONLY toward an engraved fact url
    assert FTC_DISPUTE in out and "disputing-errors-on-" not in out


def test_restoration_target_is_always_from_vertical_facts():
    fact_urls, _ = _canonical_urls("USA", "credit")
    # every fact url is a real engraved _vertical_facts source (not a guessed list)
    from agents._vertical_facts import VERTICAL_FACTS
    engraved = {f["source_url"] for f in VERTICAL_FACTS["us_credit"] if f.get("source_url")}
    assert set(fact_urls) <= engraved


def test_exact_supplied_urls_are_kept():
    facts = [FTC_DISPUTE]
    known = facts + ["https://www.irs.gov/individuals/individual-taxpayer-identification-number"]
    txt = f"[a]({FTC_DISPUTE}) [b](https://www.irs.gov/individuals/individual-taxpayer-identification-number)"
    out, rep = normalize(txt, facts, known)
    assert rep["kept"] == 2 and not rep["restored"] and not rep["removed"]


def test_fully_invented_gov_url_is_removed_text_kept():
    out, rep = normalize("see [the rule](https://www.consumerfinance.gov/totally-made-up-nonexistent-page/)",
                         [FTC_DISPUTE], [FTC_DISPUTE])
    assert rep["removed"] and "](http" not in out and "the rule" in out


def test_ambiguous_near_miss_is_not_restored():
    amb = ["https://ex.gov/a/foo-bar-baz-one", "https://ex.gov/a/foo-bar-baz-two"]
    out, rep = normalize("[x](https://ex.gov/a/foo-bar-baz-xxx)", amb, amb)
    assert not rep["restored"] and rep["removed"]          # never guess when ambiguous


def test_internal_and_offlist_links_untouched():
    txt = "[i](https://moneyabroadguide.com/x/) [e](https://www.bankofamerica.com/y/)"
    out, rep = normalize(txt, [FTC_DISPUTE], [FTC_DISPUTE])
    assert out == txt and not rep["restored"] and not rep["removed"]
