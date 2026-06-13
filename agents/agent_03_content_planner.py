"""
NEXUS-14: Agent 03 - Content Planner Agent
Creates comprehensive article outlines with H2/H3 structure,
FAQ, tables, and case studies.
Input: validated_topics.json
Output: article_outline.json

V3.3: Multi-model fallback + detailed HTTP error logging
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Models to try in order (fallback chain)
CLAUDE_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
    "claude-3-sonnet-20240229",
]

# ============================================================
# STANDALONE MAIN -- CLI entry point for workflow execution
# ============================================================

def main():
    """CLI entry point: called by workflow as python -m agents.agent_03_content_planner ..."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-03] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S,%f"
    )

    parser = argparse.ArgumentParser(description="Agent 03 - Content Planner")
    parser.add_argument("--input", required=True, help="Path to validated_topics.json")
    parser.add_argument("--output", required=True, help="Output path for article_outline.json")
    args = parser.parse_args()

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set -- cannot plan content")
        sys.exit(1)

    logger.info(f"API key present: length={len(anthropic_api_key)}, prefix={anthropic_api_key[:12]}...")

    # Load validated topics
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Topics file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        topics_data = json.load(f)
    logger.info(f"Loaded topics from: {input_path}")

    # Extract first topic
    if isinstance(topics_data, dict):
        topics = topics_data.get("topics", [])
    elif isinstance(topics_data, list):
        topics = topics_data
    else:
        topics = [topics_data]

    if not topics:
        logger.error("No topics found in input file")
        sys.exit(1)

    topic = topics[0]
    if not isinstance(topic, dict):
        topic = {"keyword": str(topic), "market": "USA", "intent": "informational"}

    logger.info(f"Planning content for: {topic.get('keyword', 'Unknown')}")

    # Plan the article outline
    try:
        outline = asyncio.run(_plan_outline_standalone(topic, anthropic_api_key))
    except Exception as e:
        logger.error(f"Content planning failed: {e}")
        sys.exit(1)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(outline, indent=2, ensure_ascii=False), encoding="utf-8")
    file_size = output_path.stat().st_size
    logger.info(f"Outline written: {output_path} ({file_size} bytes)")
    logger.info(f"Article title: {outline.get('title', 'Unknown')}")
    logger.info(f"Sections planned: {len(outline.get('sections', []))}")
    logger.info(f"FAQ questions: {len(outline.get('faq', []))}")
    sys.exit(0)

# ============================================================
# CLAUDE API CALL WITH MULTI-MODEL FALLBACK
# ============================================================

async def _call_claude_with_fallback(api_key: str, prompt: str, max_tokens: int = 3000) -> str:
    """Call Anthropic Claude API with multi-model fallback chain."""
    import urllib.request
    import urllib.error

    last_error = None
    for model in CLAUDE_MODELS:
        logger.info(f"Trying model: {model}")
        payload = json.dumps({
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                logger.info(f"Success with model: {model}")
                return data["content"][0]["text"]
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            logger.warning(f"Model {model} failed: HTTP {e.code} {e.reason} | Body: {body}")
            last_error = f"HTTP Error {e.code}: {e.reason} | {body}"
            if e.code in (401, 403):
                # Auth error - no point trying other models
                raise Exception(f"Authentication failed: {last_error}")
            # 404 or other - try next model
            continue
        except Exception as ex:
            logger.warning(f"Model {model} failed with exception: {ex}")
            last_error = str(ex)
            continue

    raise Exception(f"All Claude models failed. Last error: {last_error}")


# Keep old name for backward compatibility
async def _call_claude_03(api_key: str, prompt: str, max_tokens: int = 3000) -> str:
    return await _call_claude_with_fallback(api_key, prompt, max_tokens)


async def _plan_outline_standalone(topic: Dict, api_key: str) -> Dict:
    """Create a comprehensive article outline using Claude."""
    keyword = topic.get("keyword", "")
    market = topic.get("market", "USA")
    intent = topic.get("intent", "informational")
    year = datetime.utcnow().year

    prompt = (
        f"Create a comprehensive article outline for MoneyAbroadGuide.com.\n\n"
        f"Primary keyword: {keyword}\n"
        f"Target market: {market}\n"
        f"Search intent: {intent}\n"
        f"Target word count: 7,500 words\n\n"
        "Create a detailed outline with:\n"
        "1. SEO-optimized title (H1) - include keyword naturally\n"
        "2. Meta description (150-160 chars)\n"
        "3. Introduction hook data\n"
        "4. 6-8 H2 sections, each with 2-3 H3 subsections\n"
        "5. 8-10 FAQ questions\n"
        "6. 2-3 comparison tables\n"
        "7. 1-2 case studies\n"
        "8. Key takeaways (5 bullet points)\n"
        "9. Call-to-action\n\n"
        "Return ONLY valid JSON with this structure (no markdown, no explanation):\n"
        "{\n"
        " \"title\": \"...\"\n"
        " \"meta_description\": \"...\"\n"
        " \"primary_keyword\": \"...\"\n"
        " \"secondary_keywords\": [\"...\"]\n"
        " \"market\": \"...\"\n"
        " \"target_audience\": \"...\"\n"
        " \"search_intent\": \"...\"\n"
        " \"hook_data\": {\"statistic\": \"...\", \"question\": \"...\"}\n"
        " \"sections\": [{\"h2\": \"...\", \"h3\": [\"...\"], \"data\": [\"...\"]}]\n"
        " \"faq\": [\"question 1?\", \"question 2?\"]\n"
        " \"key_takeaways\": [\"...\"]\n"
        " \"call_to_action\": \"...\"\n"
        " \"internal_link_opportunities\": [\"...\"]\n"
        " \"affiliate_opportunities\": [\"...\"]\n"
        "}"
    )

    logger.info("Calling Claude to generate outline...")
    response = await _call_claude_with_fallback(api_key, prompt, max_tokens=3000)

    # Parse JSON from response
    try:
        outline = json.loads(response)
        logger.info("Outline JSON parsed successfully (direct)")
    except json.JSONDecodeError:
        json_match = re.search(r"{.*}", response, re.DOTALL)
        if json_match:
            try:
                outline = json.loads(json_match.group())
                logger.info("Outline JSON parsed successfully (extracted)")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed: {e} -- using fallback outline")
                outline = _build_fallback_outline(topic)
        else:
            logger.warning("No JSON found in response -- using fallback outline")
            outline = _build_fallback_outline(topic)

    outline.setdefault("primary_keyword", keyword)
    outline.setdefault("market", market)
    outline.setdefault("search_intent", intent)
    outline.setdefault("topic_data", topic)

    if not outline.get("sections"):
        outline["sections"] = _build_fallback_outline(topic)["sections"]

    if not outline.get("faq"):
        outline["faq"] = _build_fallback_outline(topic)["faq"]

    return outline


def _build_fallback_outline(topic: Dict) -> Dict:
    """Fallback outline when LLM fails to produce valid JSON."""
    keyword = topic.get("keyword", "expat banking")
    market = topic.get("market", "USA")
    year = datetime.utcnow().year
    return {
        "title": f"Complete Guide to {keyword.title()} ({market} {year})",
        "meta_description": f"Everything you need to know about {keyword} for {market} expatriates in {year}.",
        "primary_keyword": keyword,
        "secondary_keywords": [f"{keyword} guide", f"best {keyword}", f"{keyword} {market}"],
        "market": market,
        "target_audience": "expatriates and non-residents",
        "search_intent": topic.get("intent", "informational"),
        "estimated_word_count": 7500,
        "hook_data": {
            "statistic": f"Over 50 million people are living abroad and need {keyword} solutions.",
            "question": f"What is the best {keyword} option for {market} expatriates in {year}?"
        },
        "sections": [
            {"h2": f"What is {keyword.title()}?", "h3": ["Overview", "Why It Matters for Expats"], "data": []},
            {"h2": "Best Options Compared", "h3": ["Top Picks", "Comparison Table", "Pros and Cons"], "data": []},
            {"h2": "How to Get Started", "h3": ["Step-by-Step Guide", "Requirements", "Timeline"], "data": []},
            {"h2": "Costs and Fees", "h3": ["Fee Structures", "Hidden Costs", "Cost Comparison"], "data": []},
            {"h2": "Eligibility Requirements", "h3": ["Who Qualifies", "Documents Needed", "Country Restrictions"], "data": []},
            {"h2": "Common Mistakes to Avoid", "h3": ["Top Pitfalls", "Expert Tips", "Best Practices"], "data": []},
        ],
        "faq": [
            f"What is the best {keyword} for {market} expats?",
            f"How does {keyword} work for non-residents?",
            f"What are the requirements for {keyword}?",
            f"How much does {keyword} cost?",
            f"Is {keyword} safe and regulated?",
            f"How long does {keyword} take?",
            f"Can I use {keyword} from abroad?",
            f"What alternatives to {keyword} exist?",
        ],
        "key_takeaways": [
            f"{keyword.title()} is essential for {market} expatriates",
            "Compare multiple options before choosing",
            "Consider fees, exchange rates, and regulations",
            "Check eligibility requirements in advance",
            "Start the process early to avoid delays",
        ],
        "call_to_action": f"Ready to find the best {keyword}? Compare your options below.",
        "internal_link_opportunities": [],
        "affiliate_opportunities": [],
        "topic_data": topic
    }


# ============================================================
# CLASS-BASED AGENT (kept for backward compatibility)
# ============================================================

try:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService
    from services.storage_service import StorageService

    class ContentPlannerAgent(BaseAgent):
        """Agent 03: class-based wrapper (for DI orchestrators)."""
        AGENT_ID = "agent_03"
        AGENT_NAME = "Content Planner Agent"

        def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
            super().__init__(config, llm_service, storage_service)

        async def run(self, context: Dict = None) -> Dict:
            self.log_start()
            try:
                topics_data = await self._load_topics()
                topics = topics_data.get("topics", []) if isinstance(topics_data, dict) else topics_data
                if not topics:
                    raise ValueError("No topics found")
                topic = topics[0] if isinstance(topics[0], dict) else {"keyword": str(topics[0])}
                api_key = self.config.get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
                outline = await _plan_outline_standalone(topic, api_key)
                output_path = await self.save_output("article_outline.json", outline)
                self.log_complete({"sections": len(outline.get("sections", []))})
                return {"outline": outline, "output_path": str(output_path)}
            except Exception as e:
                self.log_error(e)
                raise

        async def _load_topics(self) -> Dict:
            paths = ["output/agent_02/validated_topics.json", "output/validated_topics.json"]
            for path in paths:
                if os.path.exists(path):
                    with open(path) as f:
                        return json.load(f)
            raise FileNotFoundError("validated_topics.json not found")

except ImportError:
    pass  # No BaseAgent -- standalone mode only

if __name__ == "__main__":
    main()
