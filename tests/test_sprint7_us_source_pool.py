"""Sprint 7 — US official-source pool + category routing. Offline, no API key.

Guarantees the fix for "US topics have no curated sources -> Agent 04 self-fails
the >=3/>=4 official-sources gate -> crons die":
- every US vertical has 7 verified official URLs (one above the PILLAR floor of 6);
- routing is deterministic on registry market + category (not keyword guessing);
- every US category present in the registry maps to a vertical;
- us_default is the safety net for unmapped US categories;
- ssa.gov / hhs.gov are excluded (they 403 the live-source gate);
- Canada behaviour is unchanged (resolve_vertical returns None -> legacy key).

The optional live-check (URLs really return 200) is gated behind
RUN_LIVE_SOURCE_CHECK=1 so normal CI stays offline.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

from agents._source_pool import (
    OFFICIAL_SOURCE_POOL,
    CATEGORY_TO_VERTICAL,
    resolve_vertical,
    has_curated_pool,
    select_official_sources,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = REPO_ROOT / "data" / "topic_registry.json"

US_VERTICALS = [
    "us_default", "us_banking", "us_credit", "us_transfers",
    "us_auto", "us_health", "us_housing", "us_mortgage", "us_students",
]
URLS_PER_VERTICAL = 7
PILLAR_MIN_SOURCES = 6  # hardest tier floor in agent_04
EXCLUDED_HOSTS = ("ssa.gov", "hhs.gov")


def _entries(vertical):
    return OFFICIAL_SOURCE_POOL[vertical]


def _url(entry):
    # entry format: "Authority name | https://url"
    assert " | " in entry, f"bad entry format: {entry!r}"
    return entry.split(" | ", 1)[1].strip()


def _host(url):
    return (urlparse(url).hostname or "").lower()


def _official(host):
    return host.endswith(".gov") or host.endswith(".canada.ca") or host == "canada.ca"


# ---------- pool shape ----------

def test_all_us_verticals_present_with_seven_urls():
    for v in US_VERTICALS:
        assert v in OFFICIAL_SOURCE_POOL, f"missing vertical {v}"
        assert len(_entries(v)) == URLS_PER_VERTICAL, f"{v} must have {URLS_PER_VERTICAL} urls"
        assert len(_entries(v)) > PILLAR_MIN_SOURCES, f"{v} must exceed the PILLAR floor"


def test_canada_newcomer_preserved():
    assert "canada_newcomer" in OFFICIAL_SOURCE_POOL
    assert len(_entries("canada_newcomer")) == 7


def test_every_entry_is_https_and_official_allowlist():
    for v, entries in OFFICIAL_SOURCE_POOL.items():
        for e in entries:
            url = _url(e)
            assert url.startswith("https://"), f"{v}: {url} not https"
            assert _official(_host(url)), f"{v}: {url} not on .gov/.canada.ca allow-list"


def test_no_duplicate_urls_within_a_vertical():
    for v, entries in OFFICIAL_SOURCE_POOL.items():
        urls = [_url(e) for e in entries]
        assert len(urls) == len(set(urls)), f"{v} has duplicate urls"


# ---------- reliability exclusion ----------

def test_ssa_and_hhs_are_excluded_everywhere():
    for v, entries in OFFICIAL_SOURCE_POOL.items():
        for e in entries:
            host = _host(_url(e))
            for bad in EXCLUDED_HOSTS:
                assert not host.endswith(bad), f"{v} contains excluded host {host} (403s the live-source gate)"


# ---------- category routing ----------

def test_every_us_registry_category_is_mapped():
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    us_cats = {t.get("category", "").strip().lower()
               for t in reg["topics"] if t.get("id", "").startswith("us-")}
    unmapped = {c for c in us_cats if c and c not in CATEGORY_TO_VERTICAL}
    assert not unmapped, f"US registry categories with no vertical mapping: {unmapped}"


def test_category_map_targets_exist_in_pool():
    for cat, vertical in CATEGORY_TO_VERTICAL.items():
        assert vertical in OFFICIAL_SOURCE_POOL, f"{cat} -> {vertical} missing from pool"


def test_resolve_vertical_us_known_and_unknown():
    assert resolve_vertical("USA", "assurance auto") == "us_auto"
    assert resolve_vertical("USA", "transferts") == "us_transfers"
    assert resolve_vertical("USA", "banques") == "us_banking"
    # unmapped / empty US category -> safety net
    assert resolve_vertical("USA", "totally-unknown") == "us_default"
    assert resolve_vertical("USA", "") == "us_default"


def test_resolve_vertical_non_us_falls_back_to_legacy():
    assert resolve_vertical("Canada", "banques") is None
    assert resolve_vertical("Canada", "") is None
    assert resolve_vertical("", "banques") is None


# ---------- selection semantics ----------

def test_has_curated_pool_for_all_verticals():
    for v in US_VERTICALS + ["canada_newcomer"]:
        assert has_curated_pool(v)
    assert not has_curated_pool("does_not_exist")


def test_select_returns_enough_for_pillar():
    # agent_04 asks for min_sources + 3; PILLAR -> 6 + 3 = 9, pool holds 7.
    for v in US_VERTICALS:
        got = select_official_sources(v, PILLAR_MIN_SOURCES + 3)
        assert len(got) == URLS_PER_VERTICAL
        assert len(got) >= PILLAR_MIN_SOURCES, f"{v} cannot satisfy the PILLAR floor"
    assert select_official_sources("us_auto", 0) == []
    assert select_official_sources("no_pool", 5) == []


# ---------- live-source gate must present a browser UA ----------

def test_fact_checker_uses_browser_user_agent():
    """agent_05 must send a browser User-Agent (and fall back to GET on 403), else
    the pool's state DOI/DMV/FTC URLs -- which 403 non-browser UAs -- would be
    counted broken and re-block US topics. Source-text check: keeps this test
    offline and free of the aiohttp import."""
    src = (REPO_ROOT / "agents" / "agent_05_fact_checker.py").read_text(encoding="utf-8")
    assert "_BROWSER_UA" in src
    assert 'headers={"User-Agent": _BROWSER_UA}' in src, "session must send the browser UA"
    assert "Mozilla/5.0" in src
    assert "status in (403, 405, 501)" in src, "HEAD must fall back to GET on 403"


# ---------- optional live-check (opt-in) ----------

@pytest.mark.skipif(os.environ.get("RUN_LIVE_SOURCE_CHECK") != "1",
                    reason="set RUN_LIVE_SOURCE_CHECK=1 to hit the network")
def test_all_pool_urls_live_200():
    import urllib.request
    import urllib.error
    # Match the browser UA the live-source gate (agent_05) now sends: several
    # official sites (state DOI/DMV, FTC) 403 non-browser User-Agents.
    ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    http_broken = []   # definite HTTP 4xx/5xx -> hard fail (mirrors agent_05 reason="http")
    transport = []     # timeout / connection error -> soft (agent_05 reason="transport")
    for v, entries in OFFICIAL_SOURCE_POOL.items():
        for e in entries:
            url = _url(e)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": ua})
                with urllib.request.urlopen(req, timeout=25) as resp:
                    if resp.status != 200:
                        http_broken.append((v, url, resp.status))
            except urllib.error.HTTPError as ex:
                http_broken.append((v, url, ex.code))
            except Exception as ex:  # noqa: BLE001 -- transport (timeout/URLError): soft
                transport.append((v, url, str(ex)[:60]))
    if transport:
        print(f"[soft] {len(transport)} transport errors (non-blocking, e.g. local rate-limit): {transport}")
    assert not http_broken, f"HTTP-broken pool urls (hard fail): {http_broken}"
