#!/usr/bin/env python3
"""
NEXUS-14 V3 - Agent 17: Content Cannibalization Agent
MoneyAbroadGuide.com | Prevents duplicate content before production.

Decisions: CREATE_NEW_ARTICLE | UPDATE_EXISTING_ARTICLE | MERGE_WITH_EXISTING | REJECT_DUPLICATE
Runs BEFORE Agent 04. Output: cannibalization_report.json
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
SIMILARITY_THRESHOLD = 0.72
REJECT_THRESHOLD = 0.85

DECISIONS = {
    "CREATE_NEW": "CREATE_NEW_ARTICLE",
    "UPDATE": "UPDATE_EXISTING_ARTICLE",
    "MERGE": "MERGE_WITH_EXISTING",
    "REJECT": "REJECT_DUPLICATE",
}


def fetch_wordpress_articles(status="any", per_page=100):
    if not WP_URL:
        logger.warning("WORDPRESS_URL not set - skipping WP scan")
        return []
    articles, page, auth = [], 1, HTTPBasicAuth(WP_USER, WP_PASS)
    while True:
        try:
            resp = requests.get(f"{WP_URL}/wp-json/wp/v2/posts", auth=auth,
                params={"status": status, "per_page": per_page, "page": page,
                        "fields": "id,slug,title,date,modified,status,link"}, timeout=30)
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


def ai_semantic_analysis(new_topic, new_keywords, existing_articles):
    if not ANTHROPIC_API_KEY or not existing_articles:
        return {"decision": DECISIONS["CREATE_NEW"], "reasoning": "Skipped"}
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

Return JSON only:
{{"decision":"CREATE_NEW_ARTICLE|UPDATE_EXISTING_ARTICLE|MERGE_WITH_EXISTING|REJECT_DUPLICATE","confidence":0-100,"conflicting_ids":[],"reasoning":"brief","recommended_action":"specific","content_gap":"unique angle if CREATE_NEW"}}"""
    try:
        msg = client.messages.create(model="claude-opus-4-5", max_tokens=512,
            messages=[{"role": "user", "content": prompt}])
        text = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()) if m else {"decision": DECISIONS["CREATE_NEW"]}
    except Exception as e:
        return {"decision": DECISIONS["CREATE_NEW"], "reasoning": f"Error: {e}"}


def run_cannibalization_check(new_topic, new_keywords, output_path="output/agent_17/cannibalization_report.json"):
    start = datetime.utcnow()
    logger.info(f"AGENT 17 - CANNIBALIZATION CHECK: {new_topic}")

    wp_pub = fetch_wordpress_articles(status="publish")
    wp_draft = fetch_wordpress_articles(status="draft")
    all_content = wp_pub + wp_draft
    new_kws = new_keywords or extract_keywords(new_topic)
    conflicts = []

    for article in all_content:
        t = article.get("title", {})
        title = re.sub(r'<[^>]+>', '', t.get("rendered","") if isinstance(t,dict) else str(t))
        tsim = text_similarity(new_topic, title)
        ksim = keyword_overlap(new_kws, extract_keywords(title))
        score = max(tsim, ksim)
        if score >= SIMILARITY_THRESHOLD:
            conflicts.append({
                "article_id": article.get("id"),
                "title": title,
                "status": article.get("status", "?"),
                "url": article.get("link", ""),
                "title_similarity": round(tsim, 3),
                "keyword_overlap": round(ksim, 3),
                "combined_score": round(score, 3),
            })

    conflicts.sort(key=lambda x: x["combined_score"], reverse=True)
    ai = ai_semantic_analysis(new_topic, new_kws, all_content)
    ai_dec = ai.get("decision", DECISIONS["CREATE_NEW"])
    max_score = max((c["combined_score"] for c in conflicts), default=0.0)

    if max_score >= REJECT_THRESHOLD or ai_dec == DECISIONS["REJECT"]:
        decision, blocking = DECISIONS["REJECT"], True
        action = "BLOCKED: Duplicate detected. Update or merge existing article."
        confidence = max(int(max_score * 100), ai.get("confidence", 85))
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
        "agent": "Agent 17 - Content Cannibalization Agent",
        "version": "V3",
        "timestamp": start.isoformat(),
        "new_topic": new_topic,
        "new_keywords": new_keywords,
        "decision": decision,
        "confidence": confidence,
        "blocking": blocking,
        "conflicts_found": conflicts,
        "wp_articles_scanned": len(wp_pub),
        "drafts_scanned": len(wp_draft),
        "similarity_scores": [{"article": c["title"][:80], "score": c["combined_score"]} for c in conflicts],
        "ai_analysis": ai,
        "recommended_action": action,
        "execution_duration_seconds": round((datetime.utcnow() - start).total_seconds(), 2),
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"DECISION: {decision} | Blocking: {blocking}")
    logger.info(f"Report saved: {output_path}")
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent 17 - Content Cannibalization Agent")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--keywords", default="")
    parser.add_argument("--output", default="output/agent_17/cannibalization_report.json")
    args = parser.parse_args()
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    result = run_cannibalization_check(args.topic, keywords, args.output)
    sys.exit(1 if result["blocking"] else 0)


if __name__ == "__main__":
    main()
