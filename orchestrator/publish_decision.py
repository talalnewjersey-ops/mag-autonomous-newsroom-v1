"""
NEXUS-14 V4 - orchestrator/publish_decision.py

Publication decision + execution boundary for the generation -> WordPress
orchestrator (Option 2, preparation layer).

DESIGN INVARIANTS (enforced by tests/test_v4_orchestrator_publish.py):
  1. The authoritative Quality Gate V4 result is the ONLY thing that can
     authorise a publish. action == "PUBLISH" is emitted ONLY when
     gate_result["decision"] == "READY_TO_PUBLISH".
  2. DRY-RUN IS THE DEFAULT. execute_plan() performs NO WordPress write
     unless allow_live=True is passed explicitly by the caller.
  3. NON-DESTRUCTIVE BY CONSTRUCTION. Even in live mode this module only
     calls WordPressService.create_post() with status="draft". It NEVER
     calls publish_post() / update_post(status="publish"): going live on a
     post stays a separate, manual, human-authorised step.
  4. NO network/OpenAI here. This module is pure decision + a single guarded
     await of an injected WordPress service (mocked in tests).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("NEXUS14.PublishDecision")

READY = "READY_TO_PUBLISH"


def decide_publication(gate_result: Dict, *, allow_live: bool = False) -> Dict:
    """Turn a quality_gate_v4 result into an explicit publication plan.

    Returns a plan dict; it never performs any side effect.
    """
    decision = (gate_result or {}).get("decision")
    failed = list((gate_result or {}).get("failed_gates", []))

    if decision == READY:
        return {
            "action": "PUBLISH",
            "dry_run": not allow_live,
            "target_status": "draft",  # never publish live automatically
            "reason": "quality_gate_v4 decision READY_TO_PUBLISH",
            "failed_gates": failed,
        }

    return {
        "action": "HOLD",
        "dry_run": True,
        "target_status": None,
        "reason": f"quality_gate_v4 decision={decision!r}; failed_gates={failed}",
        "failed_gates": failed,
    }


async def execute_plan(
    plan: Dict,
    wp_service: Any,
    post_data: Dict,
    *,
    allow_live: bool = False,
) -> Dict:
    """Execute (or simulate) a publication plan.

    SAFETY: a WordPress write happens ONLY when BOTH conditions hold:
      * plan["action"] == "PUBLISH", AND
      * allow_live is True.
    Otherwise this is a pure dry-run that touches nothing.

    When it does write, it creates a DRAFT only (status="draft"); it never
    transitions a post to "publish". Returns a result dict describing what
    was (or would be) done.
    """
    action = (plan or {}).get("action")

    if action != "PUBLISH":
        return {
            "executed": False,
            "dry_run": True,
            "wordpress_contacted": False,
            "reason": (plan or {}).get("reason", "no publishable plan"),
        }

    if not allow_live:
        return {
            "executed": False,
            "dry_run": True,
            "wordpress_contacted": False,
            "reason": "dry-run: allow_live is False, no WordPress write performed",
            "would_create_post_with_status": "draft",
        }

    # LIVE path (only reached with explicit allow_live=True). Force draft.
    draft_payload = {**post_data, "status": "draft"}
    result = await wp_service.create_post(draft_payload)
    post_id: Optional[int] = (result or {}).get("id")
    logger.info("execute_plan: created DRAFT post id=%s (live publish NOT performed)", post_id)
    return {
        "executed": True,
        "dry_run": False,
        "wordpress_contacted": True,
        "created_post_id": post_id,
        "status": "draft",
        "reason": "created WordPress DRAFT; live publish remains a manual step",
  }
