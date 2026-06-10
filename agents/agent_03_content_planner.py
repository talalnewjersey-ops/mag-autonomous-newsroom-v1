"""
NEXUS-14: Agent 03 - Content Planner Agent
Creates comprehensive article outlines with H2/H3 structure,
FAQ, tables, and case studies.
Input: validated_topics.json
Output: article_outline.json
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List

from agents.base_agent import BaseAgent
from services.llm_service import LLMService
from services.storage_service import StorageService


logger = logging.getLogger(__name__)


class ContentPlannerAgent(BaseAgent):
    """
    Agent 03: Content Planner Agent
    Creates detailed article outlines for Agent 04 (Article Writer).
    """
    
    AGENT_ID = "agent_03"
    AGENT_NAME = "Content Planner Agent"
    
    def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
        super().__init__(config, llm_service, storage_service)
    
    async def run(self, context: Dict = None) -> Dict:
        """Main execution: plan article structure."""
        self.log_start()
        
        try:
            # Load validated topics
            topics = await self._load_topics()
            
            outlines = []
            for topic in topics.get("topics", [])[:self.config.get("articles_per_batch", 5)]:
                logger.info(f"Planning article: {topic.get('keyword')}")
                outline = await self._create_outline(topic)
                outlines.append(outline)
                await asyncio.sleep(0.5)  # Rate limiting
            
            output = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "outlines_created": len(outlines),
                "outlines": outlines
            }
            
            # Save primary outline (first article)
            if outlines:
                await self.save_output("article_outline.json", outlines[0])
            
            await self.save_output("all_outlines.json", output)
            
            self.log_complete({"outlines_created": len(outlines)})
            return output
            
        except Exception as e:
            self.log_error(e)
            raise
    
    async def _load_topics(self) -> Dict:
        """Load validated topics from Agent 02."""
        import os
        paths = ["output/agent_02/validated_topics.json", "output/validated_topics.json"]
        for path in paths:
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        raise FileNotFoundError("validated_topics.json not found")
    
    async def _create_outline(self, topic: Dict) -> Dict:
        """Create a comprehensive article outline using LLM."""
        keyword = topic.get("keyword", "")
        market = topic.get("market", "USA")
        intent = topic.get("intent", "informational")
        
        prompt = f"""Create a comprehensive article outline for MoneyAbroadGuide.com.

Primary keyword: {keyword}
Target market: {market}
Search intent: {intent}
Target word count: 7,500 words

Create a detailed outline with:
1. SEO-optimized title (H1) - include keyword naturally
2. Meta description (150-160 chars)
3. Introduction hook data
4. 6-8 H2 sections, each with 2-3 H3 subsections
5. 8-10 FAQ questions
6. 2-3 comparison tables
7. 1-2 case studies
8. Key takeaways (5 bullet points)
9. Call-to-action

Return as JSON with this structure:
{{
  "title": "...",
  "meta_description": "...",
  "primary_keyword": "...",
  "secondary_keywords": ["..."],
  "market": "{market}",
  "target_audience": "...",
  "search_intent": "{intent}",
  "estimated_word_count": 7500,
  "hook_data": {{"statistic": "...", "question": "..."}},
  "sections": [
    {{
      "h2": "...",
      "h3": ["...", "..."],
      "data": ["key facts to include"],
      "has_table": true/false,
      "has_case_study": true/false
    }}
  ],
  "faq": ["question 1?", "question 2?"],
  "tables": [{{"title": "...", "columns": ["col1", "col2"], "purpose": "..."}}],
  "case_studies": [{{"scenario": "...", "profile": "..."}}],
  "key_takeaways": ["...", "..."],
  "call_to_action": "...",
  "internal_link_opportunities": ["..."],
  "affiliate_opportunities": ["..."]
}}"""
        
        response = await self.call_llm(prompt, max_tokens=3000)
        
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                outline = json.loads(json_match.group())
                outline["topic_data"] = topic
                return outline
        except Exception as e:
            logger.warning(f"Failed to parse outline JSON: {e}")
        
        # Fallback outline
        return {
            "title": f"Complete Guide to {keyword.title()} ({market} {datetime.utcnow().year})",
            "primary_keyword": keyword,
            "market": market,
            "search_intent": intent,
            "estimated_word_count": 7500,
            "sections": [
                {"h2": f"What is {keyword.title()}?", "h3": ["Overview", "Why It Matters"]},
                {"h2": "Best Options Compared", "h3": ["Top Picks", "Comparison Table"]},
                {"h2": "How to Get Started", "h3": ["Step-by-Step Guide", "Requirements"]},
                {"h2": "Costs and Fees", "h3": ["Fee Structures", "Hidden Costs"]},
                {"h2": "Common Mistakes to Avoid", "h3": ["Top Pitfalls", "Expert Tips"]},
            ],
            "faq": [
                f"What is the best {keyword} for {market} expats?",
                f"How does {keyword} work for non-residents?",
                f"What are the requirements for {keyword}?",
                f"How much does {keyword} cost?",
                f"Is {keyword} safe and regulated?",
                f"How long does {keyword} take?",
                f"Can I use {keyword} from abroad?",
                f"What alternatives to {keyword} exist?"
            ],
            "key_takeaways": [
                f"{keyword.title()} is essential for {market} expatriates",
                "Compare multiple options before choosing",
                "Consider fees, exchange rates, and regulations",
                "Check eligibility requirements in advance",
                "Start the process early to avoid delays"
            ],
            "call_to_action": f"Ready to find the best {keyword}? Compare your options below.",
            "topic_data": topic
        }
