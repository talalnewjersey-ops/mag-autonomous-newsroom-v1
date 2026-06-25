"""
NEXUS-14 V4 - tests/test_v4_orchestrator_publish.py

Offline tests for the Option 2 publish boundary (orchestrator/publish_decision.py).

WordPress is FULLY MOCKED. No aiohttp, no network, no OpenAI, no real write is
ever performed. These tests prove the safety invariants of the generation ->
WordPress orchestrator preparation layer:

  * a BLOCKED gate never yields a PUBLISH plan and never contacts WordPress;
  * dry-run is the default: even a READY gate performs NO write unless the
    caller passes allow_live=True;
  * live mode creates a DRAFT only (status="draft") and never publishes live;
  * publish_post() / live transition is NEVER called automatically.

asyncio.run() drives the coroutines so no pytest-asyncio plugin is required.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from orchestrator.publish_decision import decide_publication, execute_plan


READY_GATE = {"decision": "READY_TO_PUBLISH", "failed_gates": []}
BLOCKED_GATE = {"decision": "BLOCKED", "failed_gates": ["performance", "competitor"]}
POST = {"title": "Sending Money Abroad", "content": "body", "slug": "send-money"}


def _fresh_wp_mock():
    """A WordPressService stand-in whose write methods are AsyncMocks."""
    wp = MagicMock()
    wp.create_post = AsyncMock(return_value={"id": 4321, "status": "draft"})
    wp.update_post = AsyncMock(return_value={"id": 4321, "status": "publish"})
    wp.publish_post = AsyncMock(return_value={"id": 4321, "status": "publish"})
    return wp


# ---------------------------------------------------------------------------
# decide_publication()
# ---------------------------------------------------------------------------

def test_decide_ready_gate_yields_publish_plan():
    plan = decide_publication(READY_GATE)
    assert plan["action"] == "PUBLISH"
    assert plan["dry_run"] is True  # default: allow_live not set
    assert plan["target_status"] == "draft"


def test_decide_ready_gate_live_flag_marks_not_dry_run():
    plan = decide_publication(READY_GATE, allow_live=True)
    assert plan["action"] == "PUBLISH"
    assert plan["dry_run"] is False
    assert plan["target_status"] == "draft"


def test_decide_blocked_gate_yields_hold():
    plan = decide_publication(BLOCKED_GATE)
    assert plan["action"] == "HOLD"
    assert plan["target_status"] is None
    assert "BLOCKED" in plan["reason"]


def test_decide_missing_decision_is_hold():
    plan = decide_publication({})
    assert plan["action"] == "HOLD"


# ---------------------------------------------------------------------------
# execute_plan() - the safety boundary
# ---------------------------------------------------------------------------

def test_blocked_plan_never_contacts_wordpress():
    wp = _fresh_wp_mock()
    plan = decide_publication(BLOCKED_GATE)
    result = asyncio.run(execute_plan(plan, wp, POST, allow_live=True))
    assert result["executed"] is False
    assert result["wordpress_contacted"] is False
    wp.create_post.assert_not_called()
    wp.update_post.assert_not_called()
    wp.publish_post.assert_not_called()


def test_ready_plan_dry_run_default_performs_no_write():
    wp = _fresh_wp_mock()
    plan = decide_publication(READY_GATE)  # allow_live not set -> dry-run
    result = asyncio.run(execute_plan(plan, wp, POST))  # allow_live default False
    assert result["executed"] is False
    assert result["dry_run"] is True
    assert result["wordpress_contacted"] is False
    assert result["would_create_post_with_status"] == "draft"
    wp.create_post.assert_not_called()
    wp.publish_post.assert_not_called()


def test_ready_plan_without_allow_live_is_dry_run_even_if_plan_says_publish():
    """Defence in depth: execute_plan re-checks allow_live independently of
    the plan, so a PUBLISH plan still does nothing without the live flag."""
    wp = _fresh_wp_mock()
    plan = decide_publication(READY_GATE, allow_live=True)  # plan dry_run False
    result = asyncio.run(execute_plan(plan, wp, POST, allow_live=False))
    assert result["executed"] is False
    assert result["wordpress_contacted"] is False
    wp.create_post.assert_not_called()


def test_ready_plan_live_creates_draft_only():
    wp = _fresh_wp_mock()
    plan = decide_publication(READY_GATE, allow_live=True)
    result = asyncio.run(execute_plan(plan, wp, POST, allow_live=True))
    assert result["executed"] is True
    assert result["wordpress_contacted"] is True
    assert result["created_post_id"] == 4321
    assert result["status"] == "draft"
    # exactly one create_post call, forced to draft status
    wp.create_post.assert_awaited_once()
    sent_payload = wp.create_post.await_args.args[0]
    assert sent_payload["status"] == "draft"
    assert sent_payload["title"] == POST["title"]
    # live publication is NEVER triggered automatically
    wp.publish_post.assert_not_called()
    wp.update_post.assert_not_called()


def test_live_create_forces_draft_even_if_post_data_requests_publish():
    """If a caller sneaks status=publish into post_data, the boundary overrides
    it back to draft."""
    wp = _fresh_wp_mock()
    sneaky = {**POST, "status": "publish"}
    plan = decide_publication(READY_GATE, allow_live=True)
    asyncio.run(execute_plan(plan, wp, sneaky, allow_live=True))
    sent_payload = wp.create_post.await_args.args[0]
    assert sent_payload["status"] == "draft"
