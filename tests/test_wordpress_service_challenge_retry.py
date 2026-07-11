"""Hostinger hCDN challenge-403 retry in services/wordpress_service.py (2026-07-11,
PR express) -- the central aiohttp-based WordPress WRITE client used by agent_11
(create_post, update_post, upload_image, update_media, set_post_author,
set_post_meta, get_categories, get_post, find_posts). A THIRD distinct HTTP
client (after urllib in agents/_real_internal_links.py and requests in
agent_17_cannibalization.py) exercising the same shared agents/_wp_challenge.py
logic -- proves the abstraction generalizes across sync AND async clients.

Offline: aiohttp.ClientSession is replaced with a fake async context manager
that returns pre-scripted (status, body) responses in order; asyncio.sleep is
replaced with an instant, call-recording stand-in so no test really waits.
"""
import asyncio
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Some other test files in this suite install a MINIMAL services.wordpress_service
# stub (`WordPressService=object`) directly into sys.modules at import time, for
# THEIR OWN offline import-safety needs (see tests/test_fix_empty_title.py etc.).
# sys.modules is process-wide, so `from services import wordpress_service` here
# could silently resolve to that stub instead of the real module, depending on
# collection order. Load the REAL file under a private module name instead --
# never touches the shared "services.wordpress_service" sys.modules key, so this
# file's needs and theirs can never collide either way (matches the pattern
# tests/test_agent04_http_error_body_logged.py already uses for the same reason).
_spec = importlib.util.spec_from_file_location(
    "wordpress_service_challenge_retry_test", os.path.join(ROOT, "services/wordpress_service.py"))
wps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wps)


class _FakeResponse:
    def __init__(self, status, text):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakeSession:
    def __init__(self, response):
        self._response = response

    def request(self, method, url, **kwargs):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _fake_client_session_factory(responses):
    """Each `aiohttp.ClientSession()` construction (one per retry attempt --
    matches the real code's per-attempt fresh session) hands out the next
    scripted response in order."""
    it = iter(responses)

    def _factory(*args, **kwargs):
        return _FakeSession(next(it))
    return _factory


@pytest.fixture(autouse=True)
def _no_real_sleeps(monkeypatch):
    async def _instant_sleep(seconds):
        return None
    monkeypatch.setattr(wps.asyncio, "sleep", _instant_sleep)


def _record_sleeps(monkeypatch):
    sleeps = []

    async def _record(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr(wps.asyncio, "sleep", _record)
    return sleeps


def _svc():
    return wps.WordPressService({
        "wordpress_url": "https://moneyabroadguide.com",
        "wordpress_username": "user",
        "wordpress_app_password": "pass",
    })


_CHALLENGE_BODY = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
    '<meta name="robots" content="noindex,nofollow">'
    '<meta http-equiv="refresh" content="30">'
    '<link rel="preconnect" href="https://fonts.googleapis.com"></head></html>'
)
_HARD_403_BODY = '{"code":"rest_forbidden","message":"Sorry, you are not allowed to do that."}'


# ---------------------------------------------------------------- create_post (write path)

def test_create_post_challenge_403_retries_and_succeeds(monkeypatch):
    responses = [
        _FakeResponse(403, _CHALLENGE_BODY),
        _FakeResponse(403, _CHALLENGE_BODY),
        _FakeResponse(201, '{"id": 123}'),
    ]
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    result = asyncio.run(_svc().create_post({"title": "T", "content": "C"}))
    assert result == {"id": 123}
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS, 35, 70]


def test_create_post_hard_403_raises_immediately_no_retry(monkeypatch):
    responses = [_FakeResponse(403, _HARD_403_BODY)]
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    with pytest.raises(Exception, match="WordPress post creation failed"):
        asyncio.run(_svc().create_post({"title": "T", "content": "C"}))
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS]  # pacing only, no backoff retry


def test_create_post_challenge_403_exhausts_retries_then_raises(monkeypatch):
    responses = [_FakeResponse(403, _CHALLENGE_BODY) for _ in range(4)]  # 1 initial + 3 retries
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    with pytest.raises(Exception, match="WordPress post creation failed"):
        asyncio.run(_svc().create_post({"title": "T", "content": "C"}))
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS, 35, 70, 140]


# ---------------------------------------------------------------- upload_image (write path, media)

def test_upload_image_challenge_403_retries_and_succeeds(monkeypatch, tmp_path):
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fake-jpeg-bytes")
    responses = [
        _FakeResponse(403, _CHALLENGE_BODY),
        _FakeResponse(201, '{"id": 55, "source_url": "https://moneyabroadguide.com/img.jpg"}'),
    ]
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    result = asyncio.run(_svc().upload_image(str(img)))
    assert result["id"] == 55
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS, 35]


def test_upload_image_hard_403_raises_immediately_no_retry(monkeypatch, tmp_path):
    img = tmp_path / "test.jpg"
    img.write_bytes(b"fake-jpeg-bytes")
    responses = [_FakeResponse(403, _HARD_403_BODY)]
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    with pytest.raises(Exception, match="Image upload failed"):
        asyncio.run(_svc().upload_image(str(img)))
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS]


# ---------------------------------------------------------------- read-path helpers (get_categories, get_post, find_posts)

def test_get_categories_challenge_403_retries_and_succeeds(monkeypatch):
    responses = [_FakeResponse(403, _CHALLENGE_BODY), _FakeResponse(200, '[{"id": 1, "name": "Banking"}]')]
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    result = asyncio.run(_svc().get_categories())
    assert result == [{"id": 1, "name": "Banking"}]
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS, 35]


def test_get_categories_hard_403_returns_empty_no_retry(monkeypatch):
    responses = [_FakeResponse(403, _HARD_403_BODY)]
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    assert asyncio.run(_svc().get_categories()) == []
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS]


def test_find_posts_challenge_403_retries_then_exhausted_returns_empty_via_except(monkeypatch, caplog):
    # find_posts wraps the whole call in its own try/except -- a fully exhausted
    # challenge-retry here still surfaces as an ordinary "non-200" -> [] path,
    # not an exception (get/find_posts never raise on a non-200 by design).
    responses = [_FakeResponse(403, _CHALLENGE_BODY) for _ in range(4)]
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    assert asyncio.run(_svc().find_posts("some search")) == []
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS, 35, 70, 140]


# ---------------------------------------------------------------- pacing applies even on a clean, first-try success

def test_pacing_delay_applied_even_on_clean_success(monkeypatch):
    responses = [_FakeResponse(200, '{"id": 1}')]
    monkeypatch.setattr(wps.aiohttp, "ClientSession", _fake_client_session_factory(responses))
    sleeps = _record_sleeps(monkeypatch)

    asyncio.run(_svc().get_post(1))
    assert sleeps == [wps.INTER_CALL_SPACING_SECONDS]
