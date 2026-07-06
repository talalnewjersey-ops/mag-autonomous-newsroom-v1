"""
NEXUS-14: Agent 04 - Article Writer Agent COST-OPTIMIZED v5.0
TIER 1 PILLAR: 4500-5000w max | 12 FAQs | 3 case studies | 5 images | 6+ sources
TIER 2 STANDARD: 4000-4500w max | 10 FAQs | 2 case studies | 4 images | 5+ sources
TIER 3 OPPORTUNITY: 3500-4000w max | 8 FAQs | 1-2 case studies | 3 images | 3+ sources
GLOBAL RULE: Maximum quality per dollar. Search intent satisfaction > article length.
"""

import argparse, asyncio, json, logging, os, re, sys
from agents._source_pool import select_official_sources, has_curated_pool, resolve_vertical
from agents._vertical_facts import VERTICAL_FACTS  # Couche 1: verified .gov facts to cite
from agents._real_internal_links import fetch_real_posts, select_relevant_links  # POINT 4: live sitemap/REST, never a static dict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse  # used by _normalize_source_url (restored after main<-sprint4 merge)
from agents._sources import _classify_url  # shared source allow-list (single source of truth)

# --- YMYL source allow-list -----------------------------------------------
# The official-source classifier and allow-list now live in agents/_sources.py
# (single source of truth, shared with agent_05_fact_checker). _classify_url is
# imported above. Internal-link / off-list handling in the gate is unchanged.


def _normalize_source_url(url: str) -> str:
    """Normalize a URL to a single PAGE identity for de-duplication.
    The tier source minimum counts DISTINCT official pages, not raw link
    occurrences: citing one authoritative page 4x must NOT satisfy a
    minimum of 4. We collapse on scheme://host/path, stripping trailing
    markdown punctuation captured by \\S+, the #fragment, the ?query and a
    trailing slash, so the same page written several ways counts once."""
    s = url.rstrip(").],.;\"\'>")
    s = s.split("#", 1)[0]
    s = s.split("?", 1)[0]
    p = urlparse(s)
    host = (p.hostname or "").lower()
    path = (p.path or "").rstrip("/")
    return f"{p.scheme.lower()}://{host}{path}"

logger = logging.getLogger(__name__)

PILLAR_MIN_WORDS = 3800
PILLAR_TARGET_WORDS = 4200
PILLAR_MAX_WORDS = 4200
PILLAR_MIN_FAQS = 12
PILLAR_MIN_SOURCES = 6
PILLAR_MIN_INTERNAL_LINKS = 8
PILLAR_MIN_CASE_STUDIES = 0  # Sprint 8: case studies removed (anti-fabrication). DEBT: reintroduce REAL sourced ones in phase C.

STANDARD_MIN_WORDS = 3500
STANDARD_TARGET_WORDS = 4000
STANDARD_MAX_WORDS = 4000
STANDARD_MIN_FAQS = 10
STANDARD_MIN_SOURCES = 4
STANDARD_MIN_INTERNAL_LINKS = 3
STANDARD_MIN_CASE_STUDIES = 0  # Sprint 8: see PILLAR_MIN_CASE_STUDIES note

OPPORTUNITY_MIN_WORDS = 3500
OPPORTUNITY_TARGET_WORDS = 4000
OPPORTUNITY_MAX_WORDS = 4000
OPPORTUNITY_MIN_FAQS = 8
OPPORTUNITY_MIN_SOURCES = 3
OPPORTUNITY_MIN_INTERNAL_LINKS = 4
OPPORTUNITY_MIN_CASE_STUDIES = 0  # Sprint 8: see PILLAR_MIN_CASE_STUDIES note

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
    parser.add_argument("--category", type=str, default="", help="Registry category (routes the official-source vertical)")
    parser.add_argument("--market", type=str, default="", help="Registry market USA/Canada (routes the official-source vertical)")
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
    # Propagate registry market + category (CLI > env > outline) so the official-
    # source vertical is routed deterministically instead of guessed from keywords.
    resolved_category = args.category or os.environ.get("ARTICLE_CATEGORY", "") or outline.get("category", "")
    resolved_market = args.market or os.environ.get("ARTICLE_MARKET", "") or outline.get("market", "")
    if resolved_category:
        outline["category"] = resolved_category
    if resolved_market:
        outline["market"] = resolved_market
    logger.info(f"Loaded outline: {outline.get('title', 'Unknown')} | market={outline.get('market','')} category={outline.get('category','')}")
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

async def _ensure_faq_count(faq_text, keyword, market, target_audience, api_key, min_faqs, target_faqs, facts_and_rules=""):
    current_count = _count_faqs(faq_text)
    attempt = 0
    while current_count < min_faqs and attempt < 3:
        needed = target_faqs - current_count
        attempt += 1
        try:
            extra = await _call_claude(api_key,
                f"Generate EXACTLY {needed} additional FAQ items for: {keyword} ({market})\nDo NOT duplicate: {_extract_faq_questions(faq_text)}\nFormat: ### [Question?]\nAnswer 80-150w{facts_and_rules}",
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
    # Sprint 2 fix-sources: count OFFICIAL EXTERNAL sources (host-based allow-list)
    # separately. The tier minimum applies to official external sources only, so an
    # article cannot satisfy it with internal links or off-list links alone
    # (closes the YMYL false-E-E-A-T hole). Internal-link check below is UNCHANGED.
    _all_urls = re.findall(r"https?://\S+", article)
    # official_sources = raw link OCCURRENCES (a page cited 4x counts 4); kept for the log.
    official_sources = sum(1 for _u in _all_urls if _classify_url(_u) == "official")
    offlist_sources = sum(1 for _u in _all_urls if _classify_url(_u) == "offlist")
    # The tier minimum is satisfied by DISTINCT official PAGES, not occurrences, so an
    # article cannot pass by citing ONE authority N times (false E-E-A-T). De-dup on the
    # normalized scheme://host/path. NOTE: dedup is by PAGE, not by host: several distinct
    # pages on the same authority host (e.g. four different canada.ca pages) correctly
    # count as four. Reliability-first: log occurrences AND distinct pages on EVERY run
    # (pass OR fail) so runs report N without opening the artifact.
    _official_pages = {_normalize_source_url(_u) for _u in _all_urls if _classify_url(_u) == "official"}
    distinct_official = len(_official_pages)
    logger.info(f"SOURCES: {official_sources} official occurrence(s), {distinct_official} distinct page(s), {offlist_sources} off-list")
    if distinct_official < tier["min_sources"]:
        errors.append(
            f"Distinct official sources {distinct_official} < minimum {tier['min_sources']} "
            f"(allow-list: *.gov, *.canada.ca, canada.ca; counted by distinct page, not by "
            f"repeated link). Off-list external links ({offlist_sources}) and internal links "
            f"do NOT count toward the minimum."
        )
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

SYSTEM_PROMPT = """You are Chief Content Officer for MoneyAbroadGuide.com, a licensed financial information platform.
GLOBAL RULE: Maximum quality per dollar. No unnecessary padding. Satisfy search intent with authoritative financial content.
Focus: newcomers, immigrants, expats in Canada and USA.
ARTICLE-LEVEL STRUCTURE (each written ONCE, in its own dedicated end section — NEVER repeat inside body sections): comparison table | expert recommendation | compliance disclaimer | author box (Talal Eddaouahiri, founder MoneyAbroadGuide.com)
EEAT REQUIREMENTS (Google E-E-A-T compliance — achieve score 90+/100):
- EXPERTISE: Include technical terminology (FINTRAC, OSFI, FCAC, CRA, IFHP, provincial health authority, MSB, regulation, compliance, licensed)
  Include regulatory references with specific act names, regulatory bodies, official statistics
  Include data and statistics with "according to [source]", "data shows", "statistics indicate", specific percentages
  Include expert credentials: cite financial advisors, regulatory experts, licensed professionals
- EXPERIENCE: First-person examples ("newcomers report", "immigrants experience"), specific case studies, real-world scenarios
  Step-by-step processes, detailed how-to procedures, specific timelines and costs
- AUTHORITY: Reference government sources (Canada.ca, CRA, IRCC, provincial health), link to official documents
  Cite industry reports, regulatory publications, licensed provider comparisons
- TRUST: Reference official regulatory oversight and mention licensed/regulated providers.
  (The compliance disclaimer and the author box are written ONCE, only in their dedicated end sections — do NOT insert them into body sections.)
OUTPUT: Raw Markdown only — articles must score 85+ on EEAT validation."""

async def _call_claude(api_key: str, prompt: str, system: str = None, max_tokens: int = 5000,
                       model: str = None) -> str:
    # SPRINT 2 (RCA-003): writer now uses Claude Sonnet for quality. Overridable via env.
    if model is None:
        model = os.getenv("ARTICLE_WRITER_MODEL", "claude-sonnet-4-6")
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

# SPRINT 2 (B / RCA-004): cumulative-context digest.
# Deterministic, no LLM (cost ~0). Bounded reinjection so the section prompt never
# explodes the context window or cost. Lists ENTITIES and FIGURES already cited so
# the writer does not re-introduce/re-explain them (drives down diffuse repetition / DRI).
_DIGEST_DOMAIN_TERMS = {
    "bank", "banks", "account", "accounts", "newcomer", "newcomers", "immigrant",
    "immigrants", "canada", "usa", "credit", "money", "financial",
    "moneyabroadguide", "canadian",
}
_DIGEST_ENT_BLACKLIST = {
    "quick", "answer", "most", "arriving", "according", "without", "opening",
    "you", "your", "this", "the", "why", "need", "required", "documents",
    "proof", "address", "best", "guide", "processing", "immediately",
}
_DIGEST_MAX_TOTAL_CHARS = 1400  # hard cap on reinjected digest (~350 tokens max)


def _build_digest(written_sections: List[str]) -> str:
    """Bounded, deterministic summary of what was already written, to reinject
    into the next section prompt (RCA-004). Surfaces, in priority order:
    covered section titles, named entities already cited, and figures already
    stated -- so the writer references rather than re-derives them."""
    if not written_sections:
        return ""
    entities, numbers, covered, rules, offers = [], [], [], [], []
    seen_ent, seen_num, seen_rule, seen_offer = set(), set(), set(), set()
    for sec in written_sections:
        mt = re.search(r"^#{1,3}\s+(.+)$", sec, re.MULTILINE)
        if mt:
            covered.append(mt.group(1).strip()[:80])
        body = re.sub(r"^#{1,6}\s+.*$", "", sec, flags=re.MULTILINE)
        for sentence in re.split(r"(?<=[.!?])\s+", body):
            sentence = sentence.strip()
            if not sentence:
                continue
            for m in re.finditer(r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,4}|[A-Z]{2,6})\b", sentence):
                ent = m.group(0).strip()
                is_acr = bool(re.fullmatch(r"[A-Z]{2,6}", ent))
                words = ent.split()
                if m.start() == 0 and len(words) == 1 and not is_acr:
                    continue
                if not is_acr and len(words) < 2:
                    continue
                base = words[0].lower()
                if base in _DIGEST_ENT_BLACKLIST or base in _DIGEST_DOMAIN_TERMS:
                    continue
                meaningful = [w for w in words
                              if w.lower() not in _DIGEST_DOMAIN_TERMS
                              and w.lower() not in _DIGEST_ENT_BLACKLIST]
                if not meaningful and not is_acr:
                    continue
                key = ent.lower()
                if key not in seen_ent and len(ent) > 2:
                    seen_ent.add(key)
                    entities.append(ent)
        for m in re.finditer(r"(\$\s?\d[\d,.]*|\d[\d,.]*\s?(?:%|days?|business days?|months?|years?|pieces?\s+of\s+id|pieces?|CAD|USD))", sec, re.IGNORECASE):
            n = re.sub(r"\s+", " ", m.group(0).strip())
            if n and n.lower() not in seen_num and any(c.isdigit() for c in n):
                seen_num.add(n.lower())
                numbers.append(n)
        # SPRINT 2 (RCA-004 b): capture KEY RULES/REFERENCES already explained so the
        # writer does not RE-EXPLAIN them (legal citations, grouped large numbers).
        for m in re.finditer(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+Act\b(?:[^.\n]{0,40}?(?:R\.?S\.?C\.?|S\.?C\.?)\s*\d{4})?|(?:R\.?S\.?C\.?|S\.?C\.?)\s*\d{4}[^.\n]{0,12})", sec):
            ref = re.sub(r"\s+", " ", m.group(0).strip())[:60]
            if ref and ref.lower() not in seen_rule:
                seen_rule.add(ref.lower())
                rules.append(ref)
        for m in re.finditer(r"\b\d{1,3}(?:[ ,]\d{3})+\b", sec):
            n2 = re.sub(r"\s+", " ", m.group(0).strip())
            if n2 and n2.lower() not in seen_num:
                seen_num.add(n2.lower())
                numbers.append(n2)
        # SPRINT 2 (a'): capture PRODUCT/OFFER NAMES already described (e.g. "Signature No
        # Limit Banking", "StartRight Program", "NewStart", cross-border) so the writer
        # names them once and does not re-describe the same offer in a later section.
        for m in re.finditer(r"\b([A-Z][A-Za-z0-9]+(?:\s+(?:No|[A-Z][A-Za-z0-9]+)){1,4}\s+(?:Program|Account|Banking|Plan|Offer|Package|Bundle|Chequing|Savings))\b", sec):
            off = re.sub(r"\s+", " ", m.group(0).strip())[:60]
            if off and off.lower() not in seen_offer:
                seen_offer.add(off.lower())
                offers.append(off)
        for m in re.finditer(r"(?i)\b(StartRight|NewStart|Signature No Limit|cross[- ]border banking)\b", sec):
            off = re.sub(r"\s+", " ", m.group(0).strip())
            if off and off.lower() not in seen_offer:
                seen_offer.add(off.lower())
                offers.append(off)
    parts = []
    if covered:
        parts.append("SECTIONS ALREADY WRITTEN (do not re-introduce these topics):\n"
                     + "; ".join(covered[:8]))
    if entities:
        parts.append("ENTITIES/SOURCES ALREADY CITED (reference, do NOT re-explain):\n"
                     + ", ".join(entities[:25]))
    if numbers:
        parts.append("FACTS/NUMBERS ALREADY STATED (do NOT repeat these figures):\n"
                     + ", ".join(numbers[:25]))
    if rules:
        parts.append("RULES/REFERENCES ALREADY EXPLAINED (do NOT re-define or re-explain; only refer back):\n"
                     + ", ".join(rules[:15]))
    if offers:
        parts.append("PRODUCT/OFFER NAMES ALREADY DESCRIBED (name them, do NOT re-describe the same offer):\n"
                     + ", ".join(offers[:20]))
    digest = "\n".join(parts)
    if len(digest) > _DIGEST_MAX_TOTAL_CHARS:
        digest = digest[:_DIGEST_MAX_TOTAL_CHARS].rsplit(",", 1)[0] + " \u2026"
    return digest


def _build_facts_block(source_vertical: str) -> str:
    """Couche 1 (SUPPLY, not a guarantee): hand the writer VERIFIED .gov facts so it
    cites real figures instead of inventing them. This lowers the invention RATE; it
    does NOT block hallucination -- the real run on 2026-07-03 proved the writer
    ignores prompt rules. The deterministic blockers are Couche 2 (soften) and
    Couche 3 (G-Substance gate), NOT this text. Returns "" when the vertical has no
    fact sheet (graceful fallback to source-pool-only; no regression).

    VOLATILE facts are SOURCE-ONLY: neither `value` nor `note` is injected, because
    the note may carry the very moving figure we withhold (e.g. CA "30/60/25",
    Reg CC "$225->$275"). The writer is told to stay qualitative and just link the
    source -- never handed a number to parrot or a gap that invites inventing one.
    """
    facts = VERTICAL_FACTS.get(source_vertical)
    if not facts:
        return ""
    lines = []
    for f in facts:
        url = f["source_url"]
        if f.get("status") == "VOLATILE":
            lines.append(
                f"- {f['claim']}: this figure changes over time -- do NOT state a specific "
                f"number; describe it qualitatively and link {url} ."
            )
        elif f.get("value"):
            lines.append(f"- {f['claim']}: {f['value']} -- cite {url} on the same sentence.")
        else:  # STABLE qualitative: the note is safe, non-numeric guidance
            lines.append(f"- {f['claim']}: {f.get('note', '')} (link {url} ).")
    return (
        "\nVERIFIED FACTS (use THESE for any figure; never invent one outside this list; "
        "for source-only items stay qualitative and just link):\n" + "\n".join(lines)
    )


async def _write_article_standalone(outline: Dict, api_key: str, min_words: int = STANDARD_MIN_WORDS,
                                     target_words: int = STANDARD_TARGET_WORDS, tier: dict = None) -> str:
    if tier is None:
        tier = _get_tier_config("STANDARD")
    title = outline.get("title", "Article")
    keyword = outline.get("primary_keyword", "")
    market = outline.get("market", "Canada")
    category = outline.get("category", "")
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
    # Source vertical (official-source pool) is routed on the registry market +
    # category (deterministic). US topics resolve to a us_* vertical or
    # us_default; non-US topics fall back to the keyword-derived topic_key
    # (e.g. canada_newcomer) -- topic_key's only remaining use.
    source_vertical = resolve_vertical(market, category) or topic_key
    # POINT 4 (2026-07-05): the static INTERNAL_LINKS dict was removed -- it had
    # drifted to 18/21 (86%) dead links, hardcoded and never re-verified. A link
    # is now offered ONLY if it is confirmed present in the LIVE WP REST API
    # post list fetched right now; zero relevant real posts -> zero internal
    # links for this article (acceptable; never invented/guessed). Fail-soft:
    # an unreachable REST API returns [] (logged), never a crash, never a
    # fallback to a stale list.
    _real_posts = fetch_real_posts()
    _relevant_posts = select_relevant_links(f"{keyword} {title}", _real_posts, n=tier["min_links"])
    links = [f"[{p['title']}]({p['url']})" for p in _relevant_posts]
    _links_sel = links[:tier["min_links"]]
    links_block = "\n".join(f"- {l}" for l in _links_sel) if _links_sel else "(no relevant internal links found for this topic)"
    # SPRINT 2: split internal links so intro and Expert Recommendation never cite the SAME link verbatim.
    # NB: these blocks are already bounded by link COUNT (_links_sel[:_half]); NEVER char-slice them
    # ([:200]/[:300]) when interpolating into a prompt -- a char cut lands mid-URL and the model
    # faithfully reproduces the truncated link (dead internal URL, e.g. .../international-money-).
    _half = max(1, (len(_links_sel) + 1) // 2)
    links_intro_block = "\n".join(f"- {l}" for l in _links_sel[:_half])
    links_expert_block = "\n".join(f"- {l}" for l in _links_sel[_half:]) or links_intro_block

    # FIX(writer): for known verticals, hand the model a SHORT list of REAL,
    # live-checked official sources (curated in agents/_source_pool.py) instead
    # of relying on it to recall URLs from memory. Margin > tier minimum so the
    # gate is reliably met. Unknown verticals fall back to the legacy prompt.
    _official_sel = select_official_sources(source_vertical, tier["min_sources"] + 3)
    # SPRINT/COUCHE 1: verified .gov figures for this vertical, so the writer cites
    # real numbers instead of inventing. SUPPLY only -- the deterministic anti-
    # hallucination blockers are Couche 2 (soften) + Couche 3 (G-Substance), not this.
    _facts_block = _build_facts_block(source_vertical)
    # SPRINT 10 anti-hallucination (levier A): no fabricated numbers or attributions.
    # Applies to EVERY section (intro, body, comparison table). Enforced by agent_05
    # (claim<->citation) + the agent_12 QA penalty.
    _anti_fab = (
        "\nNUMBERS & ATTRIBUTIONS — ANTI-FABRICATION (YMYL, no human review): every hard "
        "statistic (a %, a $ amount, 'N times', 'X out of Y') MUST be backed by one of the "
        "official links above ON THE SAME SENTENCE, OR written qualitatively ('varies by "
        "state', 'typically', 'often') — never a fabricated precise figure. NEVER attribute a "
        "statistic to a named organisation (e.g. 'according to X', 'X reports', 'X (2024)') "
        "unless X is one of the official sources above AND linked on that claim. This applies "
        "to the comparison table too (sourced or qualitative figures only). An unsourced number "
        "or an unbacked named attribution FAILS the fact-check gate and lowers the QA score."
    )
    if has_curated_pool(source_vertical) and _official_sel:
        _official_block = "\n".join(f"- {s}" for s in _official_sel)
        sourcing_block = (
            f"SOURCING (YMYL/E-E-A-T): the full article MUST cite AT LEAST 4 DIFFERENT official pages from this list (different pages, not the same one repeated). Draw on these key REAL, "
            f"verified official sources as full https:// links. Do NOT invent or alter URLs -- copy "
            f"them exactly as given, and INTEGRATE each one into the specific claim it supports "
            f"(no orphan 'references' list). Use a DIFFERENT page for each claim; the gate counts DISTINCT pages, NOT repeated links, so re-citing the same page does NOT help. NEVER force an irrelevant source just to reach 4 -- an honest shortfall (and gate FAIL) is better than a forced, off-topic link.\n"
            f"{_official_block}\n"
            f"These official sources count toward the article-wide minimum (carried mainly by the body sections) and are counted separately from internal "
            f"moneyabroadguide.com links; off-list links (banks, financial press) are allowed but "
            f"do NOT count toward the minimum."
            + _anti_fab + _facts_block
        )
    else:
        sourcing_block = (
            f"SOURCING (YMYL/E-E-A-T): you MUST cite at least {tier['min_sources']} EXTERNAL official "
            f"sources as full https:// links. These official authorities are SAFE, EXPECTED sources -- "
            f"cite them confidently; do not invent or guess URLs, just link the real authority pages you "
            f"know. For Canadian topics use real pages on canada.ca or *.gc.ca (FCAC, CRA, IRCC, FINTRAC); "
            f"for US topics use *.gov (IRS, FDIC, CFPB, USCIS). Each source must be RELEVANT to the claim "
            f"it supports -- no duplicates. These official sources are REQUIRED and counted separately "
            f"from internal moneyabroadguide.com links; off-list links do NOT count toward the minimum."
            + _anti_fab + _facts_block
        )

    # OPTION C (2026-07-05): the anti-fabrication rule + the Couche 1 facts, appended
    # to the sections that used to generate content WITHOUT them (comparison, Expert,
    # FAQ + FAQ top-up, closing, word-count expansion). With the facts in front of it
    # the writer CITES them instead of inventing numbers -- the same effect Couche 1
    # already has in the intro + body. (intro/body get the full sourcing_block above.)
    # G3 de-dup (2026-07-05): universal injection made the writer PARROT a fact's exact
    # sentence into every section -> the anti-repetition gate (G3) tripped on duplicate
    # phrases / section similarity. Fix WITHOUT re-opening invention: keep every fact
    # AVAILABLE in every section (below), only ask for VARIED WORDING. The fact is never
    # removed, so a section can never end up without it -> worst case is a cosmetic
    # duplicate, never a fabricated number.
    _dedup_wording = (
        "\nWORDING (anti-repetition / G3): cite each fact WHERE it is genuinely relevant, "
        "but phrase it in YOUR OWN WORDS for THIS section — NEVER copy a fact's supplied "
        "wording verbatim, and NEVER reuse a sentence already used in another section. The "
        "facts and their links remain available in every section; vary the wording, keep the citation."
    )
    _facts_and_rules = _anti_fab + _dedup_wording + _facts_block

    logger.info(f"Writing {tier['tier']} article: {title} (target: {target_words}w)")

    intro = await _call_claude(api_key,
        f"Write introduction: {title} | {keyword} | {market} | Tier: {tier['tier']}\n"
        f"300-400w. Quick Answer box (40-60w). 2-3 internal links:\n{links_intro_block}\nBe concise.\n"
        f"{sourcing_block}\n",
        SYSTEM_PROMPT, max_tokens=1200)

    written_sections = []
    max_sections = 5 if tier["tier"] == "PILLAR" else (4 if tier["tier"] == "STANDARD" else 3)
    for i, section in enumerate(sections[:max_sections]):
        h2 = section.get("h2", f"Section {i+1}")
        sec_target = 600 if tier["tier"] == "PILLAR" else (500 if tier["tier"] == "STANDARD" else 400)
        # SPRINT 2 (B / RCA-004): cumulative context. Include the intro (where
        # entities/figures are first planted) plus all prior sections.
        digest = _build_digest([intro] + written_sections)
        # FIX-WRITER: curated official sources available in EACH section call (not just intro);
        # distributed via "already cited" hint so they spread instead of piling up. Gate unchanged.
        section_sources_block = ""
        if has_curated_pool(source_vertical) and _official_sel:
            _all_prior = intro + "\n" + "\n".join(written_sections)
            _cited = [u for u in _official_sel if u in _all_prior]
            _pool_lines = "\n".join(f"- {u}" for u in _official_sel)
            _cited_line = ", ".join(_cited) if _cited else "none yet"
            section_sources_block = (
                "\n\n=== OFFICIAL SOURCES - use across the article (not all in one place) ===\n"
                + _pool_lines + "\n"
                + f"Already cited in earlier sections (DO NOT repeat these to pad the count -- the gate counts distinct pages only; pick a page NOT yet used): {_cited_line}\n"
                "For THIS section: most factual sections (fees, rules, eligibility, steps, rights, "
                "deadlines) CAN be supported by one of these authorities -- actively look for which "
                "one backs a claim in this section before concluding none fits. If one genuinely "
                "supports a factual claim here, cite it as a real inline https:// link on that claim. "
                "Cite every relevant source you find for this section, without forcing any off-topic "
                "one, and do NOT add an orphan 'references' line. Strongly prefer a page NOT yet cited so the article reaches at least 4 DISTINCT official pages overall -- but NEVER force an off-topic source just to hit the count; a relevant page or none.\n"
                f"Reminder: the complete article must cite at least {tier['min_sources']} DISTINCT "
                "official sources from this list, spread across sections -- if earlier sections cited "
                "few, this section should carry one.\n=== END OFFICIAL SOURCES ===\n"
                + _facts_block
            )
        digest_block = ""
        if digest:
            digest_block = (
                "\n\n=== CONTEXT - ALREADY COVERED EARLIER IN THIS ARTICLE ===\n"
                + digest
                + "\n=== END CONTEXT ===\n"
                "INSTRUCTION: The entities, facts, numbers and rules/references listed above "
                "have ALREADY been explained earlier in this article. Do NOT give their "
                "definition or explanation a second time. If you must mention one, refer back "
                "in half a sentence (e.g. \"as noted above, CDIC insures...\") and move on. "
                "This section must ADD NEW information; do not re-derive what is already covered. "
                "If a product/offer above is relevant, refer to it BY NAME without repeating its full description. "
                "Avoid reusing the same opening sentence patterns as earlier sections.\n"
            )
        try:
            sec_text = await _call_claude(api_key,
                f"Write section ## {i+1}. {h2} for: {title} | {keyword}\n{sec_target}-{sec_target+150}w. Concise. No padding. BODY ONLY: no compliance disclaimer, no author bio, no brand slogan, no 'not financial advice' notice, no internal-link CTA in this section — those are written elsewhere exactly once.{digest_block}{section_sources_block}",
                SYSTEM_PROMPT, max_tokens=1800)
            written_sections.append(sec_text)
            await asyncio.sleep(0.2)
        except Exception as e:
            written_sections.append(f"## {i+1}. {h2}\n\nContent unavailable.\n")

    # G3 de-dup: a digest of what the body already covered, so the trailing sections
    # (comparison / Expert / FAQ / closing / expansion) do NOT re-explain the same facts
    # at length. They may still CITE a fact (it stays in _facts_and_rules), but briefly
    # and in their own words -> lowers section similarity without removing any fact.
    _covered = _build_digest([intro] + written_sections)
    _dedup_digest = (
        "\n\n=== ALREADY COVERED EARLIER IN THIS ARTICLE (do NOT re-explain these at "
        "length; if this section must reference one, state it briefly in your OWN words, "
        "not the same sentences used above) ===\n" + _covered + "\n=== END ===\n"
    ) if _covered else ""

    comparison = await _call_claude(api_key,
        f"Write comparison table section for: {keyword} ({market}). H2 header. 4+ cols 6+ rows. 200-300w context.{_facts_and_rules}{_dedup_digest}",
        SYSTEM_PROMPT, max_tokens=1200)

    # Sprint 8 (anti-fabrication, YMYL no human review): the invented case-study
    # section is REMOVED. It used to prompt for specific personas and figures with
    # no sourcing -- a Helpful-Content/AdSense liability. DEBT (phase C): reintroduce
    # case studies built ONLY from REAL, sourced material (anonymized regulator
    # examples, public rate schedules).
    case_studies = ""

    expert_section = await _call_claude(api_key,
        f"Write Expert Recommendation section for: {keyword} ({market}). H2. Top pick + runner-up. 300-400w. 2 internal links from: {links_expert_block}{_facts_and_rules}{_dedup_digest}",
        SYSTEM_PROMPT, max_tokens=1000)

    min_faqs = tier["min_faqs"]
    target_faqs = min_faqs + 2
    faq = await _call_claude(api_key,
        f"Write FAQ section for: {keyword} ({market}). {target_faqs} questions (minimum {min_faqs}).\n"
        f"### [Question?] format. 80-150w answers. MUST produce at least {min_faqs} ### headings ending with ?{_facts_and_rules}{_dedup_digest}",
        SYSTEM_PROMPT, max_tokens=target_faqs * 280)
    # Ensure minimum FAQ count — restore _ensure_faq_count (fixes FAQ validation failure)
    faq = await _ensure_faq_count(faq, keyword, market, target_audience, api_key, min_faqs, target_faqs, _facts_and_rules)

    closing = await _call_claude(api_key,
        f"Write 3 sections for: {title}\n"
        f"1. ## Conclusion (200-300w)\n"
        f"2. ## Disclaimer (150-200w, legal, affiliate disclosure)\n"
        f"3. ## About the Author (Talal Eddaouahiri, founder MoneyAbroadGuide.com, 100-150w){_facts_and_rules}{_dedup_digest}",
        SYSTEM_PROMPT, max_tokens=1200)

    _updated = datetime.utcnow().strftime("%B %Y")
    body = "\n\n".join([s for s in [intro, "\n\n".join(written_sections) if written_sections else "",
                          comparison, case_studies, expert_section, faq, closing,
                          f"> **Last Updated**: {_updated} | **Tier**: {tier['tier']} | NEXUS-14 V5.0"] if s])
    word_count = len(body.split())
    if word_count < min_words:
        try:
            extra = await _call_claude(api_key,
                f"Article needs {min_words - word_count} more words. Add 4 more FAQ questions and a practical tips section (H2, 5 tips). Return ONLY new Markdown.{_facts_and_rules}{_dedup_digest}",
                SYSTEM_PROMPT, max_tokens=1500)
            body = body + "\n\n" + extra
        except Exception as e:
            logger.warning(f"Expansion failed: {e}")

    # Sprint 8: emit NO YAML frontmatter and NO body-level title heading. Frontmatter
    # fields used to render as visible <p> paragraphs (RCA-007) and a body title
    # heading produced a SECOND page H1 on top of the WordPress post title. The post
    # title is the single page H1; metadata lives in article_metadata.json / outline.
    return body


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
