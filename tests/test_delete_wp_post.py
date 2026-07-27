"""2026-07-11: delete_wp_post.py is DESTRUCTIVE (used to clean up orphaned
witness drafts, e.g. post 48640, that permanently block their own topic --
see agent_11_wordpress_integration.py's exact-normalized-title dedup guard).

These tests cover the pure, offline-testable parts: the fat-finger guard
(main() aborts before ever calling the API if confirm_post_id doesn't match)
and the trash-vs-force URL construction. The actual DELETE call itself
requires live WordPress credentials and is exercised only via the
delete-wp-post.yml workflow_dispatch, never in CI.

2026-07-27 addition (pre-production 404 audit): main() now calls get_post()
FIRST to read live status, and branches into a redirect-creation path for
published posts. All existing tests that reach main() must mock get_post
too now, or they'd attempt a real network call -- `test_main_proceeds_when_
confirm_id_matches` was updated for this (mocks a non-published status, so
its original "does the confirm gate let a good call through" intent is
unchanged, it just also asserts no redirect is attempted for a draft).
New tests below cover the redirect branch itself: explicit REDIRECT_TO,
category fallback, abort-with-no-target, and abort-on-redirect-failure --
all offline, no real network, no API key.

Offline, no network, no API key.
"""
import importlib.util
import os
import sys
import urllib.request
import unittest.mock as mock

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


delete_wp_post = _load("scripts/delete_wp_post.py", "delete_wp_post")


def test_main_aborts_before_any_api_call_when_confirm_id_does_not_match(monkeypatch):
    monkeypatch.setenv("WORDPRESS_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "pw")
    monkeypatch.setenv("POST_ID", "48640")
    monkeypatch.setenv("CONFIRM_POST_ID", "48641")  # typo / wrong id
    monkeypatch.delenv("FORCE", raising=False)

    with mock.patch.object(delete_wp_post, "delete_post") as mocked_delete:
        with pytest.raises(SystemExit) as excinfo:
            delete_wp_post.main()

    assert excinfo.value.code == 1
    mocked_delete.assert_not_called()


def test_main_proceeds_when_confirm_id_matches(monkeypatch):
    """A draft (never publicly reachable) -- confirm-gate passes, no
    redirect is attempted (nothing to redirect from), delete proceeds."""
    monkeypatch.setenv("WORDPRESS_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "pw")
    monkeypatch.setenv("POST_ID", "48640")
    monkeypatch.setenv("CONFIRM_POST_ID", "48640")
    monkeypatch.delenv("FORCE", raising=False)
    monkeypatch.delenv("REDIRECT_TO", raising=False)

    with mock.patch.object(delete_wp_post, "get_post", return_value={"status": "draft", "slug": "x", "categories": []}), \
         mock.patch.object(delete_wp_post, "create_redirect") as mocked_create_redirect, \
         mock.patch.object(delete_wp_post, "delete_post", return_value={"id": 48640, "status": "trash"}) as mocked_delete:
        delete_wp_post.main()

    mocked_create_redirect.assert_not_called()
    mocked_delete.assert_called_once()
    args, kwargs = mocked_delete.call_args
    assert args[3] == "48640"  # post_id positional
    assert kwargs.get("force") is False


def test_published_post_with_explicit_redirect_to_uses_it(monkeypatch):
    """The preferred path: a human supplies the exact target. No category
    lookup should even be attempted."""
    monkeypatch.setenv("WORDPRESS_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "pw")
    monkeypatch.setenv("POST_ID", "48787")
    monkeypatch.setenv("CONFIRM_POST_ID", "48787")
    monkeypatch.setenv("REDIRECT_TO", "https://example.com/best-itin-friendly-bank-accounts-usa/")
    monkeypatch.delenv("FORCE", raising=False)

    with mock.patch.object(delete_wp_post, "get_post",
                            return_value={"status": "publish", "slug": "best-banks-for-immigrants-without-ssn", "categories": [7]}), \
         mock.patch.object(delete_wp_post, "get_category_link") as mocked_cat_link, \
         mock.patch.object(delete_wp_post, "create_redirect", return_value={"id": 200}) as mocked_create_redirect, \
         mock.patch.object(delete_wp_post, "delete_post", return_value={"id": 48787, "status": "trash"}) as mocked_delete:
        delete_wp_post.main()

    mocked_cat_link.assert_not_called()
    mocked_create_redirect.assert_called_once_with(
        "https://example.com", "user", "pw",
        "/best-banks-for-immigrants-without-ssn/",
        "https://example.com/best-itin-friendly-bank-accounts-usa/",
    )
    mocked_delete.assert_called_once()


def test_published_post_without_redirect_to_falls_back_to_category(monkeypatch):
    monkeypatch.setenv("WORDPRESS_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "pw")
    monkeypatch.setenv("POST_ID", "48787")
    monkeypatch.setenv("CONFIRM_POST_ID", "48787")
    monkeypatch.delenv("REDIRECT_TO", raising=False)
    monkeypatch.delenv("FORCE", raising=False)

    with mock.patch.object(delete_wp_post, "get_post",
                            return_value={"status": "publish", "slug": "some-post", "categories": [7, 17]}), \
         mock.patch.object(delete_wp_post, "get_category_link", return_value="https://example.com/banking/") as mocked_cat_link, \
         mock.patch.object(delete_wp_post, "create_redirect", return_value={"id": 201}) as mocked_create_redirect, \
         mock.patch.object(delete_wp_post, "delete_post", return_value={"id": 48787, "status": "trash"}) as mocked_delete:
        delete_wp_post.main()

    mocked_cat_link.assert_called_once_with("https://example.com", "user", "pw", 7)  # first category, not 17
    mocked_create_redirect.assert_called_once_with(
        "https://example.com", "user", "pw", "/some-post/", "https://example.com/banking/",
    )
    mocked_delete.assert_called_once()


def test_published_post_with_no_category_and_no_redirect_to_aborts(monkeypatch):
    """Refuses to guess -- no target, no delete. Silently redirecting to
    the homepage would be worse than the dead URL this fix prevents."""
    monkeypatch.setenv("WORDPRESS_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "pw")
    monkeypatch.setenv("POST_ID", "48787")
    monkeypatch.setenv("CONFIRM_POST_ID", "48787")
    monkeypatch.delenv("REDIRECT_TO", raising=False)
    monkeypatch.delenv("FORCE", raising=False)

    with mock.patch.object(delete_wp_post, "get_post",
                            return_value={"status": "publish", "slug": "some-post", "categories": []}), \
         mock.patch.object(delete_wp_post, "create_redirect") as mocked_create_redirect, \
         mock.patch.object(delete_wp_post, "delete_post") as mocked_delete:
        with pytest.raises(SystemExit) as excinfo:
            delete_wp_post.main()

    assert excinfo.value.code == 1
    mocked_create_redirect.assert_not_called()
    mocked_delete.assert_not_called()


def test_published_post_aborts_delete_when_redirect_creation_fails(monkeypatch):
    """Never end up in the state this fix exists to prevent: post gone,
    no redirect, nobody told."""
    monkeypatch.setenv("WORDPRESS_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "pw")
    monkeypatch.setenv("POST_ID", "48787")
    monkeypatch.setenv("CONFIRM_POST_ID", "48787")
    monkeypatch.setenv("REDIRECT_TO", "https://example.com/target/")
    monkeypatch.delenv("FORCE", raising=False)

    fail = urllib.error.HTTPError("https://example.com", 500, "Server Error", {}, None)
    fail.read = lambda: b"internal error"

    with mock.patch.object(delete_wp_post, "get_post",
                            return_value={"status": "publish", "slug": "some-post", "categories": [7]}), \
         mock.patch.object(delete_wp_post, "create_redirect", side_effect=fail), \
         mock.patch.object(delete_wp_post, "delete_post") as mocked_delete:
        with pytest.raises(SystemExit) as excinfo:
            delete_wp_post.main()

    assert excinfo.value.code == 1
    mocked_delete.assert_not_called()


def test_delete_post_defaults_to_trash_not_force():
    captured = {}

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"id": 48640, "status": "trash"}'

    def _fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        return _FakeResp()

    with mock.patch.object(urllib.request, "urlopen", side_effect=_fake_urlopen):
        result = delete_wp_post.delete_post("https://example.com", "user", "pw", "48640", force=False)

    assert "force=true" not in captured["url"]
    assert result["status"] == "trash"


def test_delete_post_force_true_adds_force_param_to_url():
    captured = {}

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"id": 48640, "status": "deleted"}'

    def _fake_urlopen(req, timeout=30):
        captured["url"] = req.full_url
        return _FakeResp()

    with mock.patch.object(urllib.request, "urlopen", side_effect=_fake_urlopen):
        delete_wp_post.delete_post("https://example.com", "user", "pw", "48640", force=True)

    assert "force=true" in captured["url"]
