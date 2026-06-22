#!/usr/bin/env python3
"""
NEXUS-14 V3 - Agent 17: Content Cannibalization Agent (HARDENED)
MoneyAbroadGuide.com | Prevents duplicate content before production.

Decisions: CREATE_NEW_ARTICLE | UPDATE_EXISTING_ARTICLE | MERGE_WITH_EXISTING | REJECT_DUPLICATE
Runs BEFORE Agent 04. Output: cannibalization_report.json

HARDENING (Priority 1 implementation — see Issue #4, PR #6):
  * Deterministic duplicate detection is AUTHORITATIVE. The Claude/AI semantic
    pass remains ADVISORY only and can never DOWNGRADE a deterministic block.
  * New deterministic signals:
      - Title similarity (existing, retained)
      - Primary keyword duplication (exact + normalized)
      - Slug duplication (exact + normalized)
      - Near-duplicate title detection
      - Country-aware duplication (USA vs Canada variants are NOT duplicates;
        same-country same-topic IS a duplicate)
      - Country / category conflict detection (a USA topic mapped to a Canada
        category, or vice-versa, is blocked)
  * Any blocking signal sets blocking=True and decision=REJECT_DUPLICATE and
    requires manual review. AI may add context but cannot clear the block.
"""

import json, logging, os, re, sys
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

import anthropic
import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-17] %(levelname)s %(message)s")
logger = logging.getLogger("agent_17_cannibalization")

WP_URL = os.getenv("WORDPRESS_URL", "")
WP_USER = os.getenv("WORDPRESS_USERNAME", "")
WP_PASS = os.getenv("WORDPRESS_APP_PASSWORD", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Deterministic thresholds (authoritative)
SIMILARITY_THRESHOLD = 0.72        # flag as conflict for review
REJECT_THRESHOLD = 0.85            # hard block (same-country)
TITLE_NEAR_DUP_THRESHOLD = 0.90    # near-duplicate title hard block (same-country)
KEYWORD_OVERLAP_REJECT = 0.80      # primary-keyword duplication hard block (same-country)

DECISIONS = {
    "CREATE_NEW": "CREATE_NEW_ARTICLE",
    "UPDATE": "UPDATE_EXISTING_ARTICLE",
    "MERGE": "MERGE_WITH_EXISTING",
    "REJECT": "REJECT_DUPLICATE",
}

# ------------------------------------------------------------------
# Country detection (deterministic, content-signal based)
# ------------------------------------------------------------------
COUNTRY_SIGNALS = {
    "USA": [
        "usa", "u.s.", "u.s.a", "united states", "america", "american",
        "irs", "ssn", "itin", "social security", "green card", "i-94",
        "dmv", "401k", "fafsa", "medicaid", "medicare", "fdic", "credit karma",
        "chase", "wells fargo", "bank of america", "zelle",
    ],
    "CANADA": [
        "canada", "canadian", "cra", "sin number", "social insurance",
        "rrsp", "tfsa", "gic", "interac", "newcomer to canada",
        "permanent resident", "pr card", "service canada", "cdic",
        "td canada", "rbc", "scotiabank", "cibc",
    ],
}

def detect_country(*texts):
    """Return 'USA', 'CANADA', or 'UNKNOWN' from content signals.
    Deterministic. If both countries score and are close, returns 'AMBIGUOUS'.
    """
    blob = " ".join(t for t in texts if t).lower()
    scores = {}
    for country, signals in COUNTRY_SIGNALS.items():
        scores[country] = sum(1 for s in signals if s in blob)
    usa, can = scores.get("USA", 0), scores.get("CANADA", 0)
    if usa == 0 and can == 0:
        return "UNKNOWN"
    if usa > 0 and can > 0 and abs(usa - can) <= 1:
        return "AMBIGUOUS"
    return "USA" if usa > can else "CANADA"


def normalize_slug(slug):
    s = (slug or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    # strip country qualifiers so usa/canada variants compare on the core topic
    s = re.sub(r"-(usa|us|america|canada|canadian)(-|$)", r"\\2", s)
    return s.strip("-")


def slugify_topic(topic):
    return normalize_slug(topic)


def fetch_wordpress_articles(status="any", per_page=100):
    if not WP_URL:
        logger.warning("WORDPRESS_URL not set - skipping WP scan")
        return []
    articles, page, auth = [], 1, HTTPBasicAuth(WP_USER, WP_PASS)
    while True:
        try:
            resp = requests.get(f"{WP_URL}/wp-json/wp/v2/posts", auth=auth,
                params={"status": status, "per_page": per_page, "page": page,
                        "fields": "id,slug,title,date,modified,status,link,categories"}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            articles.extend(data)
            if page >= int(resp.headers.get("X-WP-TotalPages", 1)):
                break
            page += 1
        except Exception as e:
            logger.error(f"WP fetch error: {e}")
            break
    logger.info(f"Fetched {len(articles)} articles (status={status})")
    return articles


def text_similarity(a, b):
    a_c = re.sub(r'[^a-z0-9 ]', '', a.lower().strip())
    b_c = re.sub(r'[^a-z0-9 ]', '', b.lower().strip())
    return SequenceMatcher(None, a_c, b_c).ratio()


def extract_keywords(title):
    stopwords = {'a','an','the','is','in','on','at','to','for','of','and','or',
                 'but','with','how','what','when','where','why','your','our',
                 'best','top','guide','complete','ultimate','new','get'}
    return [w for w in re.findall(r'[a-z]+', title.lower())
            if w not in stopwords and len(w) > 2]


def keyword_overlap(kws_a, kws_b):
    if not kws_a or not kws_b:
        return 0.0
    sa, sb = set(kws_a), set(kws_b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


def primary_keyword(text, explicit=None):
    """Best-effort primary keyword: explicit value wins, else the longest
    significant token-pair from the title. Used for exact-duplication checks."""
    if explicit:
        return re.sub(r'[^a-z0-9 ]', '', explicit.lower()).strip()
    kws = extract_keywords(text)
    return " ".join(kws[:3])


def ai_semantic_analysis(new_topic, new_keywords, existing_articles):
    """ADVISORY ONLY. Output is recorded but never overrides a deterministic block."""
    if not ANTHROPIC_API_KEY or not existing_articles:
        return {"decision": DECISIONS["CREATE_NEW"], "reasoning": "Skipped", "advisory": True}
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    summaries = []
    for art in existing_articles[:50]:
        t = art.get("title", {})
        title = re.sub(r'<[^>]+>', '', t.get("rendered","") if isinstance(t,dict) else str(t))
        summaries.append(f"ID:{art.get('id','?')} | {title} | {art.get('status','?')}")
    prompt = f"""Content Cannibalization Analyst for MoneyAbroadGuide.com (financial education for immigrants/newcomers USA/Canada).
NEW TOPIC: {new_topic}
KEYWORDS: {', '.join(new_keywords)}
EXISTING ARTICLES:
{chr(10).join(summaries)}
Note: USA and Canada variants of the same topic are DISTINCT and allowed.
Return JSON only:
{{"decision":"CREATE_NEW_ARTICLE|UPDATE_EXISTING_ARTICLE|MERGE_WITH_EXISTING|REJECT_DUPLICATE","confidence":0-100,"conflicting_ids":[],"reasoning":"brief","recommended_action":"specific","content_gap":"unique angle if CREATE_NEW"}}"""
    try:
        msg = client.messages.create(model="claude-opus-4-5", max_tokens=512,
            messages=[{"role": "user", "content": prompt}])
        text = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        result = json.loads(m.group()) if m else {"decision": DECISIONS["CREATE_NEW"]}
        result["advisory"] = True
        return result
    except Exception as e:
        return {"decision": DECISIONS["CREATE_NEW"], "reasoning": f"Error: {e}", "advisory": True}


# ------------------------------------------------------------------
# Deterministic evaluation of a single existing article vs the new topic
# ------------------------------------------------------------------
def evaluate_conflict(new_topic, new_kws, new_country, new_slug, new_pkw, article):
    t = article.get("title", {})
    title = re.sub(r'<[^>]+>', '', t.get("rendered","") if isinstance(t,dict) else str(t))
    ex_slug = article.get("slug", "")
    ex_country = detect_country(title, ex_slug)

    tsim = text_similarity(new_topic, title)
    ksim = keyword_overlap(new_kws, extract_keywords(title))
    slug_dup = bool(new_slug) and normalize_slug(new_slug) == normalize_slug(ex_slug)
    pkw_dup = bool(new_pkw) and new_pkw == primary_keyword(title)

    # Country-aware: USA vs CANADA on the same core topic are allowed variants.
    different_country = (
        new_country in ("USA", "CANADA")
        and ex_country in ("USA", "CANADA")
        and new_country != ex_country
    )

    reasons = []
    blocking = False
    score = max(tsim, ksim)

    if different_country:
        # Allowed variant — record but never block on similarity alone.
        return {
            "article_id": article.get("id"), "title": title, "slug": ex_slug,
            "status": article.get("status", "?"), "url": article.get("link", ""),
            "country": ex_country, "title_similarity": round(tsim, 3),
            "keyword_overlap": round(ksim, 3), "slug_duplicate": False,
            "primary_keyword_duplicate": False, "combined_score": round(score, 3),
            "blocking": False, "allowed_variant": True,
            "reasons": [f"Allowed {new_country} vs {ex_country} country variant"],
        }

    # Same-country (or unknown) — apply hard-block rules.
    if slug_dup:
        blocking = True; reasons.append("Slug duplication (normalized match)")
    if pkw_dup:
        blocking = True; reasons.append("Primary keyword duplication (exact)")
    if ksim >= KEYWORD_OVERLAP_REJECT:
        blocking = True; reasons.append(f"Keyword overlap {ksim:.0%} >= {KEYWORD_OVERLAP_REJECT:.0%}")
    if tsim >= TITLE_NEAR_DUP_THRESHOLD:
        blocking = True; reasons.append(f"Near-duplicate title {tsim:.0%}")
    if score >= REJECT_THRESHOLD:
        blocking = True; reasons.append(f"Combined similarity {score:.0%} >= {REJECT_THRESHOLD:.0%}")

    return {
        "article_id": article.get("id"), "title": title, "slug": ex_slug,
        "status": article.get("status", "?"), "url": article.get("link", ""),
        "country": ex_country, "title_similarity": round(tsim, 3),
        "keyword_overlap": round(ksim, 3), "slug_duplicate": slug_dup,
        "primary_keyword_duplicate": pkw_dup, "combined_score": round(score, 3),
        "blocking": blocking, "allowed_variant": False, "reasons": reasons,
    }


def run_cannibalization_check(new_topic, new_keywords,
                              target_country=None, target_slug=None, primary_kw=None,
                              output_path="output/agent_17/cannibalization_report.json"):
    start = datetime.utcnow()
    logger.info(f"AGENT 17 - CANNIBALIZATION CHECK: {new_topic}")

    wp_pub = fetch_wordpress_articles(status="publish")
    wp_draft = fetch_wordpress_articles(status="draft")
    all_content = wp_pub + wp_draft
    new_kws = new_keywords or extract_keywords(new_topic)
    new_country = (target_country or detect_country(new_topic, target_slug or "", primary_kw or "")).upper()
    new_slug = target_slug or slugify_topic(new_topic)
    new_pkw = primary_keyword(new_topic, primary_kw)

    conflicts = []
    for article in all_content:
        ev = evaluate_conflict(new_topic, new_kws, new_country, new_slug, new_pkw, article)
        if ev["blocking"] or ev["combined_score"] >= SIMILARITY_THRESHOLD or ev["allowed_variant"] is False and (ev["slug_duplicate"] or ev["primary_keyword_duplicate"]):
            if ev["combined_score"] >= SIMILARITY_THRESHOLD or ev["blocking"]:
                conflicts.append(ev)

    conflicts.sort(key=lambda x: (x["blocking"], x["combined_score"]), reverse=True)

    # Deterministic verdict FIRST (authoritative)
    deterministic_block = any(c["blocking"] for c in conflicts)
    max_score = max((c["combined_score"] for c in conflicts), default=0.0)

    # Advisory AI pass
    ai = ai_semantic_analysis(new_topic, new_kws, all_content)
    ai_dec = ai.get("decision", DECISIONS["CREATE_NEW"])

    if deterministic_block:
        decision, blocking = DECISIONS["REJECT"], True
        block_reasons = sorted({r for c in conflicts if c["blocking"] for r in c["reasons"]})
        action = "BLOCKED (manual review required): " + "; ".join(block_reasons)
        confidence = max(int(max_score * 100), 90)
    elif new_country == "UNKNOWN":
        decision, blocking = DECISIONS["REJECT"], True
        action = "BLOCKED: country could not be determined from content signals — manual review required."
        confidence = 80
    elif ai_dec == DECISIONS["REJECT"]:
        # AI flags a possible duplicate the deterministic layer did not catch:
        # do NOT auto-block; route to manual review as a warning instead.
        decision, blocking = DECISIONS["REJECT"], True
        action = f"BLOCKED by advisory AI for manual review: {ai.get('reasoning','possible duplicate')}"
        confidence = ai.get("confidence", 70)
    elif ai_dec == DECISIONS["MERGE"]:
        decision, blocking = DECISIONS["MERGE"], False
        action = f"Merge into existing article (similarity: {max_score:.0%})."
        confidence = int(max_score * 100)
    elif ai_dec == DECISIONS["UPDATE"]:
        decision, blocking = DECISIONS["UPDATE"], False
        action = "Update existing article rather than creating new one."
        confidence = int(max_score * 100)
    else:
        decision, blocking = DECISIONS["CREATE_NEW"], False
        action = ai.get("content_gap") or "Proceed. Content gap confirmed."
        confidence = max(50, 100 - int(max_score * 100))

    result = {
        "agent": "Agent 17 - Content Cannibalization Agent (HARDENED)",
        "version": "V3.2",
        "timestamp": start.isoformat(),
        "new_topic": new_topic,
        "new_keywords": new_keywords,
        "detected_country": new_country,
        "normalized_slug": new_slug,
        "primary_keyword": new_pkw,
        "decision": decision,
        "confidence": confidence,
        "blocking": blocking,
        "deterministic_block": deterministic_block,
        "conflicts_found": conflicts,
        "wp_articles_scanned": len(wp_pub),
        "drafts_scanned": len(wp_draft),
        "similarity_scores": [{"article": c["title"][:80], "score": c["combined_score"], "blocking": c["blocking"]} for c in conflicts],
        "ai_analysis": ai,
        "ai_is_advisory": True,
        "recommended_action": action,
        "execution_duration_seconds": round((datetime.utcnow() - start).total_seconds(), 2),
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"DECISION: {decision} | Blocking: {blocking} | Deterministic block: {deterministic_block}")
    logger.info(f"Report saved: {output_path}")
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent 17 - Content Cannibalization Agent (HARDENED)")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--keywords", default="")
    parser.add_argument("--country", default="", help="USA|CANADA (optional; auto-detected if omitted)")
    parser.add_argument("--slug", default="", help="proposed slug (optional)")
    parser.add_argument("--primary-keyword", default="", help="explicit primary keyword (optional)")
    parser.add_argument("--output", default="output/agent_17/cannibalization_report.json")
    args = parser.parse_args()
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    result = run_cannibalization_check(
        args.topic, keywords,
        target_country=(args.country or None),
        target_slug=(args.slug or None),
        primary_kw=(args.primary_keyword or None),
        output_path=args.output,
    )
    sys.exit(1 if result["blocking"] else 0)


if __name__ == "__main__":
    main()
