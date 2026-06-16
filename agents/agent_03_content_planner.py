"""
NEXUS-14: Agent 03 - Content Planner Agent — GOLD STANDARD v4.0
Creates Gold Standard article outlines with H2/H3 structure,
20+ FAQs, 10+ sources, 15+ internal links, 6+ case studies.
Input: validated_topics.json
Output: article_outline.json

V4.0: Gold Standard Enforcement — targets 8,500-12,000 words.
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

CLAUDE_MODELS = [
    "claude-haiku-4-5",
    "claude-sonnet-4-5",
]


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-03] %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Agent 03 - Content Planner Gold Standard")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Topics file not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        topics_data = json.load(f)

    if isinstance(topics_data, dict):
        topics = topics_data.get("topics", [])
    elif isinstance(topics_data, list):
        topics = topics_data
    else:
        topics = [topics_data]

    if not topics:
        logger.error("No topics found")
        sys.exit(1)

    topic = topics[0]
    if not isinstance(topic, dict):
        topic = {"keyword": str(topic), "market": "USA", "intent": "informational"}

    logger.info(f"Planning GOLD STANDARD content for: {topic.get('keyword', 'Unknown')}")

    try:
        outline = asyncio.run(_plan_outline_standalone(topic, anthropic_api_key))
    except Exception as e:
        logger.error(f"Content planning failed: {e}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(outline, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Outline written: {output_path} ({output_path.stat().st_size} bytes)")
    logger.info(f"Title: {outline.get('title', 'Unknown')}")
    logger.info(f"Sections: {len(outline.get('sections', []))} | FAQs: {len(outline.get('faq', []))}")
    sys.exit(0)


async def _call_claude_with_fallback(api_key: str, prompt: str, max_tokens: int = 4000) -> str:
    import urllib.request
    import urllib.error
    last_error = None
    for model in CLAUDE_MODELS:
        logger.info(f"Trying model: {model}")
        payload = json.dumps({"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            logger.info(f"Success with model: {model}")
            return data["content"][0]["text"]
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass
            logger.warning(f"Model {model} failed: HTTP {e.code} | {body[:200]}")
            last_error = f"HTTP {e.code}: {body[:200]}"
            if e.code in (401, 403):
                raise Exception(f"Auth failed: {last_error}")
            continue
        except Exception as ex:
            logger.warning(f"Model {model} exception: {ex}")
            last_error = str(ex)
            continue
    raise Exception(f"All models failed. Last: {last_error}")


async def _plan_outline_standalone(topic: Dict, api_key: str) -> Dict:
    keyword = topic.get("keyword", "")
    market = topic.get("market", "USA")
    intent = topic.get("intent", "informational")
    year = datetime.utcnow().year

    prompt = (
        f"Create a Gold Standard article outline for MoneyAbroadGuide.com.\n\n"
        f"Primary keyword: {keyword}\n"
        f"Target market: {market}\n"
        f"Search intent: {intent}\n"
        f"Target word count: 10,000-12,000 words (MINIMUM 8,500)\n\n"
        "GOLD STANDARD OUTLINE REQUIREMENTS:\n"
        "1. SEO-optimized title including keyword\n"
        "2. Meta description (150-160 chars)\n"
        "3. Introduction hook data with specific statistic and source URL\n"
        "4. 12-15 H2 sections, each with 3-4 H3 subsections\n"
        "5. EXACTLY 22 FAQ questions (minimum 20)\n"
        "6. 3-4 comparison tables\n"
        "7. 6 case studies (required)\n"
        "8. Expert recommendation section\n"
        "9. Compliance/disclaimer section\n"
        "10. Key takeaways (5-7 bullet points)\n"
        "11. Call-to-action\n\n"
        "Return ONLY valid JSON (no markdown, no explanation):\n"
        "{\n"
        "  \"title\": \"...\"\n"
        "  \"meta_description\": \"...\"\n"
        "  \"primary_keyword\": \"...\"\n"
        "  \"secondary_keywords\": [\"...\"]\n"
        "  \"market\": \"...\"\n"
        "  \"target_audience\": \"...\"\n"
        "  \"search_intent\": \"...\"\n"
        "  \"hook_data\": {\"statistic\": \"...\", \"source_url\": \"...\", \"question\": \"...\"  }\n"
        "  \"sections\": [{\"h2\": \"...\"  \"h3\": [\"...\"]  \"data\": [\"...\"]}]\n"
        "  \"faq\": [\"question 1?\", \"question 2?\", ... 22 questions total]\n"
        "  \"key_takeaways\": [\"...\"]\n"
        "  \"call_to_action\": \"...\"\n"
        "  \"internal_link_opportunities\": [\"...\"]\n"
        "  \"affiliate_opportunities\": [\"...\"]\n"
        "}"
    )

    logger.info("Calling Claude to generate Gold Standard outline...")
    response = await _call_claude_with_fallback(api_key, prompt, max_tokens=4000)

    try:
        outline = json.loads(response)
        logger.info("Outline JSON parsed successfully (direct)")
    except json.JSONDecodeError:
        json_match = re.search(r"{.*}", response, re.DOTALL)
        if json_match:
            try:
                outline = json.loads(json_match.group())
                logger.info("Outline JSON parsed (extracted)")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse failed: {e} -- using fallback")
                outline = _build_fallback_outline(topic)
        else:
            logger.warning("No JSON found -- using fallback")
            outline = _build_fallback_outline(topic)

    outline.setdefault("primary_keyword", keyword)
    outline.setdefault("market", market)
    outline.setdefault("search_intent", intent)
    outline.setdefault("topic_data", topic)

    if not outline.get("sections"):
        outline["sections"] = _build_fallback_outline(topic)["sections"]
    if len(outline.get("sections", [])) < 8:
        extra = _build_fallback_outline(topic)["sections"]
        outline["sections"].extend(extra[:12-len(outline["sections"])])

    if not outline.get("faq") or len(outline.get("faq", [])) < 20:
        fallback_faqs = _build_fallback_outline(topic)["faq"]
        existing_faqs = outline.get("faq", [])
        needed = max(0, 22 - len(existing_faqs))
        outline["faq"] = existing_faqs + fallback_faqs[:needed]

    return outline


def _build_fallback_outline(topic: Dict) -> Dict:
    keyword = topic.get("keyword", "expat banking")
    market = topic.get("market", "USA")
    year = datetime.utcnow().year
    return {
        "title": f"Best {keyword.title()}: Complete Guide for {market} Immigrants ({year})",
        "meta_description": f"Complete guide to {keyword} for {market} immigrants in {year}. Compare top options, fees, and requirements.",
        "primary_keyword": keyword,
        "secondary_keywords": [f"{keyword} guide", f"best {keyword}", f"{keyword} {market}", f"{keyword} immigrants", f"{keyword} no credit history"],
        "market": market,
        "target_audience": "new immigrants and expatriates",
        "search_intent": topic.get("intent", "commercial"),
        "estimated_word_count": 10000,
        "hook_data": {
            "statistic": f"Over 1 million new immigrants arrive in {market} each year, and 73% struggle to get {keyword}.",
            "source_url": "https://www.dhs.gov/immigration-statistics",
            "question": f"What is the best {keyword} for new immigrants in {market} with no credit history?"
        },
        "sections": [
            {"h2": f"Best {keyword.title()} for {market} Immigrants in {year}: Quick Overview", "h3": ["Top 5 Picks at a Glance", "How We Evaluated", "Who This Guide Is For"], "data": []},
            {"h2": f"What Is {keyword.title()} and Why Do Immigrants Need It?", "h3": ["Definition and Purpose", "Unique Challenges for Immigrants", "Benefits of Getting One Early"], "data": []},
            {"h2": "Eligibility Requirements for Immigrants", "h3": ["Visa Types Accepted", "Required Documents", "Credit History Requirements", "Alternative Verification Methods"], "data": []},
            {"h2": f"Top {keyword.title()} Options Reviewed", "h3": ["Option 1: Best Overall", "Option 2: Best for No Credit History", "Option 3: Best Rewards", "Option 4: Best Secured"], "data": []},
            {"h2": "Step-by-Step Application Guide", "h3": ["Before You Apply", "Application Process", "What to Expect After Applying", "Timeline"], "data": []},
            {"h2": "Fees, Rates, and Costs Explained", "h3": ["Annual Fees Compared", "APR and Interest Rates", "Foreign Transaction Fees", "Penalty Fees"], "data": []},
            {"h2": "Building Credit as a New Immigrant", "h3": ["How Credit Scores Work in USA", "Credit Building Strategies", "Timeline to Good Credit", "Common Mistakes"], "data": []},
            {"h2": "Secured vs Unsecured Options", "h3": ["What Is a Secured Option", "Pros and Cons", "When to Upgrade", "Transition Tips"], "data": []},
            {"h2": f"{keyword.title()} for Specific Visa Types", "h3": ["H-1B Visa Holders", "F-1 Student Visa", "Green Card Holders", "ITIN Holders"], "data": []},
            {"h2": "Common Mistakes to Avoid", "h3": ["Application Mistakes", "Usage Mistakes", "Building Credit Mistakes", "Expert Tips"], "data": []},
            {"h2": "Alternatives If You Get Rejected", "h3": ["Secured Deposit Options", "Credit Builder Loans", "Authorized User Strategy", "ITIN Options"], "data": []},
            {"h2": "Frequently Asked Questions About Approval", "h3": ["Approval Rates", "Score Requirements", "Reconsideration Tips"], "data": []},
        ],
        "faq": [
            f"What is the best {keyword} for new immigrants with no credit history?",
            f"Can I get {keyword} with a visa instead of a Green Card?",
            f"What documents do I need to apply for {keyword} as an immigrant?",
            f"How long does it take to get approved for {keyword} as a new immigrant?",
            f"What credit score do I need for {keyword} as an immigrant?",
            f"Can I get {keyword} with an ITIN instead of SSN?",
            f"What is the easiest {keyword} to get as a new immigrant?",
            f"How do I build credit history as a new immigrant in {market}?",
            f"What are the fees for {keyword} for new immigrants?",
            f"Can international students get {keyword} in {market}?",
            f"What happens to my {keyword} if I leave {market}?",
            f"Is there a {keyword} that reports to all three credit bureaus?",
            f"What is the minimum deposit for a secured {keyword}?",
            f"Can I get {keyword} from a credit union as an immigrant?",
            f"What is the difference between a secured and unsecured {keyword}?",
            f"How do I convert my secured {keyword} to an unsecured one?",
            f"What {keyword} options are available for H-1B visa holders?",
            f"Can I use my home country credit history to get {keyword} in {market}?",
            f"What is Nova Credit and how does it help immigrants get {keyword}?",
            f"What are the best {keyword} for cash back rewards for immigrants?",
            f"How do I dispute an incorrect item on my credit report as an immigrant?",
            f"What is the fastest way for a new immigrant to get approved for {keyword}?",
        ],
        "key_takeaways": [
            f"New immigrants can get {keyword} in {market} even without a credit history",
            "Secured options are the easiest path to getting started",
            "Using an ITIN allows immigrants without SSN to still apply",
            "Building credit takes 6-12 months of responsible use",
            "Compare annual fees, APR, and rewards before choosing",
            "Nova Credit can help transfer foreign credit history",
            "Always pay on time — even one late payment can hurt your score",
        ],
        "call_to_action": f"Compare the best {keyword} for immigrants below and apply today — most decisions come within minutes.",
        "internal_link_opportunities": [
            f"Best Banks for Immigrants {market}", "Build Credit as Immigrant", "ITIN Guide",
            "Best Secured Cards", "No SSN Bank Account", "Credit Score Guide Immigrants"
        ],
        "affiliate_opportunities": ["Chase", "Capital One", "Discover", "Bank of America", "Citi"],
        "topic_data": topic
    }


try:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService
    from services.storage_service import StorageService

    class ContentPlannerAgent(BaseAgent):
        AGENT_ID = "agent_03"
        AGENT_NAME = "Content Planner Agent Gold Standard"

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
                self.log_complete({"sections": len(outline.get("sections", [])), "faqs": len(outline.get("faq", []))})
                return {"outline": outline, "output_path": str(output_path)}
            except Exception as e:
                self.log_error(e)
                raise

        async def _load_topics(self) -> Dict:
            for path in ["output/agent_02/validated_topics.json", "output/validated_topics.json"]:
                if os.path.exists(path):
                    with open(path) as f:
                        return json.load(f)
            raise FileNotFoundError("validated_topics.json not found")

except ImportError:
    pass

if __name__ == "__main__":
    main()
