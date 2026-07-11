"""Hostinger hCDN challenge-403 retry on agent_17's WordPress fetch (2026-07-11,
PR express). agent_17 uses `requests` + `raise_for_status()`, a different HTTP
client than agents/_real_internal_links.py's urllib -- exercising the SAME
shared agents/_wp_challenge.py logic through a second, distinct client proves
the abstraction actually generalizes, not just "happens to work for one lib".

Offline: requests.get is monkeypatched, no real network, no real sleeps.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents import agent_17_cannibalization as a17


@pytest.fixture(autouse=True)
def _no_real_sleeps_and_wp_url(monkeypatch):
    monkeypatch.setattr(a17.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(a17, "WP_URL", "https://moneyabroadguide.com")


class _FakeResponse:
    def __init__(self, status_code, text="", json_data=None, headers=None):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data if json_data is not None else []
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.exceptions.HTTPError(f"{self.status_code} Client Error: Forbidden for url: x")

    def json(self):
        return self._json_data


_CHALLENGE_BODY = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
    '<meta name="robots" content="noindex,nofollow">'
    '<meta http-equiv="refresh" content="30">'
    '<link rel="preconnect" href="https://fonts.googleapis.com"></head></html>'
)
_HARD_403_BODY = '{"code":"rest_forbidden","message":"Sorry, you are not allowed to do that."}'


def test_challenge_403_retries_and_succeeds(monkeypatch):
    calls = []

    def fake_get(url, auth=None, params=None, timeout=None):
        calls.append(params.get("page"))
        if len(calls) < 3:
            return _FakeResponse(403, text=_CHALLENGE_BODY)
        return _FakeResponse(200, json_data=[{"id": 1, "title": {"rendered": "Post 1"}}],
                              headers={"X-WP-TotalPages": "1"})
    monkeypatch.setattr(a17.requests, "get", fake_get)

    sleeps = []
    monkeypatch.setattr(a17.time, "sleep", lambda s: sleeps.append(s))

    articles = a17.fetch_wordpress_articles(status="publish")
    assert len(articles) == 1
    assert len(calls) == 3
    assert sleeps == [a17.INTER_CALL_SPACING_SECONDS, 35, 70]


def test_challenge_403_exhausts_retries_then_fails_cleanly(monkeypatch, caplog):
    calls = []

    def fake_get(url, auth=None, params=None, timeout=None):
        calls.append(1)
        return _FakeResponse(403, text=_CHALLENGE_BODY)
    monkeypatch.setattr(a17.requests, "get", fake_get)

    sleeps = []
    monkeypatch.setattr(a17.time, "sleep", lambda s: sleeps.append(s))

    with caplog.at_level("WARNING"):
        articles = a17.fetch_wordpress_articles(status="publish")
    assert articles == []
    assert len(calls) == 4  # 1 initial + 3 retries
    assert sleeps == [a17.INTER_CALL_SPACING_SECONDS, 35, 70, 140]
    assert "challenge" in caplog.text.lower()


def test_hard_403_is_never_retried(monkeypatch):
    calls = []

    def fake_get(url, auth=None, params=None, timeout=None):
        calls.append(1)
        return _FakeResponse(403, text=_HARD_403_BODY)
    monkeypatch.setattr(a17.requests, "get", fake_get)

    sleeps = []
    monkeypatch.setattr(a17.time, "sleep", lambda s: sleeps.append(s))

    articles = a17.fetch_wordpress_articles(status="publish")
    assert articles == []
    assert len(calls) == 1  # no retry for a hard/genuine 403
    assert sleeps == [a17.INTER_CALL_SPACING_SECONDS]


def test_pacing_delay_applied_on_success_too(monkeypatch):
    def fake_get(url, auth=None, params=None, timeout=None):
        return _FakeResponse(200, json_data=[], headers={"X-WP-TotalPages": "1"})
    monkeypatch.setattr(a17.requests, "get", fake_get)

    sleeps = []
    monkeypatch.setattr(a17.time, "sleep", lambda s: sleeps.append(s))

    a17.fetch_wordpress_articles(status="publish")
    assert sleeps == [a17.INTER_CALL_SPACING_SECONDS]
