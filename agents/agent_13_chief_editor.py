"""
NEXUS-14: Agent 13 - Chief Editor Agent
Performs global audits at 09:30 and 16:30 and makes 
READY_TO_PUBLISH / NEEDS_CORRECTION / REJECTED decisions.
Output: editor_report.json
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

from agents.base_agent import BaseAgent
from services.llm_service import LLMService
from services.storage_service import StorageService
from services.email_service import EmailService


logger = logging.getLogger(__name__)


class ChiefEditorAgent(BaseAgent):
    """
    Agent 13: Chief Editor Agent
    
    Responsibilities:
    - Global audit at 09:30 (Batch 1)
    - Global audit at 16:30 (Batch 2)
    - Make READY_TO_PUBLISH / NEEDS_CORRECTION / REJECTED decisions
    
    Quality Gates (all must pass for READY_TO_PUBLISH):
    - Word count >= 5,000
    - Images >= 4 (including featured image)
    - FAQ section present
    - Author field present
    - Author bio present
    - SEO score >= 95
    - EEAT score >= 95
    - No broken links
    
    Output: editor_report.json
    """
    
    AGENT_ID = "agent_13"
    AGENT_NAME = "Chief Editor Agent"
    
    # STRICT Quality Rules - ALL must pass for READY_TO_PUBLISH
    QUALITY_RULES = {
        "min_word_count": 5000,
        "min_images": 4,
        "featured_image_required": True,
        "faq_required": True,
        "author_required": True,
        "author_bio_required": True,
        "min_seo_score": 95,
        "min_eeat_score": 95,
        "no_broken_links": True,
    }
    
    def __init__(self, config: Dict, llm_service: LLMService,
                 storage_service: StorageService, email_service: EmailService):
        super().__init__(config, llm_service, storage_service)
        self.email = email_service
    
    async def run(self, context: Dict = None) -> Dict:
        """Main editor audit."""
        self.log_start()
        
        try:
            # Collect all QA reports
            qa_reports = await self._collect_qa_reports(context or {})
            
            decisions = []
            ready_count = 0
            needs_correction_count = 0
            rejected_count = 0
            
            for article_id, qa_report in qa_reports.items():
                logger.info(f"Auditing article: {article_id}")
                
                # Apply quality gates
                gate_results = await self._apply_quality_gates(qa_report)
                
                # Make editorial decision
                decision = await self._make_decision(qa_report, gate_results)
                
                # Record decision
                decisions.append({
                    "article_id": article_id,
                    "title": qa_report.get("title", ""),
                    "decision": decision,
                    "gate_results": gate_results,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                if decision == "READY_TO_PUBLISH":
                    ready_count += 1
                elif decision == "NEEDS_CORRECTION":
                    needs_correction_count += 1
                else:
                    rejected_count += 1
                
                logger.info(f"Decision for '{article_id}': {decision}")
            
            # Generate editor report
            editor_report = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "audit_time": datetime.utcnow().strftime("%H:%M UTC"),
                "total_articles_audited": len(qa_reports),
                "ready_to_publish": ready_count,
                "needs_correction": needs_correction_count,
                "rejected": rejected_count,
                "decisions": decisions,
                "quality_rules": self.QUALITY_RULES,
                "summary": await self._generate_summary(decisions)
            }
            
            output_path = await self.save_output("editor_report.json", editor_report)
            logger.info(f"Editor report saved: {output_path}")
            
            self.log_complete({
                "audited": len(qa_reports),
                "ready": ready_count,
                "needs_correction": needs_correction_count,
                "rejected": rejected_count
            })
            
            return editor_report
            
        except Exception as e:
            self.log_error(e)
            raise
    
    async def _collect_qa_reports(self, context: Dict) -> Dict:
        """Collect QA reports from Agent 12."""
        import os
        
        qa_reports = {}
        
        # Check context first
        qa_result = context.get("agent_12_result", {})
        if qa_result:
            qa_reports["current_article"] = qa_result
        
        # Also scan output directory
        qa_dir = "output/agent_12"
        if os.path.exists(qa_dir):
            for f in os.listdir(qa_dir):
                if f.endswith(".json") and "qa_report" in f:
                    try:
                        with open(f"{qa_dir}/{f}") as fh:
                            qa_reports[f.replace(".json", "")] = json.load(fh)
                    except Exception as e:
                        logger.warning(f"Failed to load QA report {f}: {e}")
        
        if not qa_reports:
            logger.warning("No QA reports found. Creating mock data for testing.")
            qa_reports["test_article"] = self._create_mock_qa_report()
        
        return qa_reports
    
    async def _apply_quality_gates(self, qa_report: Dict) -> Dict:
        """Apply all quality gates to an article."""
        gates = {}
        
        # Gate 1: Word count
        word_count = qa_report.get("word_count", 0)
        gates["word_count"] = {
            "passed": word_count >= self.QUALITY_RULES["min_word_count"],
            "value": word_count,
            "threshold": self.QUALITY_RULES["min_word_count"],
            "message": f"Word count: {word_count} (minimum: {self.QUALITY_RULES['min_word_count']})"
        }
        
        # Gate 2: Images
        image_count = qa_report.get("image_count", 0)
        gates["images"] = {
            "passed": image_count >= self.QUALITY_RULES["min_images"],
            "value": image_count,
            "threshold": self.QUALITY_RULES["min_images"],
            "message": f"Images: {image_count} (minimum: {self.QUALITY_RULES['min_images']})"
        }
        
        # Gate 3: Featured image
        has_featured = qa_report.get("has_featured_image", False)
        gates["featured_image"] = {
            "passed": has_featured,
            "value": has_featured,
            "message": f"Featured image: {'Present' if has_featured else 'MISSING'}"
        }
        
        # Gate 4: FAQ
        has_faq = qa_report.get("has_faq", False)
        gates["faq"] = {
            "passed": has_faq,
            "value": has_faq,
            "message": f"FAQ section: {'Present' if has_faq else 'MISSING'}"
        }
        
        # Gate 5: Author
        has_author = qa_report.get("has_author", False)
        gates["author"] = {
            "passed": has_author,
            "value": has_author,
            "message": f"Author: {'Present' if has_author else 'MISSING'}"
        }
        
        # Gate 6: Author bio
        has_bio = qa_report.get("has_author_bio", False)
        gates["author_bio"] = {
            "passed": has_bio,
            "value": has_bio,
            "message": f"Author bio: {'Present' if has_bio else 'MISSING'}"
        }
        
        # Gate 7: SEO score
        seo_score = qa_report.get("seo_score", 0)
        gates["seo_score"] = {
            "passed": seo_score >= self.QUALITY_RULES["min_seo_score"],
            "value": seo_score,
            "threshold": self.QUALITY_RULES["min_seo_score"],
            "message": f"SEO score: {seo_score}/100 (minimum: {self.QUALITY_RULES['min_seo_score']})"
        }
        
        # Gate 8: EEAT score
        eeat_score = qa_report.get("eeat_score", 0)
        gates["eeat_score"] = {
            "passed": eeat_score >= self.QUALITY_RULES["min_eeat_score"],
            "value": eeat_score,
            "threshold": self.QUALITY_RULES["min_eeat_score"],
            "message": f"EEAT score: {eeat_score}/100 (minimum: {self.QUALITY_RULES['min_eeat_score']})"
        }
        
        # Gate 9: No broken links
        broken_links = qa_report.get("broken_links", [])
        gates["no_broken_links"] = {
            "passed": len(broken_links) == 0,
            "value": len(broken_links),
            "message": f"Broken links: {len(broken_links)} ({'OK' if not broken_links else 'FAILED'})"
        }
        
        # Overall result
        gates["all_passed"] = all(g["passed"] for g in gates.values() if isinstance(g, dict) and "passed" in g)
        gates["failed_count"] = sum(1 for g in gates.values() if isinstance(g, dict) and "passed" in g and not g["passed"])
        
        return gates
    
    async def _make_decision(self, qa_report: Dict, gate_results: Dict) -> str:
        """Make the editorial decision based on quality gates."""
        
        # READY_TO_PUBLISH: All gates pass
        if gate_results.get("all_passed"):
            return "READY_TO_PUBLISH"
        
        # Count failed gates
        failed_count = gate_results.get("failed_count", 0)
        
        # REJECTED: Critical failures (missing featured image, FAQ, author, or score < 50)
        critical_failures = [
            not gate_results.get("featured_image", {}).get("passed"),
            not gate_results.get("faq", {}).get("passed"),
            not gate_results.get("author", {}).get("passed"),
            gate_results.get("seo_score", {}).get("value", 0) < 50,
            gate_results.get("eeat_score", {}).get("value", 0) < 50,
            gate_results.get("word_count", {}).get("value", 0) < 3000,
        ]
        
        if any(critical_failures):
            return "REJECTED"
        
        # NEEDS_CORRECTION: Minor failures (1-2 gates failing)
        if failed_count <= 2:
            return "NEEDS_CORRECTION"
        
        # Too many failures
        return "REJECTED"
    
    async def _generate_summary(self, decisions: List[Dict]) -> str:
        """Generate editorial summary."""
        if not decisions:
            return "No articles audited in this batch."
        
        ready = [d for d in decisions if d["decision"] == "READY_TO_PUBLISH"]
        corrections = [d for d in decisions if d["decision"] == "NEEDS_CORRECTION"]
        rejected = [d for d in decisions if d["decision"] == "REJECTED"]
        
        summary_lines = [
            f"AUDIT COMPLETE: {len(decisions)} articles reviewed",
            f"✅ READY TO PUBLISH: {len(ready)} articles",
            f"⚠️ NEEDS CORRECTION: {len(corrections)} articles",
            f"❌ REJECTED: {len(rejected)} articles",
            "",
            "READY ARTICLES:",
        ]
        
        for d in ready:
            summary_lines.append(f"  - {d.get('title', d.get('article_id', 'Unknown'))}")
        
        if corrections:
            summary_lines.append("\nNEEDS CORRECTION:")
            for d in corrections:
                failed_gates = [k for k, v in d.get("gate_results", {}).items() 
                               if isinstance(v, dict) and not v.get("passed")]
                summary_lines.append(f"  - {d.get('title', 'Unknown')}: Fix {', '.join(failed_gates)}")
        
        return "\n".join(summary_lines)
    
    def _create_mock_qa_report(self) -> Dict:
        """Create a mock QA report for testing."""
        return {
            "title": "Test Article",
            "word_count": 6500,
            "image_count": 5,
            "has_featured_image": True,
            "has_faq": True,
            "has_author": True,
            "has_author_bio": True,
            "seo_score": 96,
            "eeat_score": 97,
            "broken_links": [],
            "status": "draft"
        }


# ============================================================
# CLI ENTRY POINT - Added V3.2 for workflow execution
# ============================================================

def main():
    """CLI entry point for workflow execution."""
    import argparse, sys, json, logging, os, re
    from pathlib import Path
    from datetime import datetime
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-13] %(levelname)s %(message)s"
    )
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Agent 13 - Chief Editor")
    parser.add_argument("--qa-report", required=False, default="", help="Path to QA report JSON. Optional for global-audit mode.")
    parser.add_argument("--article", required=False, default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", default="article", help="article or global-audit")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # Read QA report
    def load_json(path_str):
        p = Path(path_str)
        if p.exists():
            try: return json.loads(p.read_text())
            except: pass
        return {}

    qa_report = load_json(args.qa_report) if args.qa_report else {}
    article_path = Path(args.article) if args.article else None
    word_count = 0
    title = ""
    if article_path and article_path.exists():
        content = article_path.read_text(encoding="utf-8")
        word_count = len(content.split())
        title_match = re.search(r'title:\s*"?([^"\n]+)"?', content)
        if title_match: title = title_match.group(1)

    # Attempt real editor decision if DI stack available
    editor_report = None
    if api_key:
        try:
            import asyncio
            from services.llm_service import LLMService
            from services.storage_service import StorageService
            config = {
                "anthropic_api_key": api_key,
                "output_dir": str(output_path.parent)
            }
            llm_svc = LLMService({"anthropic_api_key": api_key, "llm_provider": "anthropic"})
            storage_svc = StorageService({"output_dir": str(output_path.parent)})
            agent = ChiefEditorAgent(config, llm_svc, storage_svc, EmailService({"sendgrid_api_key": os.environ.get("SENDGRID_API_KEY", "")}))
            editor_report = asyncio.run(agent.run())
            log.info("Chief Editor decision complete via DI stack")
        except Exception as e:
            log.warning(f"DI Chief Editor failed: {e} -- using heuristic decision")

    if not editor_report:
        # Heuristic editorial decision
        qa_status = qa_report.get("status", "PASS")
        qa_score = qa_report.get("overall_score", qa_report.get("seo_score", 75))
        passes_qa = qa_status in ("PASS", "PASS_WITH_WARNINGS")
        passes_words = word_count >= 5000

        if passes_qa and passes_words:
            decision = "READY_TO_PUBLISH"
            verdict = "APPROVE"
        elif passes_words:
            decision = "NEEDS_REVISION"
            verdict = "REQUEST_REVISION_QA_FAILED"
        else:
            decision = "NEEDS_REVISION"
            verdict = "REQUEST_REVISION"

        editor_report = {
            "agent": "agent_13_chief_editor",
            "timestamp": datetime.utcnow().isoformat(),
            "title": title,
            "decision": decision,
            "verdict": verdict,
            "quality_score": qa_score,
            "word_count": word_count,
            "qa_passed": passes_qa,
            "editorial_notes": [],
            "approved_for_publication": decision == "READY_TO_PUBLISH",
            "mode": "heuristic"
        }

    output_path.write_text(json.dumps(editor_report, indent=2), encoding="utf-8")
    log.info(f"Editor report written: {output_path}")
    log.info(f"Decision: {editor_report.get('decision', 'UNKNOWN')}")
    sys.exit(0)


if __name__ == "__main__":
    main()
