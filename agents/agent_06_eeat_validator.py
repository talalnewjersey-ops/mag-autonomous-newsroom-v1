"""
NEXUS-14 V3 - Agent 06: EEAT Validator Agent
MoneyAbroadGuide.com Autonomous Newsroom

Validates Experience, Expertise, Authority, Trust (E-E-A-T)
for SEO 2026 compliance. Target score: >= 90.
Output: eeat_report.json
CLI: python -m agents.agent_06_eeat_validator --input <file> --output <dir> --threshold 90
"""

import argparse
import json
import re
import logging
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-06] %(levelname)s %(message)s")

# E-E-A-T dimension weights (must sum to 100)
EEAT_WEIGHTS = {
    "experience": 25,
    "expertise": 30,
    "authority": 25,
    "trust": 20,
}

# Signals for each dimension
EEAT_SIGNALS = {
    "experience": {
        "first_person_narrative": {
            "weight": 20,
            "patterns": [
                r"(?i)\b(?:I|we|our|my)\s+(?:have|had|used|tried|experienced|found|discovered)",
                r"(?i)\b(?:in my experience|personally|firsthand|I can confirm)",
                r"(?i)\b(?:when I|after I|before I|once I)",
            ],
            "min_count": 3,
        },
        "specific_examples": {
            "weight": 30,
            "patterns": [
                r"(?i)\b(?:for example|for instance|such as|specifically|case study)",
                r"(?i)\b(?:real-world|real world|in practice|in reality|actual)",
            ],
            "min_count": 2,
        },
        "detailed_process": {
            "weight": 25,
            "patterns": [
                r"(?i)\bstep\s+\d+|step-by-step|step by step",
                r"(?i)\b(?:process|procedure|instructions?|how to|tutorial)",
                r"(?i)\b(?:first|second|third|then|next|finally)\s+(?:you|we|the)",
            ],
            "min_count": 3,
        },
        "recent_date": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:2024|2025|2026)\b",
                r"(?i)\b(?:last updated|updated|as of|current|latest|recent)\b",
            ],
            "min_count": 2,
        },
    },
    "expertise": {
        "technical_terminology": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:SWIFT|SEPA|IBAN|BIC|KYC|AML|FINTRAC|CRA|IRS|FATCA)",
                r"(?i)\b(?:remittance|forex|wire transfer|ACH|interbank|correspondent banking)",
                r"(?i)\b(?:TFSA|RRSP|401k|RESP|GIC|T4|W-2|1099)",
                r"(?i)\b(?:exchange rate|spread|mid-market|conversion fee|FX|hedging)",
            ],
            "min_count": 5,
        },
        "regulatory_references": {
            "weight": 30,
            "patterns": [
                r"(?i)\b(?:FINTRAC|OSFI|FCAC|CFPB|FinCEN|FDIC|OCC|NCUA)",
                r"(?i)\b(?:Bank Act|PCMLTFA|Money Services Business|MSB|MTL)",
                r"(?i)\b(?:regulation|regulatory|compliance|licensed|regulated|registered)",
            ],
            "min_count": 3,
        },
        "data_and_statistics": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:according to|research|study|survey|statistics|data|report|analysis)",
                r"(?i)\b(?:\d+(?:\.\d+)?\s*(?:percent|%|million|billion|thousand))",
            ],
            "min_count": 3,
        },
        "external_links_gov": {
            "weight": 20,
            "patterns": [
                r"https?://(?:www\.)?(?:canada\.ca|gc\.ca|irs\.gov|usa\.gov|federalreserve\.gov)",
                r"https?://(?:www\.)?(?:bankofcanada\.ca|imf\.org|worldbank\.org|oecd\.org)",
            ],
            "min_count": 2,
        },
    },
    "authority": {
        "author_credentials": {
            "weight": 35,
            "patterns": [
                r"(?i)\b(?:by|author|written by|published by|expert|specialist|advisor|consultant)",
                r"(?i)\b(?:CFA|CPA|CFP|MBA|PhD|CMA|CGA|CA)",
                r"(?i)\b(?:years of experience|licensed|certified|qualified|accredited)",
            ],
            "min_count": 1,
        },
        "brand_mentions": {
            "weight": 20,
            "patterns": [
                r"(?i)\b(?:moneyabroadguide|MoneyAbroadGuide)",
            ],
            "min_count": 2,
        },
        "publication_standards": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:editorial|reviewed by|fact-checked|editorial policy|editorial standards)",
                r"(?i)\b(?:methodology|disclosure|affiliate disclosure|sponsored)",
            ],
            "min_count": 1,
        },
        "internal_links": {
            "weight": 20,
            "patterns": [
                r"https?://(?:www\.)?moneyabroadguide\.com",
                r"\[.+?\]\((?:/[^)]+|https?://moneyabroadguide)[^)]*\)",
            ],
            "min_count": 3,
        },
    },
    "trust": {
        "disclaimer_present": {
            "weight": 30,
            "patterns": [
                r"(?i)\b(?:not financial advice|not a financial advisor|consult a professional)",
                r"(?i)\b(?:disclaimer|disclosure|this is not|general information only)",
                r"(?i)\b(?:seek professional advice|independent financial advice)",
            ],
            "min_count": 1,
        },
        "last_updated": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:last updated|updated on|published on|reviewed on)",
                r"(?i)\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
            ],
            "min_count": 1,
        },
        "author_bio": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:about the author|author bio|about us|meet the team|written by)",
                r"(?i)\b(?:author.s note|contributor|editor|journalist)",
            ],
            "min_count": 1,
        },
        "fact_checked": {
            "weight": 20,
            "patterns": [
                r"(?i)\b(?:fact[- ]?checked|fact checking|verified|accuracy|sources cited)",
                r"(?i)\b(?:references|bibliography|sources|citations|footnotes)",
            ],
            "min_count": 1,
        },
    },
}


def evaluate_dimension(dimension, article_text):
    """Evaluate one E-E-A-T dimension against its signals."""
    signals = EEAT_SIGNALS[dimension]
    total_signal_weight = sum(s["weight"] for s in signals.values())
    earned_weight = 0.0
    found_signals = []
    missing_signals = []

    for signal_name, signal_def in signals.items():
        matches = 0
        for pattern in signal_def["patterns"]:
            found = re.findall(pattern, article_text)
            matches += len(found)
        min_count = signal_def["min_count"]
        weight = signal_def["weight"]

        if matches >= min_count:
            earned_weight += weight
            found_signals.append({
                "signal": signal_name,
                "weight": weight,
                "matches": matches,
                "status": "FOUND",
            })
        elif matches > 0:
            partial = weight * (matches / min_count)
            earned_weight += partial
            found_signals.append({
                "signal": signal_name,
                "weight": round(partial, 2),
                "matches": matches,
                "status": "PARTIAL",
            })
        else:
            missing_signals.append({
                "signal": signal_name,
                "weight": weight,
                "matches": 0,
                "status": "MISSING",
                "recommendation": get_signal_recommendation(signal_name, dimension),
            })

    raw_score = (earned_weight / total_signal_weight) * 100 if total_signal_weight > 0 else 0
    return round(raw_score, 2), found_signals, missing_signals


def get_signal_recommendation(signal_name, dimension):
    recs = {
        "first_person_narrative": "Add personal experience statements (I have, my experience, we found)",
        "specific_examples": "Add concrete real-world examples and case studies",
        "technical_terminology": "Use financial terms: APR, IBAN, KYC, RRSP, TFSA, AML, SWIFT",
        "regulatory_references": "Reference regulations: FINTRAC, CRA, IRS, OSFI",
        "external_links_gov": "Link to government sites: canada.ca, irs.gov, federalreserve.gov",
        "disclaimer_present": "Add disclaimer: Not financial advice. Consult a professional.",
        "last_updated": "Add update date: Last updated: January 2026",
        "author_bio": "Add author bio section with credentials",
        "fact_checked": "Add fact-checked notation and source citations",
        "author_credentials": "Add author credentials: CFA, CPA, CFP or years of experience",
        "brand_mentions": "Mention MoneyAbroadGuide brand at least twice",
        "publication_standards": "Add editorial policy or reviewed-by section",
        "internal_links": "Add internal links to related MoneyAbroadGuide articles",
        "detailed_process": "Add step-by-step process sections with numbered steps",
        "recent_date": "Add or verify publication/update date is recent (2024-2026)",
        "data_and_statistics": "Add current statistics with percentage/number data from credible sources",
    }
    return recs.get(signal_name, f"Improve {signal_name} in {dimension}")


def calculate_total_score(scores):
    total = 0.0
    for dimension, weight in EEAT_WEIGHTS.items():
        total += (scores.get(dimension, 0) / 100) * weight
    return round(total, 2)


def run_eeat_validation(article_path, output_dir, threshold=90):
    """Run EEAT validation on an article file."""
    start_time = datetime.now()
    logger.info(f"AGENT-06 EEAT Validator starting...")
    logger.info(f"Article: {article_path} | Threshold: {threshold}")

    draft_path = Path(article_path)
    if not draft_path.exists():
        logger.error(f"Article file not found: {article_path}")
        sys.exit(1)

    article_text = draft_path.read_text(encoding="utf-8")
    word_count = len(article_text.split())
    char_count = len(article_text)
    logger.info(f"Loaded article: {word_count} words, {char_count} chars")

    # Evaluate all four dimensions
    scores = {}
    details = {}
    for dimension in ["experience", "expertise", "authority", "trust"]:
        score, found, missing = evaluate_dimension(dimension, article_text)
        scores[dimension] = score
        details[dimension] = {
            "score": score,
            "found_signals": found,
            "missing_signals": missing,
        }
        logger.info(f"  {dimension.upper()}: {score:.1f}/100 (found={len(found)}, missing={len(missing)})")

    total_score = calculate_total_score(scores)
    passes = total_score >= threshold
    verdict = "PASS" if passes else "FAIL"

    # Generate recommendations
    recommendations = []
    for dimension in ["experience", "expertise", "authority", "trust"]:
        score = scores.get(dimension, 0)
        missing = details[dimension]["missing_signals"]
        priority = "HIGH" if score < 50 else ("MEDIUM" if score < 70 else "LOW")
        for m in sorted(missing, key=lambda x: x["weight"], reverse=True)[:2]:
            recommendations.append({
                "priority": priority,
                "dimension": dimension.upper(),
                "score": round(score, 1),
                "action": m["recommendation"],
            })

    # Critical issues
    critical_issues = []
    trust_missing = [m["signal"] for m in details.get("trust", {}).get("missing_signals", [])]
    if "author_bio" in trust_missing:
        critical_issues.append("CRITICAL: No author bio detected")
    if "disclaimer_present" in trust_missing:
        critical_issues.append("CRITICAL: No disclaimer found")
    if "last_updated" in trust_missing:
        critical_issues.append("HIGH: No last-updated date")
    auth_missing = [m["signal"] for m in details.get("authority", {}).get("missing_signals", [])]
    if "external_links_gov" in auth_missing:
        critical_issues.append("HIGH: No government source links")
    if scores.get("expertise", 0) < 30:
        critical_issues.append("CRITICAL: Very low expertise score")

    elapsed = (datetime.now() - start_time).total_seconds()

    report = {
        "agent": "agent_06_eeat_validator",
        "version": "V3",
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "article_path": str(article_path),
        "word_count": word_count,
        "char_count": char_count,
        "verdict": verdict,
        "total_eeat_score": total_score,
        "minimum_required": threshold,
        "passes_threshold": passes,
        "dimension_scores": {
            "experience": scores.get("experience", 0),
            "expertise": scores.get("expertise", 0),
            "authority": scores.get("authority", 0),
            "trust": scores.get("trust", 0),
        },
        "eeat_weights": EEAT_WEIGHTS,
        "dimension_details": details,
        "recommendations": recommendations,
        "critical_issues": critical_issues,
    }

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_file = output_path / "eeat_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(f"EEAT Score: {total_score:.1f}/{threshold} | Verdict: {verdict}")
    logger.info(f"Report saved: {report_file}")
    return report


def main():
    parser = argparse.ArgumentParser(description="Agent 06 - EEAT Validator")
    parser.add_argument("--input", required=True, help="Path to article draft file")
    parser.add_argument("--output", required=True, help="Output directory for eeat_report.json")
    parser.add_argument("--threshold", type=float, default=90.0,
                        help="Minimum EEAT score to pass (default: 90)")
    args = parser.parse_args()

    report = run_eeat_validation(args.input, args.output, threshold=args.threshold)

    print(f"EEAT Score: {report['total_eeat_score']:.1f}/100")
    print(f"Verdict: {report['verdict']}")

    # P5 FIX: EEAT validator is now a BLOCKING GATE
    # If EEAT score is below threshold, publication is blocked (exit code 1)
    eeat_score = report['total_eeat_score']
    threshold = args.threshold
    verdict = report['verdict']

    if verdict == "FAIL" or eeat_score < threshold:
        critical_issues = report.get('critical_issues', [])
        print(f"EEAT GATE FAIL: score={eeat_score:.1f} < threshold={threshold}")
        print(f"Publication BLOCKED: EEAT score below minimum {threshold}/100")
        if critical_issues:
            for issue in critical_issues:
                print(f"  CRITICAL: {issue}")
        print("Fix all EEAT issues before publishing. See eeat_report.json for recommendations.")
        sys.exit(1)

    # PASS: EEAT score meets threshold
    print(f"EEAT GATE PASS: score={eeat_score:.1f} >= threshold={threshold}")
    sys.exit(0)


if __name__ == "__main__":
    main()
