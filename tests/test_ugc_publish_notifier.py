"""Offline tests for the UGC publish notifier.

Covers the contract that matters for the NEXUS-14 -> UGC handoff:
  1. Payload mapping: WordPress post -> nexus14_article_published body, with the
     exact fields the receiver validates (source_system, article_id,
     canonical_url, article_ref, published_at).
  2. Selection: only live (status=publish) posts with a URL, never already-
     announced ones, are picked.
  3. State file: notified ids round-trip and survive corrupt/missing files.
  4. Dispatch seam: builds the correct GitHub dispatch URL/headers/body and is
     idempotent across a second run.

All deterministic, no network, no secrets.
"""

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


notifier = _load("scripts/ugc_publish_notifier.py", "ugc_publish_notifier")


def _post(**overrides):
    base = {
        "id": 1842,
        "link": "https://moneyabroadguide.com/usa-banking-newcomers",
        "date_gmt": "2026-06-30T06:00:00",
        "status": "publish",
    }
    base.update(overrides)
    return base


# ----------------------------------------------------------------- payload

def test_build_payload_maps_all_contract_fields():
    payload = notifier.build_payload(_post())
    assert payload["event_type"] == "nexus14_article_published"
    cp = payload["client_payload"]
    assert cp["source_system"] == "nexus-14"
    assert cp["article_id"] == "wp-1842"
    assert cp["canonical_url"] == "https://moneyabroadguide.com/usa-banking-newcomers"
    assert cp["article_ref"] == "/wp-json/wp/v2/posts/1842"
    assert cp["published_at"] == "2026-06-30T06:00:00Z"  # naive UTC -> Z


def test_iso_utc_is_idempotent_on_z_suffixed_value():
    assert notifier.iso_utc("2026-06-30T06:00:00Z") == "2026-06-30T06:00:00Z"
    assert notifier.iso_utc("") == ""


# ----------------------------------------------------- recency floor (R1)

def test_published_after_cutoff_subtracts_window():
    now = datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc)
    assert notifier.published_after_cutoff(48, now) == "2026-06-28T12:00:00"
    assert notifier.published_after_cutoff(0, now) == "2026-06-30T12:00:00"


# --------------------------------------------------------------- selection

def test_select_skips_drafts_missing_urls_and_already_notified():
    posts = [
        _post(id=1, status="draft"),                       # not live
        _post(id=2, link=""),                              # no URL
        _post(id=3),                                       # OK
        _post(id=4),                                       # already notified
    ]
    todo = notifier.select_to_notify(posts, notified={"4"})
    assert [p["id"] for p in todo] == [3]


# ------------------------------------------------------------- state file

def test_notified_state_roundtrips(tmp_path):
    f = tmp_path / "state.json"
    notifier.save_notified(f, {"7", "3", "11"})
    assert notifier.load_notified(f) == {"7", "3", "11"}
    # sorted + json list on disk
    assert json.loads(f.read_text()) == sorted(["7", "3", "11"])


def test_load_notified_tolerates_missing_and_corrupt(tmp_path):
    assert notifier.load_notified(tmp_path / "nope.json") == set()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert notifier.load_notified(bad) == set()


# ----------------------------------------------------------- dispatch seam

class _FakeResponse:
    def __init__(self, status):
        self.status_code = status

    def raise_for_status(self):
        return None


class _RecordingSession:
    """Captures POSTs so we can assert URL/headers/body without a network."""

    def __init__(self, status=204):
        self._status = status
        self.posts = []

    def post(self, url, headers=None, data=None, timeout=None):
        self.posts.append((url, headers, data))
        return _FakeResponse(self._status)


def test_dispatch_builds_correct_github_request():
    session = _RecordingSession(status=204)
    payload = notifier.build_payload(_post())
    status = notifier.dispatch_to_ugc(session, "owner/ugc", "secret-token", payload)

    assert status == 204
    assert len(session.posts) == 1
    url, headers, body = session.posts[0]
    assert url == "https://api.github.com/repos/owner/ugc/dispatches"
    assert headers["Authorization"] == "Bearer secret-token"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert headers["Content-Type"] == "application/json"
    parsed = json.loads(body)
    assert parsed["event_type"] == "nexus14_article_published"
    assert parsed["client_payload"]["article_id"] == "wp-1842"


def test_second_run_is_idempotent_after_state_saved(tmp_path):
    # Simulate run 1 announcing post 1842, then run 2 seeing the same post.
    f = tmp_path / "state.json"
    notified = notifier.load_notified(f)
    todo = notifier.select_to_notify([_post(id=1842)], notified)
    assert [p["id"] for p in todo] == [1842]
    notified.add("1842")
    notifier.save_notified(f, notified)

    notified2 = notifier.load_notified(f)
    assert notifier.select_to_notify([_post(id=1842)], notified2) == []
