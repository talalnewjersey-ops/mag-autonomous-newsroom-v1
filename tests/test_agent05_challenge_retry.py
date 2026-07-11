"""Hostinger hCDN challenge-403 retry in agent_05's fact-checker URL-check loop
(2026-07-11, PR express) -- GATE A. Real finding: run 8's fact_check_report.json
showed the fact-checker's own URL-liveness check hitting a 403 on
`https://moneyabroadguide.com` itself (our OWN site, checked like any other
citation URL). This is the FOURTH distinct HTTP client (after urllib, requests,
and services/wordpress_service.py's aiohttp) integrated with the same shared
agents/_wp_challenge.py logic -- and the one with a real DOMAIN-SCOPING
requirement: an external .gov source's own unrelated 403 (bot-blocking
datacenter IPs, a known and already-handled case -- see
tests/test_sprint2_quality.py's bot_blocked tests) must NEVER get the 35-140s
wait-and-retry treatment; only OUR OWN domain does.

Offline: aiohttp.ClientSession.head/get are stubbed via a fake session, no real
network, no real sleeps.
"""
import asyncio
import importlib.util
import os
import sys
import types

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if "aiohttp" not in sys.modules:
    _aio = types.ModuleType("aiohttp")
    class _ClientTimeout:
        def __init__(self, *a, **k):
            pass
    class _ClientSession:
        pass
    class _ClientError(Exception):
        pass
    _aio.ClientTimeout = _ClientTimeout
    _aio.ClientSession = _ClientSession
    _aio.ClientError = _ClientError
    sys.modules["aiohttp"] = _aio


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


agent_05 = _load("agents/agent_05_fact_checker.py", "agent_05_challenge_retry_test")


@pytest.fixture(autouse=True)
def _no_real_sleeps(monkeypatch):
    async def _instant(seconds):
        return None
    monkeypatch.setattr(agent_05.asyncio, "sleep", _instant)


_CHALLENGE_BODY = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
    '<meta name="robots" content="noindex,nofollow">'
    '<meta http-equiv="refresh" content="30">'
    '<link rel="preconnect" href="https://fonts.googleapis.com"></head></html>'
)
_HARD_403_BODY = '{"code":"rest_forbidden","message":"Sorry, you are not allowed to do that."}'


class _FakeResp:
    def __init__(self, status, url, body=""):
        self.status = status
        self.url = url
        self._body = body

    async def text(self):
        return self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _ScriptedSession:
    """head()/get() both pull from the SAME ordered response queue -- matches
    check_one's real call order (HEAD first, then a GET fallback on 403/405/501)."""
    def __init__(self, responses):
        self._it = iter(responses)

    def head(self, url, **kwargs):
        return next(self._it)

    def get(self, url, **kwargs):
        return next(self._it)


def _fc(session):
    fc = agent_05.FactCheckerAgent.__new__(agent_05.FactCheckerAgent)
    fc.session = session
    return fc


# ---------------------------------------------------------------- own domain: retries

def test_own_domain_challenge_403_retries_and_succeeds(monkeypatch):
    url = "https://moneyabroadguide.com/"
    # HEAD -> 403 challenge, GET fallback -> 403 challenge (attempt 1); HEAD -> 200 (attempt 2, after backoff)
    responses = [
        _FakeResp(403, url),                              # HEAD, attempt 1
        _FakeResp(403, url, body=_CHALLENGE_BODY),         # GET fallback, attempt 1 -> challenge detected
        _FakeResp(200, url),                               # HEAD, attempt 2 (post 35s wait) -> success
    ]
    fc = _fc(_ScriptedSession(responses))

    sleeps = []
    async def _record(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr(agent_05.asyncio, "sleep", _record)

    out = asyncio.run(fc._check_urls([url]))
    assert out["live"] == [{"url": url, "status_code": 200, "trusted": True}]
    assert sleeps == [agent_05.INTER_CALL_SPACING_SECONDS, 35]


def test_own_domain_challenge_403_exhausts_retries_then_classifies_as_broken(monkeypatch, caplog):
    url = "https://moneyabroadguide.com/"
    # every attempt: HEAD 403 -> GET fallback 403, always the challenge body
    responses = []
    for _ in range(4):  # 1 initial + 3 retries
        responses.append(_FakeResp(403, url))
        responses.append(_FakeResp(403, url, body=_CHALLENGE_BODY))
    fc = _fc(_ScriptedSession(responses))

    sleeps = []
    async def _record(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr(agent_05.asyncio, "sleep", _record)

    with caplog.at_level("WARNING"):
        out = asyncio.run(fc._check_urls([url]))
    assert out["broken"][0]["url"] == url
    assert out["broken"][0]["reason"] == "http"  # our own domain isn't "official" -> hard http, not bot_blocked
    assert sleeps == [agent_05.INTER_CALL_SPACING_SECONDS, 35, 70, 140]
    assert "challenge" in caplog.text.lower()


# ---------------------------------------------------------------- own domain, hard 403: no retry

def test_own_domain_hard_403_is_never_retried(monkeypatch):
    url = "https://moneyabroadguide.com/"
    responses = [_FakeResp(403, url), _FakeResp(403, url, body=_HARD_403_BODY)]
    fc = _fc(_ScriptedSession(responses))

    sleeps = []
    async def _record(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr(agent_05.asyncio, "sleep", _record)

    out = asyncio.run(fc._check_urls([url]))
    assert out["broken"][0]["reason"] == "http"
    assert sleeps == [agent_05.INTER_CALL_SPACING_SECONDS]  # pacing only, no backoff retry


# ---------------------------------------------------------------- external domain: never gets the treatment

def test_external_domain_403_is_never_paced_or_retried_even_with_challenge_looking_body(monkeypatch):
    # an external (non-our-domain) URL must NEVER get the pacing/retry treatment,
    # even in the contrived case its body happened to look like the challenge --
    # domain-scoping is the guard, not signature-sniffing every 403 everywhere.
    url = "https://www.dfs.ny.gov/consumers/auto_insurance/minimum_auto_insurance_requirements"
    responses = [_FakeResp(403, url), _FakeResp(403, url)]  # HEAD 403 -> GET fallback 403 (body never read: not our domain)
    fc = _fc(_ScriptedSession(responses))

    sleeps = []
    async def _record(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr(agent_05.asyncio, "sleep", _record)

    out = asyncio.run(fc._check_urls([url]))
    assert out["broken"][0]["reason"] == "bot_blocked"  # official .gov domain -> existing classification, unchanged
    assert sleeps == []  # no pacing, no retry -- this path is completely untouched for external domains


def test_external_domain_403_response_without_text_method_still_works(monkeypatch):
    # regression guard: before the domain-scoping fix, this crashed (AttributeError:
    # no .text()) for any external-domain response stand-in lacking a .text() method,
    # because the code tried to read the body unconditionally on every 403.
    class _NoTextResp:
        def __init__(self, status, url):
            self.status = status
            self.url = url
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False

    class _NoTextSession:
        def head(self, url, **kwargs):
            return _NoTextResp(403, url)
        def get(self, url, **kwargs):
            return _NoTextResp(403, url)

    fc = _fc(_NoTextSession())
    out = asyncio.run(fc._check_urls(["https://somebank.com/nope"]))
    assert out["broken"][0]["reason"] == "http"
