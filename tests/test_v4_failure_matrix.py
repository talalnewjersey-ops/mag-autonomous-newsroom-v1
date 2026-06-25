"""
NEXUS-14 V4 - tests/test_v4_failure_matrix.py

Closes the explicit FAILURE-SCENARIO matrix (certification Phase 3) at the
authoritative Quality Gate V4 level. Every scenario asserts that a specific
defect is independently DETECTED and BLOCKS publication. These tests exercise
the real gate check functions (no mocks) and make NO network / WordPress /
OpenAI calls (EMBEDDINGS_PROVIDER=hashing).

Scenarios covered:
  * missing author              -> eeat gate fails
  * duplicate / broken canonical -> canonical_uniqueness gate fails
  * body JSON-LD (2nd schema src) -> schema gate fails
  * emoji heading                -> formatting gate fails
  * image missing alt text       -> accessibility gate fails
  * full-gate broken canonical   -> run_gate BLOCKED with canonical failure
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("EMBEDDINGS_PROVIDER", "hashing")

import scripts.quality_gate_v4 as qg


# A meta dict with every required EEAT element present (baseline to mutate).
COMPLETE_META = {
    "title": "How To Send Money Abroad Cheaply In 2026",
    "slug": "send-money-abroad-cheaply-2026",
    "keywords": ["send money abroad", "transfer fees"],
    "author": "Talal Eddaouahiri",
    "review_date": "2026-06-25",
    "update_date": "2026-06-25",
    "official_references": ["https://www.irs.gov/businesses"],
    "disclosure": True,
    "related_articles": ["https://moneyabroadguide.com/compare"],
}


# --------------------------------------------------------------------------- #
# EEAT - missing author                                                         #
# --------------------------------------------------------------------------- #
def test_eeat_complete_passes():
    assert qg.check_eeat(COMPLETE_META)["passed"] is True


def test_eeat_missing_author_fails():
    meta = dict(COMPLETE_META)
    meta.pop("author")
    res = qg.check_eeat(meta)
    assert res["passed"] is False
    assert "author" in res["missing_elements"]


@pytest.mark.parametrize("missing", [
    "author", "review_date", "update_date",
    "official_references", "disclosure", "related_articles",
])
def test_eeat_each_required_element_blocks(missing):
    meta = dict(COMPLETE_META)
    meta.pop(missing)
    res = qg.check_eeat(meta)
    assert res["passed"] is False
    assert missing in res["missing_elements"]


# --------------------------------------------------------------------------- #
# Canonical uniqueness - duplicate / broken canonical                           #
# --------------------------------------------------------------------------- #
def test_canonical_unique_against_unrelated_corpus_passes():
    corpus = [{"title": "best travel backpacks", "slug": "best-travel-backpacks"}]
    res = qg.check_canonical_uniqueness(
        COMPLETE_META["title"], COMPLETE_META["slug"], corpus)
    assert res["passed"] is True


def test_canonical_duplicate_title_blocks():
    # A corpus entry that is essentially the same title/slug must trip the
    # canonical-uniqueness ceiling (> 0.85 similarity).
    corpus = [{
        "title": COMPLETE_META["title"],
        "slug": COMPLETE_META["slug"],
    }]
    res = qg.check_canonical_uniqueness(
        COMPLETE_META["title"], COMPLETE_META["slug"], corpus)
    assert res["passed"] is False
    assert (res["max_title_similarity"] > qg.THRESHOLDS["canonical_title_max"]
            or res["max_slug_similarity"] > qg.THRESHOLDS["canonical_slug_max"])


# --------------------------------------------------------------------------- #
# Schema - body JSON-LD is a forbidden second schema source                     #
# --------------------------------------------------------------------------- #
def test_schema_yoast_only_passes():
    html = "<p>Body</p><!-- wp:yoast/faq-block -->"
    res = qg.check_schema(html)
    assert res["passed"] is True
    assert res["body_jsonld_present"] is False


def test_schema_body_jsonld_blocks():
    html = ('<p>Body</p>'
            '<script type="application/ld+json">{"@type":"FAQPage"}</script>')
    res = qg.check_schema(html)
    assert res["passed"] is False
    assert res["body_jsonld_present"] is True


# --------------------------------------------------------------------------- #
# Formatting - emoji headings are banned                                         #
# --------------------------------------------------------------------------- #
def test_formatting_clean_headings_pass():
    md = "## How Transfer Fees Work\nText.\n\n## Choosing A Service\nText.\n"
    assert qg.check_formatting(md)["passed"] is True


def test_formatting_emoji_heading_blocks():
    md = "## \U0001F680 Getting Started\nText.\n"
    res = qg.check_formatting(md)
    assert res["passed"] is False
    assert res["emoji_headings"]


# --------------------------------------------------------------------------- #
# Accessibility - every image needs alt text                                    #
# --------------------------------------------------------------------------- #
def test_accessibility_with_alt_passes():
    html = '<img src="chart.png" alt="fee comparison chart">'
    res = qg.check_accessibility(html)
    assert res["passed"] is True
    assert res["images_missing_alt"] == 0


def test_accessibility_missing_alt_blocks():
    html = '<img src="chart.png"><img src="ok.png" alt="ok">'
    res = qg.check_accessibility(html)
    assert res["passed"] is False
    assert res["images_missing_alt"] == 1


# --------------------------------------------------------------------------- #
# Internal links - below the minimum is a block                                 #
# --------------------------------------------------------------------------- #
def test_internal_links_below_minimum_blocks():
    md = "See [one](https://moneyabroadguide.com/a) only.\n"
    res = qg.check_internal_links(md)
    assert res["passed"] is False
    assert res["count"] < res["min"]


# --------------------------------------------------------------------------- #
# Full-gate integration: a broken-canonical article is BLOCKED end-to-end.      #
# Drives run_gate directly with a controlled temp corpus whose FILENAME stem    #
# (which run_gate uses as the corpus title/slug) duplicates the article slug.   #
# --------------------------------------------------------------------------- #
def _args(tmp_path, markdown, rendered, meta, corpus_files):
    art = tmp_path / "article.md"; art.write_text(markdown, encoding="utf-8")
    ren = tmp_path / "rendered.html"; ren.write_text(rendered, encoding="utf-8")
    met = tmp_path / "meta.json"; met.write_text(json.dumps(meta), encoding="utf-8")
    corpus_dir = tmp_path / "corpus"; corpus_dir.mkdir()
    for fname, body in corpus_files.items():
        (corpus_dir / fname).write_text(body, encoding="utf-8")
    out = tmp_path / "gate.json"

    class _A:
        pass
    a = _A()
    a.article = str(art)
    a.rendered = str(ren)
    a.meta = str(met)
    a.corpus_dir = str(corpus_dir)
    a.performance_report = None
    a.competitor_report = None
    a.output = str(out)
    return a


def test_run_gate_blocks_on_broken_canonical(tmp_path):
    # The corpus file stem equals the article slug -> run_gate derives a corpus
    # title/slug identical to the article, forcing a canonical collision.
    slug = COMPLETE_META["slug"]
    corpus_files = {slug + ".md": "## Heading\nExisting near-duplicate body.\n"}
    markdown = (
        "Intro.\n\n## How Transfer Fees Work\n"
        "Links: [a](https://moneyabroadguide.com/a) "
        "[b](https://moneyabroadguide.com/b) [c](https://moneyabroadguide.com/c) "
        "[d](https://moneyabroadguide.com/d) [e](https://moneyabroadguide.com/e).\n"
    )
    rendered = '<p>Body</p><img src="x.png" alt="x"><!-- wp:yoast/faq-block -->'
    args = _args(tmp_path, markdown, rendered, COMPLETE_META, corpus_files)
    result = qg.run_gate(args)
    assert result["decision"] == "BLOCKED"
    assert "canonical_uniqueness" in result["failed_gates"]
