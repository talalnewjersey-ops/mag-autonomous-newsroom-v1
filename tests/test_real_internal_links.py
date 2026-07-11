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


# ---------------- ratio floor (2026-07-06): the 3 REAL control-run cases ----------------
# Fixtures below are the ACTUAL real post titles/URLs fetched live from the site
# during the control run (not invented) -- frozen here so the test is offline
# and doesn't depend on the live site's content staying identical over time.

_REAL_SUBSET_FOR_AUTO_INSURANCE = [
    {"title": "Best High-Interest Savings Accounts For International Students In Canada: Complete Guide for Canada &#8211; International Students Immigrants (2026)",
     "url": "https://moneyabroadguide.com/best-high-interest-savings-accounts-for-international-students-in-canada-complete-guide-for-canada-i/"},
    {"title": "Best Banks For Canadian Newcomers International Students: Complete Guide for Canada Immigrants (2026)",
     "url": "https://moneyabroadguide.com/best-banks-for-canadian-newcomers-international-students-complete-guide-for-canada-immigrants-2026/"},
    {"title": "How to Open a Bank Account in Canada as an International Student (2026 Guide)",
     "url": "https://moneyabroadguide.com/student-bank-account-canada-newcomers-2026/"},
    {"title": "Health Insurance for New Immigrants in the USA (2026 Complete Guide)",
     "url": "https://moneyabroadguide.com/health-insurance-new-immigrants-usa/"},
]

_REAL_SUBSET_FOR_BANK_ACCOUNTS = [
    {"title": "Best Bank Accounts for Newcomers to Canada (2026 Guide)",
     "url": "https://moneyabroadguide.com/best-bank-accounts-newcomers-canada-2026/"},
    {"title": "Best ITIN-Friendly Bank Accounts for New Immigrants in the USA (2026)",
     "url": "https://moneyabroadguide.com/best-itin-friendly-bank-accounts-usa/"},
    {"title": "How to Open a Bank Account as a Newcomer in the USA (2026 Guide)",
     "url": "https://moneyabroadguide.com/open-bank-account-newcomer-usa-2026/"},
    {"title": "Best High-Interest Savings Accounts for Newcomers to Canada (2026 Guide)",
     "url": "https://moneyabroadguide.com/high-interest-savings-newcomers-canada-2026/"},
    {"title": "RBC vs Scotiabank vs TD for Newcomers Canada 2026: Which Big Bank Wins?",
     "url": "https://moneyabroadguide.com/rbc-vs-scotiabank-vs-td-newcomers/"},
]

_REAL_SUBSET_FOR_PERSONAL_LOANS = [
    {"title": "How to Rent Without Credit History in Canada 2026: No Credit Check Options",
     "url": "https://moneyabroadguide.com/rent-without-credit-canada/"},
    {"title": "Best Credit Cards for Newcomers in Canada (2026 Complete Guide)",
     "url": "https://moneyabroadguide.com/best-credit-cards-newcomers-canada/"},
    {"title": "Building Credit in Canada for Newcomers: 2026 Complete Guide",
     "url": "https://moneyabroadguide.com/building-credit-canada-newcomers-2026/"},
]


def test_real_case_auto_insurance_zero_links_ratio_too_low():
    # Best real candidates only share "international"+"students" (overlap=2) out
    # of the query's 6 distinctive words (car/insurance/foreign/drivers/
    # international/students) -- ratio 0.33, below the 0.5 floor. NONE of the
    # query's actual topic (car/insurance/foreign/drivers) is represented.
    query = ("car insurance for foreign drivers and international students Best Car "
             "Insurance For Foreign Drivers And International Students: Complete Guide "
             "for USA Immigrants (2026)")
    rel = ril.select_relevant_links(query, _REAL_SUBSET_FOR_AUTO_INSURANCE, n=4)
    assert rel == []


def test_real_case_bank_accounts_three_links_ratio_067():
    query = ("best newcomer bank accounts in canada Best Newcomer Bank Accounts In "
             "Canada: Complete Guide for Canada Immigrants (2026)")
    rel = ril.select_relevant_links(query, _REAL_SUBSET_FOR_BANK_ACCOUNTS, n=4)
    urls = {p["url"] for p in rel}
    assert len(rel) == 3
    assert urls == {
        "https://moneyabroadguide.com/best-bank-accounts-newcomers-canada-2026/",
        "https://moneyabroadguide.com/best-itin-friendly-bank-accounts-usa/",
        "https://moneyabroadguide.com/open-bank-account-newcomer-usa-2026/",
    }


def test_real_case_personal_loans_one_link_at_inclusive_ratio_050():
    # Exactly at the boundary (overlap=2/4=0.50) -- inclusive: it PASSES.
    query = ("personal loans for immigrants no credit history Best Personal Loans For "
             "Immigrants No Credit History: Complete Guide for USA Immigrants (2026)")
    rel = ril.select_relevant_links(query, _REAL_SUBSET_FOR_PERSONAL_LOANS, n=4)
    assert len(rel) == 1
    assert rel[0]["url"] == "https://moneyabroadguide.com/rent-without-credit-canada/"


def test_ratio_boundary_is_inclusive_not_exclusive():
    # Sanity-check the boundary logic directly: overlap=2, query has 4 tokens ->
    # ratio EXACTLY 0.5 -> must pass (>=), not fail (>).
    assert ril.select_relevant_links(
        "alpha beta gamma delta",
        [{"title": "alpha beta", "url": "https://moneyabroadguide.com/x/"}],
        n=1,
    ) != []


# ---------------- end-to-end: "sitemap/REST down" -> zero internal links ----------------

def test_rest_api_down_yields_zero_internal_links_end_to_end(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise TimeoutError("connection timed out")
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    real_posts = ril.fetch_real_posts()           # [] -- fail-soft
    rel = ril.select_relevant_links("Best Newcomer Bank Accounts in Canada", real_posts, n=3)
    assert real_posts == [] and rel == []          # article gets NO internal links, no crash


# ---------------- fetch_methodology_links (2026-07-10, site-level EEAT signal) ----------------
# Same fail-soft, live-only, never-hardcode contract as fetch_real_posts above --
# a real, published site page (Fact-Checking Process, How We Test) is only
# ever linked if the WP REST API confirms it live RIGHT NOW.

def _pages_json(items):
    return json.dumps([
        {"slug": s, "link": f"https://moneyabroadguide.com/{s}/", "title": {"rendered": t}}
        for s, t in items
    ])


def test_fetch_methodology_links_success(monkeypatch):
    body = _pages_json([("fact-checking-process", "Fact-Checking Process"),
                         ("how-we-test", "How We Test")])

    def fake_urlopen(req, timeout=None):
        assert "wp-json/wp/v2/pages" in req.full_url
        assert "fact-checking-process" in req.full_url and "how-we-test" in req.full_url
        return _FakeHTTPResponse(200, body)
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    links = ril.fetch_methodology_links()
    assert links == [
        {"title": "Fact-Checking Process", "url": "https://moneyabroadguide.com/fact-checking-process/"},
        {"title": "How We Test", "url": "https://moneyabroadguide.com/how-we-test/"},
    ]


def test_fetch_methodology_links_network_error_returns_empty_not_raise(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("no route to host")
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    assert ril.fetch_methodology_links() == []


def test_fetch_methodology_links_non_200_returns_empty_not_raise(monkeypatch):
    def fake_urlopen(req, timeout=None):
        return _FakeHTTPResponse(503, "")
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    assert ril.fetch_methodology_links() == []


def test_fetch_methodology_links_a_renamed_or_unpublished_page_is_simply_absent(monkeypatch):
    # e.g. "how-we-test" gets renamed/unpublished -- the API returns only the
    # slug that's still live. Never invented, never a stale guess.
    body = _pages_json([("fact-checking-process", "Fact-Checking Process")])

    def fake_urlopen(req, timeout=None):
        return _FakeHTTPResponse(200, body)
    monkeypatch.setattr(ril.urllib.request, "urlopen", fake_urlopen)

    links = ril.fetch_methodology_links()
    assert len(links) == 1
    assert links[0]["url"] == "https://moneyabroadguide.com/fact-checking-process/"
