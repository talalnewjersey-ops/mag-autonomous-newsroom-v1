#!/usr/bin/env python3
"""
NEXUS-14 PRODUCTION v4.0 -- Production Gate
scripts/production_gate.py

3-GATE MINIMUM for WordPress draft delivery:
  GATE A: Fact Check PASS (Agent 05 produced report with enough sources)
  GATE B: EEAT PASS (Agent 06 score >= threshold)
  GATE C: WordPress Draft Created (Post ID confirmed, HTTP 200)

All other checks (SEO score, image count, word count, affiliate) are
logged as WARNINGS only and do NOT block draft creation.
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PRODUCTION-GATE] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def load_json(path: str, name: str) -> dict:
    p = Path(path)
    if not p.exists():
        logger.warning(f"{name}: file not found at {path}")
        return {"_missing": True, "_path": path}
    try:
        with open(p) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"{name}: JSON parse error -- {e}")
        return {"_invalid": True, "_path": path, "_error": str(e)}


def run_gate(args) -> dict:
    start = datetime.utcnow()
    logger.info("=" * 60)
    logger.info("NEXUS-14 PRODUCTION GATE v4.0 -- 3-GATE MINIMUM")
    logger.info("=" * 60)

    failures = []
    warnings = []
    gates = {}

    # ── GATE A: Fact Check ────────────────────────────────────
    fact = load_json(args.fact_check, "Fact Check Report")
    if fact.get("_missing") or fact.get("_invalid"):
        gate_a = False
        failures.append("GATE A FAIL: fact_check_report.json missing or invalid")
    else:
        # Check verdict field first (PASS or PASS_WITH_WARNINGS = Gate A pass)
        verdict = fact.get("verdict", "")
        if verdict in ("PASS", "PASS_WITH_WARNINGS"):
            gate_a = True
        elif verdict == "FAIL":
            gate_a = False
        else:
            # Fallback: check overall_passed or passed fields
            passed = fact.get("overall_passed", fact.get("passed", None))
            if passed is None:
                # Last resort: infer from source count
                sources = fact.get("sources_verified", fact.get("sources_count", 0))
                passed = sources >= 3
            gate_a = bool(passed)
        if not gate_a:
            failures.append(
                f"GATE A FAIL: Fact checker did not pass -- "
                f"sources={fact.get('sources_verified', fact.get('sources_count', 0))}, "
                f"disputed={fact.get('disputed_claims', 0)}"
            )

    gates["gate_a_fact_check"] = {
        "gate": "A - Fact Check PASS",
        "passed": gate_a,
        "sources": fact.get("sources_verified", fact.get("sources_count", 0)),
    }

    # ── GATE B: EEAT ──────────────────────────────────────────
    # Agent 06 outputs to a directory; look for eeat_report.json inside
    eeat_dir = Path(args.eeat_dir)
    eeat_report_path = None
    for candidate in ["eeat_report.json", "eeat_validation_report.json", "report.json"]:
        p = eeat_dir / candidate
        if p.exists():
            eeat_report_path = str(p)
            break

    if eeat_report_path is None:
        gate_b = False
        eeat_score = 0
        failures.append(f"GATE B FAIL: EEAT report not found in {args.eeat_dir}")
    else:
        eeat = load_json(eeat_report_path, "EEAT Report")
        if eeat.get("_missing") or eeat.get("_invalid"):
            gate_b = False
            eeat_score = 0
            failures.append("GATE B FAIL: EEAT report missing or invalid")
        else:
            eeat_score = eeat.get("total_eeat_score", eeat.get("eeat_score", eeat.get("overall_score", eeat.get("score", 0))))
            threshold = getattr(args, "eeat_threshold", 85)
            passed = eeat.get("overall_passed", eeat.get("passed", None))
            if passed is None:
                passed = eeat_score >= threshold
            gate_b = bool(passed)
            if not gate_b:
                failures.append(
                    f"GATE B FAIL: EEAT score {eeat_score} below threshold {threshold}"
                )

    gates["gate_b_eeat"] = {
        "gate": "B - EEAT Validation PASS",
        "passed": gate_b,
        "eeat_score": eeat_score,
    }

    # ── GATE C: WordPress Draft ───────────────────────────────
    wp = load_json(args.wordpress_report, "WordPress Validation Report")
    if wp.get("_missing") or wp.get("_invalid"):
        gate_c = False
        post_id = None
        failures.append("GATE C FAIL: wordpress_validation_report.json missing or invalid")
    else:
        post_id = wp.get("post_id")
        draft_created = wp.get("draft_created", wp.get("success", bool(post_id)))
        gate_c = bool(draft_created and post_id)
        if not gate_c:
            failures.append(
                f"GATE C FAIL: WordPress draft not confirmed -- "
                f"post_id={post_id}, draft_created={draft_created}"
            )

    gates["gate_c_wordpress"] = {
        "gate": "C - WordPress Draft Created",
        "passed": gate_c,
        "post_id": post_id,
        "draft_url": wp.get("draft_url", wp.get("post_url")),
    }

    # ── WARNINGS (non-blocking informational checks) ──────────
    # Load optional reports for warnings
    if args.cannibalization:
        cann = load_json(args.cannibalization, "Cannibalization Report")
        if not cann.get("_missing"):
            decision = cann.get("decision", "UNKNOWN")
            if cann.get("blocking"):
                warnings.append(f"WARNING: Cannibalization flagged {decision} (not blocking in v4.0)")

    if args.revenue:
        rev = load_json(args.revenue, "Revenue Score")
        if not rev.get("_missing"):
            score = rev.get("revenue_score", 0)
            if score < 60:
                warnings.append(f"WARNING: Revenue score {score}/100 below 60 (not blocking in v4.0)")

    if args.image_report:
        img = load_json(args.image_report, "Image Report")
        if not img.get("_missing"):
            gen = img.get("images_generated", img.get("images_uploaded", 0))
            if gen < 4:
                warnings.append(f"WARNING: Only {gen}/4 images generated (not blocking)")

    # ── FINAL VERDICT ─────────────────────────────────────────
    overall_passed = len(failures) == 0
    status = "DRAFT_READY" if overall_passed else "DRAFT_BLOCKED"
    gates_passed = sum(1 for g in gates.values() if g.get("passed"))

    result = {
        "script": "production_gate.py",
        "version": "v4.0",
        "system": "NEXUS-14 PRODUCTION v4.0",
        "timestamp": start.isoformat(),
        "execution_seconds": round((datetime.utcnow() - start).total_seconds(), 2),
        "status": status,
        "overall_passed": overall_passed,
        "gates_passed": gates_passed,
        "gates_total": 3,
        "failures": failures,
        "warnings": warnings,
        "gates": gates,
        "post_id": post_id,
        "article_type": getattr(args, "article_type", "STANDARD"),
    }

    logger.info(f"Gates passed: {gates_passed}/3")
    if failures:
        for f in failures:
            logger.error(f"  {f}")
    if warnings:
        for w in warnings:
            logger.warning(f"  {w}")
    logger.info(f"STATUS: {status}")
    if post_id:
        logger.info(f"WordPress Post ID: {post_id}")
    logger.info("=" * 60)

    return result


def main():
    parser = argparse.ArgumentParser(description="NEXUS-14 Production Gate v4.0 -- 3-Gate Minimum")
    parser.add_argument("--fact-check", required=True,
                        help="Path to agent_05 fact_check_report.json")
    parser.add_argument("--eeat-dir", required=True,
                        help="Path to agent_06 output directory")
    parser.add_argument("--wordpress-report", required=True,
                        help="Path to agent_11 wordpress_validation_report.json")
    parser.add_argument("--cannibalization", default="",
                        help="Path to agent_17 cannibalization_report.json (optional, warning only)")
    parser.add_argument("--revenue", default="",
                        help="Path to agent_18 revenue_score.json (optional, warning only)")
    parser.add_argument("--image-report", default="",
                        help="Path to agent_10 image_validation_report.json (optional, warning only)")
    parser.add_argument("--article-type", default="STANDARD",
                        choices=["STANDARD", "PILLAR", "OPPORTUNITY"])
    parser.add_argument("--eeat-threshold", type=int, default=85)
    parser.add_argument("--output", required=True,
                        help="Output path for production_gate_result.json")

    args = parser.parse_args()

    result = run_gate(args)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Gate result saved: {args.output}")

    if not result["overall_passed"]:
        logger.error("PRODUCTION GATE FAILED -- WordPress draft will NOT be counted.")
        sys.exit(1)
    else:
        logger.info("PRODUCTION GATE PASSED -- WordPress draft delivered.")
        sys.exit(0)


if __name__ == "__main__":
    main()
