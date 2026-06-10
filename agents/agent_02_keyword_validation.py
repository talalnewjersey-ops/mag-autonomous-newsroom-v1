"""
NEXUS-14: Agent 02 - Keyword Validation Agent
Validates and prioritizes keywords from Agent 01's output.
Input: topics.json
Output: validated_topics.json
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Set

from agents.base_agent import BaseAgent
from services.llm_service import LLMService
from services.storage_service import StorageService


logger = logging.getLogger(__name__)


class KeywordValidationAgent(BaseAgent):
    """
    Agent 02: Keyword Validation Agent
    
    Responsibilities:
    - Eliminate duplicate keywords
    - Verify user search intent
    - Prioritize topics by opportunity score
    
    Output: validated_topics.json
    """
    
    AGENT_ID = "agent_02"
    AGENT_NAME = "Keyword Validation Agent"
    
    # Intent categories
    VALID_INTENTS = ["informational", "commercial", "transactional", "navigational"]
    PREFERRED_INTENTS = ["informational", "commercial"]  # Best for content
    
    # Quality thresholds
    MIN_PRIORITY_SCORE = 20.0
    MAX_KEYWORD_LENGTH = 80
    MIN_WORD_COUNT = 3
    
    def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
        super().__init__(config, llm_service, storage_service)
        self.seen_keywords: Set[str] = set()
        self.seen_topics: Set[str] = set()
    
    async def run(self, context: Dict = None) -> Dict:
        """Main agent execution flow."""
        self.log_start()
        
        try:
            # Load input from Agent 01
            topics_data = await self._load_topics()
            raw_topics = topics_data.get("topics", [])
            
            logger.info(f"Processing {len(raw_topics)} raw topics from Agent 01...")
            
            # Phase 1: Remove duplicates
            logger.info("Phase 1: Removing duplicates...")
            deduped = await self._remove_duplicates(raw_topics)
            logger.info(f"After deduplication: {len(deduped)} topics")
            
            # Phase 2: Verify search intent
            logger.info("Phase 2: Verifying search intent...")
            intent_verified = await self._verify_intent(deduped)
            logger.info(f"After intent verification: {len(intent_verified)} topics")
            
            # Phase 3: Quality filtering
            logger.info("Phase 3: Quality filtering...")
            quality_filtered = await self._quality_filter(intent_verified)
            logger.info(f"After quality filter: {len(quality_filtered)} topics")
            
            # Phase 4: LLM-enhanced prioritization
            logger.info("Phase 4: LLM-enhanced prioritization...")
            prioritized = await self._llm_prioritize(quality_filtered)
            
            # Phase 5: Final scoring and sorting
            logger.info("Phase 5: Final scoring and sorting...")
            final_topics = await self._final_score_and_sort(prioritized)
            
            # Phase 6: Categorize into USA/Canada hubs
            logger.info("Phase 6: Categorizing into content hubs...")
            categorized = await self._categorize_into_hubs(final_topics)
            
            # Build output
            output = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "raw_count": len(raw_topics),
                "validated_count": len(final_topics),
                "rejection_rate": round(1 - len(final_topics)/max(len(raw_topics), 1), 2),
                "topics": final_topics,
                "hubs": categorized,
                "statistics": self._compute_statistics(final_topics)
            }
            
            output_path = await self.save_output("validated_topics.json", output)
            logger.info(f"Validated topics saved to: {output_path}")
            
            self.log_complete({
                "validated_topics": len(final_topics),
                "usa_topics": len([t for t in final_topics if t.get("market") == "USA"]),
                "canada_topics": len([t for t in final_topics if t.get("market") == "Canada"])
            })
            
            return output
            
        except Exception as e:
            self.log_error(e)
            raise
    
    async def _load_topics(self) -> Dict:
        """Load topics from Agent 01's output."""
        import os
        
        # Try to load from storage
        topics_paths = [
            "output/agent_01/topics.json",
            "output/topics.json",
            "/tmp/nexus14/topics.json"
        ]
        
        for path in topics_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        
        raise FileNotFoundError("topics.json not found. Run Agent 01 first.")
    
    async def _remove_duplicates(self, topics: List[Dict]) -> List[Dict]:
        """Remove duplicate keywords and very similar topics."""
        unique_topics = []
        seen_normalized = set()
        
        for topic in topics:
            keyword = topic.get("keyword", "")
            
            # Normalize: lowercase, strip, remove extra spaces
            normalized = " ".join(keyword.lower().strip().split())
            
            # Skip if exact duplicate
            if normalized in seen_normalized:
                continue
            
            # Skip if very short
            if len(normalized.split()) < self.MIN_WORD_COUNT:
                continue
            
            # Check for near-duplicates (same first 3 words)
            first_three = " ".join(normalized.split()[:3])
            if first_three in self.seen_topics:
                # Keep the one with higher priority score
                existing = next((t for t in unique_topics 
                               if " ".join(t.get("keyword","").lower().split()[:3]) == first_three), None)
                if existing and topic.get("priority_score", 0) > existing.get("priority_score", 0):
                    unique_topics.remove(existing)
                    self.seen_topics.discard(first_three)
                else:
                    continue
            
            seen_normalized.add(normalized)
            self.seen_topics.add(first_three)
            unique_topics.append(topic)
        
        return unique_topics
    
    async def _verify_intent(self, topics: List[Dict]) -> List[Dict]:
        """Verify and assign search intent to each topic."""
        verified = []
        
        # Intent keywords patterns
        commercial_patterns = ["best", "top", "compare", "review", "vs", "alternative"]
        transactional_patterns = ["buy", "open", "sign up", "apply", "get", "download"]
        informational_patterns = ["how", "what", "why", "guide", "tutorial", "explained"]
        
        for topic in topics:
            keyword = topic.get("keyword", "").lower()
            intent = topic.get("intent", "")
            
            # If intent not set, determine it
            if not intent or intent not in self.VALID_INTENTS:
                if any(p in keyword for p in transactional_patterns):
                    intent = "transactional"
                elif any(p in keyword for p in commercial_patterns):
                    intent = "commercial"
                elif any(p in keyword for p in informational_patterns):
                    intent = "informational"
                else:
                    intent = "informational"  # Default for finance content
            
            topic["intent"] = intent
            topic["intent_score"] = self._score_intent(intent)
            
            # Only keep content-suitable intents
            if intent in self.PREFERRED_INTENTS:
                topic["content_suitable"] = True
                verified.append(topic)
            elif intent == "transactional":
                # Transactional can work if CPC is high (commercial value)
                if topic.get("cpc", 0) > 2.0:
                    topic["content_suitable"] = True
                    verified.append(topic)
        
        return verified
    
    async def _quality_filter(self, topics: List[Dict]) -> List[Dict]:
        """Apply quality filters."""
        filtered = []
        
        for topic in topics:
            keyword = topic.get("keyword", "")
            
            # Skip if keyword too long
            if len(keyword) > self.MAX_KEYWORD_LENGTH:
                continue
            
            # Skip if priority score too low
            if topic.get("priority_score", 0) < self.MIN_PRIORITY_SCORE:
                continue
            
            # Skip brand-specific queries (unless we have affiliate)
            if self._is_competitor_branded(keyword) and "affiliate" not in topic.get("opportunity_types", []):
                continue
            
            filtered.append(topic)
        
        return filtered
    
    async def _llm_prioritize(self, topics: List[Dict]) -> List[Dict]:
        """Use LLM to enhance prioritization with context."""
        if not topics:
            return topics
        
        # Only send top candidates to LLM for efficiency
        top_topics = sorted(topics, key=lambda x: x.get("priority_score", 0), reverse=True)[:30]
        
        topics_summary = [
            f"- {t['keyword']} (score: {t.get('priority_score', 0)}, vol: {t.get('search_volume', 0)}, market: {t.get('market', 'unknown')})"
            for t in top_topics
        ]
        
        prompt = f"""You are an SEO expert for MoneyAbroadGuide.com, a site focused on financial services for expatriates.

Review these keyword opportunities and rate each one for content potential (1-10):

{chr(10).join(topics_summary)}

For each keyword, provide:
1. Content potential score (1-10)
2. Article angle (one sentence)
3. Target audience

Return as JSON array with format:
[{{"keyword": "...", "llm_score": X, "angle": "...", "audience": "..."}}]

Focus on keywords that:
- Have clear educational or comparison value
- Target people living abroad or planning to
- Can generate affiliate revenue
- Are specific to USA or Canadian expats"""

        try:
            response = await self.call_llm(prompt, max_tokens=2000)
            
            # Parse LLM response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                llm_scores = json.loads(json_match.group())
                
                # Merge LLM scores with topics
                score_map = {item["keyword"].lower(): item for item in llm_scores}
                
                for topic in topics:
                    kw_lower = topic.get("keyword", "").lower()
                    if kw_lower in score_map:
                        llm_data = score_map[kw_lower]
                        topic["llm_score"] = llm_data.get("llm_score", 5)
                        topic["content_angle"] = llm_data.get("angle", "")
                        topic["target_audience"] = llm_data.get("audience", "")
                        
                        # Boost priority score with LLM score
                        topic["priority_score"] = round(
                            topic.get("priority_score", 0) * 0.7 + 
                            topic["llm_score"] * 10 * 0.3, 2
                        )
        except Exception as e:
            self.log_warning(f"LLM prioritization failed: {e}. Using default scoring.")
        
        return topics
    
    async def _final_score_and_sort(self, topics: List[Dict]) -> List[Dict]:
        """Final scoring and sorting."""
        for i, topic in enumerate(topics):
            # Add rank
            topic["rank"] = i + 1
            
            # Ensure all required fields
            topic.setdefault("keyword", "")
            topic.setdefault("market", "USA")
            topic.setdefault("priority_score", 0)
            topic.setdefault("opportunity_types", ["seo"])
            topic.setdefault("content_suitable", True)
            topic.setdefault("validated", True)
            
            # Add content metadata
            topic["estimated_word_count"] = self._estimate_word_count(topic)
            topic["content_type"] = self._determine_content_type(topic)
        
        # Sort by priority score
        topics.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return topics
    
    async def _categorize_into_hubs(self, topics: List[Dict]) -> Dict:
        """Categorize topics into content hubs."""
        hubs = {
            "usa_banking": [],
            "usa_investment": [],
            "usa_tax": [],
            "usa_money_transfer": [],
            "canada_banking": [],
            "canada_investment": [],
            "canada_tax": [],
            "canada_newcomers": [],
        }
        
        banking_kws = ["bank", "account", "savings", "checking", "credit"]
        investment_kws = ["invest", "etf", "stocks", "portfolio", "brokerage"]
        tax_kws = ["tax", "fatca", "fbar", "cra", "irs", "filing"]
        transfer_kws = ["transfer", "send money", "wire", "remittance"]
        newcomer_kws = ["newcomer", "immigrant", "new to", "arriving", "moving to canada"]
        
        for topic in topics:
            kw = topic.get("keyword", "").lower()
            market = topic.get("market", "USA")
            
            prefix = market.lower().replace(" ", "_")
            if prefix == "usa":
                if any(k in kw for k in banking_kws):
                    hubs["usa_banking"].append(topic["keyword"])
                elif any(k in kw for k in investment_kws):
                    hubs["usa_investment"].append(topic["keyword"])
                elif any(k in kw for k in tax_kws):
                    hubs["usa_tax"].append(topic["keyword"])
                elif any(k in kw for k in transfer_kws):
                    hubs["usa_money_transfer"].append(topic["keyword"])
            elif prefix == "canada":
                if any(k in kw for k in newcomer_kws):
                    hubs["canada_newcomers"].append(topic["keyword"])
                elif any(k in kw for k in banking_kws):
                    hubs["canada_banking"].append(topic["keyword"])
                elif any(k in kw for k in investment_kws):
                    hubs["canada_investment"].append(topic["keyword"])
                elif any(k in kw for k in tax_kws):
                    hubs["canada_tax"].append(topic["keyword"])
        
        return hubs
    
    def _score_intent(self, intent: str) -> float:
        """Score intent for content value."""
        scores = {
            "informational": 1.0,
            "commercial": 0.9,
            "transactional": 0.7,
            "navigational": 0.3
        }
        return scores.get(intent, 0.5)
    
    def _is_competitor_branded(self, keyword: str) -> bool:
        """Check if keyword is branded to a specific competitor."""
        competitor_brands = [
            "wise", "revolut", "n26", "monzo", "starling",
            "hsbc", "citibank", "chase", "wells fargo", "td bank"
        ]
        keyword_lower = keyword.lower()
        return any(brand in keyword_lower for brand in competitor_brands)
    
    def _estimate_word_count(self, topic: Dict) -> int:
        """Estimate ideal word count for article."""
        base = 5000
        if topic.get("keyword_difficulty", 0) > 50:
            base = 7000
        if "guide" in topic.get("keyword", "").lower():
            base = 8000
        if "complete" in topic.get("keyword", "").lower():
            base = 10000
        return base
    
    def _determine_content_type(self, topic: Dict) -> str:
        """Determine content type (article, comparison, guide, listicle)."""
        keyword = topic.get("keyword", "").lower()
        if "vs" in keyword or "compare" in keyword or "comparison" in keyword:
            return "comparison"
        elif "guide" in keyword or "how to" in keyword:
            return "guide"
        elif "best" in keyword or "top" in keyword:
            return "listicle"
        else:
            return "article"
    
    def _compute_statistics(self, topics: List[Dict]) -> Dict:
        """Compute statistics about validated topics."""
        if not topics:
            return {}
        
        volumes = [t.get("search_volume", 0) for t in topics]
        difficulties = [t.get("keyword_difficulty", 0) for t in topics]
        
        return {
            "total_validated": len(topics),
            "usa_count": len([t for t in topics if t.get("market") == "USA"]),
            "canada_count": len([t for t in topics if t.get("market") == "Canada"]),
            "avg_search_volume": round(sum(volumes) / len(volumes), 0),
            "avg_difficulty": round(sum(difficulties) / len(difficulties), 1),
            "informational_count": len([t for t in topics if t.get("intent") == "informational"]),
            "commercial_count": len([t for t in topics if t.get("intent") == "commercial"]),
            "affiliate_opportunities": len([t for t in topics if "affiliate" in t.get("opportunity_types", [])]),
            "ebook_opportunities": len([t for t in topics if "ebook" in t.get("opportunity_types", [])])
        }
