"""
NEXUS-14: Agent 01 - SEO Research Agent
Responsible for researching SEO opportunities for MoneyAbroadGuide.com
Target markets: USA & Canada
Output: topics.json
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from services.search_service import SearchService
from services.llm_service import LLMService
from services.storage_service import StorageService
from agents.base_agent import BaseAgent


logger = logging.getLogger(__name__)


class SEOResearchAgent(BaseAgent):
    """
    Agent 01: SEO Research Agent
    
    Responsibilities:
    - Research SEO opportunities for USA market
    - Research SEO opportunities for Canada market
    - Identify keyword opportunities
    - Identify affiliate opportunities
    - Identify ebook opportunities
    
    Output: topics.json
    """
    
    AGENT_ID = "agent_01"
    AGENT_NAME = "SEO Research Agent"
    
    def __init__(self, config: Dict, search_service: SearchService, 
                 llm_service: LLMService, storage_service: StorageService):
        super().__init__(config, llm_service, storage_service)
        self.search_service = search_service
        self.target_markets = ["USA", "Canada"]
        self.min_search_volume = config.get("min_search_volume", 500)
        self.max_keyword_difficulty = config.get("max_keyword_difficulty", 65)
        self.topics_per_batch = config.get("topics_per_batch", 10)
        
    async def run(self, context: Dict = None) -> Dict:
        """Main agent execution flow."""
        self.log_start()
        
        try:
            # Phase 1: Research trending topics
            logger.info("Phase 1: Researching trending financial topics for expats...")
            trending_topics = await self._research_trending_topics()
            
            # Phase 2: Keyword research - USA
            logger.info("Phase 2: SEO research for USA market...")
            usa_keywords = await self._research_usa_keywords(trending_topics)
            
            # Phase 3: Keyword research - Canada
            logger.info("Phase 3: SEO research for Canada market...")
            canada_keywords = await self._research_canada_keywords(trending_topics)
            
            # Phase 4: Affiliate opportunities
            logger.info("Phase 4: Identifying affiliate opportunities...")
            affiliate_opportunities = await self._identify_affiliate_opportunities(
                usa_keywords + canada_keywords
            )
            
            # Phase 5: Ebook opportunities
            logger.info("Phase 5: Identifying ebook opportunities...")
            ebook_opportunities = await self._identify_ebook_opportunities(
                usa_keywords + canada_keywords
            )
            
            # Phase 6: Compile and score topics
            logger.info("Phase 6: Compiling and scoring all topics...")
            topics = await self._compile_topics(
                usa_keywords, canada_keywords,
                affiliate_opportunities, ebook_opportunities
            )
            
            # Save output
            output = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "markets": self.target_markets,
                "total_topics": len(topics),
                "usa_count": len(usa_keywords),
                "canada_count": len(canada_keywords),
                "affiliate_count": len(affiliate_opportunities),
                "ebook_count": len(ebook_opportunities),
                "topics": topics
            }
            
            output_path = await self.save_output("topics.json", output)
            logger.info(f"Topics saved to: {output_path}")
            
            self.log_complete({"topics_found": len(topics)})
            return output
            
        except Exception as e:
            self.log_error(e)
            raise
    
    async def _research_trending_topics(self) -> List[str]:
        """Research trending topics in the expat finance niche."""
        prompts = [
            "expatriate banking abroad 2026",
            "money transfer international expat",
            "tax obligations living abroad USA Canada",
            "best bank accounts for Americans Canada",
            "digital banking expats",
            "wire transfer fees international",
            "FBAR FATCA compliance expats",
            "pension abroad US Canada",
            "investment accounts non-resident"
        ]
        
        trending = []
        for prompt in prompts:
            results = await self.search_service.get_trending_searches(prompt)
            trending.extend(results)
        
        return list(set(trending))
    
    async def _research_usa_keywords(self, seed_topics: List[str]) -> List[Dict]:
        """Research SEO keywords for the USA market."""
        keywords = []
        
        usa_seed_queries = [
            "best international bank account american expat",
            "how to send money from usa to",
            "US expat banking guide",
            "american living abroad financial guide",
            "FATCA reporting requirements 2026",
            "best credit card no foreign transaction fee usa",
            "US citizen banking outside america",
            "wire transfer usa international fees comparison",
            "tax filing american abroad",
            "social security abroad american expat"
        ]
        
        for query in usa_seed_queries:
            try:
                kw_data = await self.search_service.get_keyword_data(query, country="US")
                for kw in kw_data:
                    if (kw.get("search_volume", 0) >= self.min_search_volume and
                            kw.get("keyword_difficulty", 100) <= self.max_keyword_difficulty):
                        kw["market"] = "USA"
                        kw["opportunity_type"] = "seo"
                        keywords.append(kw)
            except Exception as e:
                logger.warning(f"Failed to get keyword data for '{query}': {e}")
        
        logger.info(f"Found {len(keywords)} USA keyword opportunities")
        return keywords
    
    async def _research_canada_keywords(self, seed_topics: List[str]) -> List[Dict]:
        """Research SEO keywords for the Canada market."""
        keywords = []
        
        canada_seed_queries = [
            "best bank account canadian expat",
            "send money from canada abroad",
            "canadian living abroad banking",
            "newcomer to canada banking guide",
            "canadian non-resident banking",
            "wire transfer canada international comparison",
            "CRA tax obligations non-resident canadian",
            "best credit card canada no foreign fee",
            "TFSA RRSP non-resident canada",
            "newcomer canada financial guide 2026"
        ]
        
        for query in canada_seed_queries:
            try:
                kw_data = await self.search_service.get_keyword_data(query, country="CA")
                for kw in kw_data:
                    if (kw.get("search_volume", 0) >= self.min_search_volume and
                            kw.get("keyword_difficulty", 100) <= self.max_keyword_difficulty):
                        kw["market"] = "Canada"
                        kw["opportunity_type"] = "seo"
                        keywords.append(kw)
            except Exception as e:
                logger.warning(f"Failed to get keyword data for '{query}': {e}")
        
        logger.info(f"Found {len(keywords)} Canada keyword opportunities")
        return keywords
    
    async def _identify_affiliate_opportunities(self, keywords: List[Dict]) -> List[Dict]:
        """Identify affiliate marketing opportunities from keywords."""
        affiliate_programs = [
            {"name": "Wise (TransferWise)", "category": "money_transfer", "commission": "per_signup"},
            {"name": "Revolut", "category": "digital_banking", "commission": "per_signup"},
            {"name": "N26", "category": "digital_banking", "commission": "per_signup"},
            {"name": "OFX", "category": "money_transfer", "commission": "percentage"},
            {"name": "Remitly", "category": "money_transfer", "commission": "per_transfer"},
            {"name": "WorldRemit", "category": "money_transfer", "commission": "per_transfer"},
            {"name": "Charles Schwab", "category": "investment", "commission": "per_account"},
            {"name": "Interactive Brokers", "category": "investment", "commission": "per_account"},
            {"name": "HSBC Expat", "category": "banking", "commission": "per_account"},
        ]
        
        opportunities = []
        for kw in keywords:
            for program in affiliate_programs:
                if self._keyword_matches_program(kw.get("keyword", ""), program):
                    opportunities.append({
                        "keyword": kw.get("keyword"),
                        "market": kw.get("market"),
                        "affiliate_program": program["name"],
                        "category": program["category"],
                        "commission_type": program["commission"],
                        "search_volume": kw.get("search_volume", 0),
                        "opportunity_score": self._calculate_affiliate_score(kw, program)
                    })
        
        # Sort by opportunity score
        opportunities.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        logger.info(f"Found {len(opportunities)} affiliate opportunities")
        return opportunities[:50]  # Top 50
    
    async def _identify_ebook_opportunities(self, keywords: List[Dict]) -> List[Dict]:
        """Identify ebook/digital product opportunities."""
        ebook_topics = []
        
        ebook_seed_topics = [
            "complete guide expat banking",
            "tax guide americans abroad",
            "financial planning expats",
            "money management international living",
            "banking abroad comprehensive guide",
            "newcomer financial guide canada",
            "investment guide non-residents"
        ]
        
        for kw in keywords:
            keyword_text = kw.get("keyword", "").lower()
            for topic in ebook_seed_topics:
                if any(word in keyword_text for word in topic.split()):
                    ebook_topics.append({
                        "keyword": kw.get("keyword"),
                        "market": kw.get("market"),
                        "ebook_angle": topic,
                        "search_volume": kw.get("search_volume", 0),
                        "potential_revenue": self._estimate_ebook_revenue(kw)
                    })
                    break
        
        logger.info(f"Found {len(ebook_topics)} ebook opportunities")
        return ebook_topics[:20]
    
    async def _compile_topics(self, usa_keywords: List[Dict], canada_keywords: List[Dict],
                              affiliate_opps: List[Dict], ebook_opps: List[Dict]) -> List[Dict]:
        """Compile all opportunities into prioritized topics."""
        topics = []
        
        # Process USA keywords
        for kw in usa_keywords[:self.topics_per_batch]:
            topic = {
                "id": f"usa_{len(topics):04d}",
                "keyword": kw.get("keyword"),
                "market": "USA",
                "search_volume": kw.get("search_volume", 0),
                "keyword_difficulty": kw.get("keyword_difficulty", 0),
                "cpc": kw.get("cpc", 0),
                "opportunity_types": ["seo"],
                "priority_score": self._calculate_priority_score(kw),
                "intent": kw.get("intent", "informational"),
                "serp_features": kw.get("serp_features", [])
            }
            
            # Check if it has affiliate potential
            for aff in affiliate_opps:
                if aff.get("keyword") == kw.get("keyword"):
                    topic["opportunity_types"].append("affiliate")
                    topic["affiliate_programs"] = [aff.get("affiliate_program")]
                    break
            
            topics.append(topic)
        
        # Process Canada keywords
        for kw in canada_keywords[:self.topics_per_batch]:
            topic = {
                "id": f"can_{len(topics):04d}",
                "keyword": kw.get("keyword"),
                "market": "Canada",
                "search_volume": kw.get("search_volume", 0),
                "keyword_difficulty": kw.get("keyword_difficulty", 0),
                "cpc": kw.get("cpc", 0),
                "opportunity_types": ["seo"],
                "priority_score": self._calculate_priority_score(kw),
                "intent": kw.get("intent", "informational"),
                "serp_features": kw.get("serp_features", [])
            }
            
            topics.append(topic)
        
        # Add ebook opportunities
        for ebook in ebook_opps[:5]:
            topic = {
                "id": f"ebook_{len(topics):04d}",
                "keyword": ebook.get("keyword"),
                "market": ebook.get("market"),
                "search_volume": ebook.get("search_volume", 0),
                "opportunity_types": ["ebook", "seo"],
                "ebook_angle": ebook.get("ebook_angle"),
                "potential_revenue": ebook.get("potential_revenue"),
                "priority_score": self._calculate_priority_score(ebook)
            }
            topics.append(topic)
        
        # Sort by priority
        topics.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return topics
    
    def _keyword_matches_program(self, keyword: str, program: Dict) -> bool:
        """Check if a keyword matches an affiliate program."""
        keyword_lower = keyword.lower()
        program_name_lower = program["name"].lower().split("(")[0].strip().lower()
        category = program["category"]
        
        category_keywords = {
            "money_transfer": ["transfer", "send money", "remittance", "wire"],
            "digital_banking": ["digital bank", "online bank", "neobank"],
            "banking": ["bank", "account", "savings"],
            "investment": ["invest", "portfolio", "stocks", "etf", "brokerage"]
        }
        
        return any(kw in keyword_lower for kw in category_keywords.get(category, []))
    
    def _calculate_affiliate_score(self, keyword: Dict, program: Dict) -> float:
        """Calculate affiliate opportunity score."""
        score = 0.0
        
        # Search volume component (0-40 points)
        volume = keyword.get("search_volume", 0)
        score += min(40, volume / 250)
        
        # CPC component (0-30 points) - higher CPC = more valuable
        cpc = keyword.get("cpc", 0)
        score += min(30, cpc * 3)
        
        # Difficulty component (0-30 points) - lower difficulty = better
        difficulty = keyword.get("keyword_difficulty", 100)
        score += max(0, 30 - difficulty * 0.3)
        
        return round(score, 2)
    
    def _estimate_ebook_revenue(self, keyword: Dict) -> float:
        """Estimate potential ebook revenue from a keyword."""
        volume = keyword.get("search_volume", 0)
        # Assume 0.1% conversion rate, $27 average ebook price
        return round(volume * 0.001 * 27, 2)
    
    def _calculate_priority_score(self, item: Dict) -> float:
        """Calculate priority score for a topic."""
        score = 0.0
        
        # Search volume (0-40 points)
        volume = item.get("search_volume", 0)
        score += min(40, volume / 250)
        
        # Keyword difficulty inverse (0-30 points)
        difficulty = item.get("keyword_difficulty", 100)
        score += max(0, 30 - difficulty * 0.3)
        
        # CPC (0-20 points)
        cpc = item.get("cpc", 0)
        score += min(20, cpc * 2)
        
        # Bonus for multiple opportunity types
        opp_types = item.get("opportunity_types", [])
        score += len(opp_types) * 5
        
        return round(score, 2)


if __name__ == "__main__":
    # Test the agent
    from config.config_loader import ConfigLoader
    from services.search_service import SearchService
    from services.llm_service import LLMService
    from services.storage_service import StorageService
    
    config = ConfigLoader.load()
    
    agent = SEOResearchAgent(
        config=config,
        search_service=SearchService(config),
        llm_service=LLMService(config),
        storage_service=StorageService(config)
    )
    
    result = asyncio.run(agent.run())
    print(f"Found {result['total_topics']} topics")
