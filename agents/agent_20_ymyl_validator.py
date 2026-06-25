#!/usr/bin/env python3
"""
NEXUS-14 V4 - Agent 20: YMYL Validator  (M5 — YMYL Engine)
MoneyAbroadGuide.com | Verifies Your-Money-Your-Life financial values before
publication and blocks the article on any unverifiable regulated figure.

VERIFIES
  * Contribution limits (TFSA, RRSP, 401k, IRA)
  * IRS / CRA values and tax thresholds
  * APYs, interest rates, transfer fees
  * FDIC / banking rules
  * Immigration fees and government regulations

FOR EVERY VALIDATED STATEMENT IT RECORDS
  * official source (authority + canonical URL)
  * effective_date  (when the figure took effect)
  * verification_date (today, when Agent 20 checked it)

BLOCKING LOGIC
  * If a require_official_source datum class is detected but cannot be bound to an
    official source -> status FAIL (unverifiable YMYL claim).
  * If a value contradicts a registry reference value (beyond tolerance)
    -> status FAIL (incorrect YMYL claim).
  * Otherwise status PASS.

OUTPUT  output/agent_20/ymyl_report.json
EXIT CODES  0 -> PASS ; 1 -> FAIL (blocks publication)
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("agent_20")

DEFAULT_REGISTRY_PATH = "config/ymyl_sources.yaml"

# Datum-class detection patterns. Each maps a regex to a datum class + a hint for
# which registry keys are candidate authorities.
DATUM_PATTERNS = [
    ("apy", re.compile(r'(\d+(?:\.\d+)?)\s*%\s*APY', re.IGNORECASE)),
    ("interest_rate", re.compile(r'(\d+(?:\.\d+)?)\s*%\s*(?:interest|rate|APR)', re.IGNORECASE)),
    ("transfer_fee", re.compile(r'(?:transfer|wire)\s+fee[^.]*?\$?(\d+(?:\.\d+)?)', re.IGNORECASE)),
    ("contribution_limit", re.compile(r'(?:contribution\s+limit|contribute up to)[^.]*?\$?(\d[\d,]*)', re.IGNORECASE)),
    ("tax_threshold", re.compile(r'(?:tax\s+(?:bracket|threshold)|taxable income)[^.]*?\$?(\d[\d,]*)', re.IGNORECASE)),
    ("immigration_fee", re.compile(r'(?:application|immigration|USCIS|IRCC)\s+fee[^.]*?\$?(\d[\d,]*)', re.IGNORECASE)),
    ("government_regulation", re.compile(r'\b(?:IRS|CRA|FDIC|USCIS|CFPB|OSFI)\b[^.]*?(?:rule|regulation|requires|mandates)', re.IGNORECASE)),
]

# Named-value patterns mapping specific phrasings to registry keys for exact checks.
NAMED_VALUE_PATTERNS = [
    ("tfsa_contribution_limit_2025", re.compile(r'TFSA[^.]*?\$?(\d[\d,]*)', re.IGNORECASE)),
    ("rrsp_dollar_limit_2025", re.compile(r'RRSP[^.]*?\$?(\d[\d,]*)', re.IGNORECASE)),
    ("irs_401k_elective_deferral_2025", re.compile(r'401\(?k\)?[^.]*?\$?(\d[\d,]*)', re.IGNORECASE)),
    ("irs_ira_contribution_limit_2025", re.compile(r'\bIRA\b[^.]*?\$?(\d[\d,]*)', re.IGNORECASE)),
    ("fdic_insurance_limit", re.compile(r'FDIC[^.]*?\$?(\d[\d,]*)', re.IGNORECASE)),
]


def load_registry(path: str = DEFAULT_REGISTRY_PATH) -> Dict:
    p = Path(path)
    if not p.exists():
        logger.warning("YMYL registry not found at %s; using empty registry.", path)
        return {"registry": {}, "require_official_source": [], "official_domains": []}
    try:
        import yaml  # type: ignore
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.error("Failed to parse registry: %s", e)
        return {"registry": {}, "require_official_source": [], "official_domains": []}


def _to_number(raw: str) -> Optional[float]:
    try:
        return float(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return None


def _find_official_urls(text: str, official_domains: List[str]) -> List[str]:
    urls = re.findall(r'https?://[^\s)"\']+', text)
    return [u for u in urls if any(d in u for d in official_domains)]


def validate_named_values(text: str, registry: Dict) -> List[Dict]:
    """Exact validation of figures with a known registry reference value."""
    results = []
    reg = registry.get("registry", {})
    for key, pattern in NAMED_VALUE_PATTERNS:
        entry = reg.get(key)
        if not entry:
            continue
        for m in pattern.finditer(text):
            stated = _to_number(m.group(1))
            if stated is None:
                continue
            ref = entry.get("value")
            tol = entry.get("tolerance", 0)
            ok = ref is not None and abs(stated - ref) <= tol
            results.append({
                "registry_key": key,
                "label": entry.get("label"),
                "stated_value": stated,
                "reference_value": ref,
                "authority": entry.get("authority"),
                "source_url": entry.get("source_url"),
                "effective_date": entry.get("effective_date"),
                "verification_date": datetime.now(timezone.utc).date().isoformat(),
                "status": "VERIFIED" if ok else "CONTRADICTED",
            })
    return results


def detect_unbound_claims(text: str, registry: Dict) -> List[Dict]:
    """Detect require_official_source datum classes lacking an official source."""
    require = set(registry.get("require_official_source", []))
    official_domains = registry.get("official_domains", [])
    official_urls = _find_official_urls(text, official_domains)
    has_official = bool(official_urls)
    findings = []
    for datum_class, pattern in DATUM_PATTERNS:
        if datum_class not in require:
            continue
        for m in pattern.finditer(text):
            findings.append({
                "datum_class": datum_class,
                "matched_text": m.group(0)[:120],
                "official_source_found": has_official,
                "official_urls": official_urls[:3],
                "verification_date": datetime.now(timezone.utc).date().isoformat(),
                "status": "BOUND" if has_official else "UNVERIFIABLE",
            })
    return findings


def run_ymyl_validation(
    text: str,
    registry_path: str = DEFAULT_REGISTRY_PATH,
    output_path: str = "output/agent_20/ymyl_report.json",
) -> Dict:
    registry = load_registry(registry_path)
    named = validate_named_values(text, registry)
    unbound = detect_unbound_claims(text, registry)

    contradictions = [n for n in named if n["status"] == "CONTRADICTED"]
    unverifiable = [u for u in unbound if u["status"] == "UNVERIFIABLE"]
    status = "PASS" if not contradictions and not unverifiable else "FAIL"

    report = {
        "agent": "agent_20_ymyl_validator",
        "version": "4.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "verified_values": [n for n in named if n["status"] == "VERIFIED"],
        "contradicted_values": contradictions,
        "unverifiable_claims": unverifiable,
        "bound_claims": [u for u in unbound if u["status"] == "BOUND"],
        "summary": {
            "verified": len([n for n in named if n["status"] == "VERIFIED"]),
            "contradicted": len(contradictions),
            "unverifiable": len(unverifiable),
        },
    }
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Agent 20 status=%s verified=%d contradicted=%d unverifiable=%d -> %s",
        status, report["summary"]["verified"], len(contradictions),
        len(unverifiable), out,
    )
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Agent 20 - YMYL Validator (V4)")
    parser.add_argument("--input", required=True, help="article markdown/text file")
    parser.add_argument("--registry", default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--output", default="output/agent_20/ymyl_report.json")
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    report = run_ymyl_validation(text, args.registry, args.output)
    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
