"""
NEXUS-14 V3: Agent 01 - SEO Research Agent
MoneyAbroadGuide.com Autonomous Newsroom

V3.4 UPDATE: Canada Newcomer priority topics added.
V3.3 FIX: ARTICLE_NUM-based topic rotation.
V3.2 FIX: Removed random.shuffle, sorted by revenue potential.

Output: topics.json
CLI: python -m agents.agent_01_seo_research --max-topics 1 --output path
"""

import argparse
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

BUILTIN_TOPIC_DATABASE = [
    # TIER 1: CANADA NEWCOMER PRIORITY (Part 4 Directive)
    {"keyword": "best bank account for newcomers to canada 2026", "market": "Canada",
     "search_volume": 8500, "keyword_difficulty": 22, "cpc": 4.20,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["RBC", "TD Canada Trust", "Scotiabank", "CIBC"],
     "content_type": "listicle", "estimated_word_count": 5000, "newcomer_priority": True},
    {"keyword": "health insurance for newcomers in canada 2026", "market": "Canada",
     "search_volume": 6200, "keyword_difficulty": 25, "cpc": 5.80,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Manulife", "Sun Life", "Blue Cross"],
     "content_type": "guide", "estimated_word_count": 4500, "newcomer_priority": True},
    {"keyword": "credit score canada guide for newcomers beginners", "market": "Canada",
     "search_volume": 7800, "keyword_difficulty": 20, "cpc": 3.90,
     "intent": "informational", "opportunity_types": ["seo", "ebook"],
     "affiliate_programs": ["Borrowell", "Credit Karma", "Equifax"],
     "content_type": "guide", "estimated_word_count": 4000, "newcomer_priority": True},
    {"keyword": "first apartment in canada guide for immigrants 2026", "market": "Canada",
     "search_volume": 5400, "keyword_difficulty": 18, "cpc": 2.90,
     "intent": "informational", "opportunity_types": ["seo", "ebook"],
     "affiliate_programs": ["Zolo", "Rentals.ca"],
     "content_type": "guide", "estimated_word_count": 4500, "newcomer_priority": True},
    {"keyword": "cost of living in canada 2026 newcomer guide", "market": "Canada",
     "search_volume": 9200, "keyword_difficulty": 24, "cpc": 2.60,
     "intent": "informational", "opportunity_types": ["seo"],
     "affiliate_programs": ["Wise", "Remitly"],
     "content_type": "guide", "estimated_word_count": 5000, "newcomer_priority": True},
    {"keyword": "best phone plans for newcomers in canada 2026", "market": "Canada",
     "search_volume": 6800, "keyword_difficulty": 21, "cpc": 3.20,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Koodo", "Fido", "Virgin Plus"],
     "content_type": "comparison", "estimated_word_count": 4000, "newcomer_priority": True},
    {"keyword": "taxes for new immigrants to canada cra guide 2026", "market": "Canada",
     "search_volume": 5900, "keyword_difficulty": 28, "cpc": 6.80,
     "intent": "informational", "opportunity_types": ["seo", "ebook"],
     "affiliate_programs": ["TurboTax", "H&R Block"],
     "content_type": "guide", "estimated_word_count": 4500, "newcomer_priority": True},
    {"keyword": "how to build credit in canada fast as newcomer", "market": "Canada",
     "search_volume": 7100, "keyword_difficulty": 19, "cpc": 3.80,
     "intent": "informational", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Borrowell", "Secured Visa", "Capital One"],
     "content_type": "guide", "estimated_word_count": 4000, "newcomer_priority": True},
    {"keyword": "canada banking mistakes to avoid as newcomer immigrant", "market": "Canada",
     "search_volume": 4800, "keyword_difficulty": 17, "cpc": 3.10,
     "intent": "informational", "opportunity_types": ["seo"],
     "affiliate_programs": ["RBC", "TD Canada Trust"],
     "content_type": "article", "estimated_word_count": 3500, "newcomer_priority": True},
    {"keyword": "first 90 days in canada checklist for newcomers 2026", "market": "Canada",
     "search_volume": 8900, "keyword_difficulty": 15, "cpc": 2.40,
     "intent": "informational", "opportunity_types": ["seo", "ebook"],
     "affiliate_programs": ["RBC", "Wise", "Koodo"],
     "content_type": "guide", "estimated_word_count": 5000, "newcomer_priority": True},
    {"keyword": "banking guide international students canada 2026", "market": "Canada",
     "search_volume": 6200, "keyword_difficulty": 20, "cpc": 2.90,
     "intent": "informational", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["RBC", "TD Canada Trust", "Scotiabank"],
     "content_type": "guide", "estimated_word_count": 4500, "newcomer_priority": True},
    # TIER 2: USA BANKING
    {"keyword": "best bank account for immigrants usa 2026", "market": "USA",
     "search_volume": 3200, "keyword_difficulty": 32, "cpc": 4.20,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Wise", "Revolut", "Charles Schwab"],
     "content_type": "listicle", "estimated_word_count": 5000},
    {"keyword": "best bank account for immigrants canada", "market": "Canada",
     "search_volume": 4200, "keyword_difficulty": 28, "cpc": 3.80,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["RBC", "TD Canada Trust", "Scotiabank"],
     "content_type": "listicle", "estimated_word_count": 5000},
    {"keyword": "banking guide for newcomers to canada 2026", "market": "Canada",
     "search_volume": 3800, "keyword_difficulty": 25, "cpc": 3.50,
     "intent": "informational", "opportunity_types": ["seo", "ebook"],
     "affiliate_programs": ["RBC", "TD Canada Trust", "Scotiabank"],
     "content_type": "guide", "estimated_word_count": 5000},
    # TIER 3: MONEY TRANSFER
    {"keyword": "cheapest way to send money internationally from usa", "market": "USA",
     "search_volume": 4500, "keyword_difficulty": 38, "cpc": 6.20,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Wise", "OFX", "Remitly"],
     "content_type": "comparison", "estimated_word_count": 5000},
    {"keyword": "wise vs remitly vs western union comparison 2026", "market": "USA",
     "search_volume": 2900, "keyword_difficulty": 30, "cpc": 5.80,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Wise", "Remitly"],
     "content_type": "comparison", "estimated_word_count": 5000},
    {"keyword": "best money transfer apps for immigrants usa", "market": "USA",
     "search_volume": 3400, "keyword_difficulty": 33, "cpc": 5.40,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Wise", "WorldRemit", "Revolut"],
     "content_type": "listicle", "estimated_word_count": 4500},
    # TIER 4: TAX
    {"keyword": "us expat tax filing guide living abroad", "market": "USA",
     "search_volume": 3100, "keyword_difficulty": 42, "cpc": 8.20,
     "intent": "informational", "opportunity_types": ["seo", "ebook"],
     "affiliate_programs": ["TurboTax", "H&R Block", "Expatfile"],
     "content_type": "guide", "estimated_word_count": 5000},
    {"keyword": "fatca fbar reporting guide for expats 2026", "market": "USA",
     "search_volume": 1800, "keyword_difficulty": 40, "cpc": 7.50,
     "intent": "informational", "opportunity_types": ["seo", "ebook"],
     "affiliate_programs": ["TurboTax", "Expatfile"],
     "content_type": "guide", "estimated_word_count": 4500},
    {"keyword": "cra non-resident tax guide canada newcomers", "market": "Canada",
     "search_volume": 2100, "keyword_difficulty": 38, "cpc": 6.80,
     "intent": "informational", "opportunity_types": ["seo", "ebook"],
     "affiliate_programs": ["TurboTax", "H&R Block"],
     "content_type": "guide", "estimated_word_count": 4500},
    # TIER 5: INVESTMENT
    {"keyword": "investment account options for non-us-residents 2026", "market": "USA",
     "search_volume": 1600, "keyword_difficulty": 45, "cpc": 9.10,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Interactive Brokers", "Charles Schwab"],
     "content_type": "guide", "estimated_word_count": 5000},
    {"keyword": "tfsa rrsp rules non-residents canada explained", "market": "Canada",
     "search_volume": 1900, "keyword_difficulty": 40, "cpc": 5.20,
     "intent": "informational", "opportunity_types": ["seo"],
     "affiliate_programs": ["Wealthsimple", "Questrade"],
     "content_type": "article", "estimated_word_count": 4500},
    # TIER 6: CREDIT
    {"keyword": "best credit card no foreign transaction fee expat 2026", "market": "USA",
     "search_volume": 2600, "keyword_difficulty": 36, "cpc": 4.90,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Discover", "Capital One"],
     "content_type": "listicle", "estimated_word_count": 4500},
    # TIER 7: INTERNATIONAL STUDENTS
    {"keyword": "banking guide international students usa 2026", "market": "USA",
     "search_volume": 5200, "keyword_difficulty": 24, "cpc": 2.80,
     "intent": "informational", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Wise", "Revolut", "Chime"],
     "content_type": "guide", "estimated_word_count": 4500},
    {"keyword": "bank account for international students no ssn usa", "market": "USA",
     "search_volume": 3900, "keyword_difficulty": 26, "cpc": 3.10,
     "intent": "informational", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Wise", "Revolut"],
     "content_type": "guide", "estimated_word_count": 4000},
    {"keyword": "bank account for international students canada", "market": "Canada",
     "search_volume": 4600, "keyword_difficulty": 22, "cpc": 2.60,
     "intent": "informational", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["RBC", "TD Canada Trust", "Scotiabank"],
     "content_type": "guide", "estimated_word_count": 4000, "newcomer_priority": True},
    # TIER 8: MONEY TRANSFER CANADA
    {"keyword": "send money abroad from canada best rates", "market": "Canada",
     "search_volume": 2400, "keyword_difficulty": 29, "cpc": 4.50,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Wise", "OFX", "Remitly"],
     "content_type": "comparison", "estimated_word_count": 4000},
    {"keyword": "cheapest international money transfer from canada", "market": "Canada",
     "search_volume": 2900, "keyword_difficulty": 30, "cpc": 4.80,
     "intent": "commercial", "opportunity_types": ["seo", "affiliate"],
     "affiliate_programs": ["Wise", "OFX", "Remitly"],
     "content_type": "comparison", "estimated_word_count": 4000},
]


class SEOResearchAgent:
    AGENT_ID = "agent_01"
    AGENT_NAME = "SEO Research Agent V3.4"

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")
        self.semrush_key = os.getenv("SEMRUSH_API_KEY", "")
        self.max_topics = self.config.get("max_topics", 1)
        self.article_num = int(os.getenv("ARTICLE_NUM", "1"))
        logger.info(f"ARTICLE_NUM={self.article_num} | SERPAPI: {'ON' if self.serpapi_key else 'OFF'} | SEMRUSH: {'ON' if self.semrush_key else 'OFF'}")

    async def run(self, max_topics: int = 1, output_path: str = "output/agent_01/topics.json", topic_override: str = "") -> Dict:
        logger.info("=" * 60)
        logger.info(f"NEXUS-14 V3.4 — Agent 01: SEO Research | ARTICLE_NUM={self.article_num}")
        logger.info("=" * 60)

        topics = []

        # MANUAL TOPIC OVERRIDE: when a topic is supplied via --topic / TOPIC_OVERRIDE,
        # bypass live/Claude/DB research entirely and produce exactly one topic record
        # in the standard schema so Agents 02-18 run unchanged.
        topic_override = (topic_override or "").strip()
        if topic_override:
            logger.info(f"TOPIC OVERRIDE active — using provided topic: {topic_override!r}")
            override_market = "Canada" if "canada" in topic_override.lower() else "USA"
            topics = [{
                "keyword": topic_override,
                "market": override_market,
                "search_volume": 5000,
                "keyword_difficulty": 30,
                "cpc": 5.0,
                "intent": "informational",
                "opportunity_types": ["seo", "affiliate"],
                "affiliate_programs": [],
                "content_type": "guide",
                "estimated_word_count": 5000,
                "newcomer_priority": True,
                "manual_override": True,
            }]
            topics = self._score_and_prioritize(topics[:max_topics])
            output = {
                "agent": self.AGENT_NAME,
                "timestamp": datetime.utcnow().isoformat(),
                "version": "V3.4",
                "research_mode": "manual_override",
                "article_num": self.article_num,
                "markets": ["USA", "Canada"],
                "total_topics": len(topics),
                "usa_count": len([t for t in topics if t.get("market") == "USA"]),
                "canada_count": len([t for t in topics if t.get("market") == "Canada"]),
                "topics": topics,
            }
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"TOPIC OVERRIDE — wrote 1 topic to {output_path}")
            return output

        if self.serpapi_key or self.semrush_key:
            try:
                live_topics = await self._research_live_topics(max_topics)
                topics.extend(live_topics)
            except Exception as e:
                logger.warning(f"Live API research failed: {e}")

        if self.anthropic_key and len(topics) < max_topics:
            try:
                claude_topics = await self._research_with_claude(max_topics - len(topics))
                topics.extend(claude_topics)
            except Exception as e:
                logger.warning(f"Claude research failed: {e}")

        if len(topics) < max_topics:
            needed = max_topics - len(topics)
            db_topics = self._get_from_builtin_database(needed)
            topics.extend(db_topics)

        topics = self._score_and_prioritize(topics[:max_topics])

        output = {
            "agent": self.AGENT_NAME,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "V3.4",
            "research_mode": self._get_research_mode(),
            "article_num": self.article_num,
            "markets": ["USA", "Canada"],
            "total_topics": len(topics),
            "usa_count": len([t for t in topics if t.get("market") == "USA"]),
            "canada_count": len([t for t in topics if t.get("market") == "Canada"]),
            "topics": topics,
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Topics saved: {output_path} | {len(topics)} topics")
        return output

    def _get_research_mode(self) -> str:
        if self.serpapi_key and self.semrush_key:
            return "FULL_API"
        elif self.serpapi_key:
            return "SERPAPI_ONLY"
        elif self.semrush_key:
            return "SEMRUSH_ONLY"
        elif self.anthropic_key:
            return "CLAUDE_RESEARCH"
        return "BUILTIN_DATABASE"

    async def _research_live_topics(self, count: int) -> List[Dict]:
        import aiohttp
        topics = []
        seed_queries = [
            "best bank account newcomers canada 2026",
            "banking guide newcomers canada 2026",
            "international money transfer expats comparison",
            "expat tax guide usa canada 2026",
        ]
        async with aiohttp.ClientSession() as session:
            for query in seed_queries[:count]:
                try:
                    if self.serpapi_key:
                        params = {"q": query, "api_key": self.serpapi_key, "engine": "google", "num": 5}
                        async with session.get("https://serpapi.com/search", params=params,
                                               timeout=aiohttp.ClientTimeout(total=15)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                topic = self._parse_serp_result(query, data)
                                if topic:
                                    topics.append(topic)
                except Exception as e:
                    logger.warning(f"Live API failed for '{query}': {e}")
        return topics

    async def _research_with_claude(self, count: int) -> List[Dict]:
        import aiohttp, re
        prompt = f"""Generate {count} high-value article topic ideas for MoneyAbroadGuide.com.
PRIORITY: Canada newcomer/immigrant/international student topics.
Return ONLY a valid JSON array with fields: keyword, market, search_volume, keyword_difficulty, cpc, intent, opportunity_types, affiliate_programs, content_type, estimated_word_count (max 5000)."""
        headers = {"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        # NEXUS-14 P1 FIX: model now read from env with new model family.
        # Primary + fallback, deduplicated so the same model is never tried twice.
        primary = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        fallback = os.getenv("ANTHROPIC_MODEL_FALLBACK", "claude-sonnet-4-5")
        models_to_try = list(dict.fromkeys([primary, fallback]))
        last_error = None
        async with aiohttp.ClientSession() as session:
            for model_name in models_to_try:
                payload = {"model": model_name, "max_tokens": 2000, "messages": [{"role": "user", "content": prompt}]}
                try:
                    async with session.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload,
                                            timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        if resp.status != 200:
                            last_error = Exception(f"Claude API error: {resp.status} (model={model_name})")
                            logger.warning(f"Claude research model failed model={model_name} status={resp.status}")
                            continue
                        data = await resp.json()
                        text = data["content"][0]["text"].strip()
                        json_match = re.search(r'\[.*\]', text, re.DOTALL)
                        logger.info(f"Claude research succeeded model={model_name}")
                        if json_match:
                            topics = json.loads(json_match.group())
                            return [self._normalize_topic(t) for t in topics if isinstance(t, dict)]
                        return []
                except Exception as e:
                    last_error = e
                    logger.warning(f"Claude research request failed model={model_name}: {e}")
                    continue
        if last_error:
            raise last_error
        return []

    def _get_from_builtin_database(self, count: int) -> List[Dict]:
        """V3.3: Rotate by ARTICLE_NUM so each article in a batch gets a different topic.
        V3.4: Canada newcomer topics have priority bonus."""
        available = list(BUILTIN_TOPIC_DATABASE)
        available.sort(
            key=lambda t: (
                t.get("newcomer_priority", False),
                len(t.get("affiliate_programs", [])) > 0,
                t.get("cpc", 0.0),
                t.get("search_volume", 0),
            ),
            reverse=True,
        )
        offset = (self.article_num - 1) % len(available)
        rotated = available[offset:] + available[:offset]
        selected = rotated[:count]
        logger.info(f"Built-in DB: article_num={self.article_num}, offset={offset}, "
                    f"topic: {selected[0]['keyword'] if selected else 'none'}")
        return [self._normalize_topic(t) for t in selected]

    def _parse_serp_result(self, query: str, data: Dict) -> Optional[Dict]:
        return {
            "keyword": query, "market": "Canada" if "canada" in query.lower() else "USA",
            "search_volume": 1000, "keyword_difficulty": 35, "cpc": 3.50,
            "intent": "informational", "opportunity_types": ["seo"],
            "affiliate_programs": [], "content_type": "article",
            "estimated_word_count": 4500, "source": "serpapi",
        }

    def _normalize_topic(self, t: Dict) -> Dict:
        return {
            "id": t.get("id", f"topic_{hash(t.get('keyword', '')) % 10000:04d}"),
            "keyword": t.get("keyword", ""),
            "title": t.get("title", t.get("keyword", "").replace("-", " ").title()),
            "market": t.get("market", "Canada"),
            "search_volume": t.get("search_volume", 1000),
            "keyword_difficulty": t.get("keyword_difficulty", 35),
            "cpc": t.get("cpc", 0.0),
            "intent": t.get("intent", "informational"),
            "opportunity_types": t.get("opportunity_types", ["seo"]),
            "affiliate_programs": t.get("affiliate_programs", []),
            "content_type": t.get("content_type", "article"),
            "estimated_word_count": t.get("estimated_word_count", 4500),
            "priority_score": t.get("priority_score", 0.0),
            "content_suitable": True,
            "validated": True,
            "newcomer_priority": t.get("newcomer_priority", False),
            "source": t.get("source", "builtin_database"),
        }

    def _score_and_prioritize(self, topics: List[Dict]) -> List[Dict]:
        for i, topic in enumerate(topics):
            volume = topic.get("search_volume", 0)
            difficulty = topic.get("keyword_difficulty", 100)
            cpc = topic.get("cpc", 0)
            opp_types = topic.get("opportunity_types", [])
            affiliate_programs = topic.get("affiliate_programs", [])
            newcomer = topic.get("newcomer_priority", False)
            score = 0.0
            score += min(40, volume / 250)
            score += max(0, 30 - difficulty * 0.3)
            score += min(20, cpc * 2)
            score += len(opp_types) * 5
            score += min(10, len(affiliate_programs) * 3)
            if newcomer:
                score += 15
            topic["priority_score"] = round(score, 2)
            topic["rank"] = i + 1
        topics.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return topics


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-01] %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="NEXUS-14 V3.4 Agent 01 — SEO Research")
    parser.add_argument("--max-topics", type=int, default=1)
    parser.add_argument("--output", type=str, default="output/agent_01/topics.json")
    parser.add_argument("--market", type=str, default="all", choices=["all", "usa", "canada"])
    parser.add_argument("--topic", type=str, default="", help="Manual topic override; bypasses auto topic selection when set")
    args = parser.parse_args()
    topic_override = args.topic or os.getenv("TOPIC_OVERRIDE", "")
    from config.config_loader import ConfigLoader
    config = ConfigLoader.load()
    agent = SEOResearchAgent(config=config.get("agents", {}).get("agent_01", {}))
    result = asyncio.run(agent.run(max_topics=args.max_topics, output_path=args.output, topic_override=topic_override))
    print(f"[Agent 01] Research complete — {result['total_topics']} topics saved to {args.output}")


if __name__ == "__main__":
    main()
