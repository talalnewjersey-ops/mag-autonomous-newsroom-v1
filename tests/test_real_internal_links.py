"""POINT 4 (2026-07-05): live WP-REST-verified internal links, replacing
agent_04's static INTERNAL_LINKS dict (which had drifted to 18/21 = 86% dead
links). Offline: urllib.request.urlopen is mocked, no real network.

Proves the 3 cases the user asked for explicitly:
  - existing/relevant real post -> IS linked
  - no relevant real post -> NOT linked (empty, never a forced/guessed link)
  - REST API unreachable ("sitemap down") -> article gets ZERO internal
    links, never a crash, never a fallback to a hardcoded list
"""
import json
import os
import sys
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents import _real_internal_links as ril


class _FakeHTTPResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body.encode("utf-8")
    def read(self):
        return self._body
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _posts_json(items):
    return json.dumps([
        {"slug": s, "link": f"https://moneyabroadguide.com/{s}/", "title": {"rendered": t}}
        for s, t in items
    ])


# ---------------- fetch_real_posts: success, failure, pagination ----------------

def test_fetch_real_posts_success(monkeypatch):
    page1 = _posts_json([("a", "Best Bank Accounts for Newcomers to Canada 2026")])

    def fake_urlopen(req, timeout=None):
        return _FakeHTTPResponse(200, page1)
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    posts = ril.fetch_real_posts(max_pages=1)
    assert posts == [{"title": "Best Bank Accounts for Newcomers to Canada 2026",
                       "url": "https://moneyabroadguide.com/a/"}]


def test_fetch_real_posts_network_error_returns_empty_not_raise(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("no route to host")
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    posts = ril.fetch_real_posts()
    assert posts == []


def test_fetch_real_posts_non_200_returns_empty_not_raise(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeHTTPResponse(503, "")
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    assert ril.fetch_real_posts() == []


def test_fetch_real_posts_malformed_json_returns_empty_not_raise(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeHTTPResponse(200, "not json{{{")
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    assert ril.fetch_real_posts() == []


def test_fetch_real_posts_paginates_until_a_short_page(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        if req.full_url.endswith("page=1"):    # NB: "per_page=100" itself contains "page=1" as
            items = [(f"post-{i}", f"Title {i}") for i in range(ril._PER_PAGE)]  # a substring --
            return _FakeHTTPResponse(200, _posts_json(items))                     # must match the end
        return _FakeHTTPResponse(200, _posts_json([("last", "Last Post")]))       # short page -> stop
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    posts = ril.fetch_real_posts()
    assert len(posts) == ril._PER_PAGE + 1
    assert len(calls) == 2   # stopped after the short page, did not fetch page 3


# ---------------- select_relevant_links: exists/linked, absent/not-linked ----------------

REAL_POSTS = [
    {"title": "Best Bank Accounts for Newcomers to Canada (2026 Guide)",
     "url": "https://moneyabroadguide.com/best-bank-accounts-newcomers-canada-2026/"},
    {"title": "How to Get an ITIN Number in the USA (2026)",
     "url": "https://moneyabroadguide.com/how-to-get-itin-number-usa-2026/"},
]


def test_relevant_real_post_is_linked():
    rel = ril.select_relevant_links("Best Newcomer Bank Accounts in Canada", REAL_POSTS, n=3)
    assert len(rel) == 1
    assert rel[0]["url"] == "https://moneyabroadguide.com/best-bank-accounts-newcomers-canada-2026/"


def test_no_relevant_real_post_is_not_linked():
    # A topic with no genuine overlap with anything on the (small) real-post list.
    rel = ril.select_relevant_links("Best Car Insurance for Foreign Drivers", REAL_POSTS, n=3)
    assert rel == []


def test_min_overlap_prevents_a_forced_tenuous_match():
    # Only 1 shared significant word ("usa") -- below the default min_overlap=2 ->
    # correctly NOT linked (no forced link just because n slots are available).
    rel = ril.select_relevant_links("Renting an Apartment in the USA", REAL_POSTS, n=3)
    assert rel == []


# ---------------- end-to-end: "sitemap/REST down" -> zero internal links ----------------

def test_rest_api_down_yields_zero_internal_links_end_to_end(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise TimeoutError("connection timed out")
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    real_posts = ril.fetch_real_posts()           # [] -- fail-soft
    rel = ril.select_relevant_links("Best Newcomer Bank Accounts in Canada", real_posts, n=3)
    assert real_posts == [] and rel == []          # article gets NO internal links, no crash
