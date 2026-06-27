#!/usr/bin/env python3
"""
NEXUS-14 V3 - Agent 18: Revenue Intelligence Agent
MoneyAbroadGuide.com | Evaluates revenue potential before production.

Scores topics 0-100 for revenue potential.
Rules: Score < 60 = REJECT | 60-70 = OPTIONAL | 70-85 = PRIORITIZE | 85+ = HIGH_PRIORITY
Output: revenue_score.json

V3.1 FIX: Partner name matching + search_volume/CPC boosting + broader keyword triggers
"""

import json, logging, os, re, sys
from datetime import datetime
from pathlib import Path

import anthropic

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-18] %(levelname)s %(message)s")
logger = logging.getLogger("agent_18_revenue_intelligence")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

REVENUE_THRESHOLDS = {
    "REJECT": 60,
    "OPTIONAL": 70,
    "PRIORITIZE": 85,
    "HIGH_PRIORITY": 86,
}

REVENUE_DECISIONS = {
    "HIGH_PRIORITY": "HIGH_PRIORITY_QUEUE",
    "PRIORITIZE": "PRIORITIZE",
    "OPTIONAL": "OPTIONAL",
    "REJECT": "REJECT_TOPIC",
}

# High-value affiliate categories for MoneyAbroadGuide
# V3.1: Added partner name matching + broader keyword triggers
AFFILIATE_CATEGORIES = {
    "banking": {
        "keywords": ["bank account", "checking", "savings", "open account", "direct deposit",
                     "routing number", "chime", "mercury", "wise bank", "revolut bank",
                     "bank for immigrants", "bank for newcomers", "bank for expats",
                     "bank for international students", "bank no ssn", "bank non-resident",
                     "banking for newcomers", "banking for immigrants", "banking for expats",
                     "newcomers banking", "immigrants banking", "guide for newcomers",
                     # V3.5: Added simpler single-word triggers
                     "banking", "banking guide", "banque", "online banking",
                     "expat banking", "student banking", "banking students",
                     "international students banking", "newcomers to canada", "newcomers to usa", "newcomers guide",
                     "immigrants guide", "expats guide", "financial guide",
                     "newcomers", "newcomer", "immigrants", "expats", "new to canada",
                     "new to usa", "new to america", "move to canada", "move to usa"],
        "partners": ["Wise", "Remitly", "Chime", "Mercury", "Chase", "Bank of America",
                     "TD Bank", "RBC", "Scotiabank", "HSBC", "Citibank",
                     "TD Canada Trust", "Charles Schwab", "Revolut"],
        "commission_tier": "HIGH",
        "score_boost": 20,
    },
    "money_transfer": {
        "keywords": ["send money", "wire transfer", "remittance", "international transfer",
                     "exchange rate", "money transfer", "transfer abroad", "transfer internationally",
                     "comparison", "vs", "cheapest", "best rates", "transfer apps",
                     "send abroad", "transfer fees", "remit", "worldremit", "xe.com",
                     "wise", "remitly", "western union", "moneygram", "ofx"],
        "partners": ["Wise", "Remitly", "Western Union", "MoneyGram", "XE", "OFX",
                     "WorldRemit", "Revolut", "Skrill", "PayPal", "Zelle", "TransferGo"],
        "commission_tier": "HIGH",
        "score_boost": 18,
    },
    "credit": {
        "keywords": ["credit card", "credit score", "credit history", "secured card",
                     "credit builder", "no foreign transaction", "cashback", "rewards card",
                     "credit for immigrants", "credit for newcomers", "build credit",
                     "first credit card", "credit without ssn"],
        "partners": ["Discover", "Capital One", "Chime", "Self", "Credit Karma", "Petal"],
        "commission_tier": "HIGH",
        "score_boost": 17,
    },
    "insurance": {
        "keywords": ["health insurance", "car insurance", "renters insurance", "life insurance",
                     "coverage", "insurance for immigrants", "insurance for expats",
                     "health plan", "medical insurance", "auto insurance"],
        "partners": ["Policygenius", "Health Sherpa", "Progressive", "State Farm", "Lemonade"],
        "commission_tier": "MEDIUM",
        "score_boost": 12,
    },
    "taxes": {
        "keywords": ["tax return", "ITIN", "tax filing", "SSN", "CRA", "IRS", "T4", "W-2",
                     "1040", "FATCA", "FBAR", "tax guide", "tax for expats", "tax for immigrants",
                     "non-resident tax", "expat tax", "CRA non-resident", "tax obligations"],
        "partners": ["TurboTax", "H&R Block", "TaxAct", "FreeTaxUSA", "Expatfile"],
        "commission_tier": "MEDIUM",
        "score_boost": 12,
    },
    "investment": {
        "keywords": ["invest", "brokerage", "TFSA", "RRSP", "401k", "IRA", "stocks", "ETF",
                     "investment account", "trading", "wealthsimple", "questrade",
                     "investment for non-residents", "investment for expats"],
        "partners": ["Wealthsimple", "Questrade", "Robinhood", "Fidelity", "Interactive Brokers",
                     "Charles Schwab", "TD Ameritrade"],
        "commission_tier": "MEDIUM",
        "score_boost": 14,
    },
    "housing": {
        "keywords": ["rent", "apartment", "mortgage", "first home", "credit check", "lease",
                     "rental", "renting", "housing", "real estate"],
        "partners": ["Zumper", "Apartments.com", "Realtor.ca", "Zillow"],
        "commission_tier": "LOW",
        "score_boost": 6,
    },
}

EBOOK_TOPICS = [
    "complete guide", "step by step", "for beginners", "newcomer guide",
    "immigrant guide", "how to", "everything you need", "checklist",
    "banking guide", "credit guide", "tax guide", "financial guide",
    "comparison guide", "explained", "tips", "mistakes to avoid",
    "newcomers guide", "immigrants guide", "expats guide", "newcomer's guide",
    "guide for newcomers", "guide for immigrants", "guide for expats",
    # V3.3: Added missing patterns for students, non-residents, tax topics
    "international students", "for international students", "students guide",
    "no ssn", "without ssn", "non-resident", "non resident",
    "fatca", "fbar", "tax treaty", "filing guide",
    "send money abroad", "best rates", "cheapest way",
    "credit card guide", "credit card comparison",
    "expat banking", "expat finance", "expat guide",
    "transfer money", "money transfer guide", "remittance guide",
    # V3.4: Additional patterns to cover tax, credit, filing topics
    "expat tax", "tax filing", "tax guide for", "living abroad",
    "foreign income", "non-resident tax", "filing abroad",
    "credit card", "credit guide", "credit score",
    "send money", "wire transfer guide", "international transfer",
    "bank account", "open account", "banking guide",
    "best rates", "compare rates", "comparison",
]

HIGH_INTENT_PHRASES = [
    "how to open", "best bank", "best credit card", "how to apply", "how to get",
    "step by step", "guide for", "for newcomers", "for immigrants", "for international students",
    "first time", "as an immigrant", "after arriving", "new to usa", "new to canada",
    "comparison", "vs", "best rates", "cheapest", "top", "review",
]

ADSENSE_HIGH_VALUE_KEYWORDS = [
    "bank account", "credit card", "insurance", "mortgage", "loan",
    "investment", "tax", "ITIN", "SSN", "RRSP", "TFSA", "send money",
    "wire transfer", "money transfer", "credit score",
    "wise", "remitly", "western union", "comparison", "transfer",
    "international", "expat", "immigrant", "newcomer",
]

# Known high-value partner brands for quick-match affiliate detection
PARTNER_BRANDS = {
    "wise": "money_transfer",
    "remitly": "money_transfer",
    "western union": "money_transfer",
    "moneygram": "money_transfer",
    "ofx": "money_transfer",
    "worldremit": "money_transfer",
    "xe": "money_transfer",
    "transfergo": "money_transfer",
    "chime": "banking",
    "revolut": "banking",
    "mercury": "banking",
    "n26": "banking",
    "monzo": "banking",
    "rbc": "banking",
    "scotiabank": "banking",
    "td bank": "banking",
    "td canada": "banking",
    "charles schwab": "banking",
    "wealthsimple": "investment",
    "questrade": "investment",
    "interactive brokers": "investment",
    "turbotax": "taxes",
    "policygenius": "insurance",
    "discover": "credit",
    "capital one": "credit",
}


def analyze_affiliate_opportunities(topic, keywords, search_volume=0, cpc=0.0):
    """Identify affiliate opportunities and calculate affiliate score.

    V3.1 FIX: Also matches partner brand names in topic/keywords.
    Uses search_volume and CPC as additional scoring signals when available.
    """
    topic_lower = topic.lower()
    all_text = topic_lower + " " + " ".join(k.lower() for k in keywords)

    opportunities = []
    affiliate_score = 0
    categories_matched = set()

    # Primary match: keyword phrases in AFFILIATE_CATEGORIES
    for category, data in AFFILIATE_CATEGORIES.items():
        matches = [kw for kw in data["keywords"] if kw in all_text]
        if matches:
            boost = data["score_boost"]
            opportunities.append({
                "category": category,
                "matched_keywords": matches,
                "potential_partners": data["partners"],
                "commission_tier": data["commission_tier"],
                "score_boost": boost,
                "match_type": "keyword",
            })
            categories_matched.add(category)

    # Secondary match: partner brand names (V3.1 addition)
    for brand, category in PARTNER_BRANDS.items():
        if brand in all_text and category not in categories_matched:
            data = AFFILIATE_CATEGORIES[category]
            opportunities.append({
                "category": category,
                "matched_keywords": [brand],
                "potential_partners": data["partners"],
                "commission_tier": data["commission_tier"],
                "score_boost": data["score_boost"],
                "match_type": "brand_name",
            })
            categories_matched.add(category)

    # Calculate score: sum of top 3 opportunities, capped at 40
    affiliate_score = min(40, sum(op["score_boost"] for op in opportunities[:3]))

    # CPC boost: high CPC indicates valuable keywords ($5+ = financial)
    if cpc >= 8.0:
        affiliate_score = min(40, affiliate_score + 8)
    elif cpc >= 5.0:
        affiliate_score = min(40, affiliate_score + 5)
    elif cpc >= 3.0:
        affiliate_score = min(40, affiliate_score + 2)

    return opportunities, affiliate_score


def analyze_ebook_opportunities(topic, keywords):
    """Identify ebook/lead magnet opportunities."""
    all_text = topic.lower() + " " + " ".join(k.lower() for k in keywords)
    matches = [phrase for phrase in EBOOK_TOPICS if phrase in all_text]

    score = 0
    if len(matches) >= 2:
        score = 15
    elif len(matches) == 1:
        score = 8
    elif any(k in all_text for k in ["guide", "checklist", "steps", "process", "how", "tips"]):
        score = 5

    opportunities = []
    if score > 0:
        topic_clean = topic.replace("-", " ").title()
        opportunities = [
            f"The Complete {topic_clean} Guide for Newcomers",
            f"{topic_clean} Checklist for Immigrants",
            f"Step-by-Step {topic_clean} Workbook",
        ]

    return opportunities[:2], score


def analyze_adsense_potential(topic, keywords, search_volume=0, cpc=0.0):
    """Estimate AdSense CPC potential based on topic.

    V3.1 FIX: Uses actual CPC and search_volume from topic database when available.
    """
    all_text = topic.lower() + " " + " ".join(k.lower() for k in keywords)
    high_cpc_matches = [kw for kw in ADSENSE_HIGH_VALUE_KEYWORDS if kw in all_text]

    # Use actual CPC from topic database if provided
    if cpc >= 5.0:
        score = 20
        potential = f"HIGH (actual CPC: ${cpc:.2f})"
    elif cpc >= 2.0:
        score = 12
        potential = f"MEDIUM (actual CPC: ${cpc:.2f})"
    elif cpc > 0:
        score = 7
        potential = f"STANDARD (actual CPC: ${cpc:.2f})"
    elif len(high_cpc_matches) >= 3:
        score = 20
        potential = "HIGH ($3-8 CPC estimated)"
    elif len(high_cpc_matches) >= 1:
        score = 12
        potential = "MEDIUM ($1.50-3 CPC estimated)"
    else:
        score = 5
        potential = "STANDARD ($0.50-1.50 CPC estimated)"

    # Search volume boost: high volume = more AdSense impressions
    if search_volume >= 3000:
        score = min(20, score + 3)
    elif search_volume >= 1500:
        score = min(20, score + 1)

    return potential, score, high_cpc_matches


def analyze_search_intent(topic, keywords):
    """Evaluate commercial/transactional search intent."""
    all_text = topic.lower() + " " + " ".join(k.lower() for k in keywords)

    transactional = ["best", "open", "apply", "get", "find", "compare", "top", "cheapest",
                     "free", "vs", "comparison", "review", "rates", "cost", "fee", "cheap",
                     # V3.3: Added banking/finance intent signals
                     "bank account", "open account", "send money", "transfer money",
                     "credit card", "wire transfer", "no ssn", "without ssn"]
    informational = ["what is", "how does", "why", "when", "where", "definition"]
    navigational = ["login", "contact", "sign in", "website", "official"]

    t_matches = sum(1 for w in transactional if w in all_text)
    i_matches = sum(1 for w in informational if w in all_text)

    if t_matches >= 2:
        intent = "COMMERCIAL_INVESTIGATIONAL"
        score = 18
    elif t_matches >= 1:
        intent = "TRANSACTIONAL"
        score = 15
    elif i_matches > 0:
        intent = "INFORMATIONAL_HIGH_VALUE"
        score = 10
    else:
        intent = "INFORMATIONAL"
        score = 7

    # Boost for newcomer/immigrant intent
    high_intent_count = sum(1 for phrase in HIGH_INTENT_PHRASES if phrase in all_text)
    if high_intent_count >= 2:
        score += 8
        intent += "_NEWCOMER_TARGETED"
    elif high_intent_count == 1:
        score += 4

    return intent, min(score, 25)


def analyze_internal_linking(topic, keywords):
    """Estimate internal linking opportunities."""
    link_categories = {
        "banking": ["bank account", "checking account", "savings account", "bank", "banking"],
        "credit": ["credit score", "credit card", "credit history", "credit"],
        "taxes": ["tax", "ITIN", "IRS", "CRA", "fatca", "fbar"],
        "money_transfer": ["send money", "wire transfer", "remittance", "transfer",
                           "wise", "remitly", "western union"],
        "insurance": ["insurance", "coverage", "health insurance"],
    }
    all_text = topic.lower() + " " + " ".join(k.lower() for k in keywords)
    link_opportunities = []
    for cat, terms in link_categories.items():
        if any(t in all_text for t in terms):
            link_opportunities.append(cat)

    count = len(link_opportunities)
    score = min(count * 3, 12)
    return link_opportunities, score


def ai_revenue_analysis(topic, keywords, preliminary_score):
    """Use Claude for deep revenue opportunity analysis."""
    if not ANTHROPIC_API_KEY:
        return {"ai_revenue_analysis": "Skipped - no API key", "ai_score_adjustment": 0}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You are the Revenue Intelligence Analyst for MoneyAbroadGuide.com.

TOPIC TO EVALUATE: {topic}
KEYWORDS: {", ".join(keywords)}
PRELIMINARY REVENUE SCORE: {preliminary_score}/100

Analyze this topic revenue potential for affiliate marketing, ebook sales, AdSense revenue.

Return JSON only:
{{"ai_score_adjustment": -10 to +10, "affiliate_rating": "HIGH|MEDIUM|LOW", "ebook_viability": "YES|MAYBE|NO", "adsense_cpc_estimate": "$X.XX-$X.XX", "commercial_intent": "HIGH|MEDIUM|LOW", "audience_fit": "PERFECT|GOOD|POOR", "reasoning": "brief analysis", "top_affiliate_recommendation": "partner name", "revenue_maximization_tip": "actionable advice"}}"""

    try:
        msg = client.messages.create(model="claude-3-5-haiku-20241022", max_tokens=512,
                                     messages=[{"role": "user", "content": prompt}])
        text = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()) if m else {"ai_score_adjustment": 0}
    except Exception as e:
        return {"ai_score_adjustment": 0, "error": str(e)}


def run_revenue_analysis(topic, keywords, output_path="output/agent_18/revenue_score.json",
                         search_volume=0, cpc=0.0):
    """Run full revenue intelligence analysis."""
    start = datetime.utcnow()
    logger.info(f"AGENT 18 - REVENUE INTELLIGENCE: {topic}")
    logger.info(f"Keywords: {keywords}")
    logger.info(f"Search Volume: {search_volume} | CPC: ${cpc:.2f}")

    affiliate_opps, affiliate_score = analyze_affiliate_opportunities(
        topic, keywords, search_volume=search_volume, cpc=cpc
    )
    ebook_opps, ebook_score = analyze_ebook_opportunities(topic, keywords)
    adsense_potential, adsense_score, adsense_kws = analyze_adsense_potential(
        topic, keywords, search_volume=search_volume, cpc=cpc
    )
    search_intent, intent_score = analyze_search_intent(topic, keywords)
    link_opps, link_score = analyze_internal_linking(topic, keywords)

    preliminary_score = affiliate_score + ebook_score + adsense_score + intent_score + link_score
    preliminary_score = min(100, preliminary_score)

    logger.info(f"Score breakdown: affiliate={affiliate_score} ebook={ebook_score} "
                f"adsense={adsense_score} intent={intent_score} links={link_score} "
                f"= {preliminary_score}/100 (before AI)")

    ai_analysis = ai_revenue_analysis(topic, keywords, preliminary_score)
    ai_adjustment = ai_analysis.get("ai_score_adjustment", 0)
    final_score = min(100, max(0, preliminary_score + ai_adjustment))

    if final_score >= REVENUE_THRESHOLDS["HIGH_PRIORITY"]:
        decision = REVENUE_DECISIONS["HIGH_PRIORITY"]
        priority = "HIGH_PRIORITY_QUEUE"
        blocking = False
    elif final_score >= REVENUE_THRESHOLDS["OPTIONAL"]:
        decision = REVENUE_DECISIONS["PRIORITIZE"]
        priority = "PRIORITIZE"
        blocking = False
    elif final_score >= REVENUE_THRESHOLDS["REJECT"]:
        decision = REVENUE_DECISIONS["OPTIONAL"]
        priority = "OPTIONAL"
        blocking = False
    else:
        decision = REVENUE_DECISIONS["REJECT"]
        priority = "REJECT"
        blocking = True

    result = {
        "agent": "Agent 18 - Revenue Intelligence Agent",
        "version": "V3.1",
        "timestamp": start.isoformat(),
        "topic": topic,
        "keywords": keywords,
        "input_search_volume": search_volume,
        "input_cpc": cpc,
        "revenue_score": final_score,
        "preliminary_score": preliminary_score,
        "ai_adjustment": ai_adjustment,
        "decision": decision,
        "priority": priority,
        "blocking": blocking,
        "score_breakdown": {
            "affiliate_score": affiliate_score,
            "ebook_score": ebook_score,
            "adsense_score": adsense_score,
            "intent_score": intent_score,
            "internal_linking_score": link_score,
        },
        "affiliate_opportunities": affiliate_opps,
        "ebook_opportunities": ebook_opps,
        "adsense_potential": adsense_potential,
        "adsense_keywords": adsense_kws,
        "search_intent": search_intent,
        "internal_linking_opportunities": link_opps,
        "ai_analysis": ai_analysis,
        "thresholds": {
            "reject_below": REVENUE_THRESHOLDS["REJECT"],
            "optional_60_70": f'{REVENUE_THRESHOLDS["REJECT"]}-{REVENUE_THRESHOLDS["OPTIONAL"]}',
            "prioritize_70_85": f'{REVENUE_THRESHOLDS["OPTIONAL"]}-{REVENUE_THRESHOLDS["PRIORITIZE"]}',
            "high_priority_above": REVENUE_THRESHOLDS["HIGH_PRIORITY"],
        },
        "execution_duration_seconds": round((datetime.utcnow() - start).total_seconds(), 2),
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"REVENUE SCORE: {final_score}/100 | Decision: {decision} | Blocking: {blocking}")
    logger.info(f"Affiliate opps: {len(affiliate_opps)} | Ebook opps: {len(ebook_opps)}")
    logger.info(f"Report saved: {output_path}")
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent 18 - Revenue Intelligence Agent")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--keywords", default="")
    parser.add_argument("--output", default="output/agent_18/revenue_score.json")
    parser.add_argument("--search-volume", type=int, default=0,
                        help="Monthly search volume from topic database (optional)")
    parser.add_argument("--cpc", type=float, default=0.0,
                        help="Cost-per-click in USD from topic database (optional)")
    args = parser.parse_args()
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    result = run_revenue_analysis(
        args.topic, keywords, args.output,
        search_volume=args.search_volume,
        cpc=args.cpc,
    )

    print(f"Revenue Score: {result['revenue_score']}/100")
    print(f"Decision: {result['decision']}")
    sys.exit(1 if result["blocking"] else 0)



# ============================================================
# NEXUS-14 V3 — RevenueIntelligenceAgent BaseAgent Wrapper
# Added to support orchestrator class-based dispatch.
# Delegates to run_revenue_analysis() function above.
# ============================================================
try:
    from agents.base_agent import BaseAgent as _BaseAgent
except ImportError:
    try:
        from base_agent import BaseAgent as _BaseAgent
    except ImportError:
        class _BaseAgent:
            def __init__(self, config=None, **kwargs):
                self.config = config or {}

class RevenueIntelligenceAgent(_BaseAgent):
    """Orchestrator-compatible wrapper for Agent 18 revenue intelligence scoring."""
    AGENT_ID = "agent_18"
    AGENT_NAME = "Revenue Intelligence Agent"

    def __init__(self, config=None, **kwargs):
        try:
            super().__init__(config or {}, **kwargs)
        except Exception:
            self.config = config or {}

    async def run(self, context=None):
        ctx = context or {}
        topic = (ctx.get("current_topic") or {}).get("title", "") or ctx.get("topic", "")
        kws_raw = (ctx.get("current_topic") or {}).get("keyword", "")
        keywords = [k.strip() for k in str(kws_raw).split(",") if k.strip()] if kws_raw else []
        sv = int((ctx.get("current_topic") or {}).get("search_volume", 2000))
        cpc = float((ctx.get("current_topic") or {}).get("cpc", 3.50))
        out_path = "output/agent_18/revenue_score.json"
        result = run_revenue_analysis(topic, keywords, out_path, sv, cpc)
        return result


if __name__ == "__main__":
    main()
