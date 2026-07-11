"""2026-07-11: delete_wp_post.py is DESTRUCTIVE (used to clean up orphaned
witness drafts, e.g. post 48640, that permanently block their own topic --
see agent_11_wordpress_integration.py's exact-normalized-title dedup guard).

These tests cover the pure, offline-testable parts: the fat-finger guard
(main() aborts before ever calling the API if confirm_post_id doesn't match)
and the trash-vs-force URL construction. The actual DELETE call itself
requires live WordPress credentials and is exercised only via the
delete-wp-post.yml workflow_dispatch, never in CI.

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
    monkeypatch.setenv("WORDPRESS_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "user")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "pw")
    monkeypatch.setenv("POST_ID", "48640")
    monkeypatch.setenv("CONFIRM_POST_ID", "48640")
    monkeypatch.delenv("FORCE", raising=False)

    with mock.patch.object(delete_wp_post, "delete_post", return_value={"id": 48640, "status": "trash"}) as mocked_delete:
        delete_wp_post.main()

    mocked_delete.assert_called_once()
    args, kwargs = mocked_delete.call_args
    assert args[3] == "48640"  # post_id positional
    assert kwargs.get("force") is False


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
