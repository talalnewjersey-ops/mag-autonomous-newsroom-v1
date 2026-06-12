"""
NEXUS-14 V3: Agent 02 - Keyword Validation Agent
MoneyAbroadGuide.com Autonomous Newsroom

Validates and prioritizes keywords from Agent 01's output.
Input:  output/agent_01/topics.json
Output: output/agent_02/validated_topics.json

V3 UPDATE: No external API dependencies.
All validation is done via:
  - Claude AI (LLM-enhanced scoring, optional)
  - Internal scoring algorithms
  - Built-in intent classification

SERPAPI and SEMRUSH are NOT used in Agent 02.
Production NEVER fails due to missing API keys.

CLI: python -m agents.agent_02_keyword_validation --input ... --output ...
"""

import argparse
import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)


class KeywordValidationAgent:
    """
    Agent 02 V3: Keyword Validation Agent
    Zero external API dependencies.
    Optional Claude enhancement when ANTHROPIC_API_KEY is available.
    """

    AGENT_ID = "agent_02"
    AGENT_NAME = "Keyword Validation Agent V3"

    # Intent classification patterns
    COMMERCIAL_PATTERNS = ["best", "top", "compare", "review", "vs", "alternative", "cheapest", "cheapest way"]
    TRANSACTIONAL_PATTERNS = ["buy", "open", "sign up", "apply", "get", "download", "start"]
    INFORMATIONAL_PATTERNS = ["how", "what", "why", "guide", "tutorial", "explained", "meaning"]

    # Quality thresholds
    MIN_PRIORITY_SCORE = 10.0  # Lowered from 20.0 — built-in topics are pre-qualified
    MAX_KEYWORD_LENGTH = 100
    MIN_WORD_COUNT = 3

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.seen_normalized: Set[str] = set()

        if self.anthropic_key:
            logger.info("ANTHROPIC_API_KEY detected — LLM-enhanced validation enabled")
        else:
            logger.info("ANTHROPIC_API_KEY not set — using algorithmic validation (production continues)")

    async def run(self, input_path: str = "output/agent_01/topics.json",
                  output_path: str = "output/agent_02/validated_topics.json") -> Dict:
        """Main execution. Always succeeds."""
        logger.info("=" * 60)
        logger.info("NEXUS-14 V3 — Agent 02: Keyword Validation Starting")
        logger.info(f"Input: {input_path}")
        logger.info(f"Output: {output_path}")
        logger.info("=" * 60)

        # Load topics from Agent 01
        raw_topics = self._load_topics(input_path)
        logger.info(f"Loaded {len(raw_topics)} topics from Agent 01")

        # Phase 1: Deduplicate
        deduped = self._remove_duplicates(raw_topics)
        logger.info(f"After deduplication: {len(deduped)} topics")

        # Phase 2: Classify intent
        intent_classified = self._classify_intent(deduped)

        # Phase 3: Quality filter
        quality_filtered = self._quality_filter(intent_classified)
        logger.info(f"After quality filter: {len(quality_filtered)} topics")

        # Phase 4: LLM enhancement (optional, graceful fallback)
        if self.anthropic_key and quality_filtered:
            try:
                enhanced = await self._llm_enhance(quality_filtered)
                quality_filtered = enhanced
                logger.info("LLM enhancement applied successfully")
            except Exception as e:
                logger.warning(f"LLM enhancement failed (using algorithmic scores): {e}")

        # Phase 5: Final scoring + sort
        final_topics = self._final_score_and_sort(quality_filtered)

        # Phase 6: Categorize into content hubs
        hubs = self._categorize_into_hubs(final_topics)

        output = {
            "agent": self.AGENT_NAME,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "V3",
            "validation_mode": "LLM_ENHANCED" if self.anthropic_key else "ALGORITHMIC",
            "raw_count": len(raw_topics),
            "validated_count": len(final_topics),
            "rejection_rate": round(1 - len(final_topics) / max(len(raw_topics), 1), 2),
            "topics": final_topics,
            "hubs": hubs,
            "statistics": self._compute_statistics(final_topics),
        }

        # Save output
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Validated topics saved to: {output_path}")
        logger.info(f"Agent 02 COMPLETE — {len(final_topics)} validated topics ready")

        return output

    def _load_topics(self, input_path: str) -> List[Dict]:
        """Load topics from Agent 01 output. Returns empty list gracefully."""
        try:
            p = Path(input_path)
            if not p.exists():
                logger.warning(f"Input file not found: {input_path}. Using empty topic list.")
                return []
            data = json.loads(p.read_text(encoding="utf-8"))
            # Handle both raw list and wrapped format
            if isinstance(data, list):
                return data
            return data.get("topics", [])
        except Exception as e:
            logger.warning(f"Failed to load topics from {input_path}: {e}. Continuing with empty list.")
            return []

    def _remove_duplicates(self, topics: List[Dict]) -> List[Dict]:
        """Remove duplicate and near-duplicate topics."""
        unique = []
        seen_normalized: Set[str] = set()
        seen_first_three: Set[str] = set()

        for topic in topics:
            keyword = topic.get("keyword", "")
            normalized = " ".join(keyword.lower().strip().split())

            if len(normalized.split()) < self.MIN_WORD_COUNT:
                continue
            if normalized in seen_normalized:
                continue

            first_three = " ".join(normalized.split()[:3])
            if first_three in seen_first_three:
                # Keep higher priority score
                existing = next(
                    (t for t in unique if " ".join(t.get("keyword", "").lower().split()[:3]) == first_three),
                    None
                )
                if existing and topic.get("priority_score", 0) > existing.get("priority_score", 0):
                    unique.remove(existing)
                    seen_first_three.discard(first_three)
                else:
                    continue

            seen_normalized.add(normalized)
            seen_first_three.add(first_three)
            unique.append(topic)

        return unique

    def _classify_intent(self, topics: List[Dict]) -> List[Dict]:
        """Classify and validate search intent."""
        classified = []
        for topic in topics:
            keyword = topic.get("keyword", "").lower()
            intent = topic.get("intent", "")

            if intent not in ["informational", "commercial", "transactional", "navigational"]:
                if any(p in keyword for p in self.TRANSACTIONAL_PATTERNS):
                    intent = "transactional"
                elif any(p in keyword for p in self.COMMERCIAL_PATTERNS):
                    intent = "commercial"
                elif any(p in keyword for p in self.INFORMATIONAL_PATTERNS):
                    intent = "informational"
                else:
                    intent = "informational"

            topic["intent"] = intent
            topic["content_suitable"] = intent in ["informational", "commercial"]

            # Accept transactional if high CPC value
            if intent == "transactional" and topic.get("cpc", 0) > 2.0:
                topic["content_suitable"] = True

            if topic["content_suitable"]:
                classified.append(topic)

        return classified

    def _quality_filter(self, topics: List[Dict]) -> List[Dict]:
        """Apply quality filters."""
        filtered = []
        for topic in topics:
            keyword = topic.get("keyword", "")
            if len(keyword) > self.MAX_KEYWORD_LENGTH:
                continue
            if topic.get("priority_score", 100) < self.MIN_PRIORITY_SCORE:
                # Re-calculate score if zero
                if topic.get("priority_score", 0) == 0:
                    topic["priority_score"] = self._calculate_score(topic)
                if topic.get("priority_score", 0) < self.MIN_PRIORITY_SCORE:
                    continue
            filtered.append(topic)
        return filtered

    async def _llm_enhance(self, topics: List[Dict]) -> List[Dict]:
        """Use Claude to enhance topic scoring with editorial intelligence."""
        import aiohttp

        top_topics = sorted(topics, key=lambda x: x.get("priority_score", 0), reverse=True)[:20]
        topics_summary = [
            f"- {t['keyword']} (score: {t.get('priority_score', 0):.1f}, market: {t.get('market', 'USA')})"
            for t in top_topics
        ]

        prompt = f"""You are an SEO content strategist for MoneyAbroadGuide.com.

Rate these keyword opportunities for the expat finance niche (1-10 content potential):

{chr(10).join(topics_summary)}

Return ONLY a JSON array:
[{{"keyword": "...", "llm_score": X, "angle": "one-sentence article angle"}}]"""

        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-3-5-haiku-20241022",
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Claude API error: {resp.status}")
                data = await resp.json()
                text = data["content"][0]["text"].strip()

                json_match = re.search(r'\[.*\]', text, re.DOTALL)
                if json_match:
                    llm_scores = json.loads(json_match.group())
                    score_map = {item["keyword"].lower(): item for item in llm_scores}
                    for topic in topics:
                        kw_lower = topic.get("keyword", "").lower()
                        if kw_lower in score_map:
                            llm_data = score_map[kw_lower]
                            topic["llm_score"] = llm_data.get("llm_score", 5)
                            topic["content_angle"] = llm_data.get("angle", "")
                            # Blend algorithmic + LLM score
                            topic["priority_score"] = round(
                                topic.get("priority_score", 0) * 0.7 + topic["llm_score"] * 10 * 0.3, 2
                            )
        return topics

    def _final_score_and_sort(self, topics: List[Dict]) -> List[Dict]:
        """Final scoring, enrichment, and sort."""
        for i, topic in enumerate(topics):
            if topic.get("priority_score", 0) == 0:
                topic["priority_score"] = self._calculate_score(topic)
            topic["rank"] = i + 1
            topic.setdefault("keyword", "")
            topic.setdefault("market", "USA")
            topic.setdefault("opportunity_types", ["seo"])
            topic.setdefault("content_suitable", True)
            topic.setdefault("validated", True)
            topic["estimated_word_count"] = topic.get("estimated_word_count") or self._estimate_word_count(topic)
            topic["content_type"] = topic.get("content_type") or self._determine_content_type(topic)

        topics.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return topics

    def _categorize_into_hubs(self, topics: List[Dict]) -> Dict:
        """Categorize topics into content hubs."""
        hubs = {
            "usa_banking": [], "usa_investment": [], "usa_tax": [],
            "usa_money_transfer": [], "usa_students": [],
            "canada_banking": [], "canada_newcomers": [], "canada_tax": [],
            "canada_money_transfer": [],
        }
        for topic in topics:
            kw = topic.get("keyword", "").lower()
            market = topic.get("market", "USA").lower()
            kw_entry = topic["keyword"]
            if market == "usa":
                if any(k in kw for k in ["student", "f-1", "f1", "visa"]):
                    hubs["usa_students"].append(kw_entry)
                elif any(k in kw for k in ["bank", "account", "credit", "savings"]):
                    hubs["usa_banking"].append(kw_entry)
                elif any(k in kw for k in ["invest", "etf", "stock", "brokerage"]):
                    hubs["usa_investment"].append(kw_entry)
                elif any(k in kw for k in ["tax", "fatca", "fbar", "irs"]):
                    hubs["usa_tax"].append(kw_entry)
                elif any(k in kw for k in ["transfer", "send", "wire", "remit"]):
                    hubs["usa_money_transfer"].append(kw_entry)
            elif market == "canada":
                if any(k in kw for k in ["newcomer", "new to", "immigrant", "arrive"]):
                    hubs["canada_newcomers"].append(kw_entry)
                elif any(k in kw for k in ["bank", "account", "credit", "savings"]):
                    hubs["canada_banking"].append(kw_entry)
                elif any(k in kw for k in ["tax", "cra", "tfsa", "rrsp"]):
                    hubs["canada_tax"].append(kw_entry)
                elif any(k in kw for k in ["transfer", "send", "wire", "remit"]):
                    hubs["canada_money_transfer"].append(kw_entry)
        return hubs

    def _calculate_score(self, topic: Dict) -> float:
        score = 0.0
        score += min(40, topic.get("search_volume", 0) / 250)
        score += max(0, 30 - topic.get("keyword_difficulty", 100) * 0.3)
        score += min(20, topic.get("cpc", 0) * 2)
        score += len(topic.get("opportunity_types", [])) * 5
        return round(score, 2)

    def _estimate_word_count(self, topic: Dict) -> int:
        base = 5000
        kw = topic.get("keyword", "").lower()
        if topic.get("keyword_difficulty", 0) > 50:
            base = 7000
        if "guide" in kw or "complete" in kw or "comprehensive" in kw:
            base = 8000
        return base

    def _determine_content_type(self, topic: Dict) -> str:
        kw = topic.get("keyword", "").lower()
        if "vs" in kw or "compare" in kw or "comparison" in kw:
            return "comparison"
        elif "guide" in kw or "how to" in kw or "how " in kw:
            return "guide"
        elif "best" in kw or "top" in kw:
            return "listicle"
        return "article"

    def _compute_statistics(self, topics: List[Dict]) -> Dict:
        if not topics:
            return {"total_validated": 0}
        volumes = [t.get("search_volume", 0) for t in topics]
        difficulties = [t.get("keyword_difficulty", 0) for t in topics]
        return {
            "total_validated": len(topics),
            "usa_count": len([t for t in topics if t.get("market") == "USA"]),
            "canada_count": len([t for t in topics if t.get("market") == "Canada"]),
            "avg_search_volume": round(sum(volumes) / len(volumes), 0) if volumes else 0,
            "avg_difficulty": round(sum(difficulties) / len(difficulties), 1) if difficulties else 0,
            "informational_count": len([t for t in topics if t.get("intent") == "informational"]),
            "commercial_count": len([t for t in topics if t.get("intent") == "commercial"]),
            "affiliate_opportunities": len([t for t in topics if "affiliate" in t.get("opportunity_types", [])]),
            "ebook_opportunities": len([t for t in topics if "ebook" in t.get("opportunity_types", [])]),
        }


def main():
    """CLI entry point: python -m agents.agent_02_keyword_validation --input ... --output ..."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-02] %(levelname)s %(message)s"
    )

    parser = argparse.ArgumentParser(description="NEXUS-14 V3 Agent 02 — Keyword Validation")
    parser.add_argument("--input", type=str, default="output/agent_01/topics.json")
    parser.add_argument("--output", type=str, default="output/agent_02/validated_topics.json")
    args = parser.parse_args()

    from config.config_loader import ConfigLoader
    config = ConfigLoader.load()

    agent = KeywordValidationAgent(config=config.get("agents", {}).get("agent_02", {}))
    result = asyncio.run(agent.run(input_path=args.input, output_path=args.output))
    print(f"[Agent 02] Validation complete — {result['validated_count']} topics saved to {args.output}")


if __name__ == "__main__":
    main()
