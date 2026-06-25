#!/usr/bin/env python3
"""
NEXUS-14 V4 - Agent 22: Performance Engine  (M7 — SECONDARY / interface)

STATUS: Interface + report contract implemented. The Lighthouse/CWV MEASUREMENT
is a documented runtime integration point (Option A scope): it requires invoking
a headless Lighthouse run against a live URL, which cannot be validated in this
environment. The agent therefore EITHER:
  (a) parses a Lighthouse JSON result supplied via --lighthouse-json, OR
  (b) when no result is supplied, emits status="PENDING" and passed=False so the
      Quality Gate BLOCKS rather than silently passing.

This keeps the gate's contract honest: performance cannot be marked PASS without
a real measurement. There is NO fake "everything is 100" behaviour.

REPORT CONTRACT (consumed by scripts/quality_gate_v4.py::_consult_report)
  output/agent_22/performance_report.json
  { "passed": bool, "status": "PASS|FAIL|PENDING", "metrics": {...},
    "thresholds": {...} }

THRESHOLDS (publication-blocking)
  SEO >= 95 ; Performance >= 90 ; Accessibility >= 95 ; Best Practices >= 95 ;
  CLS <= 0.10

RUNTIME INTEGRATION POINT (implement in CI, see run_lighthouse()):
  npx lighthouse <url> --output=json --output-path=<tmp> --only-categories=...
  then pass --lighthouse-json <tmp> to this agent.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent_22")

THRESHOLDS = {
    "seo": 95,
    "performance": 90,
    "accessibility": 95,
    "best_practices": 95,
    "cls_max": 0.10,
}


def parse_lighthouse(lh: Dict) -> Dict:
    """Extract the metrics we gate on from a Lighthouse JSON result object."""
    cats = lh.get("categories", {})
    audits = lh.get("audits", {})

    def cat_score(key):
        c = cats.get(key)
        return round((c.get("score") or 0) * 100) if c else None

    cls = None
    if "cumulative-layout-shift" in audits:
        cls = audits["cumulative-layout-shift"].get("numericValue")

    return {
        "seo": cat_score("seo"),
        "performance": cat_score("performance"),
        "accessibility": cat_score("accessibility"),
        "best_practices": cat_score("best-practices"),
        "lcp_ms": audits.get("largest-contentful-paint", {}).get("numericValue"),
        "inp_ms": audits.get("interaction-to-next-paint", {}).get("numericValue"),
        "tbt_ms": audits.get("total-blocking-time", {}).get("numericValue"),
        "speed_index_ms": audits.get("speed-index", {}).get("numericValue"),
        "cls": cls,
    }


def evaluate(metrics: Dict) -> bool:
    def ok(name, val):
        if val is None:
            return False
        return val >= THRESHOLDS[name]
    passed = (
        ok("seo", metrics.get("seo"))
        and ok("performance", metrics.get("performance"))
        and ok("accessibility", metrics.get("accessibility"))
        and ok("best_practices", metrics.get("best_practices"))
        and (metrics.get("cls") is not None and metrics["cls"] <= THRESHOLDS["cls_max"])
    )
    return passed


def run_lighthouse(url: str) -> Optional[Dict]:
    """RUNTIME INTEGRATION POINT.

    Intentionally not auto-invoking a subprocess here: CI should run Lighthouse and
    pass the JSON via --lighthouse-json. Returning None signals "no measurement".
    """
    logger.info("run_lighthouse() is a CI integration point; supply --lighthouse-json. url=%s", url)
    return None


def run_performance_check(lighthouse_json: Optional[str],
                          url: Optional[str],
                          output_path: str = "output/agent_22/performance_report.json") -> Dict:
    lh = None
    if lighthouse_json and Path(lighthouse_json).exists():
        lh = json.loads(Path(lighthouse_json).read_text(encoding="utf-8"))
    elif url:
        lh = run_lighthouse(url)

    if lh is None:
        report = {
            "agent": "agent_22_performance",
            "version": "4.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "PENDING",
            "passed": False,
            "detail": "No Lighthouse measurement supplied; gate must not pass on PENDING.",
            "thresholds": THRESHOLDS,
        }
    else:
        metrics = parse_lighthouse(lh)
        passed = evaluate(metrics)
        report = {
            "agent": "agent_22_performance",
            "version": "4.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "PASS" if passed else "FAIL",
            "passed": passed,
            "metrics": metrics,
            "thresholds": THRESHOLDS,
        }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Agent 22 status=%s passed=%s -> %s", report["status"], report["passed"], out)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent 22 - Performance Engine (V4)")
    parser.add_argument("--url", help="URL to measure (CI runs Lighthouse)")
    parser.add_argument("--lighthouse-json", help="path to a Lighthouse JSON result")
    parser.add_argument("--output", default="output/agent_22/performance_report.json")
    args = parser.parse_args()
    report = run_performance_check(args.lighthouse_json, args.url, args.output)
    sys.exit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
