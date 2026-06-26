#!/usr/bin/env python3
"""
NEXUS-14 V4 - agents/agent_04_writer_v4.py (M2 - Writer V4 regeneration loop)

This is the V4 orchestration layer on top of the existing Agent 04 generator
(agents/agent_04_article_writer.py). It implements the closed loop that the
V3 writer was missing:

    Agent 04 (draft) -> Agent 19 (originality) -> if regenerate_sections:
        writer_variation.build_variation_directives -> regenerate ONLY those
        sections -> strip_banned_patterns + verify_variation -> reassemble
    -> repeat until originality passes or max_rounds reached.

WHY A SEPARATE MODULE
The base agent_04_article_writer.py remains the (large, working) section
generator. This module imports it rather than rewriting it, so the proven
generation prompts are untouched while the V4 differentiation contract lives in
one small, testable place. Single source of truth for the banned-pattern
vocabulary stays in agent_19 (re-exported through services.writer_variation).

HONEST SCOPE
The actual section regeneration calls the Anthropic API (via the base module),
so the full loop only runs where ANTHROPIC_API_KEY is configured (CI/staging).
The loop CONTROL LOGIC, directive construction, banned-pattern stripping and
variation verification are all deterministic and unit-tested offline. When no
API key is present, regenerate_with_variation() raises a clear RuntimeError
instead of fabricating regenerated content.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Callable, Dict, List, Optional

from services.writer_variation import (
    build_variation_directives,
    strip_banned_patterns,
    verify_variation,
    plan_regeneration,
)
from agents.agent_19_originality import run_originality_check, split_sections

logger = logging.getLogger("agent_04_writer_v4")

# Section name -> markdown heading anchor used when reassembling the article.
SECTION_ANCHORS = {
    "introduction": None,           # leading content before the first H2
    "conclusion": "## Conclusion",
    "faq": "## FAQ",
    "body": None,                   # body is diffuse; handled by full re-emit
}

MAX_ROUNDS = 2


def reassemble_intro(article_markdown: str, new_intro: str) -> str:
    """Replace the introduction (text before the first H2) with new_intro."""
    m = re.search(r"^\s*##\s+", article_markdown, re.MULTILINE)
    if not m:
        return new_intro.strip() + "\n\n" + article_markdown.strip()
    return new_intro.strip() + "\n\n" + article_markdown[m.start():]


def replace_section(article_markdown: str, heading: str, new_text: str) -> str:
    """Replace a "## Heading ... (until next H2)" block with new_text.

    If the heading is not found, the new section is appended. Deterministic and
    safe: never deletes more than the single targeted section.
    """
    pattern = re.compile(
        re.escape(heading) + r"(.*?)(?=\n##\s+|$)",
        re.DOTALL,
    )
    block = heading + "\n\n" + new_text.strip() + "\n"
    if pattern.search(article_markdown):
        return pattern.sub(block, article_markdown, count=1)
    return article_markdown.rstrip() + "\n\n" + block


def apply_regenerated_sections(
    article_markdown: str,
    regenerated: Dict[str, str],
    seed: str = "",
) -> str:
    """Splice regenerated sections back into the article deterministically.

    Each regenerated section is first passed through strip_banned_patterns so a
    banned opener/phrase can never be reintroduced, regardless of what the model
    returned.
    """
    out = article_markdown
    for section, new_text in regenerated.items():
        cleaned, _changes = strip_banned_patterns(new_text, seed + section)
        if section == "introduction":
            out = reassemble_intro(out, cleaned)
        elif section == "body":
            # Body is diffuse; we cannot safely splice a partial body, so a body
            # flag forces the caller to regenerate the whole draft next round.
            logger.info("body flagged: full-draft regeneration required upstream")
        else:
            anchor = SECTION_ANCHORS.get(section) or ("## " + section.title())
            out = replace_section(out, anchor, cleaned)
    return out


def regenerate_with_variation(
    article_markdown: str,
    regenerate_sections: List[str],
    section_generator: Callable[[str, str], str],
    seed: str = "",
) -> Dict[str, str]:
    """Regenerate each flagged section using the supplied section_generator.

    section_generator(section_name, directive) -> new section markdown.
    In production Agent 04 passes a closure that calls the Anthropic API with the
    differentiation directive. Tests pass a deterministic stub, which is why this
    function takes the generator as a parameter (dependency injection).
    """
    plan = plan_regeneration(article_markdown, regenerate_sections, seed)
    directives = plan["directives"]
    prior = plan["prior_sections"]
    regenerated: Dict[str, str] = {}
    for section in regenerate_sections:
        directive = directives.get(section, "")
        new_text = section_generator(section, directive)
        cleaned, _ = strip_banned_patterns(new_text, seed + section)
        check = verify_variation(cleaned, prior.get(section, ""))
        if not check["sufficiently_different"]:
            logger.warning(
                "Section %s still too similar (%.3f); keeping but flagging.",
                section, check["similarity"],
            )
        regenerated[section] = cleaned
    return regenerated


def run_writer_v4_loop(
    initial_markdown: str,
    corpus: List[Dict],
    section_generator: Callable[[str, str], str],
    seed: str = "",
    max_rounds: int = MAX_ROUNDS,
    quality_check: Optional[Callable[[str], List[str]]] = None,
) -> Dict:
    """Full Writer V4 loop: draft -> originality -> targeted regeneration.

    Returns {"markdown", "rounds", "final_report", "passed"}. Pure control logic;
    all LLM work is delegated to section_generator (injected).
    """
    markdown = initial_markdown
    rounds = 0
    report = run_originality_check(markdown, corpus,
                                   output_path="output/agent_04/originality_round_0.json")
    while True:
        flagged = list(report["regenerate_sections"])
        # M8: fold in any sections the (optional) quality gate wants regenerated.
        # Never blocks: a failing or missing gate simply contributes no sections.
        if quality_check is not None:
            try:
                for sec in quality_check(markdown):
                    if sec not in flagged:
                        flagged.append(sec)
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                logger.warning("M8 quality gate skipped (%s)", exc)
        if report["passed"] and not flagged:
            break
        if rounds >= max_rounds or not flagged:
            break
        rounds += 1
        regenerated = regenerate_with_variation(markdown, flagged, section_generator, seed)
        markdown = apply_regenerated_sections(markdown, regenerated, seed)
        report = run_originality_check(
            markdown, corpus,
            output_path="output/agent_04/originality_round_%d.json" % rounds,
        )
    return {
        "markdown": markdown,
        "rounds": rounds,
        "passed": report["passed"],
        "final_report": report,
    }


def _anthropic_section_generator(seed: str = "") -> Callable[[str, str], str]:
    """Build the production section generator that calls the Anthropic API.

    INTEGRATION POINT. Imports the base writer lazily so this module can be
    imported (and unit-tested) without the heavy generator or an API key.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set: cannot regenerate sections. "
            "Writer V4 loop control is testable offline, but real regeneration "
            "requires the API (run in CI/staging)."
        )
    import asyncio
    from agents.agent_04_article_writer import _call_claude, SYSTEM_PROMPT

    def _gen(section: str, directive: str) -> str:
        prompt = (
            "Regenerate the article section: " + section + ".\n"
            + directive + "\n"
            "Return ONLY the new Markdown for this section."
        )
        return asyncio.run(_call_claude(api_key, prompt, SYSTEM_PROMPT, max_tokens=1800))

    return _gen


if __name__ == "__main__":
    import argparse, json, sys
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Agent 04 Writer V4 regeneration loop")
    parser.add_argument("--input", required=True, help="initial article markdown")
    parser.add_argument("--corpus-dir", default="output/published_corpus")
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", default="")
    args = parser.parse_args()

    md = Path(args.input).read_text(encoding="utf-8")
    corpus = []
    cdir = Path(args.corpus_dir)
    if cdir.exists():
        for f in sorted(cdir.glob("*.md")):
            corpus.append({"markdown": f.read_text(encoding="utf-8")})

    gen = _anthropic_section_generator(args.seed)  # raises if no API key
    result = run_writer_v4_loop(md, corpus, gen, seed=args.seed)
    Path(args.output).write_text(result["markdown"], encoding="utf-8")
    logger.info("Writer V4 loop rounds=%d passed=%s", result["rounds"], result["passed"])
    sys.exit(0 if result["passed"] else 2)

# end of Writer V4 loop (M2 + M8 quality hook
