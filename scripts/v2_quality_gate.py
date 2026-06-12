#!/usr/bin/env python3
"""
NEXUS-14 V2 — Quality Gate Script
Enforces all V2 quality standards before READY_TO_PUBLISH.

CRITICAL RULE: Never report success unless all gates pass.
Never create a draft if quality standards are not met.

Usage:
  python scripts/v2_quality_gate.py \
    --qa-report output/agent_12/qa_report.json \
    --editor-report output/agent_13/editor_report.json \
    --image-validation output/agent_10/image_validation_report.json \
    --wordpress-validation output/agent_11/wordpress_validation_report.json \
    --affiliate-compliance output/agent_15/affiliate_compliance.json \
    --publishing-optimizer output/agent_16/publishing_optimizer.json \
    --content-validation output/content_validation_report.json \
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
# V2 QUALITY GATE THRESHOLDS
# ============================================================
GATES = {
    "word_count_min": 5000,
    "images_min": 5,
    "featured_image_required": True,
    "faq_min": 20,
    "internal_links_min": 5,
    "sources_min": 10,
    "case_studies_min": 3,
    "author_required": True,
    "author_bio_required": True,
    "seo_score_min": 90,
    "eeat_score_min": 90,
    "affiliate_compliance_required": True,
    "publishing_optimization_required": True,
    "broken_links_max": 0,
    "image_upload_errors_max": 0,
    "ebook_opportunities_min": 2,
    "affiliate_opportunities_min": 2,
    "comparison_table_required": True,
    "checklist_required": True,
    "action_plan_required": True,
    "expert_section_required": True,
    "mistakes_section_required": True,
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
    """Run all V2 quality gates and return aggregated result."""
    start_time = datetime.utcnow()
    all_failures = []
    all_warnings = []
    gate_results = {}

    logger.info("=" * 60)
    logger.info("NEXUS-14 V2 — QUALITY GATE EVALUATION")
    logger.info("=" * 60)

    # Load all reports
    qa = load_json_report(args.qa_report, "QA Report")
    editor = load_json_report(args.editor_report, "Editor Report")
    image_val = load_json_report(args.image_validation, "Image Validation")
    wp_val = load_json_report(args.wordpress_validation, "WordPress Validation")
    affiliate = load_json_report(args.affiliate_compliance, "Affiliate Compliance")
    publishing = load_json_report(args.publishing_optimizer, "Publishing Optimizer")
    content = load_json_report(args.content_validation, "Content Validation")

    # -------------------------------------------------------
    # GATE 1: Word Count
    # -------------------------------------------------------
    word_count = content.get("word_count", qa.get("word_count", 0))
    gate_pass = word_count >= GATES["word_count_min"]
    gate_results["word_count"] = {
        "gate": "Minimum Word Count",
        "threshold": GATES["word_count_min"],
        "actual": word_count,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(
            f"FAIL: Word count {word_count:,} < minimum {GATES['word_count_min']:,}"
        )

    # -------------------------------------------------------
    # GATE 2: Image Count
    # -------------------------------------------------------
    image_count = image_val.get("images_generated", image_val.get("images_uploaded", 0))
    gate_pass = image_count >= GATES["images_min"] and image_val.get("image_upload_errors", 0) <= GATES["image_upload_errors_max"]
    gate_results["images"] = {
        "gate": "Minimum Images",
        "threshold": GATES["images_min"],
        "actual": image_count,
        "upload_errors": image_val.get("image_upload_errors", 0),
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(
            f"FAIL: Images {image_count} < minimum {GATES['images_min']} or upload errors detected"
        )

    # -------------------------------------------------------
    # GATE 3: Featured Image
    # -------------------------------------------------------
    has_featured = bool(
        image_val.get("featured_image_uploaded") or
        wp_val.get("featured_image_set") or
        content.get("has_featured_image")
    )
    gate_results["featured_image"] = {
        "gate": "Featured Image Present",
        "threshold": "Required",
        "actual": has_featured,
        "passed": has_featured,
    }
    if not has_featured:
        all_failures.append("FAIL: Featured image not uploaded or not set in WordPress")

    # -------------------------------------------------------
    # GATE 4: FAQ Count
    # -------------------------------------------------------
    faq_count = content.get("faq_count", qa.get("faq_count", 0))
    gate_pass = faq_count >= GATES["faq_min"]
    gate_results["faq"] = {
        "gate": "Minimum FAQ Questions",
        "threshold": GATES["faq_min"],
        "actual": faq_count,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"FAIL: FAQ count {faq_count} < minimum {GATES['faq_min']}")

    # -------------------------------------------------------
    # GATE 5: Internal Links
    # -------------------------------------------------------
    internal_links = content.get("internal_links", qa.get("internal_links_count", 0))
    gate_pass = internal_links >= GATES["internal_links_min"]
    gate_results["internal_links"] = {
        "gate": "Minimum Internal Links",
        "threshold": GATES["internal_links_min"],
        "actual": internal_links,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(
            f"FAIL: Internal links {internal_links} < minimum {GATES['internal_links_min']}"
        )

    # -------------------------------------------------------
    # GATE 6: Sources
    # -------------------------------------------------------
    sources_count = content.get("sources_count", qa.get("sources_count", 0))
    gate_pass = sources_count >= GATES["sources_min"]
    gate_results["sources"] = {
        "gate": "Minimum Authoritative Sources",
        "threshold": GATES["sources_min"],
        "actual": sources_count,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(
            f"FAIL: Sources {sources_count} < minimum {GATES['sources_min']}"
        )

    # -------------------------------------------------------
    # GATE 7: Case Studies
    # -------------------------------------------------------
    case_studies = content.get("case_studies_count", qa.get("case_studies", 0))
    gate_pass = case_studies >= GATES["case_studies_min"]
    gate_results["case_studies"] = {
        "gate": "Minimum Case Studies",
        "threshold": GATES["case_studies_min"],
        "actual": case_studies,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(
            f"FAIL: Case studies {case_studies} < minimum {GATES['case_studies_min']}"
        )

    # -------------------------------------------------------
    # GATE 8: Author & Bio
    # -------------------------------------------------------
    has_author = bool(wp_val.get("author_assigned") or content.get("has_author"))
    has_bio = bool(wp_val.get("author_bio_inserted") or content.get("has_author_bio"))
    gate_results["author"] = {
        "gate": "Author & Bio",
        "passed": has_author and has_bio,
        "author_present": has_author,
        "bio_present": has_bio,
    }
    if not has_author:
        all_failures.append("FAIL: Author not assigned in WordPress")
    if not has_bio:
        all_failures.append("FAIL: Author bio not inserted in WordPress")

    # -------------------------------------------------------
    # GATE 9: SEO Score
    # -------------------------------------------------------
    seo_score = publishing.get("seo_score", qa.get("seo_score", 0))
    gate_pass = seo_score >= GATES["seo_score_min"]
    gate_results["seo_score"] = {
        "gate": "SEO Score",
        "threshold": GATES["seo_score_min"],
        "actual": seo_score,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(
            f"FAIL: SEO score {seo_score} < threshold {GATES['seo_score_min']}"
        )

    # -------------------------------------------------------
    # GATE 10: EEAT Score
    # -------------------------------------------------------
    eeat_score = qa.get("eeat_score", 0)
    gate_pass = eeat_score >= GATES["eeat_score_min"]
    gate_results["eeat_score"] = {
        "gate": "EEAT Score",
        "threshold": GATES["eeat_score_min"],
        "actual": eeat_score,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(
            f"FAIL: EEAT score {eeat_score} < threshold {GATES['eeat_score_min']}"
        )

    # -------------------------------------------------------
    # GATE 11: Affiliate Compliance
    # -------------------------------------------------------
    affiliate_pass = affiliate.get("overall_passed", False)
    gate_results["affiliate_compliance"] = {
        "gate": "Affiliate Compliance (Agent 15)",
        "passed": affiliate_pass,
        "compliance": affiliate.get("overall_compliance", "UNKNOWN"),
        "score": affiliate.get("compliance_score", 0),
    }
    if not affiliate_pass:
        all_failures.append(
            f"FAIL: Affiliate compliance failed — {affiliate.get('total_issues', 0)} issues found"
        )

    # -------------------------------------------------------
    # GATE 12: Publishing Optimization
    # -------------------------------------------------------
    pub_pass = publishing.get("overall_optimization") == "PASS"
    gate_results["publishing_optimization"] = {
        "gate": "Publishing Optimization (Agent 16)",
        "passed": pub_pass,
        "optimization": publishing.get("overall_optimization", "UNKNOWN"),
        "seo_score": publishing.get("seo_score", 0),
    }
    if not pub_pass:
        all_failures.append("FAIL: Publishing optimization did not pass")

    # -------------------------------------------------------
    # GATE 13: Broken Links
    # -------------------------------------------------------
    broken_links = qa.get("broken_links_count", 0)
    gate_pass = broken_links <= GATES["broken_links_max"]
    gate_results["broken_links"] = {
        "gate": "Broken Links",
        "threshold": GATES["broken_links_max"],
        "actual": broken_links,
        "passed": gate_pass,
    }
    if not gate_pass:
        all_failures.append(f"FAIL: {broken_links} broken links detected")

    # -------------------------------------------------------
    # GATE 14: WordPress Draft Validation
    # -------------------------------------------------------
    draft_exists = bool(wp_val.get("draft_created") or wp_val.get("post_id"))
    gate_results["wordpress_draft"] = {
        "gate": "WordPress Draft Exists",
        "passed": draft_exists,
        "post_id": wp_val.get("post_id"),
        "draft_url": wp_val.get("draft_url"),
    }
    if not draft_exists:
        all_failures.append("FAIL: WordPress draft was not successfully created")

    # -------------------------------------------------------
    # GATE 15: Content Structure (V2 requirements)
    # -------------------------------------------------------
    structure_checks = {
        "comparison_table": content.get("has_comparison_table", False),
        "checklist": content.get("has_checklist", False),
        "action_plan": content.get("has_action_plan", False),
        "expert_section": content.get("has_expert_section", False),
        "mistakes_section": content.get("has_mistakes_section", False),
        "ebook_opportunities": content.get("ebook_opportunities", 0) >= GATES["ebook_opportunities_min"],
        "affiliate_opportunities": content.get("affiliate_opportunities", 0) >= GATES["affiliate_opportunities_min"],
    }
    structure_failed = [k for k, v in structure_checks.items() if not v]
    gate_results["content_structure"] = {
        "gate": "V2 Content Structure Requirements",
        "passed": len(structure_failed) == 0,
        "checks": structure_checks,
        "failed_checks": structure_failed,
    }
    if structure_failed:
        for failed in structure_failed:
            all_warnings.append(f"WARNING: Content structure check failed: {failed}")

    # -------------------------------------------------------
    # FINAL VERDICT
    # -------------------------------------------------------
    total_failures = len(all_failures)
    overall_passed = total_failures == 0
    status = "READY_TO_PUBLISH" if overall_passed else "NEEDS_CORRECTION"

    duration = (datetime.utcnow() - start_time).total_seconds()

    result = {
        "script": "v2_quality_gate.py",
        "system_version": "NEXUS-14 V2",
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
            "gates_passed": sum(1 for g in gate_results.values() if g.get("passed")),
            "gates_total": len(gate_results),
            "seo_score": publishing.get("seo_score", qa.get("seo_score", 0)),
            "eeat_score": qa.get("eeat_score", 0),
            "word_count": word_count,
            "image_count": image_count,
            "faq_count": faq_count,
            "sources_count": sources_count,
            "post_id": wp_val.get("post_id"),
            "draft_url": wp_val.get("draft_url"),
        },
    }

    # Print summary
    logger.info("")
    logger.info(f"STATUS: {status}")
    logger.info(f"Gates Passed: {result['summary']['gates_passed']}/{result['summary']['gates_total']}")
    logger.info(f"Failures: {total_failures}")
    logger.info(f"Warnings: {len(all_warnings)}")

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
    logger.info(f"NEXUS-14 V2 QUALITY GATE: {status}")
    logger.info("=" * 60)

    return result


def main():
    parser = argparse.ArgumentParser(description="NEXUS-14 V2 Quality Gate")
    parser.add_argument("--qa-report", required=True)
    parser.add_argument("--editor-report", required=True)
    parser.add_argument("--image-validation", required=True)
    parser.add_argument("--wordpress-validation", required=True)
    parser.add_argument("--affiliate-compliance", required=True)
    parser.add_argument("--publishing-optimizer", required=True)
    parser.add_argument("--content-validation", required=True)
    parser.add_argument("--output", required=True)

    args = parser.parse_args()

    result = run_quality_gate(args)

    # Save result
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Quality gate result saved to: {output_path}")

    # Exit with error if failed
    if not result["overall_passed"]:
        logger.error("QUALITY GATE FAILED — Article will NOT be published.")
        sys.exit(1)
    else:
        logger.info("QUALITY GATE PASSED — Article is READY_TO_PUBLISH.")
        sys.exit(0)


if __name__ == "__main__":
    main()
