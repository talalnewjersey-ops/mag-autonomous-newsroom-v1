"""2026-07-10 (site-level EEAT signal, lever "b" of the 48624 QA-score
diagnosis): agent_04_article_writer.py now appends a deterministic,
zero-LLM-cost paragraph linking the site's own published methodology pages
(Fact-Checking Process, How We Test) after the author bio -- a real,
already-published site signal, not fabricated content.

Same POINT-4 rule (2026-07-05) as the article-to-article internal links: the
URL is fetched LIVE via agents._real_internal_links.fetch_methodology_links()
at write time, never hardcoded in source (a hardcoded deep link can silently
go dead the way the old static INTERNAL_LINKS dict did -- see
tests/test_fix_l189_internal_url.py's guard against that class of bug).

Offline: fetch_methodology_links is monkeypatched, no real network.
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_spec = importlib.util.spec_from_file_location(
    "agent_04_methodology_links_test", os.path.join(ROOT, "agents/agent_04_article_writer.py"))
agent_04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_04)

SRC = open(os.path.join(ROOT, "agents/agent_04_article_writer.py"), encoding="utf-8").read()


def test_builds_markdown_from_two_live_links(monkeypatch):
    monkeypatch.setattr(agent_04, "fetch_methodology_links", lambda: [
        {"title": "Fact-Checking Process", "url": "https://moneyabroadguide.com/fact-checking-process/"},
        {"title": "How We Test", "url": "https://moneyabroadguide.com/how-we-test/"},
    ])
    md = agent_04._build_methodology_links_md()
    assert "[Fact-Checking Process](https://moneyabroadguide.com/fact-checking-process/)" in md
    assert "[How We Test](https://moneyabroadguide.com/how-we-test/)" in md
    assert md.startswith("*") and md.endswith("*")  # italicized, matches _AUTHOR_BIO_MD's tone


def test_builds_markdown_from_a_single_live_link(monkeypatch):
    # e.g. one page renamed/unpublished -- must still produce a valid,
    # non-empty block from whatever IS confirmed live (fetch_methodology_
    # links itself never invents the missing one, see test_real_internal_
    # links.py::test_fetch_methodology_links_a_renamed_or_unpublished_page...).
    monkeypatch.setattr(agent_04, "fetch_methodology_links", lambda: [
        {"title": "How We Test", "url": "https://moneyabroadguide.com/how-we-test/"},
    ])
    md = agent_04._build_methodology_links_md()
    assert "[How We Test](https://moneyabroadguide.com/how-we-test/)" in md


def test_returns_empty_string_when_no_pages_confirmed_live(monkeypatch):
    # REST API down / both pages unpublished -- never invents a URL, never
    # falls back to a hardcoded link.
    monkeypatch.setattr(agent_04, "fetch_methodology_links", lambda: [])
    assert agent_04._build_methodology_links_md() == ""


def test_empty_methodology_block_is_skipped_in_the_final_assembly():
    # mirrors the real join in write_article(): "\n\n".join([s for s in [...] if s])
    body, bio, methodology, updated = "Article body.", "## About the Author\n\nBio.", "", "> **Last Updated**: July 2026"
    assembled = "\n\n".join([s for s in [body, bio, methodology, updated] if s])
    assert "\n\n\n" not in assembled  # no stray blank block from the empty string
    assert assembled == f"{body}\n\n{bio}\n\n{updated}"


def test_non_empty_methodology_block_is_included_in_the_final_assembly():
    body, bio = "Article body.", "## About the Author\n\nBio."
    methodology = "*Learn more about our [How We Test](https://moneyabroadguide.com/how-we-test/).*"
    updated = "> **Last Updated**: July 2026"
    assembled = "\n\n".join([s for s in [body, bio, methodology, updated] if s])
    assert methodology in assembled
    # order preserved: bio, then methodology, then the update line
    assert assembled.index(bio) < assembled.index(methodology) < assembled.index(updated)


# ---------------------------------------------------------------- source guards

def test_no_hardcoded_methodology_page_url_in_source():
    # POINT 4 (2026-07-05) extended: a hardcoded deep link to a specific site
    # page is exactly the failure mode that made the old INTERNAL_LINKS dict
    # go 86% dead -- the methodology links must come ONLY from the live
    # fetch, never a literal URL string in source (mirrors tests/test_fix_
    # l189_internal_url.py's existing guard for article-to-article links).
    hardcoded = __import__("re").findall(
        r"\[[^\]]+\]\(https?://moneyabroadguide\.com/[^\)]+\)", SRC)
    assert hardcoded == [], f"a hardcoded methodology/internal link reappeared in source: {hardcoded}"


def test_build_methodology_links_calls_the_live_fetch_function():
    assert "fetch_methodology_links()" in SRC
    assert "from agents._real_internal_links import" in SRC
    assert "fetch_methodology_links" in SRC
