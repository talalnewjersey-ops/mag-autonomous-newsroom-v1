"""
NEXUS-14 V3 - Agent 06: EEAT Validator Agent
MoneyAbroadGuide.com Autonomous Newsroom

Validates Experience, Expertise, Authority, Trust (E-E-A-T)
for SEO 2026 compliance. Target score: >= 90.
Output: eeat_report.json
CLI: python -m agents.agent_06_eeat_validator --input <file> --output <dir> --threshold 90

UNIFIED SCORING (2026-07-11): this used to carry its own, independent EEAT_SIGNALS/
evaluate_dimension implementation, completely separate from agent_12_quality_
assurance.py's _audit_eeat/_calculate_eeat_score. The two had already diverged --
witness run 9 scored the SAME article at 98.3 here (GATE B) and 81.2 in GATE QA,
a 17-point gap on one supposedly well-defined metric. Root cause (verified against
the real article, not guessed): agent_12 received the 2026-07-10 EEAT fixes (PR #68
firsthand-experience recognition, PR #70 illustrative-scenario recognition);
this file never did. Worse, this file's OWN "author_credentials" signal matched
generically on words like "licensed" ANYWHERE in the body (e.g. "insurers licensed
in California" -- describing a THIRD PARTY, never the article's own author),
inflating authority scores with false positives. Now delegates to
agents/_eeat_scoring.py, the single EEAT implementation shared with agent_12 --
both agents score the exact same article identically.
"""

import argparse
import json
import re
import logging
import sys
from datetime import datetime
from pathlib import Path

from agents._eeat_scoring import audit_eeat, calculate_eeat_score, derive_flags_from_content

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-06] %(levelname)s %(message)s")

# E-E-A-T dimension weights -- kept only for the report's own display/back-compat;
# agents/_eeat_scoring.py::calculate_eeat_score is the ACTUAL formula used (equal
# 25% per dimension, matching agent_12 -- see that module's docstring for why).
EEAT_WEIGHTS = {
    "experience": 25,
    "expertise": 25,
    "authority": 25,
    "trust": 25,
}


def get_signal_recommendation(signal_name, dimension):
    recs = {
        "experience_signals": "Add concrete real-world examples, case studies, or firsthand-experience language",
        "expertise_signals": "Use more financial/regulatory terminology and cite official sources",
        "has_credentials": "Add a real, honest author credential (CPA/CFA/CFP/attorney) -- never fabricate one",
        "has_author": "Add an author byline",
        "has_author_bio": "Add an author bio section",
        "trust_signals": "Add source citations, references, or trust/security language",
        "has_update_date": "Add a 'Last Updated' date line",
    }
    return recs.get(signal_name, f"Improve {signal_name} in {dimension}")


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

    # UNIFIED (2026-07-11): same call agent_12 makes, so both agents score the
    # same article identically. has_author/has_author_bio/has_update_date are
    # derived straight from the text (this CLI has no separate upstream flags
    # the way agent_12's pipeline data does) -- see derive_flags_from_content's
    # docstring for why that's reliable for this pipeline's fixed output shape.
    flags = derive_flags_from_content(article_text)
    checks = audit_eeat(article_text, word_count=word_count, **flags)
    total_score = calculate_eeat_score(checks)
    scores = {
        "experience": checks["experience_score"],
        "expertise": checks["expertise_score"],
        "authority": checks["authority_score"],
        "trust": checks["trust_score"],
    }
    for dimension, score in scores.items():
        logger.info(f"  {dimension.upper()}: {score:.1f}/100")

    passes = total_score >= threshold
    verdict = "PASS" if passes else "FAIL"

    # Recommendations -- one per weak (<70) dimension, using the raw checks
    # (no more per-signal found/missing breakdown; that structure belonged to
    # the old per-dimension signal system this file no longer has).
    recommendations = []
    if scores["experience"] < 70:
        recommendations.append({"priority": "HIGH" if scores["experience"] < 50 else "MEDIUM",
                                 "dimension": "EXPERIENCE", "score": scores["experience"],
                                 "action": get_signal_recommendation("experience_signals", "experience")})
    if scores["expertise"] < 70:
        recommendations.append({"priority": "HIGH" if scores["expertise"] < 50 else "MEDIUM",
                                 "dimension": "EXPERTISE", "score": scores["expertise"],
                                 "action": get_signal_recommendation("expertise_signals", "expertise")})
    if not checks["has_credentials"]:
        recommendations.append({"priority": "LOW", "dimension": "AUTHORITY", "score": scores["authority"],
                                 "action": get_signal_recommendation("has_credentials", "authority")})
    if scores["trust"] < 70:
        recommendations.append({"priority": "HIGH" if scores["trust"] < 50 else "MEDIUM",
                                 "dimension": "TRUST", "score": scores["trust"],
                                 "action": get_signal_recommendation("trust_signals", "trust")})

    # Critical issues
    critical_issues = []
    if not checks["has_author_bio"]:
        critical_issues.append("CRITICAL: No author bio detected")
    if not flags["has_update_date"]:
        critical_issues.append("HIGH: No last-updated date")
    if scores["expertise"] < 30:
        critical_issues.append("CRITICAL: Very low expertise score")

    elapsed = (datetime.now() - start_time).total_seconds()

    report = {
        "agent": "agent_06_eeat_validator",
        "version": "V4",  # unified scoring (2026-07-11) -- see module docstring
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "article_path": str(article_path),
        "word_count": word_count,
        "char_count": char_count,
        "verdict": verdict,
        "total_eeat_score": total_score,
        "minimum_required": threshold,
        "passes_threshold": passes,
        "dimension_scores": scores,
        "eeat_weights": EEAT_WEIGHTS,
        "checks": checks,
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


# ---------------------------------------------------------------------------
# NEXUS-14 compatibility: BaseAgent wrapper
# Exposes EEATValidatorAgent so orchestrator can import and run this agent
# via the standard BaseAgent interface (async run(context)).
# Falls back silently (functions/CLI still work) if BaseAgent is unavailable.
# ---------------------------------------------------------------------------
try:
    from agents.base_agent import BaseAgent

    class EEATValidatorAgent(BaseAgent):
        AGENT_ID = "agent_06"
        AGENT_NAME = "EEAT Validator Agent"
        VERSION = "3.0.0"

        def __init__(self, config, llm_service=None, storage_service=None, **kwargs):
            super().__init__(config, llm_service, storage_service, **kwargs)
            self.threshold = float(config.get("eeat_threshold", 90))

        def _resolve_article_path(self, context):
            if context:
                for key in ("article_path", "draft_path", "article_file", "draft_file"):
                    val = context.get(key)
                    if val and Path(val).exists():
                        return str(val)
                agent_results = [
                    context.get("agent_04_result"),
                    context.get("agent_05_result"),
                ]
                for res in agent_results:
                    if isinstance(res, dict):
                        for key in ("output_path", "article_path", "draft_path"):
                            val = res.get(key)
                            if val and Path(val).exists():
                                return str(val)
            for candidate in (
                "output/agent_05/article_fact_checked.md",
                "output/agent_04/article_draft.md",
                "output/article_draft.md",
            ):
                if Path(candidate).exists():
                    return candidate
            return None

        async def run(self, context=None):
            self.log_start()
            try:
                article_path = self._resolve_article_path(context)
                if not article_path:
                    raise FileNotFoundError(
                        "EEATValidatorAgent: no article draft found in context or output dirs"
                    )
                report = run_eeat_validation(
                    article_path,
                    str(self.output_dir),
                    threshold=self.threshold,
                )
                self.log_complete({
                    "verdict": report.get("verdict"),
                    "score": report.get("total_eeat_score"),
                })
                return {
                    "eeat_report": report,
                    "verdict": report.get("verdict"),
                    "total_eeat_score": report.get("total_eeat_score"),
                    "output_path": str(self.output_dir / "eeat_report.json"),
                }
            except Exception as e:
                self.log_error(e)
                raise

except ImportError:
    pass
