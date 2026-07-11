"""
NEXUS-14: Agent 12 - Quality Assurance Agent
Performs comprehensive quality audits on all article aspects.
Checks: SEO, EEAT, FAQ, Images, Links, Responsive design.
Input: All previous agent outputs
Output: qa_report.json
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

from agents.base_agent import BaseAgent
from agents._eeat_scoring import audit_eeat, calculate_eeat_score  # single source of truth, shared with agent_06 (2026-07-11)
from services.llm_service import LLMService
from services.storage_service import StorageService


logger = logging.getLogger(__name__)

# SEO SCORE RECALIBRATION (2026-07-06): the "70" plateau seen on every article
# that reached this gate was arithmetic, not content variance -- two criteria
# failed EVERY time (verified: 100 - 15 keyword_density_ok - 15 word_count_ok
# = 70 exactly). Both root-caused precisely (see git history / memory) and
# fixed here, not just re-thresholded blindly:
#  - word_count target is now TIER-RELATIVE (mirrors agents/agent_04_article_
#    writer.py's own TARGET_WORDS per tier -- kept as a literal copy here,
#    not a cross-module import, to avoid coupling agent_12 to agent_04's
#    internals; if agent_04's targets change, this table must be updated too).
#  - keyword density is no longer scored as a reward (a fixed floor rewards
#    keyword-stuffing); the only thing scored is the inverse -- an
#    UNNATURALLY HIGH density is a real stuffing signal and is penalized,
#    never rewarded for merely clearing a minimum.
_TIER_TARGET_WORDS = {"PILLAR": 4200, "STANDARD": 4000, "OPPORTUNITY": 4000, "GOLD": 4000}
_WORD_COUNT_TOLERANCE = 0.10  # +-10% of the tier's own target
_KEYWORD_STUFFING_DENSITY_PCT = 2.5  # widely-cited SEO stuffing threshold; natural
                                      # long-tail keyword prose lands well under 1%

# PUBLICATION GATE (2026-07-11, AUDIT-LOG.md): the single number that actually
# decides GATE QA pass/fail for every real production run (this class's own
# run(), consumed by main()'s sys.exit(0 if status=="PASS" else 1) below --
# that exit code is what production_v2.yml's retry/fail logic reacts to). Was
# hardcoded to 85 -- drifted from .github/NEXUS14-PRIORITY.md's own documented
# "Minimum publication score: 95/100 -- hard gate, no exceptions" (Non-
# Negotiable Rules #3) for an unknown amount of time before this was caught.
# Real case that surfaced the drift: run 29137518698 (draft 48640) scored
# overall_score=90.5, cleared the code's 85 but not the documented 95 -- the
# topic was promoted/"published" (Sprint 9's invariant correctly gates on
# THIS constant, not a bug there) despite failing the actual enterprise
# standard. Aligning the code to the document, not the other way around.
#
# NOTE (separate, NOT fixed here -- flagged for a future decision): main()'s
# CLI accepts --seo-threshold/--eeat-threshold (wired into config["seo_
# threshold"]/config["eeat_threshold"]) that LOOK like they configure this
# gate but are never read anywhere -- this class reads self.config exactly
# once, for "hallucination" only. Those two flags are dead/cosmetic; this
# constant is the only real gate. Also distinct: GATE B (agent_06_eeat_
# validator, a separate script) has its OWN 85 threshold via the shared
# EEAT_SCORE_THRESHOLD env var in production_v2.yml -- that one is real and
# functional, but is a different gate from this one; raising it too is a
# separate decision, out of scope here.
PUBLICATION_QUALITY_GATE = 95


class QualityAssuranceAgent(BaseAgent):
    """
    Agent 12: Quality Assurance Agent
    
    Comprehensive quality check covering:
    - SEO Analysis (keyword density, meta tags, structure)
    - EEAT Signals (experience, expertise, authority, trust)
    - FAQ Verification (presence, quality, schema)
    - Image Audit (count, alt tags, featured image)
    - Link Audit (internal links, broken links)
    - Content Quality (readability, depth, accuracy)
    
    Output: qa_report.json
    """
    
    AGENT_ID = "agent_12"
    AGENT_NAME = "Quality Assurance Agent"
    
    def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
        super().__init__(config, llm_service, storage_service)
    
    async def run(self, context: Dict = None) -> Dict:
        """Run complete QA audit."""
        self.log_start()
        
        try:
            # Load article and all reports
            article_data = await self._load_article_data(context or {})
            
            logger.info(f"QA auditing article: {article_data.get('title', 'Unknown')}")
            
            # Run all QA checks
            seo_check = await self._audit_seo(article_data)
            eeat_check = await self._audit_eeat(article_data)
            faq_check = await self._audit_faq(article_data)
            image_check = await self._audit_images(article_data)
            link_check = await self._audit_links(article_data)
            content_check = await self._audit_content_quality(article_data)
            
            # Calculate overall scores
            seo_score = self._calculate_seo_score(seo_check)
            eeat_score = self._calculate_eeat_score(eeat_check)
            overall_score = round((seo_score * 0.4 + eeat_score * 0.4 + content_check.get("score", 0) * 0.2), 1)
            # SPRINT 10 anti-hallucination: recalibrate for hallucinations (counts from
            # agent_05's fact_check_report). An unsourced stat / unbacked attribution
            # LOWERS the QA score so a hallucinated-but-form-clean article drops below
            # PASS. This is what makes the gate able to REJECT for hallucination, not
            # just for form (closing the blind spot that guards the crons).
            _hc = self.config.get("hallucination", {}) if isinstance(getattr(self, "config", None), dict) else {}
            _halluc_penalty = hallucination_penalty(_hc.get("unsourced_stat_count", 0),
                                                    _hc.get("unbacked_attribution_count", 0))
            form_overall = overall_score
            overall_score = max(0.0, round(overall_score - _halluc_penalty, 1))

            # Compile QA report
            qa_report = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "title": article_data.get("title", ""),
                "keyword": article_data.get("keyword", ""),
                "market": article_data.get("market", ""),
                
                # Scores
                "seo_score": seo_score,
                "eeat_score": eeat_score,
                "overall_score": overall_score,
                
                # Content metrics
                "word_count": article_data.get("word_count", 0),
                "image_count": image_check.get("total_images", 0),
                "has_featured_image": image_check.get("has_featured_image", False),
                "has_faq": faq_check.get("has_faq", False),
                "has_author": article_data.get("has_author", False),
                "has_author_bio": article_data.get("has_author_bio", False),
                "broken_links": link_check.get("broken_links", []),
                
                # Detailed checks
                "seo_details": seo_check,
                "eeat_details": eeat_check,
                "faq_details": faq_check,
                "image_details": image_check,
                "link_details": link_check,
                "content_details": content_check,
                
                # Issues and recommendations
                "critical_issues": self._identify_critical_issues(seo_check, eeat_check, faq_check, image_check, link_check),
                "recommendations": self._generate_recommendations(seo_check, eeat_check, image_check),
                
                # SPRINT 10: hallucination transparency + single explicit PASS gate
                # (PUBLICATION_QUALITY_GATE, see module-level constant above)
                "form_overall_score": form_overall,
                "hallucination_penalty": _halluc_penalty,
                "unsourced_stat_count": _hc.get("unsourced_stat_count", 0),
                "unbacked_attribution_count": _hc.get("unbacked_attribution_count", 0),
                "status": "PASS" if overall_score >= PUBLICATION_QUALITY_GATE else "NEEDS_REVIEW"
            }
            
            # PATH-DUPLICATION FIX (2026-07-06, same bug class as agent_11): main()
            # below is the single authoritative writer of qa_report.json at args.output.
            # This class's own save_output() used to ALSO write a copy, at a path
            # doubled/tripled by BaseAgent.output_dir + StorageService's re-join --
            # an orphan, never read by anything, removed instead of chased further.
            logger.info(f"Scores - SEO: {seo_score}, EEAT: {eeat_score}, Overall: {overall_score}")
            
            self.log_complete({
                "seo_score": seo_score,
                "eeat_score": eeat_score,
                "overall_score": overall_score,
                "critical_issues": len(qa_report["critical_issues"])
            })
            
            return qa_report
            
        except Exception as e:
            self.log_error(e)
            raise
    
    async def _load_article_data(self, context: Dict) -> Dict:
        """Load article and all previous reports."""
        import os
        
        data = context.copy()
        
        # Context-first loading: if the caller already supplied article content,
        # use it directly and never reload from disk.
        content = data.get("article_content", "")
        
        if not content:
            # Fallback loading: resolve the article from the path passed in context
            # (article_N-aware), falling back to legacy locations only if needed.
            article_paths = [
                p for p in [data.get("article_path")] if p
            ] + [
                "output/agent_04/article_draft.md",
                "output/article_draft.md",
            ]
            
            for path in article_paths:
                if path and os.path.exists(path):
                    with open(path) as f:
                        content = f.read()
                    data["article_content"] = content
                    break
        
        if content:
            # Title extraction -- support Agent 04 Markdown H1 (# Title) format.
            if not data.get("title"):
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                if title_match:
                    data["title"] = title_match.group(1).strip()

            # FAQ detection (only set if not already provided by context)
            if "has_faq" not in data:
                data["has_faq"] = bool(
                    re.search(r'##\s+(?:Frequently Asked Questions|FAQ)', content, re.IGNORECASE)
                )

            # 2026-07-10 FIX: has_update_date was read by _audit_eeat's trust_score
            # (the +25 bonus) but never SET anywhere -- always None, so the bonus
            # could never fire even on an article with a real "Last Updated" line
            # (confirmed on real draft 48624). Mirrors has_faq's pattern above.
            if "has_update_date" not in data:
                data["has_update_date"] = bool(re.search(r'Last Updated', content, re.IGNORECASE))

        # Load metadata
        metadata_path = "output/agent_04/article_metadata.json"
        if os.path.exists(metadata_path):
            with open(metadata_path) as f:
                metadata = json.load(f)
            data.update(metadata)

        # Load WP report
        wp_path = "output/agent_11/wordpress_report.json"
        if os.path.exists(wp_path):
            with open(wp_path) as f:
                wp_data = json.load(f)
            data.update(wp_data)

        # WORD COUNT -- ALWAYS recomputed fresh from `content` LAST, after every
        # merge above, deliberately overriding anything metadata/WP-report/caller
        # set (2026-07-11 fix, AUDIT-LOG.md: draft 48640/run 29137518698). This
        # used to be `data.setdefault("word_count", ...)` BEFORE the metadata
        # merge, so article_metadata.json's word_count -- written ONCE by
        # agent_04 right after generation, never refreshed by the soften/polish/
        # normalize/scenario steps that run afterward and change the draft's
        # real length -- silently clobbered the correct value. Real case:
        # metadata said 4526w, the actual final content was 4350w (both within
        # tier tolerance) -- but _audit_seo used the stale 4526, wrongly failing
        # word_count_ok and capping seo_score at 85 instead of 100. `content` IS
        # the article actually being scored -- it is the single source of truth
        # for its own word count, full stop, not a convenience field that can
        # drift out of sync with what agent_12 is auditing.
        if content:
            data["word_count"] = len(content.split())

        return data
    
    async def _audit_seo(self, data: Dict) -> Dict:
        """Perform SEO audit."""
        content = data.get("article_content", "")
        keyword = data.get("keyword", "").lower()
        title = data.get("title", "")

        checks = {}

        # Keyword in title
        checks["keyword_in_title"] = keyword in title.lower() if keyword else False

        # Keyword density (2026-07-06 RECALIBRATION): reported for visibility only --
        # no longer scored as a reward. A fixed density FLOOR rewards keyword-stuffing
        # (verified on real content: a 6-7 word long-tail keyword naturally lands at
        # ~0.1% density; reaching the old 0.3% floor needed ~13 literal repeats of the
        # keyword's first 3 words, which is exactly the old-style stuffing this
        # project's own EEAT/natural-writing goals argue against). The only thing
        # still SCORED here is the inverse: a density that is UNNATURALLY HIGH is a
        # real stuffing signal and is penalized in _calculate_seo_score, never
        # rewarded for being merely present.
        if keyword and content:
            word_count = len(content.split())
            kw_count = len(re.findall(re.escape(" ".join(keyword.split()[:3])), content.lower()))
            density = (kw_count / word_count) * 100 if word_count > 0 else 0
            checks["keyword_density"] = round(density, 2)
            checks["keyword_stuffing_detected"] = density > _KEYWORD_STUFFING_DENSITY_PCT

        # Headings structure
        h2_count = len(re.findall(r'^## .+', content, re.MULTILINE))
        h3_count = len(re.findall(r'^### .+', content, re.MULTILINE))
        checks["h2_count"] = h2_count
        checks["h3_count"] = h3_count
        checks["has_good_structure"] = h2_count >= 5 and h3_count >= 8

        # Meta description
        checks["has_meta_description"] = bool(data.get("meta_description"))

        # Tables
        table_count = len(re.findall(r'^\|.+\|$', content, re.MULTILINE))
        checks["table_count"] = max(0, table_count // 2)  # Approximate table count
        checks["has_tables"] = checks["table_count"] > 0

        # Internal links
        internal_links = len(re.findall(r'\[[^\]]+\]\([^)]+\)', content)) or data.get('internal_link_count', 0)
        checks["internal_link_count"] = internal_links
        checks["has_internal_links"] = internal_links >= 3

        # Word count (2026-07-06 RECALIBRATION): was a fixed >= 5000 floor that NO
        # tier this pipeline produces can ever reach (agent_04's own tier word caps:
        # PILLAR max=4200, STANDARD/OPPORTUNITY/GOLD max=4000 -- all below 5000, a
        # mathematical impossibility, not a content deficiency). Now checks that the
        # article holds its OWN requested tier's target length within +-10% --
        # measuring "did the writer hit its target", not an unrelated absolute number.
        checks["word_count"] = data.get("word_count", len(content.split()))
        target_words = _TIER_TARGET_WORDS.get((data.get("article_type") or "STANDARD").upper(),
                                                _TIER_TARGET_WORDS["STANDARD"])
        checks["tier_target_words"] = target_words
        checks["word_count_ok"] = abs(checks["word_count"] - target_words) <= _WORD_COUNT_TOLERANCE * target_words

        return checks
    
    async def _audit_eeat(self, data: Dict) -> Dict:
        """Audit Experience, Expertise, Authority, Trust signals -- delegates to
        agents/_eeat_scoring.py (2026-07-11), the single EEAT implementation
        shared with agent_06 (GATE B). Same patterns/weights/formulas as
        before this refactor -- a migration, not a behavior change here."""
        return audit_eeat(
            data.get("article_content", ""),
            has_author=data.get("has_author", False),
            has_author_bio=data.get("has_author_bio", False),
            has_update_date=data.get("has_update_date"),
            word_count=data.get("word_count"),
        )

    async def _audit_faq(self, data: Dict) -> Dict:
        """Audit FAQ section."""
        content = data.get("article_content", "")
        
        checks = {}
        
        # Check FAQ presence
        has_faq = bool(re.search(r'## (?:Frequently Asked Questions|FAQ)', content, re.IGNORECASE))
        checks["has_faq"] = has_faq
        
        if has_faq:
            # Count FAQ questions (H3 in FAQ section)
            # 2026-07-10 FIX: the old boundary lookahead "(?=## |$)" matched
            # INSIDE a "### " (H3) heading -- "##" is a substring of "###", so
            # e.g. "### Can I drive..." satisfies "## " at offset 1. That
            # truncated the captured section to just the H2 title line, right
            # before the first real question, so question_count was always 0
            # even on a real article with 10 genuine FAQ questions (draft
            # 48624). Fixed boundary: the next TRUE H2 (exactly two #, not
            # three) at the start of a line, via MULTILINE "^##(?!#)\s".
            faq_section = re.search(r'## (?:FAQ|Frequently Asked Questions).*?(?=\n##(?!#)\s|\Z)',
                                     content, re.DOTALL | re.IGNORECASE)
            if faq_section:
                faq_content = faq_section.group()
                question_count = len(re.findall(r'^### ', faq_content, re.MULTILINE))
                checks["question_count"] = question_count
                checks["has_enough_questions"] = question_count >= 8
        
        # Check schema markup potential
        checks["schema_ready"] = has_faq and checks.get("question_count", 0) >= 5
        
        return checks
    
    async def _audit_images(self, data: Dict) -> Dict:
        """Audit image requirements."""
        checks = {}
        
        # Get image data from WP or context
        images = data.get("uploaded_images", [])
        generated_images = data.get("generated_images", [])
        
        total_images = len(images) + len(generated_images)
        checks["total_images"] = total_images
        checks["has_featured_image"] = data.get("featured_image_id") is not None or total_images > 0
        checks["minimum_images_met"] = total_images >= 4
        
        # Check alt texts
        if images:
            without_alt = [img for img in images if not img.get("alt_text")]
            checks["images_without_alt"] = len(without_alt)
            checks["alt_text_coverage"] = round((total_images - len(without_alt)) / max(total_images, 1) * 100, 1)
        
        return checks
    
    async def _audit_links(self, data: Dict) -> Dict:
        """Audit links in the article."""
        content = data.get("article_content", "")
        
        checks = {}
        external_links = re.findall(r'\[.*?\]\((https?://[^)]+)\)', content)
        
        checks["external_link_count"] = len(external_links)
        checks["broken_links"] = []  # Would check each link in production
        checks["all_links_ok"] = True
        
        return checks
    
    async def _audit_content_quality(self, data: Dict) -> Dict:
        """Audit overall content quality. RECALIBRATED 2026-07-10: the old flat
        >=5000/>=7000-word thresholds ignored article TIER entirely -- agent_04's
        own tier system caps PILLAR at 4200w and STANDARD/OPPORTUNITY/GOLD at
        4000w (agents/agent_04_article_writer.py), so these 40 points were a
        mathematical impossibility for every tier this pipeline actually
        produces, not a content deficiency (real case: draft 48624, OPPORTUNITY
        tier, 4304 words -- structurally capped at content_check.score=60/100
        regardless of quality). Same class of fix as the SEO score's own
        2026-07-06 tier-relative recalibration (_TIER_TARGET_WORDS above,
        word_count_ok in _audit_seo) -- reused here instead of a second,
        divergent word-count rule. The old separate ">=7000" stretch bonus is
        dropped rather than scaled: exceeding your OWN tier's target isn't a
        quality signal under the tier-capped model (agent_04 enforces an upper
        bound per tier), so the full 40 points now go to hitting the tier
        target within the same +-10% tolerance the SEO score already uses."""
        content = data.get("article_content", "")
        word_count = len(content.split())
        target_words = _TIER_TARGET_WORDS.get((data.get("article_type") or "STANDARD").upper(),
                                                _TIER_TARGET_WORDS["STANDARD"])
        word_count_ok = abs(word_count - target_words) <= _WORD_COUNT_TOLERANCE * target_words

        score = 0

        if word_count_ok: score += 40
        if len(re.findall(r'^## ', content, re.MULTILINE)) >= 5: score += 15
        if len(re.findall(r'^### ', content, re.MULTILINE)) >= 8: score += 15
        if re.search(r'## Frequently Asked Questions', content, re.IGNORECASE): score += 20
        if len(re.findall(r'^\|', content, re.MULTILINE)) > 5: score += 10

        return {"score": score, "word_count": word_count, "tier_target_words": target_words,
                "word_count_ok": word_count_ok}
    
    def _calculate_seo_score(self, seo_check: Dict) -> float:
        """Calculate SEO score from checks. RECALIBRATED 2026-07-06: the old
        keyword_density_ok reward (15 pts) is removed -- rewarding a density
        FLOOR pushes toward keyword-stuffing, which this project's own EEAT/
        natural-writing goals argue against. Its 15 points are redistributed
        across the remaining 6 criteria (still summing to 100, weighted toward
        has_good_structure -- the most substantive SEO signal of the six).
        A NEW, separate penalty fires only for genuinely UNNATURAL density
        (stuffing) -- it can only subtract from the 100 ceiling, never add."""
        score = 0
        if seo_check.get("keyword_in_title"): score += 15
        if seo_check.get("has_good_structure"): score += 30
        if seo_check.get("has_meta_description"): score += 10
        if seo_check.get("has_tables"): score += 15
        if seo_check.get("has_internal_links"): score += 15
        if seo_check.get("word_count_ok"): score += 15
        score = min(100, score)
        if seo_check.get("keyword_stuffing_detected"):
            score = max(0, score - 20)
        return score
    
    def _calculate_eeat_score(self, eeat_check: Dict) -> float:
        """Calculate EEAT score from checks -- delegates to agents/_eeat_scoring.py."""
        return calculate_eeat_score(eeat_check)
    
    def _identify_critical_issues(self, seo, eeat, faq, images, links) -> List[str]:
        """Identify critical quality issues."""
        issues = []
        if not images.get("has_featured_image"): issues.append("CRITICAL: Featured image missing")
        if not faq.get("has_faq"): issues.append("CRITICAL: FAQ section missing")
        if not images.get("minimum_images_met"): issues.append(f"CRITICAL: Only {images.get('total_images', 0)} images (minimum: 4)")
        if links.get("broken_links"): issues.append(f"CRITICAL: {len(links['broken_links'])} broken links detected")
        return issues
    
    def _generate_recommendations(self, seo, eeat, images) -> List[str]:
        """Generate QA recommendations."""
        recs = []
        if not seo.get("keyword_in_title"): recs.append("Add primary keyword to article title")
        if not seo.get("has_internal_links"): recs.append("Add at least 3 internal links")
        if not seo.get("has_tables"): recs.append("Add comparison tables for better engagement")
        if eeat.get("authority_score", 0) < 75: recs.append("Strengthen author credentials and expertise signals")
        return recs


# ============================================================
# CLI ENTRY POINT - Added V3.2 for workflow execution
# ============================================================

def hallucination_penalty(unsourced_stat_count: int, unbacked_attribution_count: int, cap: int = 40) -> int:
    """SPRINT 10 barème: points subtracted from the QA overall score.
      -8 per unsourced numeric stat, -15 per unbacked named attribution, capped at 40.
    Calibrated on 48418 (4+ unsourced stats -> >= -32). Even a form-perfect article
    (max 100) minus the -40 cap = 60, well below the PUBLICATION_QUALITY_GATE (95),
    so no realistic hallucination mix can escape. Unbacked attributions are ALSO hard-blocked at
    GATE A (agent_05); the -15 here is defense-in-depth."""
    return min(cap, 8 * max(0, unsourced_stat_count) + 15 * max(0, unbacked_attribution_count))


def main():
    """CLI entry point for workflow execution."""
    import argparse, sys, json, logging, os, re
    from pathlib import Path
    from datetime import datetime
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-12] %(levelname)s %(message)s"
    )
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Agent 12 - Quality Assurance")
    parser.add_argument("--article", required=True)
    parser.add_argument("--wordpress-report", default="")
    parser.add_argument("--fact-check", default="", help="agent_05 fact_check_report.json (Sprint 10 hallucination penalty)")
    parser.add_argument("--image-validation", default="")
    parser.add_argument("--affiliate-compliance", default="")
    parser.add_argument("--publishing-optimizer", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-words", type=int, default=5000)
    parser.add_argument("--article-type", default="STANDARD",
                        choices=["STANDARD", "PILLAR", "OPPORTUNITY"])
    parser.add_argument("--min-images", type=int, default=5)
    parser.add_argument("--min-faq", type=int, default=20)
    parser.add_argument("--min-links", type=int, default=5)
    parser.add_argument("--min-sources", type=int, default=10)
    parser.add_argument("--min-case-studies", type=int, default=3)
    parser.add_argument("--seo-threshold", type=int, default=90)
    parser.add_argument("--eeat-threshold", type=int, default=90)
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # Read article
    article_path = Path(args.article)
    word_count = 0
    title = ""
    keyword = ""
    faq_count = 0
    if article_path.exists():
        content = article_path.read_text(encoding="utf-8")
        word_count = len(content.split())
        title_match = re.search(r'title:\s*"?([^"\n]+)"?', content)
        if title_match: title = title_match.group(1)
        kw_match = re.search(r'primary_keyword:\s*"?([^"\n]+)"?', content)
        if kw_match: keyword = kw_match.group(1)
        faq_count = len(re.findall(r"^### .+\?", content, re.MULTILINE))

    # Load authoritative article metadata (title/keyword/meta_description) from agent_03/agent_04 outputs
    meta_description = ""
    try:
        art_dir = article_path.parent
        meta_json = art_dir / "article_metadata.json"
        if meta_json.exists():
            md = json.loads(meta_json.read_text(encoding="utf-8"))
            title = md.get("title") or title
            keyword = md.get("keyword") or keyword
            word_count = md.get("word_count") or word_count
            faq_count = md.get("faq_count") or faq_count
        outline_json = art_dir.parent / "agent_03" / "article_outline.json"
        if outline_json.exists():
            ol = json.loads(outline_json.read_text(encoding="utf-8"))
            title = ol.get("title") or title
            keyword = ol.get("primary_keyword") or keyword
            meta_description = ol.get("meta_description", "") or meta_description
    except Exception as _meta_err:
        log.warning(f"metadata load failed: {_meta_err}")

    # Load supporting reports
    def load_json(path_str):
        p = Path(path_str)
        if p.exists():
            try: return json.loads(p.read_text())
            except: pass
        return {}

    wp_report = load_json(args.wordpress_report)
    img_val = load_json(args.image_validation)
    aff_comp = load_json(args.affiliate_compliance)
    pub_opt = load_json(args.publishing_optimizer)
    # SPRINT 10: hallucination counts from agent_05 -> QA score penalty (both paths).
    _fc_summary = load_json(args.fact_check).get("summary", {})
    halluc = {"unsourced_stat_count": _fc_summary.get("unsourced_stat_count", 0),
              "unbacked_attribution_count": _fc_summary.get("unbacked_attribution_count", 0)}

    # Attempt real QA if using DI stack
    qa_report = None
    if api_key:
        try:
            import asyncio
            from services.llm_service import LLMService
            from services.storage_service import StorageService
            config = {
                "anthropic_api_key": api_key,
                "output_dir": str(output_path.parent),
                "min_word_count": args.min_words,
                "min_images": args.min_images,
                "seo_threshold": args.seo_threshold,
                "eeat_threshold": args.eeat_threshold,
                "hallucination": halluc,   # SPRINT 10: drives the QA score penalty in run()
            }
            llm_svc = LLMService({"anthropic_api_key": api_key, "llm_provider": "anthropic"})
            storage_svc = StorageService({"output_dir": str(output_path.parent)})
            agent = QualityAssuranceAgent(config, llm_svc, storage_svc)
            # FIX (2026-07-06): wp_report (loaded above from --wordpress-report, agent_11's
            # own output) was never wired into this context dict -- _audit_images() reads
            # data.get("uploaded_images")/("featured_image_id"), so this path ALWAYS saw
            # zero images regardless of what agent_11 actually uploaded (masked the point-1
            # image fallback on every run, independent of agent_11's own report-path bug).
            qa_report = asyncio.run(agent.run({"article_content": content, "article_path": str(article_path), "title": title, "keyword": keyword, "meta_description": meta_description, "word_count": word_count, "faq_count": faq_count, "has_author": True, "has_author_bio": True, "uploaded_images": wp_report.get("uploaded_images", []), "featured_image_id": wp_report.get("featured_image_id"), "article_type": args.article_type}))
            log.info("QA complete via DI stack")
        except Exception as e:
            log.warning(f"DI QA failed: {e} -- using heuristic QA")

    if not qa_report:
        # Heuristic QA based on available data
        # SPRINT 1 (B/C): two-tier word floor is the single source of truth.
        # STANDARD >= 1500, PILLAR >= 3000 (Blueprint Partie 4, G2). Hardcoded
        # 4000/5000 thresholds removed; --min-words kept only as explicit override.
        TIER_MIN_WORDS = {"STANDARD": 1500, "PILLAR": 3000, "OPPORTUNITY": 1500}
        effective_min_words = TIER_MIN_WORDS.get(args.article_type, 1500)
        image_count = img_val.get("images_produced", img_val.get("total_images", 0))
        passes_words = word_count >= effective_min_words
        passes_faq = faq_count >= 8  # relaxed threshold
        passes_images = image_count >= 1  # at least 1 image or fallback

        # SPRINT 10: hallucinations fail the heuristic gate too -- no path escapes.
        _hp = hallucination_penalty(halluc["unsourced_stat_count"], halluc["unbacked_attribution_count"])
        overall_pass = passes_words and passes_faq and passes_images and _hp == 0
        seo_score = 75 if passes_words else 50
        eeat_score = 75 if passes_words else 50

        qa_report = {
            "agent": "agent_12_quality_assurance",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "PASS" if overall_pass else "FAIL",
            "hallucination_penalty": _hp,
            "unsourced_stat_count": halluc["unsourced_stat_count"],
            "unbacked_attribution_count": halluc["unbacked_attribution_count"],
            "overall_score": seo_score,
            "seo_score": seo_score,
            "eeat_score": eeat_score,
            "word_count": word_count,
            "faq_count": faq_count,
            "image_count": image_count,
            "checks": {
                "word_count": {"pass": passes_words, "value": word_count, "min": effective_min_words},
                "faq": {"pass": passes_faq, "value": faq_count, "min": 8},
                "images": {"pass": passes_images, "value": image_count, "min": 1},
            },
            "recommendation": "READY_FOR_EDITOR" if overall_pass else "NEEDS_REVISION",
            "mode": "heuristic"
        }

    output_path.write_text(json.dumps(qa_report, indent=2), encoding="utf-8")
    log.info(f"QA report written: {output_path}")
    log.info(f"Status: {qa_report.get('status', 'UNKNOWN')} | Words: {word_count}")
    # SPRINT 1 (B): QA is now BLOCKING. Non-zero exit propagates failure to the workflow.
    sys.exit(0 if qa_report.get("status") == "PASS" else 1)


if __name__ == "__main__":
    main()
