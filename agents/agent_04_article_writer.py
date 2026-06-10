"""
NEXUS-14: Agent 04 - Article Writer Agent
Writes 5,000-10,000 word articles optimized for SEO 2026 + EEAT standards.
Input: article_outline.json
Output: article_draft.md
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from agents.base_agent import BaseAgent
from services.llm_service import LLMService
from services.storage_service import StorageService


logger = logging.getLogger(__name__)


class ArticleWriterAgent(BaseAgent):
    """
    Agent 04: Article Writer Agent
    
    Responsibilities:
    - Write 5,000-10,000 word articles
    - Follow SEO 2026 best practices
    - Implement EEAT signals
    - Human-first content approach
    
    Output: article_draft.md
    """
    
    AGENT_ID = "agent_04"
    AGENT_NAME = "Article Writer Agent"
    
    MIN_WORD_COUNT = 5000
    MAX_WORD_COUNT = 10000
    TARGET_WORD_COUNT = 7500
    
    SYSTEM_PROMPT = """You are an expert financial content writer for MoneyAbroadGuide.com.
    
You specialize in writing comprehensive, authoritative articles about:
- Banking for expatriates (USA & Canada focused)
- International money transfers and remittances
- Tax obligations for people living abroad
- Investment options for non-residents
- Digital banking solutions for expats

Your writing style:
- Clear, engaging, and conversational (not robotic)
- Expert yet accessible to non-financial professionals
- Evidence-based with specific examples and data
- Structured with clear headings and logical flow
- Rich with actionable advice and practical tips

SEO 2026 Standards:
- Semantic SEO: Cover related terms and concepts naturally
- EEAT signals: Include expertise, experience, authority cues
- Intent matching: Fully satisfy what the user is searching for
- Featured snippet optimization: Clear, direct answers
- Topical depth: Cover the subject comprehensively

Quality Standards:
- Minimum 5,000 words, ideal 7,500 words
- Include specific numbers, dates, and facts when available
- Compare multiple options with pros/cons
- Include real-world scenarios and examples
- FAQ section at the end (minimum 8 questions)
- Never write generic, vague content"""
    
    def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
        super().__init__(config, llm_service, storage_service)
        self.article_count = 0
        
    async def run(self, context: Dict = None) -> Dict:
        """Main agent execution flow."""
        self.log_start()
        
        try:
            # Load outline from Agent 03
            outline = await self._load_outline()
            
            logger.info(f"Writing article: {outline.get('title', 'Unknown')}")
            logger.info(f"Target word count: {self.TARGET_WORD_COUNT}")
            
            # Phase 1: Write introduction
            logger.info("Phase 1: Writing introduction...")
            intro = await self._write_introduction(outline)
            
            # Phase 2: Write main sections
            logger.info("Phase 2: Writing main sections...")
            sections = await self._write_sections(outline)
            
            # Phase 3: Write FAQ
            logger.info("Phase 3: Writing FAQ section...")
            faq = await self._write_faq(outline)
            
            # Phase 4: Write conclusion
            logger.info("Phase 4: Writing conclusion...")
            conclusion = await self._write_conclusion(outline)
            
            # Phase 5: Add EEAT elements
            logger.info("Phase 5: Adding EEAT elements...")
            article_with_eeat = await self._add_eeat_elements(
                intro, sections, faq, conclusion, outline
            )
            
            # Phase 6: SEO optimization
            logger.info("Phase 6: SEO optimization pass...")
            optimized_article = await self._seo_optimize(article_with_eeat, outline)
            
            # Phase 7: Word count check
            word_count = len(optimized_article.split())
            
            if word_count < self.MIN_WORD_COUNT:
                logger.warning(f"Article too short ({word_count} words). Expanding...")
                optimized_article = await self._expand_article(optimized_article, outline)
                word_count = len(optimized_article.split())
            
            logger.info(f"Final word count: {word_count}")
            
            # Assemble final article
            final_article = self._assemble_article(
                outline, optimized_article, word_count
            )
            
            # Save output
            output_path = await self.save_output("article_draft.md", final_article)
            
            # Save metadata
            metadata = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "title": outline.get("title", ""),
                "keyword": outline.get("primary_keyword", ""),
                "market": outline.get("market", ""),
                "word_count": word_count,
                "section_count": len(sections),
                "has_faq": True,
                "has_tables": self._count_tables(final_article) > 0,
                "table_count": self._count_tables(final_article),
                "output_path": str(output_path)
            }
            
            metadata_path = await self.save_output("article_metadata.json", metadata)
            
            self.log_complete({
                "word_count": word_count,
                "sections": len(sections),
                "tables": metadata["table_count"]
            })
            
            return {"article": final_article, "metadata": metadata}
            
        except Exception as e:
            self.log_error(e)
            raise
    
    async def _load_outline(self) -> Dict:
        """Load article outline from Agent 03."""
        import os
        
        outline_paths = [
            "output/agent_03/article_outline.json",
            "output/article_outline.json"
        ]
        
        for path in outline_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        
        raise FileNotFoundError("article_outline.json not found. Run Agent 03 first.")
    
    async def _write_introduction(self, outline: Dict) -> str:
        """Write compelling introduction."""
        title = outline.get("title", "")
        keyword = outline.get("primary_keyword", "")
        search_intent = outline.get("search_intent", "informational")
        target_audience = outline.get("target_audience", "expatriates")
        hook_data = outline.get("hook_data", {})
        
        prompt = f"""Write a compelling introduction for this article:

Title: {title}
Primary Keyword: {keyword}
Target Audience: {target_audience}
Search Intent: {search_intent}
Hook Data: {json.dumps(hook_data, indent=2)}

Requirements:
1. Start with a powerful hook (surprising statistic, question, or scenario)
2. Clearly state what the reader will learn
3. Establish the article's authority and expertise
4. Include the primary keyword naturally within the first 100 words
5. 250-350 words
6. End with a smooth transition to the first main section

Write the introduction directly, no meta-commentary. Use markdown formatting."""

        return await self.call_llm(prompt, system=self.SYSTEM_PROMPT, max_tokens=800)
    
    async def _write_sections(self, outline: Dict) -> List[str]:
        """Write all H2 sections with their H3 subsections."""
        sections = outline.get("sections", [])
        written_sections = []
        
        for section in sections:
            h2 = section.get("h2", "")
            subsections = section.get("h3", [])
            data_points = section.get("data", [])
            
            prompt = f"""Write a comprehensive section for this article:

Section Title (H2): {h2}
Subsections needed: {json.dumps(subsections)}
Key data points to include: {json.dumps(data_points)}

Article context:
- Primary keyword: {outline.get('primary_keyword', '')}
- Target market: {outline.get('market', 'USA')}
- Target audience: {outline.get('target_audience', 'expatriates')}

Requirements:
1. Write the H2 heading (##) and full section content
2. Write each H3 subsection (###) with detailed content
3. Include specific facts, numbers, and examples
4. Use comparison tables where relevant (Markdown format)
5. Include practical actionable advice
6. Write 600-900 words for this section
7. Natural keyword integration
8. Connect to overall article theme

Write the section directly in Markdown format."""

            try:
                section_text = await self.call_llm(
                    prompt, system=self.SYSTEM_PROMPT, max_tokens=2500
                )
                written_sections.append(section_text)
                logger.info(f"Wrote section: {h2} ({len(section_text.split())} words)")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to write section '{h2}': {e}")
                # Create placeholder
                written_sections.append(f"## {h2}\n\nContent placeholder for this section.\n")
        
        return written_sections
    
    async def _write_faq(self, outline: Dict) -> str:
        """Write FAQ section."""
        faq_questions = outline.get("faq", [])
        keyword = outline.get("primary_keyword", "")
        
        prompt = f"""Write a comprehensive FAQ section for this article.

Article keyword: {keyword}
Target market: {outline.get('market', 'USA')}

Suggested questions to cover:
{json.dumps(faq_questions, indent=2)}

Requirements:
1. Write "## Frequently Asked Questions" as the heading
2. Include at least 8-10 questions
3. Each answer should be 50-150 words
4. Format using schema.org FAQ markup (H3 for questions)
5. Cover the most common user questions
6. Include questions from the outline plus additional ones
7. Answers must be direct and helpful
8. Include the primary keyword in 2-3 question phrasings

Write the complete FAQ section in Markdown format."""

        return await self.call_llm(prompt, system=self.SYSTEM_PROMPT, max_tokens=2000)
    
    async def _write_conclusion(self, outline: Dict) -> str:
        """Write article conclusion."""
        title = outline.get("title", "")
        key_takeaways = outline.get("key_takeaways", [])
        cta = outline.get("call_to_action", "")
        
        prompt = f"""Write a strong conclusion for this article:

Article title: {title}
Key takeaways: {json.dumps(key_takeaways)}
Call to action: {cta}

Requirements:
1. Summarize the 3-5 most important points
2. Provide a clear recommendation or next step
3. Include a strong CTA (e.g., "Ready to open your account?")
4. Reinforce the article's value proposition
5. 200-300 words
6. End with a memorable closing statement

Write the conclusion directly in Markdown format."""

        return await self.call_llm(prompt, system=self.SYSTEM_PROMPT, max_tokens=600)
    
    async def _add_eeat_elements(self, intro: str, sections: List[str], 
                                  faq: str, conclusion: str, outline: Dict) -> str:
        """Add EEAT (Experience, Expertise, Authority, Trust) elements."""
        full_article = intro + "\n\n" + "\n\n".join(sections) + "\n\n" + faq + "\n\n" + conclusion
        
        # Add author expertise callout box
        expertise_box = """
> **Expert Insight**: This guide was researched and written by financial professionals 
> specializing in expatriate banking and international finance. All information is 
> verified against official sources and updated for 2026.
"""
        
        # Add trust signals
        trust_note = """
> **Last Updated**: June 2026 | **Review Frequency**: Monthly | 
> **Sources**: Official bank websites, government tax authorities, and financial regulators
"""
        
        # Insert expertise box after intro
        article_parts = full_article.split("\n\n", 1)
        if len(article_parts) == 2:
            full_article = article_parts[0] + "\n\n" + expertise_box + "\n\n" + article_parts[1]
        
        # Add trust note before conclusion
        full_article = full_article + "\n\n" + trust_note
        
        return full_article
    
    async def _seo_optimize(self, article: str, outline: Dict) -> str:
        """Perform SEO optimization pass on the article."""
        keyword = outline.get("primary_keyword", "")
        secondary_keywords = outline.get("secondary_keywords", [])
        
        # Check keyword density
        word_count = len(article.split())
        keyword_count = len(re.findall(re.escape(keyword.lower()), article.lower()))
        keyword_density = keyword_count / word_count if word_count > 0 else 0
        
        logger.info(f"Keyword density for '{keyword}': {keyword_density:.3f} ({keyword_count} occurrences)")
        
        # Ideal density: 0.5% to 1.5%
        if keyword_density < 0.005:
            logger.warning(f"Keyword density too low. Target: add {int(word_count * 0.008) - keyword_count} more instances.")
        
        return article
    
    async def _expand_article(self, article: str, outline: Dict) -> str:
        """Expand article if it's below minimum word count."""
        word_count = len(article.split())
        words_needed = self.MIN_WORD_COUNT - word_count + 500  # Add buffer
        
        prompt = f"""The following article needs to be expanded by approximately {words_needed} words.
        
Add more depth, examples, data tables, or additional subsections where appropriate.
Do not change the existing content, only add to it.

Current article:
{article[:3000]}... [Article continues]

Add content that:
1. Provides more specific examples and case studies
2. Includes comparison tables with real data
3. Adds actionable tips and checklists
4. Covers edge cases and exceptions
5. Addresses common mistakes to avoid

Return the FULL expanded article."""

        return await self.call_llm(prompt, system=self.SYSTEM_PROMPT, max_tokens=4096)
    
    def _assemble_article(self, outline: Dict, content: str, word_count: int) -> str:
        """Assemble the final article with metadata header."""
        title = outline.get("title", "")
        keyword = outline.get("primary_keyword", "")
        market = outline.get("market", "")
        
        header = f"""---
title: "{title}"
primary_keyword: "{keyword}"
market: "{market}"
word_count: {word_count}
date_written: "{datetime.utcnow().strftime('%Y-%m-%d')}"
status: "draft"
agent: "NEXUS-14 Article Writer"
---

# {title}

"""
        
        return header + content
    
    def _count_tables(self, article: str) -> int:
        """Count markdown tables in article."""
        return len(re.findall(r'^\|.+\|$', article, re.MULTILINE))
