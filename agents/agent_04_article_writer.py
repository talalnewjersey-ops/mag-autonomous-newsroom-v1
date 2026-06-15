"""
NEXUS-14: Agent 04 - Article Writer Agent COST-OPTIMIZED v5.0
TIER 1 PILLAR: 4500-5000w max | 12 FAQs | 3 case studies | 5 images | 6+ sources
TIER 2 STANDARD: 4000-4500w max | 10 FAQs | 2 case studies | 4 images | 5+ sources
TIER 3 OPPORTUNITY: 3500-4000w max | 8 FAQs | 1-2 case studies | 3 images | 3+ sources
GLOBAL RULE: Maximum quality per dollar. Search intent satisfaction > article length.
"""

import argparse, asyncio, json, logging, os, re, sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

PILLAR_MIN_WORDS = 4500
PILLAR_TARGET_WORDS = 5000
PILLAR_MAX_WORDS = 5000
PILLAR_MIN_FAQS = 12
PILLAR_MIN_SOURCES = 6
PILLAR_MIN_INTERNAL_LINKS = 8
PILLAR_MIN_CASE_STUDIES = 3

STANDARD_MIN_WORDS = 4000
STANDARD_TARGET_WORDS = 4500
STANDARD_MAX_WORDS = 4500
STANDARD_MIN_FAQS = 10
STANDARD_MIN_SOURCES = 5
STANDARD_MIN_INTERNAL_LINKS = 3
STANDARD_MIN_CASE_STUDIES = 2

OPPORTUNITY_MIN_WORDS = 3500
OPPORTUNITY_TARGET_WORDS = 4000
OPPORTUNITY_MAX_WORDS = 4000
OPPORTUNITY_MIN_FAQS = 8
OPPORTUNITY_MIN_SOURCES = 3
OPPORTUNITY_MIN_INTERNAL_LINKS = 4
OPPORTUNITY_MIN_CASE_STUDIES = 1

GOLD_MIN_WORDS = STANDARD_MIN_WORDS
GOLD_TARGET_WORDS = STANDARD_TARGET_WORDS
GOLD_MAX_WORDS = STANDARD_MAX_WORDS
GOLD_MIN_FAQS = STANDARD_MIN_FAQS
GOLD_MIN_SOURCES = STANDARD_MIN_SOURCES
GOLD_MIN_INTERNAL_LINKS = STANDARD_MIN_INTERNAL_LINKS
GOLD_MIN_CASE_STUDIES = STANDARD_MIN_CASE_STUDIES


def _get_tier_config(article_type: str) -> dict:
    t = (article_type or "STANDARD").upper()
    if t == "PILLAR":
        return {"min_words": PILLAR_MIN_WORDS, "target_words": PILLAR_TARGET_WORDS,
                "max_words": PILLAR_MAX_WORDS, "min_faqs": PILLAR_MIN_FAQS,
                "min_sources": PILLAR_MIN_SOURCES, "min_links": PILLAR_MIN_INTERNAL_LINKS,
                "min_case_studies": PILLAR_MIN_CASE_STUDIES, "tier": "PILLAR"}
    elif t == "OPPORTUNITY":
        return {"min_words": OPPORTUNITY_MIN_WORDS, "target_words": OPPORTUNITY_TARGET_WORDS,
                "max_words": OPPORTUNITY_MAX_WORDS, "min_faqs": OPPORTUNITY_MIN_FAQS,
                "min_sources": OPPORTUNITY_MIN_SOURCES, "min_links": OPPORTUNITY_MIN_INTERNAL_LINKS,
                "min_case_studies": OPPORTUNITY_MIN_CASE_STUDIES, "tier": "OPPORTUNITY"}
    return {"min_words": STANDARD_MIN_WORDS, "target_words": STANDARD_TARGET_WORDS,
            "max_words": STANDARD_MAX_WORDS, "min_faqs": STANDARD_MIN_FAQS,
            "min_sources": STANDARD_MIN_SOURCES, "min_links": STANDARD_MIN_INTERNAL_LINKS,
            "min_case_studies": STANDARD_MIN_CASE_STUDIES, "tier": "STANDARD"}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-04] %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Agent 04 - Article Writer Cost-Optimized V5.0")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-words", type=int, default=0)
    parser.add_argument("--target-words", type=int, default=0)
    parser.add_argument("--article-type", type=str, default="")
    args = parser.parse_args()
    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)
    article_type = args.article_type or os.environ.get("ARTICLE_TYPE", "STANDARD")
    tier = _get_tier_config(article_type)
    min_words = min(args.min_words if args.min_words > 0 else tier["min_words"], tier["max_words"])
    target_words = min(args.target_words if args.target_words > 0 else tier["target_words"], tier["max_words"])
    logger.info(f"TIER: {tier['tier']} | Min: {min_words} | Target: {target_words} | Max: {tier['max_words']}")
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Outline not found: {input_path}")
        sys.exit(1)
    with open(input_path, "r", encoding="utf-8") as f:
        outline = json.load(f)
    logger.info(f"Loaded outline: {outline.get('title', 'Unknown')}")
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        article = asyncio.run(_write_article_standalone(outline=outline, api_key=anthropic_api_key,
                                                         min_words=min_words, target_words=target_words, tier=tier))
    except Exception as e:
        logger.error(f"Article writing failed: {e}")
        sys.exit(1)
    output_path.write_text(article, encoding="utf-8")
    word_count = len(article.split())
    file_size = output_path.stat().st_size
    if not output_path.exists() or file_size == 0:
        logger.error(f"Output file empty: {output_path}")
        sys.exit(1)
    logger.info(f"Article written: {output_path} | Words: {word_count} | Size: {file_size}")
    validation_errors = _validate_tier_standard(article, word_count, tier)
    if validation_errors:
        logger.error(f"TIER {tier['tier']} VALIDATION FAILED:")
        for err in validation_errors:
            logger.error(f"  FAIL: {err}")
        sys.exit(1)
    logger.info(f"TIER {tier['tier']} VALIDATION: ALL CHECKS PASSED")
    faq_count = len(re.findall(r"^###\s+.+\?", article, re.MULTILINE))
    source_count = len(re.findall(r"https?://\S+", article))
    internal_links = len(re.findall(r"\[.*?\]\(https?://moneyabroadguide\.com[^\)]*\)", article, re.IGNORECASE))
    case_study_count = len(re.findall(r"(?i)(case study|real.?world example|success story)", article))
    metadata = {"agent": "agent_04_article_writer", "version": "5.0", "tier": tier["tier"],
                "timestamp": datetime.utcnow().isoformat(), "title": outline.get("title", ""),
                "keyword": outline.get("primary_keyword", ""), "market": outline.get("market", ""),
                "word_count": word_count, "faq_count": faq_count, "source_count": source_count,
                "internal_link_count": internal_links, "case_study_count": case_study_count,
                "tier_passed": True, "status": "COMPLETE", "min_words": min_words,
                "target_words": target_words, "max_words": tier["max_words"]}
    (output_path.parent / "article_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    sys.exit(0)


def _count_faqs(text: str) -> int:
    return len(re.findall(r"^###\s+.+\?", text, re.MULTILINE))

def _extract_faq_questions(faq_text: str) -> str:
    questions = re.findall(r"^###\s+(.+\?)\s*$", faq_text, re.MULTILINE)
    return "\n".join(f"- {q}" for q in questions[:20])

async def _ensure_faq_count(faq_text, keyword, market, target_audience, api_key, min_faqs, target_faqs):
    current_count = _count_faqs(faq_text)
    attempt = 0
    while current_count < min_faqs and attempt < 3:
        needed = target_faqs - current_count
        attempt += 1
        try:
            extra = await _call_claude(api_key,
                f"Generate EXACTLY {needed} additional FAQ items for: {keyword} ({market})\nDo NOT duplicate: {_extract_faq_questions(faq_text)}\nFormat: ### [Question?]\nAnswer 80-150w",
                SYSTEM_PROMPT, max_tokens=min(needed * 300, 4000))
            faq_text = faq_text + "\n\n" + extra
            current_count = _count_faqs(faq_text)
        except Exception as e:
            logger.warning(f"FAQ top-up {attempt} failed: {e}")
    return faq_text

def _validate_tier_standard(article: str, word_count: int, tier: dict) -> list:
    errors = []
    if word_count < tier["min_words"]:
        errors.append(f"Word count {word_count} < minimum {tier['min_words']} for {tier['tier']}")
    faq_count = _count_faqs(article)
    if faq_count < tier["min_faqs"]:
        errors.append(f"FAQ count {faq_count} < minimum {tier['min_faqs']}")
    source_count = len(re.findall(r"https?://\S+", article))
    if source_count < tier["min_sources"]:
        errors.append(f"Source count {source_count} < minimum {tier['min_sources']}")
    internal_links = len(re.findall(r"\[.*?\]\(https?://moneyabroadguide\.com[^\)]*\)", article, re.IGNORECASE))
    if internal_links < tier["min_links"]:
        errors.append(f"Internal links {internal_links} < minimum {tier['min_links']}")
    case_studies = len(re.findall(r"(?i)(case study|real.?world example|success story)", article))
    if case_studies < tier["min_case_studies"]:
        errors.append(f"Case studies {case_studies} < minimum {tier['min_case_studies']}")
    if not re.search(r"\|.+\|.+\|", article):
        errors.append("Missing comparison table")
    if not re.search(r"(?i)(expert recommendation|our recommendation|we recommend)", article):
        errors.append("Missing expert recommendation section")
    if not re.search(r"(?i)(disclaimer|compliance|regulatory notice)", article):
        errors.append("Missing compliance/disclaimer section")
    if not re.search(r"(?i)(about the author|author bio|written by|founder)", article):
        errors.append("Missing author bio / founder section")
    return errors

SYSTEM_PROMPT = """You are Chief Content Officer for MoneyAbroadGuide.com.
GLOBAL RULE: Maximum quality per dollar. No unnecessary padding. Satisfy search intent.
Focus: newcomers, immigrants, expats in Canada and USA.
MANDATORY: comparison table | expert recommendation | compliance disclaimer | author box (Talal Eddaouahiri, founder MoneyAbroadGuide.com)
OUTPUT: Raw Markdown only."""

async def _call_claude(api_key: str, prompt: str, system: str = None, max_tokens: int = 5000,
                       model: str = "claude-sonnet-4-5") -> str:
    import urllib.request
    payload_dict = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        payload_dict["system"] = system
    payload = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload,
                                 headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["content"][0]["text"]

INTERNAL_LINKS = {
    "canada_newcomer": [
        "[Best Bank Account for Newcomers to Canada](https://moneyabroadguide.com/best-bank-account-newcomers-canada/)",
        "[How to Build Credit in Canada as a Newcomer](https://moneyabroadguide.com/build-credit-canada-newcomer/)",
        "[Health Insurance for Newcomers in Canada](https://moneyabroadguide.com/health-insurance-newcomers-canada/)",
        "[Cost of Living in Canada 2026 Guide](https://moneyabroadguide.com/cost-of-living-canada/)",
        "[First 90 Days in Canada Checklist](https://moneyabroadguide.com/first-90-days-canada-checklist/)",
        "[Taxes for New Immigrants to Canada](https://moneyabroadguide.com/taxes-new-immigrants-canada/)",
        "[Best Phone Plans for Newcomers in Canada](https://moneyabroadguide.com/best-phone-plans-newcomers-canada/)",
        "[Canada Banking Mistakes to Avoid](https://moneyabroadguide.com/canada-banking-mistakes/)",
    ],
    "credit_cards": [
        "[Best Credit Cards for New Immigrants](https://moneyabroadguide.com/best-credit-cards-immigrants/)",
        "[Credit Score Guide for Immigrants](https://moneyabroadguide.com/credit-score-immigrants/)",
        "[Best No-Foreign-Transaction-Fee Cards 2026](https://moneyabroadguide.com/no-foreign-transaction-fee-cards/)",
        "[Best Banks for New Immigrants USA 2026](https://moneyabroadguide.com/best-banks-immigrants-usa/)",
    ],
    "banking": [
        "[Best Banks for New Immigrants USA 2026](https://moneyabroadguide.com/best-banks-immigrants-usa/)",
        "[How to Open a Bank Account Without SSN](https://moneyabroadguide.com/bank-account-no-ssn/)",
        "[Wise vs Revolut for Expats](https://moneyabroadguide.com/wise-vs-revolut/)",
        "[International Wire Transfer Guide](https://moneyabroadguide.com/international-wire-transfer/)",
    ],
    "default": [
        "[Complete Expat Financial Guide](https://moneyabroadguide.com/expat-financial-guide/)",
        "[Best Banks for New Immigrants USA 2026](https://moneyabroadguide.com/best-banks-immigrants-usa/)",
        "[Best Bank Account for Newcomers to Canada](https://moneyabroadguide.com/best-bank-account-newcomers-canada/)",
        "[International Money Transfer Guide](https://moneyabroadguide.com/international-money-transfer/)",
        "[Tax Guide for Expats and Immigrants](https://moneyabroadguide.com/tax-guide-expats/)",
    ]
}

async def _write_article_standalone(outline: Dict, api_key: str, min_words: int = STANDARD_MIN_WORDS,
                                     target_words: int = STANDARD_TARGET_WORDS, tier: dict = None) -> str:
    if tier is None:
        tier = _get_tier_config("STANDARD")
    title = outline.get("title", "Article")
    keyword = outline.get("primary_keyword", "")
    market = outline.get("market", "Canada")
    target_audience = outline.get("target_audience", "newcomers and immigrants in Canada")
    sections = outline.get("sections", [])
    faq_questions = outline.get("faq", [])
    key_takeaways = outline.get("key_takeaways", [])

    kw_lower = (keyword + " " + title + " " + market).lower()
    if "canada" in kw_lower and ("newcomer" in kw_lower or "immigrant" in kw_lower or "student" in kw_lower):
        topic_key = "canada_newcomer"
    elif "credit card" in kw_lower:
        topic_key = "credit_cards"
    elif "bank" in kw_lower:
        topic_key = "banking"
    else:
        topic_key = "default"
    links = INTERNAL_LINKS[topic_key]
    links_block = "\n".join(f"- {l}" for l in links[:tier["min_links"]])

    logger.info(f"Writing {tier['tier']} article: {title} (target: {target_words}w)")

    intro = await _call_claude(api_key,
        f"Write introduction: {title} | {keyword} | {market} | Tier: {tier['tier']}\n"
        f"300-400w. Quick Answer box (40-60w). 2-3 internal links:\n{links_block[:300]}\nBe concise.",
        SYSTEM_PROMPT, max_tokens=1200)

    written_sections = []
    max_sections = 5 if tier["tier"] == "PILLAR" else (4 if tier["tier"] == "STANDARD" else 3)
    for i, section in enumerate(sections[:max_sections]):
        h2 = section.get("h2", f"Section {i+1}")
        sec_target = 600 if tier["tier"] == "PILLAR" else (500 if tier["tier"] == "STANDARD" else 400)
        try:
            sec_text = await _call_claude(api_key,
                f"Write section ## {i+1}. {h2} for: {title} | {keyword}\n{sec_target}-{sec_target+150}w. Concise. No padding.",
                SYSTEM_PROMPT, max_tokens=1800)
            written_sections.append(sec_text)
            await asyncio.sleep(0.2)
        except Exception as e:
            written_sections.append(f"## {i+1}. {h2}\n\nContent unavailable.\n")

    comparison = await _call_claude(api_key,
        f"Write comparison table section for: {keyword} ({market}). H2 header. 4+ cols 6+ rows. 200-300w context.",
        SYSTEM_PROMPT, max_tokens=1200)

    n_cases = tier["min_case_studies"]
    case_studies = await _call_claude(api_key,
        f"Write {n_cases} case {'study' if n_cases == 1 else 'studies'} for: {keyword} ({market}).\n"
        f"H2: ## Real-World Examples. 150-200w each. Specific names, outcomes, numbers.",
        SYSTEM_PROMPT, max_tokens=n_cases * 500)

    expert_section = await _call_claude(api_key,
        f"Write Expert Recommendation section for: {keyword} ({market}). H2. Top pick + runner-up. 300-400w. 2 internal links from: {links_block[:200]}",
        SYSTEM_PROMPT, max_tokens=1000)

    min_faqs = tier["min_faqs"]
    target_faqs = min_faqs + 2
    faq = await _call_claude(api_key,
        f"Write FAQ section for: {keyword} ({market}). {target_faqs} questions (minimum {min_faqs}).\n"
        f"### [Question?] format. 80-150w answers. MUST produce at least {min_faqs} ### headings ending with ?",
        SYSTEM_PROMPT, max_tokens=target_faqs * 280)
    faq = await _ensure_faq_count(faq, keyword, market, target_audience, api_key, min_faqs, target_faqs)

    closing = await _call_claude(api_key,
        f"Write 3 sections for: {title}\n"
        f"1. ## Conclusion (200-300w)\n"
        f"2. ## Disclaimer (150-200w, legal, affiliate disclosure)\n"
        f"3. ## About the Author (Talal Eddaouahiri, founder MoneyAbroadGuide.com, 100-150w)",
        SYSTEM_PROMPT, max_tokens=1200)

    body = "\n\n".join([intro, "\n\n".join(written_sections) if written_sections else "",
                          comparison, case_studies, expert_section, faq, closing,
                          f"\n---\n> **Last Updated**: June 2026 | **Tier**: {tier['tier']} | NEXUS-14 V5.0\n"])
    word_count = len(body.split())
    if word_count < min_words:
        try:
            extra = await _call_claude(api_key,
                f"Article needs {min_words - word_count} more words. Add 4 more FAQ questions and a practical tips section (H2, 5 tips). Return ONLY new Markdown.",
                SYSTEM_PROMPT, max_tokens=1500)
            body = body + "\n\n" + extra
        except Exception as e:
            logger.warning(f"Expansion failed: {e}")

    word_count = len(body.split())
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    header = (f"---\ntitle: \"{title}\"\nprimary_keyword: \"{keyword}\"\nmarket: \"{market}\"\n"
              f"word_count: {word_count}\ndate_written: \"{date_str}\"\ntier: {tier['tier'].lower()}\n"
              f"status: draft\nagent: NEXUS-14 Agent 04 V5.0\n---\n\n# {title}\n\n")
    return header + body


try:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService
    from services.storage_service import StorageService

    class ArticleWriterAgent(BaseAgent):
        AGENT_ID = "agent_04"
        AGENT_NAME = "Article Writer Agent V5.0"
        def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
            super().__init__(config, llm_service, storage_service)
        async def run(self, context: Dict = None) -> Dict:
            self.log_start()
            try:
                outline = await self._load_outline()
                api_key = self.config.get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
                tier = _get_tier_config(os.environ.get("ARTICLE_TYPE", "STANDARD"))
                article = await _write_article_standalone(outline=outline, api_key=api_key,
                    min_words=tier["min_words"], target_words=tier["target_words"], tier=tier)
                wc = len(article.split())
                errs = _validate_tier_standard(article, wc, tier)
                if errs:
                    raise ValueError(f"Tier validation failed: {errs}")
                output_path = await self.save_output("article_draft.md", article)
                meta = {"agent": self.AGENT_NAME, "tier": tier["tier"], "word_count": wc,
                        "output_path": str(output_path), "status": "COMPLETE"}
                await self.save_output("article_metadata.json", meta)
                self.log_complete({"word_count": wc})
                return {"article": article, "metadata": meta}
            except Exception as e:
                self.log_error(e)
                raise
        async def _load_outline(self) -> Dict:
            for path in ["output/agent_03/article_outline.json", "output/article_outline.json"]:
                if os.path.exists(path):
                    with open(path) as f:
                        return json.load(f)
            raise FileNotFoundError("article_outline.json not found")
except ImportError:
    pass

if __name__ == "__main__":
    main()
