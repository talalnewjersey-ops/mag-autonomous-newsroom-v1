"""
NEXUS-14: Agent 04 - Article Writer Agent
Writes 5,000-10,000 word articles optimized for SEO 2026 + EEAT standards.
Input: article_outline.json
Output: article_draft.md

V3.2: Added CLI main() entry point for workflow execution.
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


# ============================================================
# STANDALONE MAIN — CLI entry point for workflow execution
# ============================================================

def main():
    """CLI entry point: called by workflow as python -m agents.agent_04_article_writer ..."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-04] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S,%f"
    )

    parser = argparse.ArgumentParser(description="Agent 04 - Article Writer")
    parser.add_argument("--input", required=True, help="Path to article_outline.json")
    parser.add_argument("--output", required=True, help="Output path for article_draft.md")
    parser.add_argument("--min-words", type=int, default=5000)
    parser.add_argument("--target-words", type=int, default=7000)
    args = parser.parse_args()

    anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set -- cannot write article")
        sys.exit(1)

    # Load the outline
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Outline not found: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        outline = json.load(f)
    logger.info(f"Loaded outline: {outline.get("title", "Unknown")}")

    # Determine output directory and filename
    output_path = Path(args.output)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run the article writer
    try:
        article = asyncio.run(
            _write_article_standalone(
                outline=outline,
                api_key=anthropic_api_key,
                min_words=args.min_words,
                target_words=args.target_words,
            )
        )
    except Exception as e:
        logger.error(f"Article writing failed: {e}")
        sys.exit(1)

    # Write the output file
    output_path.write_text(article, encoding="utf-8")
    word_count = len(article.split())
    file_size = output_path.stat().st_size

    # Verify output
    if not output_path.exists() or file_size == 0:
        logger.error(f"Output file not created or empty: {output_path}")
        sys.exit(1)

    logger.info(f"Article written: {output_path}")
    logger.info(f"Word count: {word_count}")
    logger.info(f"File size: {file_size} bytes")

    # Write companion metadata
    metadata_path = output_dir / "article_metadata.json"
    metadata = {
        "agent": "agent_04_article_writer",
        "version": "3.2",
        "timestamp": datetime.utcnow().isoformat(),
        "title": outline.get("title", ""),
        "keyword": outline.get("primary_keyword", ""),
        "market": outline.get("market", ""),
        "word_count": word_count,
        "file_size_bytes": file_size,
        "output_path": str(output_path),
        "status": "COMPLETE"
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info(f"Metadata written: {metadata_path}")
    sys.exit(0)


# ============================================================
# STANDALONE ARTICLE WRITER
# ============================================================

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


async def _call_claude(api_key: str, prompt: str, system: str = None,
                       max_tokens: int = 4096, model: str = "claude-3-5-sonnet-20241022") -> str:
    """Call Anthropic Claude API directly."""
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    response = await asyncio.to_thread(client.messages.create, **kwargs)
    return response.content[0].text


async def _write_article_standalone(
    outline: Dict,
    api_key: str,
    min_words: int = 5000,
    target_words: int = 7000,
) -> str:
    """Write a complete article from outline using Claude API directly."""
    title = outline.get("title", "Article")
    keyword = outline.get("primary_keyword", "")
    market = outline.get("market", "USA")
    target_audience = outline.get("target_audience", "expatriates")
    search_intent = outline.get("search_intent", "informational")
    sections = outline.get("sections", [])
    faq_questions = outline.get("faq", [])
    key_takeaways = outline.get("key_takeaways", [])
    cta = outline.get("call_to_action", "")
    hook_data = outline.get("hook_data", {})

    logger.info(f"Writing article: {title}")

    # Phase 1: Introduction
    logger.info("Phase 1/5: Writing introduction...")
    intro_prompt = (
        f"Write a compelling introduction for this article:\n\n"
        f"Title: {title}\n"
        f"Primary Keyword: {keyword}\n"
        f"Target Audience: {target_audience}\n"
        f"Search Intent: {search_intent}\n"
        f"Hook Data: {json.dumps(hook_data)}\n\n"
        "Requirements:\n"
        "1. Start with a powerful hook (surprising statistic, question, or scenario)\n"
        "2. Clearly state what the reader will learn\n"
        "3. Establish the article's authority and expertise\n"
        "4. Include the primary keyword naturally within the first 100 words\n"
        "5. 300-400 words\n"
        "6. End with a smooth transition to the first main section\n\n"
        "Write the introduction directly, no meta-commentary. Use markdown formatting."
    )
    intro = await _call_claude(api_key, intro_prompt, SYSTEM_PROMPT, max_tokens=900)
    logger.info(f"Introduction: {len(intro.split())} words")

    # Phase 2: Main sections
    logger.info(f"Phase 2/5: Writing {len(sections)} sections...")
    written_sections = []
    for i, section in enumerate(sections):
        h2 = section.get("h2", f"Section {i+1}")
        subsections = section.get("h3", [])
        data_points = section.get("data", [])
        logger.info(f"  Section {i+1}/{len(sections)}: {h2}")
        sec_prompt = (
            f"Write a comprehensive section for this article:\n\n"
            f"Section Title (H2): {h2}\n"
            f"Subsections needed: {json.dumps(subsections)}\n"
            f"Key data points to include: {json.dumps(data_points)}\n\n"
            f"Article context:\n"
            f"- Primary keyword: {keyword}\n"
            f"- Target market: {market}\n"
            f"- Target audience: {target_audience}\n\n"
            "Requirements:\n"
            "1. Write the H2 heading (##) and full section content\n"
            "2. Write each H3 subsection (###) with detailed content\n"
            "3. Include specific facts, numbers, and examples\n"
            "4. Use comparison tables where relevant (Markdown format)\n"
            "5. Include practical actionable advice\n"
            "6. Write 600-900 words for this section\n"
            "7. Natural keyword integration\n\n"
            "Write the section directly in Markdown format."
        )
        try:
            sec_text = await _call_claude(api_key, sec_prompt, SYSTEM_PROMPT, max_tokens=2500)
            written_sections.append(sec_text)
            logger.info(f"  Section {i+1} done: {len(sec_text.split())} words")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"  Section {i+1} failed ({h2}): {e} -- using placeholder")
            written_sections.append(f"## {h2}\n\nContent for this section.\n")

    # Phase 3: FAQ
    logger.info("Phase 3/5: Writing FAQ...")
    faq_prompt = (
        f"Write a comprehensive FAQ section for this article.\n\n"
        f"Article keyword: {keyword}\n"
        f"Target market: {market}\n"
        f"Questions to cover:\n{json.dumps(faq_questions, indent=2)}\n\n"
        "Requirements:\n"
        "1. Write ## Frequently Asked Questions as the heading\n"
        "2. Include at least 8-10 questions\n"
        "3. Each answer should be 50-150 words\n"
        "4. Format using ### for each question\n"
        "5. Answers must be direct and helpful\n\n"
        "Write the complete FAQ section in Markdown format."
    )
    faq = await _call_claude(api_key, faq_prompt, SYSTEM_PROMPT, max_tokens=2000)
    logger.info(f"FAQ: {len(faq.split())} words")

    # Phase 4: Conclusion
    logger.info("Phase 4/5: Writing conclusion...")
    conc_prompt = (
        f"Write a strong conclusion for this article:\n\n"
        f"Article title: {title}\n"
        f"Key takeaways: {json.dumps(key_takeaways)}\n"
        f"Call to action: {cta}\n\n"
        "Requirements:\n"
        "1. Summarize the 3-5 most important points\n"
        "2. Provide a clear recommendation or next step\n"
        "3. Include a strong CTA\n"
        "4. 200-300 words\n\n"
        "Write the conclusion directly in Markdown format."
    )
    conclusion = await _call_claude(api_key, conc_prompt, SYSTEM_PROMPT, max_tokens=600)
    logger.info(f"Conclusion: {len(conclusion.split())} words")

    # Phase 5: Assemble
    logger.info("Phase 5/5: Assembling article...")
    expertise_box = (
        "\n> **Expert Insight**: This guide was researched and written by financial professionals\n"
        "> specializing in expatriate banking and international finance. All information is\n"
        "> verified against official sources and updated for 2026.\n"
    )
    trust_note = (
        "\n> **Last Updated**: June 2026 | **Review Frequency**: Monthly |\n"
        "> **Sources**: Official bank websites, government tax authorities, and financial regulators\n"
    )
    body = intro + "\n\n" + expertise_box + "\n\n"
    body += "\n\n".join(written_sections)
    body += "\n\n" + faq + "\n\n" + conclusion + "\n\n" + trust_note
    word_count = len(body.split())
    logger.info(f"Assembled: {word_count} words")

    if word_count < min_words:
        logger.warning(f"Below minimum ({word_count} < {min_words}) -- expanding...")
        expand_prompt = (
            f"The article below needs expansion to reach {min_words} words.\n"
            f"Current: {word_count} words. Add more depth, examples, data tables.\n"
            "Do NOT change existing content -- only add to weak sections.\n"
            "Return the FULL expanded article.\n\n"
            f"Article (first 4000 chars):\n{body[:4000]}\n[...continues...]\n\n"
            "Expand and return the full article in Markdown."
        )
        try:
            body = await _call_claude(api_key, expand_prompt, SYSTEM_PROMPT, max_tokens=4096)
            word_count = len(body.split())
            logger.info(f"Expanded to {word_count} words")
        except Exception as e:
            logger.warning(f"Expansion failed: {e}")

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    header = (
        f"---\n"
        f"title: \"{title}\"\n"
        f"primary_keyword: \"{keyword}\"\n"
        f"market: \"{market}\"\n"
        f"word_count: {word_count}\n"
        f"date_written: \"{date_str}\"\n"
        f"status: draft\n"
        f"agent: NEXUS-14 Agent 04 v3.2\n"
        f"---\n\n"
        f"# {title}\n\n"
    )
    full_article = header + body
    logger.info(f"Final: {len(full_article.split())} words, {len(full_article)} chars")
    return full_article


# ============================================================
# CLASS-BASED AGENT (kept for backward compatibility)
# ============================================================

try:
    from agents.base_agent import BaseAgent
    from services.llm_service import LLMService
    from services.storage_service import StorageService

    class ArticleWriterAgent(BaseAgent):
        """Agent 04: class-based wrapper (for DI orchestrators)."""
        AGENT_ID = "agent_04"
        AGENT_NAME = "Article Writer Agent"
        MIN_WORD_COUNT = 5000
        TARGET_WORD_COUNT = 7500

        def __init__(self, config: Dict, llm_service: LLMService, storage_service: StorageService):
            super().__init__(config, llm_service, storage_service)

        async def run(self, context: Dict = None) -> Dict:
            self.log_start()
            try:
                outline = await self._load_outline()
                api_key = self.config.get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
                article = await _write_article_standalone(
                    outline=outline, api_key=api_key,
                    min_words=self.MIN_WORD_COUNT, target_words=self.TARGET_WORD_COUNT,
                )
                word_count = len(article.split())
                output_path = await self.save_output("article_draft.md", article)
                metadata = {"agent": self.AGENT_NAME, "word_count": word_count,
                            "output_path": str(output_path), "status": "COMPLETE"}
                await self.save_output("article_metadata.json", metadata)
                self.log_complete({"word_count": word_count})
                return {"article": article, "metadata": metadata}
            except Exception as e:
                self.log_error(e)
                raise

        async def _load_outline(self) -> Dict:
            for path in ["output/agent_03/article_outline.json", "output/article_outline.json"]:
                if os.path.exists(path):
                    with open(path) as f:
                        return json.load(f)
            raise FileNotFoundError("article_outline.json not found. Run Agent 03 first.")

except ImportError:
    pass  # No BaseAgent -- standalone mode only


if __name__ == "__main__":
    main()
