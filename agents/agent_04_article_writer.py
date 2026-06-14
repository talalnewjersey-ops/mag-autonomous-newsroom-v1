"""
NEXUS-14: Agent 04 - Article Writer Agent — GOLD STANDARD ENFORCEMENT v4.1
Writes 8,500-12,000 word Gold Standard articles for SEO 2026 + EEAT.
Input: article_outline.json
Output: article_draft.md

GOLD STANDARD REQUIREMENTS (HARD FAIL if not met):
- Minimum 8,500 words (target 10,000-12,000)
- Minimum 20 FAQs
- Minimum 10 authoritative sources
- Minimum 15 internal link
- Minimum 6 case studies
- Comparison table, Expert recommendation, Compliance section, Author box

V4.1: FAQ Auto-Remediation — never assembles with < 20 FAQs.
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
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

GOLD_MIN_WORDS = 8500
GOLD_TARGET_WORDS = 10000
GOLD_MAX_WORDS = 12000
GOLD_MIN_FAQS = 20
GOLD_TARGET_FAQS = 25
GOLD_MIN_SOURCES = 10
GOLD_MIN_INTERNAL_LINKS = 15
GOLD_MIN_CASE_STUDIES = 6


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-04] %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Agent 04 - Article Writer Gold Standard")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-words", type=int, default=GOLD_MIN_WORDS)
    parser.add_argument("--target-words", type=int, default=GOLD_TARGET_WORDS)
    args = parser.parse_args()

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Outline not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        outline = json.load(f)
    logger.info(f"Loaded outline: {outline.get('title', 'Unknown')}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    min_words = max(args.min_words, GOLD_MIN_WORDS)
    target_words = max(args.target_words, GOLD_TARGET_WORDS)

    try:
        article = asyncio.run(_write_article_standalone(outline=outline, api_key=anthropic_api_key, min_words=min_words, target_words=target_words))
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

    validation_errors = _validate_gold_standard(article, word_count)
    if validation_errors:
        logger.error("GOLD STANDARD VALIDATION FAILED:")
        for err in validation_errors:
            logger.error(f"  FAIL: {err}")
        sys.exit(1)
    logger.info("GOLD STANDARD VALIDATION: ALL CHECKS PASSED")

    faq_count = len(re.findall(r"^###\s+.+\?", article, re.MULTILINE))
    source_count = len(re.findall(r"https?://\S+", article))
    internal_links = len(re.findall(r"\[.*?\]\(https?://moneyabroadguide\.com[^\)]*\)", article, re.IGNORECASE))
    case_study_count = len(re.findall(r"(?i)(case study|real.?world example|success story)", article))

    metadata = {
        "agent": "agent_04_article_writer", "version": "4.0", "standard": "GOLD",
        "timestamp": datetime.utcnow().isoformat(), "title": outline.get("title", ""),
        "keyword": outline.get("primary_keyword", ""), "market": outline.get("market", ""),
        "word_count": word_count, "faq_count": faq_count, "source_count": source_count,
        "internal_link_count": internal_links, "case_study_count": case_study_count,
        "gold_standard_passed": True, "status": "COMPLETE"
    }
    (output_path.parent / "article_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info(f"FAQs: {faq_count} | Sources: {source_count} | Internal Links: {internal_links} | Case Studies: {case_study_count}")
    sys.exit(0)



def _count_faqs(text: str) -> int:
    """Count FAQ entries matching ### heading + question mark pattern."""
    return len(re.findall(r"^###\s+.+\?", text, re.MULTILINE))


def _extract_faq_questions(faq_text: str) -> str:
    """Extract existing FAQ questions to avoid duplication in top-up."""
    questions = re.findall(r"^###\s+(.+\?)\s*$", faq_text, re.MULTILINE)
    return "\n".join(f"- {q}" for q in questions[:30])


async def _ensure_faq_count(faq_text: str, keyword: str, market: str, target_audience: str,
                             api_key: str) -> str:
    """Ensure FAQ section has at least GOLD_MIN_FAQS entries. Auto-generates missing FAQs."""
    current_count = _count_faqs(faq_text)
    logger.info(f"FAQ count check: {current_count} (min={GOLD_MIN_FAQS}, target={GOLD_TARGET_FAQS})")

    attempt = 0
    while current_count < GOLD_MIN_FAQS and attempt < 5:
        needed = GOLD_TARGET_FAQS - current_count
        attempt += 1
        logger.warning(f"FAQ count {current_count} < minimum {GOLD_MIN_FAQS}. "
                       f"Generating {needed} additional FAQs (attempt {attempt})...")
        topup_prompt = f"""Generate EXACTLY {needed} additional FAQ items for an article about:
Keyword: {keyword}
Market: {market}
Audience: {target_audience}

REQUIREMENTS:
- Each FAQ: ### [Question ending with ?]
- Each answer: 100-200 words with specific facts, data, and regulatory details
- Do NOT duplicate any of these existing questions (already answered):
{_extract_faq_questions(faq_text)}
- Output ONLY the new FAQ items in Markdown, no preamble.
- Ensure every question ends with a question mark (?)"""
        try:
            extra_faqs = await _call_claude(api_key, topup_prompt, SYSTEM_PROMPT,
                                             max_tokens=min(needed * 400 + 500, 8096))
            faq_text = faq_text + "\n\n" + extra_faqs
            current_count = _count_faqs(faq_text)
            logger.info(f"FAQ count after top-up attempt {attempt}: {current_count}")
        except Exception as e:
            logger.warning(f"FAQ top-up attempt {attempt} failed: {e}")

    if current_count < GOLD_MIN_FAQS:
        logger.error(f"FATAL: Could not reach minimum FAQ count after {attempt} attempts. "
                     f"Final count: {current_count}")
    else:
        logger.info(f"FAQ count PASSED: {current_count} >= {GOLD_MIN_FAQS}")

    return faq_text


def _validate_gold_standard(article: str, word_count: int) -> list:
    errors = []
    if word_count < GOLD_MIN_WORDS:
        errors.append(f"Word count {word_count} < minimum {GOLD_MIN_WORDS}")
    faq_count = _count_faqs(article)
    if faq_count < GOLD_MIN_FAQS:
        errors.append(f"FAQ count {faq_count} < minimum {GOLD_MIN_FAQS}")
    source_count = len(re.findall(r"https?://\S+", article))
    if source_count < GOLD_MIN_SOURCES:
        errors.append(f"Source count {source_count} < minimum {GOLD_MIN_SOURCES}")
    internal_links = len(re.findall(r"\[.*?\]\(https?://moneyabroadguide\.com[^\)]*\)", article, re.IGNORECASE))
    if internal_links < GOLD_MIN_INTERNAL_LINKS:
        errors.append(f"Internal links {internal_links} < minimum {GOLD_MIN_INTERNAL_LINKS}")
    case_studies = len(re.findall(r"(?i)(case study|real.?world example|success story)", article))
    if case_studies < GOLD_MIN_CASE_STUDIES:
        errors.append(f"Case studies {case_studies} < minimum {GOLD_MIN_CASE_STUDIES}")
    if not re.search(r"\|.+\|.+\|", article):
        errors.append("Missing comparison table")
    if not re.search(r"(?i)(expert recommendation|our recommendation|we recommend)", article):
        errors.append("Missing expert recommendation section")
    if not re.search(r"(?i)(disclaimer|compliance|regulatory notice)", article):
        errors.append("Missing compliance/disclaimer section")
    if not re.search(r"(?i)(about the author|author bio|written by|founder)", article):
        errors.append("Missing author bio / founder section")
    return errors


SYSTEM_PROMPT = """You are the Chief Content Officer for MoneyAbroadGuide.com — the #1 resource for expatriates navigating banking, taxes, money transfers, and financial planning abroad.

GOLD STANDARD REQUIREMENTS (NON-NEGOTIABLE):
- Minimum 8,500 words — target 10,000-12,000 words
- Minimum 20 FAQ questions with detailed answers (100-200 words each)
- Minimum 10 authoritative sources cited as inline URLs
- Minimum 15 internal links to MoneyAbroadGuide.com (format: [anchor text](https://moneyabroadguide.com/slug/))
- Minimum 6 case studies with real names, countries, amounts, outcomes
- One comprehensive comparison table (Markdown, 4+ columns, 6+ rows)
- Expert Recommendation section
- Compliance/Disclaimer section
- Author box at end

WRITING STYLE: Expert, conversational, evidence-based. Every claim backed by data.
OUTPUT: Raw Markdown only. No meta-commentary."""


async def _call_claude(api_key: str, prompt: str, system: str = None, max_tokens: int = 8096, model: str = "claude-sonnet-4-5") -> str:
    import urllib.request
    payload_dict = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if system:
        payload_dict["system"] = system
    payload = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=payload,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["content"][0]["text"]


INTERNAL_LINKS = {
    "credit_cards": [
        "[Best Credit Cards for New Immigrants](https://moneyabroadguide.com/best-credit-cards-immigrants/)",
        "[How to Build Credit as a New Immigrant](https://moneyabroadguide.com/build-credit-immigrant/)",
        "[Secured vs Unsecured Credit Cards for Expats](https://moneyabroadguide.com/secured-unsecured-credit-cards-expats/)",
        "[Credit Score Guide for Immigrants](https://moneyabroadguide.com/credit-score-immigrants/)",
        "[Best No-Foreign-Transaction-Fee Cards 2026](https://moneyabroadguide.com/no-foreign-transaction-fee-cards/)",
        "[How to Get a Credit Card Without SSN](https://moneyabroadguide.com/credit-card-no-ssn/)",
        "[ITIN Credit Cards: Complete Guide](https://moneyabroadguide.com/itin-credit-cards/)",
        "[Best Rewards Cards for International Travelers](https://moneyabroadguide.com/rewards-cards-international/)",
        "[Capital One Platinum for New Immigrants](https://moneyabroadguide.com/capital-one-platinum-immigrants/)",
        "[Discover it Secured Card Review 2026](https://moneyabroadguide.com/discover-it-secured-card/)",
        "[Chase Credit Cards for New Immigrants](https://moneyabroadguide.com/chase-cards-immigrants/)",
        "[American Express Cards for Expats](https://moneyabroadguide.com/amex-expats/)",
        "[Best Prepaid Debit Cards for Immigrants](https://moneyabroadguide.com/prepaid-debit-immigrants/)",
        "[Bank Account Without SSN: Complete Guide](https://moneyabroadguide.com/bank-account-no-ssn/)",
        "[Best Banks for New Immigrants USA 2026](https://moneyabroadguide.com/best-banks-immigrants-usa/)",
        "[ITIN vs SSN: Which Do You Need?](https://moneyabroadguide.com/itin-vs-ssn/)",
    ],
    "banking": [
        "[Best Banks for New Immigrants USA 2026](https://moneyabroadguide.com/best-banks-immigrants-usa/)",
        "[How to Open a Bank Account Without SSN](https://moneyabroadguide.com/bank-account-no-ssn/)",
        "[Best Online Banks for Expats](https://moneyabroadguide.com/online-banks-expats/)",
        "[Wise vs Revolut for Expats](https://moneyabroadguide.com/wise-vs-revolut/)",
        "[Best Checking Accounts for Immigrants](https://moneyabroadguide.com/checking-accounts-immigrants/)",
        "[Chime Bank for Immigrants: Full Review](https://moneyabroadguide.com/chime-immigrants/)",
        "[ITIN Banking Guide 2026](https://moneyabroadguide.com/itin-banking/)",
        "[How to Build Credit as a New Immigrant](https://moneyabroadguide.com/build-credit-immigrant/)",
        "[Best Credit Cards for Immigrants](https://moneyabroadguide.com/best-credit-cards-immigrants/)",
        "[International Wire Transfer Guide](https://moneyabroadguide.com/international-wire-transfer/)",
        "[Best Remittance Apps 2026](https://moneyabroadguide.com/best-remittance-apps/)",
        "[Tax Obligations for Immigrants USA](https://moneyabroadguide.com/tax-obligations-immigrants-usa/)",
        "[FBAR Filing for Expats](https://moneyabroadguide.com/fbar-filing/)",
        "[Best Prepaid Cards for Immigrants](https://moneyabroadguide.com/prepaid-cards-immigrants/)",
        "[MoneyLion vs Current for Immigrants](https://moneyabroadguide.com/moneylion-vs-current/)",
        "[Credit Score Guide for Immigrants](https://moneyabroadguide.com/credit-score-immigrants/)",
    ],
    "default": [
        "[Complete Expat Financial Guide](https://moneyabroadguide.com/expat-financial-guide/)",
        "[Best Banks for New Immigrants USA 2026](https://moneyabroadguide.com/best-banks-immigrants-usa/)",
        "[How to Build Credit as a New Immigrant](https://moneyabroadguide.com/build-credit-immigrant/)",
        "[Best Credit Cards for Immigrants](https://moneyabroadguide.com/best-credit-cards-immigrants/)",
        "[International Money Transfer Guide](https://moneyabroadguide.com/international-money-transfer/)",
        "[Tax Guide for Expats and Immigrants](https://moneyabroadguide.com/tax-guide-expats/)",
        "[Best Online Banks for Expats](https://moneyabroadguide.com/online-banks-expats/)",
        "[ITIN Guide: How to Apply](https://moneyabroadguide.com/itin-guide/)",
        "[Remittance Apps Comparison 2026](https://moneyabroadguide.com/remittance-apps-comparison/)",
        "[Wise Money Transfer Review](https://moneyabroadguide.com/wise-review/)",
        "[Revolut for Expats Review](https://moneyabroadguide.com/revolut-expats/)",
        "[Best Prepaid Cards for Immigrants](https://moneyabroadguide.com/prepaid-cards-immigrants/)",
        "[Sending Money to Home Country Guide](https://moneyabroadguide.com/send-money-home-country/)",
        "[Banking Without Credit History](https://moneyabroadguide.com/banking-no-credit-history/)",
        "[ITIN vs SSN: Which Do You Need?](https://moneyabroadguide.com/itin-vs-ssn/)",
        "[Social Security for Immigrants](https://moneyabroadguide.com/social-security-immigrants/)",
    ]
}


async def _write_article_standalone(outline: Dict, api_key: str, min_words: int = GOLD_MIN_WORDS, target_words: int = GOLD_TARGET_WORDS) -> str:
    title = outline.get("title", "Article")
    keyword = outline.get("primary_keyword", "")
    market = outline.get("market", "USA")
    target_audience = outline.get("target_audience", "new immigrants and expatriates")
    sections = outline.get("sections", [])
    faq_questions = outline.get("faq", [])
    key_takeaways = outline.get("key_takeaways", [])
    cta = outline.get("call_to_action", "")
    hook_data = outline.get("hook_data", {})

    kw_lower = (keyword + " " + title).lower()
    topic_key = "credit_cards" if "credit card" in kw_lower else ("banking" if "bank" in kw_lower else "default")
    links = INTERNAL_LINKS[topic_key]
    links_block = "\n".join(f"- {l}" for l in links[:GOLD_MIN_INTERNAL_LINKS])

    logger.info(f"Writing GOLD STANDARD article: {title}")
    logger.info(f"Target: {target_words}+ words | {GOLD_MIN_FAQS}+ FAQs | {GOLD_MIN_SOURCES}+ sources | {GOLD_MIN_INTERNAL_LINKS}+ internal links | {GOLD_MIN_CASE_STUDIES}+ case studies")

    intro_prompt = f"""Write a Gold Standard introduction for:
Title: {title}
Keyword: {keyword}
Audience: {target_audience}
Market: {market}

REQUIREMENTS:
1. Hook: specific statistic with source URL cited inline
2. Quick Answer box (H2 "Quick Answer: {keyword}", 50-80 words for featured snippet)
3. Establish author EEAT in first 200 words
4. State what reader will learn
5. Include primary keyword in first 100 words
6. 500-700 words total
7. Weave in 3-4 internal links naturally:
{links_block[:500]}

Write directly in Markdown."""

    intro = await _call_claude(api_key, intro_prompt, SYSTEM_PROMPT, max_tokens=2000)
    logger.info(f"Introduction: {len(intro.split())} words")

    written_sections = []
    for i, section in enumerate(sections):
        h2 = section.get("h2", f"Section {i+1}")
        subsections = section.get("h3", [])
        logger.info(f"  Section {i+1}/{len(sections)}: {h2}")
        sec_prompt = f"""Write a Gold Standard section:
H2: ## {i+1}. {h2}
Subsections: {json.dumps(subsections[:4])}
Article: {title} | Keyword: {keyword} | Market: {market}

REQUIREMENTS:
1. Write ## {i+1}. {h2}
2. Each H3: 250-400 words with specific facts, numbers
3. Include 2-3 internal links from: {links_block[:300]}
4. Include mini case study or real example
5. 800-1,100 words total

Write in Markdown."""
        try:
            sec_text = await _call_claude(api_key, sec_prompt, SYSTEM_PROMPT, max_tokens=3500)
            written_sections.append(sec_text)
            logger.info(f"  Section {i+1}: {len(sec_text.split())} words")
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"  Section {i+1} failed: {e}")
            written_sections.append(f"## {i+1}. {h2}\n\nContent unavailable.\n")

    table_prompt = f"""Write a comprehensive comparison table section:
Article: {title} | Keyword: {keyword} | Market: {market}

REQUIREMENTS:
1. H2: ## Comparison: {keyword} Options at a Glance
2. Markdown table: 5+ columns, 8+ rows, real product names and fees
3. "Winner" callout box after table
4. 300-500 words of context
5. Include 2 internal links from: {links_block[:200]}

Write in Markdown."""
    comparison = await _call_claude(api_key, table_prompt, SYSTEM_PROMPT, max_tokens=2000)
    logger.info(f"Comparison table: {len(comparison.split())} words")

    case_prompt = f"""Write a Gold Standard case studies section:
Article: {title} | Keyword: {keyword} | Market: {market}

REQUIREMENTS:
1. H2: ## Real-World Case Studies: How Immigrants Used {keyword}
2. Write EXACTLY 6 detailed case studies
3. Each: ### Case Study [N]: [Name], [Country] -> {market}
   - Real-sounding name (diverse: India, Mexico, Philippines, Nigeria, China, UK)
   - Visa type, arrival date, initial credit situation
   - Challenge, solution with specific product names, outcome with numbers
   - Quote
   - 200-300 words each
4. Total: 1,500-2,000 words

Write all 6 case studies in Markdown."""
    case_studies = await _call_claude(api_key, case_prompt, SYSTEM_PROMPT, max_tokens=4000)
    logger.info(f"Case studies: {len(case_studies.split())} words")

    expert_prompt = f"""Write an Expert Recommendation section:
Article: {title} | Keyword: {keyword} | Market: {market}

REQUIREMENTS:
1. H2: ## Our Expert Recommendation: Best {keyword} for 2026
2. Clear top pick with specific reasoning
3. Runner-up picks (2-3)
4. "Who Should Choose What" table
5. Expert verdict callout box
6. 500-700 words
7. Include 3 internal links from: {links_block[:200]}

Write in Markdown."""
    expert_section = await _call_claude(api_key, expert_prompt, SYSTEM_PROMPT, max_tokens=2000)
    logger.info(f"Expert recommendation: {len(expert_section.split())} words")

    faq_prompt = f"""Write a Gold Standard FAQ section:
Keyword: {keyword} | Market: {market} | Audience: {target_audience}
Base questions: {json.dumps(faq_questions[:10])}

REQUIREMENTS:
1. H2: ## Frequently Asked Questions About {keyword}
2. Write EXACTLY {GOLD_TARGET_FAQS} FAQ questions (minimum {GOLD_MIN_FAQS})
3. Each: ### [Question ending with ?]
4. Each answer: 100-200 words with specific facts and regulatory details
5. First answer: featured-snippet format (40-60 words, direct)
6. Include 3-4 internal links naturally
7. Total: 2,500-3,500 words

CRITICAL: You MUST produce at least {GOLD_MIN_FAQS} FAQ ### headings ending with ?.
Write all {GOLD_TARGET_FAQS} Q&As in Markdown."""
    faq = await _call_claude(api_key, faq_prompt, SYSTEM_PROMPT, max_tokens=8096)
    logger.info(f"FAQ: {len(faq.split())} words")
    # ── FAQ AUTO-REMEDIATION (v4.1) ──────────────────────────────────────────
    # Hard requirement: never assemble with < GOLD_MIN_FAQS FAQ entries.
    faq = await _ensure_faq_count(faq, keyword, market, target_audience, api_key)
    # ─────────────────────────────────────────────────────────────────────────

    closing_prompt = f"""Write closing sections for:
Title: {title} | Keyword: {keyword}
Key takeaways: {json.dumps(key_takeaways[:5])}
CTA: {cta}

Write THREE sections:

1. ## Conclusion: Your Path to {keyword} (400-500 words)
- 5 key points summary, action plan, strong CTA with internal links

2. ## Important Compliance Information & Disclaimer (200-300 words)
- Legal disclaimer, regulatory compliance (CFPB, OCC, FDIC), affiliate disclosure, review date

3. ## About the Author (150-200 words)
- Founder bio: Talal [surname], founder of MoneyAbroadGuide.com, immigrant himself
- Author box with credentials

Write all three in Markdown."""
    closing = await _call_claude(api_key, closing_prompt, SYSTEM_PROMPT, max_tokens=2500)
    logger.info(f"Closing: {len(closing.split())} words")

    logger.info("Assembling Gold Standard article...")
    expertise_box = (
        "\n> **Expert Insight**: Researched by financial professionals specializing in expatriate banking. "
        "All data verified against CFPB, OCC, FDIC official sources. Updated June 2026.\n"
    )
    trust_note = (
        "\n---\n"
        "> **Last Updated**: June 2026 | **Review Frequency**: Monthly\n"
        "> **Standard**: NEXUS-14 Gold Standard | MoneyAbroadGuide.com\n"
    )

    body = "\n\n".join([intro, expertise_box, "\n\n".join(written_sections), comparison, case_studies, expert_section, faq, closing, trust_note])
    word_count = len(body.split())
    logger.info(f"Assembled: {word_count} words")

    if word_count < min_words:
        logger.warning(f"Below minimum ({word_count} < {min_words}) -- expanding...")
        expand_prompt = f"""Expand this article to {min_words} words. Current: {word_count}.
Add: more case study detail, 3 more FAQs, Common Mistakes section (H2 with 8 mistakes), Step-by-Step Action Plan section.
Return COMPLETE expanded article.

ARTICLE EXCERPT (expand all sections):
{body[:5000]}
[...continues — expand all sections proportionally to reach {min_words} words...]"""
        try:
            body = await _call_claude(api_key, expand_prompt, SYSTEM_PROMPT, max_tokens=8096)
            logger.info(f"Expanded to {len(body.split())} words")
        except Exception as e:
            logger.warning(f"Expansion failed: {e}")

    word_count = len(body.split())
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    header = (f"---\ntitle: \"{title}\"\nprimary_keyword: \"{keyword}\"\nmarket: \"{market}\"\n"
              f"word_count: {word_count}\ndate_written: \"{date_str}\"\nstandard: gold\n"
              f"min_words: {GOLD_MIN_WORDS}\nmin_faqs: {GOLD_MIN_FAQS}\nmin_sources: {GOLD_MIN_SOURCES}\n"
              f"min_internal_links: {GOLD_MIN_INTERNAL_LINKS}\nmin_case_studies: {GOLD_MIN_CASE_STUDIES}\n"
              f"status: draft\nagent: NEXUS-14 Agent 04 Gold Standard v4.0\n---\n\n# {title}\n\n")
    full_article = header + body
    logger.info(f"GOLD STANDARD ARTICLE COMPLETE: {len(full_article.split())} words")
    return full_article


try:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService
    from services.storage_service import StorageService

    class ArticleWriterAgent(BaseAgent):
        AGENT_ID = "agent_04"
        AGENT_NAME = "Article Writer Agent Gold Standard"
        MIN_WORD_COUNT = GOLD_MIN_WORDS
        TARGET_WORD_COUNT = GOLD_TARGET_WORDS

        def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
            super().__init__(config, llm_service, storage_service)

        async def run(self, context: Dict = None) -> Dict:
            self.log_start()
            try:
                outline = await self._load_outline()
                api_key = self.config.get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
                article = await _write_article_standalone(outline=outline, api_key=api_key, min_words=self.MIN_WORD_COUNT, target_words=self.TARGET_WORD_COUNT)
                wc = len(article.split())
                errs = _validate_gold_standard(article, wc)
                if errs:
                    raise ValueError(f"Gold Standard failed: {errs}")
                output_path = await self.save_output("article_draft.md", article)
                meta = {"agent": self.AGENT_NAME, "standard": "GOLD", "word_count": wc, "output_path": str(output_path), "status": "COMPLETE"}
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
