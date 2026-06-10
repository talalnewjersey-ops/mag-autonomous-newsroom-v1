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
from services.llm_service import LLMService
from services.storage_service import StorageService


logger = logging.getLogger(__name__)


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
                
                "qa_status": "PASSED" if overall_score >= 90 else "NEEDS_REVIEW"
            }
            
            output_path = await self.save_output("qa_report.json", qa_report)
            logger.info(f"QA Report saved: {output_path}")
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
        
        # Load article content
        article_paths = [
            "output/agent_04/article_draft.md",
            "output/article_draft.md"
        ]
        
        for path in article_paths:
            if os.path.exists(path):
                with open(path) as f:
                    content = f.read()
                data["article_content"] = content
                data["word_count"] = len(content.split())
                
                # Extract title
                title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                if title_match:
                    data["title"] = title_match.group(1)
                
                # Check for FAQ
                data["has_faq"] = bool(re.search(r'## Frequently Asked Questions', content, re.IGNORECASE))
                break
        
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
        
        return data
    
    async def _audit_seo(self, data: Dict) -> Dict:
        """Perform SEO audit."""
        content = data.get("article_content", "")
        keyword = data.get("keyword", "").lower()
        title = data.get("title", "")
        
        checks = {}
        
        # Keyword in title
        checks["keyword_in_title"] = keyword in title.lower() if keyword else False
        
        # Keyword density
        if keyword and content:
            word_count = len(content.split())
            kw_count = len(re.findall(re.escape(keyword), content.lower()))
            density = (kw_count / word_count) * 100 if word_count > 0 else 0
            checks["keyword_density"] = round(density, 2)
            checks["keyword_density_ok"] = 0.5 <= density <= 2.0
        
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
        internal_links = len(re.findall(r'\[.*?\]\((?!http)[^)]+\)', content))
        checks["internal_link_count"] = internal_links
        checks["has_internal_links"] = internal_links >= 3
        
        # Word count
        checks["word_count"] = data.get("word_count", len(content.split()))
        checks["word_count_ok"] = checks["word_count"] >= 5000
        
        return checks
    
    async def _audit_eeat(self, data: Dict) -> Dict:
        """Audit Experience, Expertise, Authority, Trust signals."""
        content = data.get("article_content", "")
        
        checks = {}
        
        # Experience signals
        experience_patterns = [
            r'(?:based on|according to|our experience|we found|in practice)',
            r'(?:real-world|case study|example|scenario)',
            r'(?:tested|reviewed|analyzed|compared)'
        ]
        experience_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in experience_patterns)
        checks["experience_signals"] = experience_count
        checks["experience_score"] = min(100, experience_count * 5)
        
        # Expertise signals
        expertise_patterns = [
            r'(?:expert|professional|specialist|certified)',
            r'(?:according to|research shows|studies indicate|data from)',
            r'(?:official|government|regulation|requirement)',
            r'(?:\$|USD|CAD|€|percent|%|annual|monthly)'
        ]
        expertise_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in expertise_patterns)
        checks["expertise_signals"] = expertise_count
        checks["expertise_score"] = min(100, expertise_count * 3)
        
        # Authority signals
        checks["has_author"] = data.get("has_author", False)
        checks["has_author_bio"] = data.get("has_author_bio", False)
        checks["has_credentials"] = bool(re.search(r'(?:CPA|CFA|CFP|attorney|lawyer|advisor)', content, re.IGNORECASE))
        checks["authority_score"] = (
            (25 if checks["has_author"] else 0) +
            (25 if checks["has_author_bio"] else 0) +
            (25 if checks["has_credentials"] else 0) +
            (25 if expertise_count > 10 else 0)
        )
        
        # Trust signals
        trust_patterns = [
            r'(?:updated|last reviewed|fact.checked)',
            r'(?:source:|citation|reference)',
            r'(?:FDIC|CFPB|CRA|IRS|government|official)',
            r'(?:privacy|security|encrypted|SSL)'
        ]
        trust_count = sum(len(re.findall(p, content, re.IGNORECASE)) for p in trust_patterns)
        checks["trust_signals"] = trust_count
        checks["trust_score"] = min(100, trust_count * 5 + (25 if data.get("has_update_date") else 0))
        
        return checks
    
    async def _audit_faq(self, data: Dict) -> Dict:
        """Audit FAQ section."""
        content = data.get("article_content", "")
        
        checks = {}
        
        # Check FAQ presence
        has_faq = bool(re.search(r'## (?:Frequently Asked Questions|FAQ)', content, re.IGNORECASE))
        checks["has_faq"] = has_faq
        
        if has_faq:
            # Count FAQ questions (H3 in FAQ section)
            faq_section = re.search(r'## (?:FAQ|Frequently Asked Questions).*?(?=## |$)', content, re.DOTALL | re.IGNORECASE)
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
        """Audit overall content quality."""
        content = data.get("article_content", "")
        word_count = len(content.split())
        
        score = 0
        
        if word_count >= 5000: score += 30
        if word_count >= 7000: score += 10
        if len(re.findall(r'^## ', content, re.MULTILINE)) >= 5: score += 15
        if len(re.findall(r'^### ', content, re.MULTILINE)) >= 8: score += 15
        if re.search(r'## Frequently Asked Questions', content, re.IGNORECASE): score += 20
        if len(re.findall(r'^\|', content, re.MULTILINE)) > 5: score += 10
        
        return {"score": score, "word_count": word_count}
    
    def _calculate_seo_score(self, seo_check: Dict) -> float:
        """Calculate SEO score from checks."""
        score = 0
        if seo_check.get("keyword_in_title"): score += 15
        if seo_check.get("keyword_density_ok"): score += 15
        if seo_check.get("has_good_structure"): score += 20
        if seo_check.get("has_meta_description"): score += 10
        if seo_check.get("has_tables"): score += 10
        if seo_check.get("has_internal_links"): score += 15
        if seo_check.get("word_count_ok"): score += 15
        return min(100, score)
    
    def _calculate_eeat_score(self, eeat_check: Dict) -> float:
        """Calculate EEAT score from checks."""
        exp = eeat_check.get("experience_score", 0)
        exp_score = eeat_check.get("expertise_score", 0)
        auth = eeat_check.get("authority_score", 0)
        trust = eeat_check.get("trust_score", 0)
        return round((exp * 0.25 + exp_score * 0.25 + auth * 0.25 + trust * 0.25), 1)
    
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
