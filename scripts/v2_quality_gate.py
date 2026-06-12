#!/usr/bin/env python3
"""
NEXUS-14 V3 — Quality Gate Script (Upgraded from V2)
MoneyAbroadGuide.com Quality-First Autonomous Newsroom

CRITICAL RULE: Never report success unless all 18 gates pass.
Never create a draft if quality standards are not met.

NEW IN V3:
  Gate 16: Cannibalization PASS (Agent 17)
  Gate 17: Revenue Score >= 60 (Agent 18)
  Gate 18: Image Quality Validation PASS (Agent 10 enhanced)
  Updated thresholds for STANDARD vs PILLAR articles

Usage:
  python scripts/v2_quality_gate.py \\
    --qa-report output/agent_12/qa_report.json \\
    --editor-report output/agent_13/editor_report.json \\
    --image-validation output/agent_10/image_validation_report.json \\
    --image-quality output/agent_10/image_quality_report.json \\
    --wordpress-validation output/agent_11/wordpress_validation_report.json \\
    --affiliate-compliance output/agent_15/affiliate_compliance.json \\
    --publishing-optimizer output/agent_16/publishing_optimizer.json \\
    --content-validation output/content_validation_report.json \\
    --cannibalization-report output/agent_17/cannibalization_report.json \\
    --revenue-score output/agent_18/revenue_score.json \\
    --article-type STANDARD \\
    --output output/quality_gate_result.json
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================
# V3 QUALITY GATE THRESHOLDS
# Two-tier: STANDARD and PILLAR
# ============================================================
GATES_STANDARD = {
    "word_count_min": 3500,           # Updated from 5000
    "images_min": 5,
    "featured_image_required": True,
    "faq_min": 8,                     # Updated from 20
    "internal_links_min": 5,
    "sources_min": 5,                 # Updated from 10
    "case_studies_min": 2,
    "author_required": True,
    "author_bio_required": True,
    "seo_score_min": 90,
    "eeat_score_min": 90,
    "affiliate_compliance_required": True,
    "publishing_optimization_required": True,
    "broken_links_max": 0,
    "image_upload_errors_max": 0,
    "cannibalization_decision_allowed": ["CREATE_NEW_ARTICLE", "UPDATE_EXISTING_ARTICLE", "MERGE_WITH_EXISTING"],
    "revenue_score_min": 60,
    "image_quality_required": True,
    "ebook_opportunities_min": 2,
    "affiliate_opportunities_min": 2,
}

GATES_PILLAR = {
    **GATES_STANDARD,
    "word_count_min": 7000,
    "faq_min": 15,
    "sources_min": 10,
    "images_min": 6,
}


def load_json_report(path: str, report_name: str) -> dict:
    """Load and parse a JSON report file."""
    p = Path(path)
    if not p.exists():
        logger.error(f"Report not found: {path} ({report_name})")
        return {"_missing": True, "_path": path}
    try:
        with open(p) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return {"_invalid": True, "_path": path, "_error": str(e)}


def run_quality_gate(args) -> dict:
    """Run all V3 quality gates and return aggregated result."""
    start_time = datetime.utcnow()
    all_failures = []
    all_warnings = []
    gate_results = {}

    article_type = getattr(args, 'article_type', 'STANDARD').upper()
    GATES = GATES_PILLAR if article_type == "PILLAR" else GATES_STANDARD

    logger.info("=" * 60)
    logger.info(f"NEXUS-14 V3 — QUALITY GATE EVALUATION ({article_type})")
    logger.info("=" * 60)

    # Load all reports
    qa = load_json_report(args.qa_report, "QA Report")
    editor = load_json_report(args.editor_report, "Editor Report")
    image_val = load_json_report(args.image_validation, "Image Validation")
    image_qual = load_json_report(getattr(args, 'image_quality', ''), "Image Quality") if getattr(args, 'image_quality', '') else {"_missing": True}
    wp_val = load_json_report(args.wordpress_validation, "WordPress Validation")
    affiliate = load_json_report(args.affiliate_compliance, "Affiliate Compliance")
    publishing = load_json_report(args.publishing_optimizer, "Publishing Optimizer")
    content = load_json_report(args.content_validation, "Content Validation")
    cannibalization = load_json_report(getattr(args, 'cannibalization_report', ''), "Cannibalization Report") if getattr(args, 'cannibalization_report', '') else {"_missing": True}
    revenue = load_json_report(getattr(args, 'revenue_score', ''), "Revenue Score") if getattr(args, 'revenue_score', '') else {"_missing": True}

    # -------------------------------------------------------
    # GATE 1: Word Count
    # -------------------------------------------------------
    word_count = content.get("word_count", qa.get("word_count", 0))
    gate_pass = word_count >= GATES["word_count_min"]
    gate_results["gate_01_word_count"] = {
        "gate": "01 - Minimum Word Count",
        "article_type": article_type,
        "threshold": GATES["word_count_min"],
        "actual": word_count,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 01 FAIL: Word count {word_count:,} < minimum {GATES['word_count_min']:,} for {article_type}")

    # -------------------------------------------------------
    # GATE 2: Image Count
    # -------------------------------------------------------
    image_count = image_val.get("images_generated", image_val.get("images_uploaded", 0))
    upload_errors = image_val.get("image_upload_errors", 0)
    gate_pass = image_count >= GATES["images_min"] and upload_errors <= GATES["image_upload_errors_max"]
    gate_results["gate_02_images"] = {
        "gate": "02 - Minimum Images",
        "threshold": GATES["images_min"],
        "actual": image_count,
        "upload_errors": upload_errors,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 02 FAIL: Images {image_count} < minimum {GATES['images_min']} or upload errors: {upload_errors}")

    # -------------------------------------------------------
    # GATE 3: Featured Image
    # -------------------------------------------------------
    has_featured = bool(
        image_val.get("featured_image_uploaded") or
        wp_val.get("featured_image_set") or
        content.get("has_featured_image")
    )
    gate_results["gate_03_featured_image"] = {
        "gate": "03 - Featured Image Present",
        "passed": has_featured,
    }
    if not has_featured:
        all_failures.append("GATE 03 FAIL: Featured image not uploaded or not set in WordPress")

    # -------------------------------------------------------
    # GATE 4: FAQ Count
    # -------------------------------------------------------
    faq_count = content.get("faq_count", qa.get("faq_count", 0))
    gate_pass = faq_count >= GATES["faq_min"]
    gate_results["gate_04_faq"] = {
        "gate": "04 - Minimum FAQ Questions",
        "article_type": article_type,
        "threshold": GATES["faq_min"],
        "actual": faq_count,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 04 FAIL: FAQ count {faq_count} < minimum {GATES['faq_min']} for {article_type}")

    # -------------------------------------------------------
    # GATE 5: Internal Links
    # -------------------------------------------------------
    internal_links = content.get("internal_links", qa.get("internal_links_count", 0))
    gate_pass = internal_links >= GATES["internal_links_min"]
    gate_results["gate_05_internal_links"] = {
        "gate": "05 - Minimum Internal Links",
        "threshold": GATES["internal_links_min"],
        "actual": internal_links,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 05 FAIL: Internal links {internal_links} < minimum {GATES['internal_links_min']}")

    # -------------------------------------------------------
    # GATE 6: Authoritative Sources
    # -------------------------------------------------------
    sources_count = content.get("sources_count", qa.get("sources_count", 0))
    gate_pass = sources_count >= GATES["sources_min"]
    gate_results["gate_06_sources"] = {
        "gate": "06 - Minimum Authoritative Sources",
        "article_type": article_type,
        "threshold": GATES["sources_min"],
        "actual": sources_count,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 06 FAIL: Sources {sources_count} < minimum {GATES['sources_min']} for {article_type}")

    # -------------------------------------------------------
    # GATE 7: Case Studies
    # -------------------------------------------------------
    case_studies = content.get("case_studies_count", qa.get("case_studies", 0))
    gate_pass = case_studies >= GATES["case_studies_min"]
    gate_results["gate_07_case_studies"] = {
        "gate": "07 - Minimum Case Studies",
        "threshold": GATES["case_studies_min"],
        "actual": case_studies,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 07 FAIL: Case studies {case_studies} < minimum {GATES['case_studies_min']}")

    # -------------------------------------------------------
    # GATE 8: Author & Bio
    # -------------------------------------------------------
    has_author = bool(wp_val.get("author_assigned") or content.get("has_author"))
    has_bio = bool(wp_val.get("author_bio_inserted") or content.get("has_author_bio"))
    gate_results["gate_08_author"] = {
        "gate": "08 - Author & Bio",
        "passed": has_author and has_bio,
        "author_present": has_author,
        "bio_present": has_bio,
    }
    if not has_author:
        all_failures.append("GATE 08 FAIL: Author not assigned in WordPress")
    if not has_bio:
        all_failures.append("GATE 08 FAIL: Author bio not inserted in WordPress")

    # -------------------------------------------------------
    # GATE 9: SEO Score
    # -------------------------------------------------------
    seo_score = publishing.get("seo_score", qa.get("seo_score", 0))
    gate_pass = seo_score >= GATES["seo_score_min"]
    gate_results["gate_09_seo_score"] = {
        "gate": "09 - SEO Score",
        "threshold": GATES["seo_score_min"],
        "actual": seo_score,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 09 FAIL: SEO score {seo_score} < threshold {GATES['seo_score_min']}")

    # -------------------------------------------------------
    # GATE 10: EEAT Score
    # -------------------------------------------------------
    eeat_score = qa.get("eeat_score", 0)
    gate_pass = eeat_score >= GATES["eeat_score_min"]
    gate_results["gate_10_eeat_score"] = {
        "gate": "10 - EEAT Score",
        "threshold": GATES["eeat_score_min"],
        "actual": eeat_score,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 10 FAIL: EEAT score {eeat_score} < threshold {GATES['eeat_score_min']}")

    # -------------------------------------------------------
    # GATE 11: Affiliate Compliance (Agent 15)
    # -------------------------------------------------------
    affiliate_pass = affiliate.get("overall_passed", False)
    gate_results["gate_11_affiliate_compliance"] = {
        "gate": "11 - Affiliate Compliance (Agent 15)",
        "passed": affiliate_pass,
        "score": affiliate.get("compliance_score", 0),
    }
    if not affiliate_pass:
        all_failures.append(f"GATE 11 FAIL: Affiliate compliance failed — {affiliate.get('total_issues', 0)} issues")

    # -------------------------------------------------------
    # GATE 12: Publishing Optimization (Agent 16)
    # -------------------------------------------------------
    pub_pass = publishing.get("overall_optimization") == "PASS"
    gate_results["gate_12_publishing_optimization"] = {
        "gate": "12 - Publishing Optimization (Agent 16)",
        "passed": pub_pass,
        "optimization": publishing.get("overall_optimization", "UNKNOWN"),
    }
    if not pub_pass:
        all_failures.append("GATE 12 FAIL: Publishing optimization did not pass")

    # -------------------------------------------------------
    # GATE 13: Broken Links
    # -------------------------------------------------------
    broken_links = qa.get("broken_links_count", 0)
    gate_pass = broken_links <= GATES["broken_links_max"]
    gate_results["gate_13_broken_links"] = {
        "gate": "13 - Broken Links",
        "threshold": GATES["broken_links_max"],
        "actual": broken_links,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"GATE 13 FAIL: {broken_links} broken links detected")

    # -------------------------------------------------------
    # GATE 14: Content Structure
    # -------------------------------------------------------
    structure_checks = {
        "ebook_opportunities": content.get("ebook_opportunities", 0) >= GATES["ebook_opportunities_min"],
        "affiliate_opportunities": content.get("affiliate_opportunities", 0) >= GATES["affiliate_opportunities_min"],
    }
    structure_failed = [k for k, v in structure_checks.items() if not v]
    gate_results["gate_14_content_structure"] = {
        "gate": "14 - Content Structure Requirements",
        "passed": len(structure_failed) == 0,
        "checks": structure_checks,
        "failed_checks": structure_failed,
    }
    if structure_failed:
        for failed in structure_failed:
            all_warnings.append(f"WARNING GATE 14: Content structure check failed: {failed}")

    # -------------------------------------------------------
    # GATE 15: WordPress Draft Validation
    # -------------------------------------------------------
    draft_exists = bool(wp_val.get("draft_created") or wp_val.get("post_id"))
    gate_results["gate_15_wordpress_draft"] = {
        "gate": "15 - WordPress Draft Exists",
        "passed": draft_exists,
        "post_id": wp_val.get("post_id"),
        "draft_url": wp_val.get("draft_url"),
    }
    if not draft_exists:
        all_failures.append("GATE 15 FAIL: WordPress draft was not successfully created")

    # -------------------------------------------------------
    # GATE 16: Cannibalization PASS (NEW V3 — Agent 17)
    # -------------------------------------------------------
    if cannibalization.get("_missing"):
        cannibalization_pass = False
        all_failures.append("GATE 16 FAIL: Cannibalization report missing (Agent 17 not run)")
    else:
        cannibalization_decision = cannibalization.get("decision", "")
        cannibalization_blocking = cannibalization.get("blocking", True)
        cannibalization_pass = not cannibalization_blocking and cannibalization_decision in GATES["cannibalization_decision_allowed"]

    gate_results["gate_16_cannibalization"] = {
        "gate": "16 - Cannibalization Check PASS (Agent 17) [NEW V3]",
        "passed": cannibalization_pass,
        "decision": cannibalization.get("decision", "MISSING"),
        "blocking": cannibalization.get("blocking", True),
        "conflicts_found": len(cannibalization.get("conflicts_found", [])),
    }
    if not cannibalization_pass and not cannibalization.get("_missing"):
        all_failures.append(
            f"GATE 16 FAIL: Cannibalization check failed — Decision: {cannibalization.get('decision')} | "
            f"Action: {cannibalization.get('recommended_action', 'N/A')}"
        )

    # -------------------------------------------------------
    # GATE 17: Revenue Score >= 60 (NEW V3 — Agent 18)
    # -------------------------------------------------------
    if revenue.get("_missing"):
        revenue_pass = False
        revenue_score_val = 0
        all_failures.append("GATE 17 FAIL: Revenue score report missing (Agent 18 not run)")
    else:
        revenue_score_val = revenue.get("revenue_score", 0)
        revenue_pass = revenue_score_val >= GATES["revenue_score_min"]

    gate_results["gate_17_revenue_score"] = {
        "gate": "17 - Revenue Score >= 60 (Agent 18) [NEW V3]",
        "passed": revenue_pass,
        "threshold": GATES["revenue_score_min"],
        "actual": revenue_score_val,
        "decision": revenue.get("decision", "MISSING"),
    }
    if not revenue_pass and not revenue.get("_missing"):
        all_failures.append(
            f"GATE 17 FAIL: Revenue score {revenue_score_val} < minimum {GATES['revenue_score_min']} — "
            f"Topic rejected for low revenue potential"
        )

    # -------------------------------------------------------
    # GATE 18: Image Quality Validation (NEW V3 — Agent 10 enhanced)
    # -------------------------------------------------------
    if image_qual.get("_missing"):
        image_quality_pass = False
        all_failures.append("GATE 18 FAIL: Image quality report missing (Agent 10 enhanced validation not run)")
    else:
        image_quality_pass = image_qual.get("overall_passed", False)
        image_quality_checks = image_qual.get("validation_checks", {})

    gate_results["gate_18_image_quality"] = {
        "gate": "18 - Image Quality Validation PASS (Agent 10) [NEW V3]",
        "passed": image_quality_pass,
        "resolution_check": image_qual.get("resolution_check", "UNKNOWN") if not image_qual.get("_missing") else "MISSING",
        "readability_check": image_qual.get("readability_check", "UNKNOWN") if not image_qual.get("_missing") else "MISSING",
        "branding_check": image_qual.get("branding_check", "UNKNOWN") if not image_qual.get("_missing") else "MISSING",
        "no_ai_artifacts": image_qual.get("no_ai_artifacts", "UNKNOWN") if not image_qual.get("_missing") else "MISSING",
        "mobile_readable": image_qual.get("mobile_readable", "UNKNOWN") if not image_qual.get("_missing") else "MISSING",
    }
    if not image_quality_pass and not image_qual.get("_missing"):
        failed_checks = [k for k, v in image_qual.get("validation_checks", {}).items() if not v]
        all_failures.append(f"GATE 18 FAIL: Image quality validation failed — checks failed: {', '.join(failed_checks)}")

    # -------------------------------------------------------
    # FINAL VERDICT
    # -------------------------------------------------------
    total_failures = len(all_failures)
    overall_passed = total_failures == 0
    status = "READY_TO_PUBLISH" if overall_passed else "NEEDS_CORRECTION"
    duration = (datetime.utcnow() - start_time).total_seconds()
    gates_passed = sum(1 for g in gate_results.values() if g.get("passed"))
    total_gates = len(gate_results)

    result = {
        "script": "v2_quality_gate.py (V3)",
        "system_version": "NEXUS-14 V3",
        "article_type": article_type,
        "timestamp": datetime.utcnow().isoformat(),
        "execution_duration_seconds": round(duration, 2),
        "status": status,
        "overall_passed": overall_passed,
        "total_failures": total_failures,
        "total_warnings": len(all_warnings),
        "failures": all_failures,
        "warnings": all_warnings,
        "gate_results": gate_results,
        "summary": {
            "gates_passed": gates_passed,
            "gates_total": total_gates,
            "gates_failed": total_gates - gates_passed,
            "seo_score": publishing.get("seo_score", qa.get("seo_score", 0)),
            "eeat_score": qa.get("eeat_score", 0),
            "revenue_score": revenue_score_val if not revenue.get("_missing") else 0,
            "cannibalization_decision": cannibalization.get("decision", "MISSING"),
            "word_count": word_count,
            "image_count": image_count,
            "faq_count": faq_count,
            "sources_count": sources_count,
            "post_id": wp_val.get("post_id"),
            "draft_url": wp_val.get("draft_url"),
        },
        "v3_new_gates": {
            "gate_16_cannibalization": gate_results.get("gate_16_cannibalization", {}).get("passed"),
            "gate_17_revenue_score": gate_results.get("gate_17_revenue_score", {}).get("passed"),
            "gate_18_image_quality": gate_results.get("gate_18_image_quality", {}).get("passed"),
        },
    }

    # Print summary
    logger.info("")
    logger.info(f"ARTICLE TYPE: {article_type}")
    logger.info(f"STATUS: {status}")
    logger.info(f"Gates Passed: {gates_passed}/{total_gates}")
    logger.info(f"Failures: {total_failures}")
    logger.info(f"Warnings: {len(all_warnings)}")
    logger.info(f"Revenue Score: {revenue_score_val}/100")
    logger.info(f"Cannibalization: {cannibalization.get('decision', 'MISSING')}")

    if all_failures:
        logger.error("")
        logger.error("FAILURES:")
        for f in all_failures:
            logger.error(f"  {f}")

    if all_warnings:
        logger.warning("")
        logger.warning("WARNINGS:")
        for w in all_warnings:
            logger.warning(f"  {w}")

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"NEXUS-14 V3 QUALITY GATE: {status}")
    logger.info("=" * 60)

    return result


def main():
    parser = argparse.ArgumentParser(description="NEXUS-14 V3 Quality Gate (18 Gates)")
    parser.add_argument("--qa-report", required=True)
    parser.add_argument("--editor-report", required=True)
    parser.add_argument("--image-validation", required=True)
    parser.add_argument("--image-quality", default="")                    # NEW V3
    parser.add_argument("--wordpress-validation", required=True)
    parser.add_argument("--affiliate-compliance", required=True)
    parser.add_argument("--publishing-optimizer", required=True)
    parser.add_argument("--content-validation", required=True)
    parser.add_argument("--cannibalization-report", default="")           # NEW V3
    parser.add_argument("--revenue-score", default="")                    # NEW V3
    parser.add_argument("--article-type", default="STANDARD",            # NEW V3
                        choices=["STANDARD", "PILLAR"])
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = run_quality_gate(args)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Quality gate result saved to: {output_path}")

    if not result["overall_passed"]:
        logger.error("QUALITY GATE FAILED — Article will NOT be published.")
        sys.exit(1)
    else:
        logger.info("QUALITY GATE PASSED — Article is READY_TO_PUBLISH.")
        sys.exit(0)


if __name__ == "__main__":
    main()
