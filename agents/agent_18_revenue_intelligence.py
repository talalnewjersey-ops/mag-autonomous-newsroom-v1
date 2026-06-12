#!/usr/bin/env python3
"""
NEXUS-14 V3 - Agent 18: Revenue Intelligence Agent
MoneyAbroadGuide.com | Evaluates revenue potential before production.

Scores topics 0-100 for revenue potential.
Rules: Score < 60 = REJECT | 60-70 = OPTIONAL | 70-85 = PRIORITIZE | 85+ = HIGH_PRIORITY
Output: revenue_score.json
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
AFFILIATE_CATEGORIES = {
    "banking": {
        "keywords": ["bank account","checking","savings","open account","direct deposit","routing number"],
        "partners": ["Wise","Remitly","Chime","Mercury","Chase","Bank of America","TD Bank","RBC","Scotiabank"],
        "commission_tier": "HIGH",
        "score_boost": 20,
    },
    "money_transfer": {
        "keywords": ["send money","wire transfer","remittance","international transfer","exchange rate"],
        "partners": ["Wise","Remitly","Western Union","MoneyGram","XE","OFX"],
        "commission_tier": "HIGH",
        "score_boost": 18,
    },
    "credit": {
        "keywords": ["credit card","credit score","credit history","secured card","credit builder"],
        "partners": ["Discover","Capital One","Chime","Self","Credit Karma"],
        "commission_tier": "HIGH",
        "score_boost": 17,
    },
    "insurance": {
        "keywords": ["health insurance","car insurance","renters insurance","life insurance","coverage"],
        "partners": ["Policygenius","Health Sherpa","Progressive","State Farm"],
        "commission_tier": "MEDIUM",
        "score_boost": 12,
    },
    "taxes": {
        "keywords": ["tax return","ITIN","tax filing","SSN","CRA","IRS","T4","W-2","1040"],
        "partners": ["TurboTax","H&R Block","TaxAct","FreeTaxUSA"],
        "commission_tier": "MEDIUM",
        "score_boost": 12,
    },
    "investment": {
        "keywords": ["invest","brokerage","TFSA","RRSP","401k","IRA","stocks","ETF"],
        "partners": ["Wealthsimple","Questrade","Robinhood","Fidelity"],
        "commission_tier": "MEDIUM",
        "score_boost": 14,
    },
    "housing": {
        "keywords": ["rent","apartment","mortgage","first home","credit check","lease"],
        "partners": ["Zumper","Apartments.com","Realtor.ca"],
        "commission_tier": "LOW",
        "score_boost": 6,
    },
}

EBOOK_TOPICS = [
    "complete guide","step by step","for beginners","newcomer guide",
    "immigrant guide","how to","everything you need","checklist",
    "banking guide","credit guide","tax guide","financial guide",
]

HIGH_INTENT_PHRASES = [
    "how to open","best bank","best credit card","how to apply","how to get",
    "step by step","guide for","for newcomers","for immigrants","for international students",
    "first time","as an immigrant","after arriving","new to usa","new to canada",
]

ADSENSE_HIGH_VALUE_KEYWORDS = [
    "bank account", "credit card", "insurance", "mortgage", "loan",
    "investment", "tax", "ITIN", "SSN", "RRSP", "TFSA", "send money",
    "wire transfer", "money transfer", "credit score",
]


def analyze_affiliate_opportunities(topic, keywords):
    """Identify affiliate opportunities and calculate affiliate score."""
    topic_lower = topic.lower()
    all_text = topic_lower + " " + " ".join(k.lower() for k in keywords)

    opportunities = []
    affiliate_score = 0
    max_boost = 0

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
            })
            max_boost = max(max_boost, boost)

    affiliate_score = min(40, sum(op["score_boost"] for op in opportunities[:3]))
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
    elif any(k in all_text for k in ["guide","checklist","steps","process","how"]):
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


def analyze_adsense_potential(topic, keywords):
    """Estimate AdSense CPC potential based on topic."""
    all_text = topic.lower() + " " + " ".join(k.lower() for k in keywords)
    high_cpc_matches = [kw for kw in ADSENSE_HIGH_VALUE_KEYWORDS if kw in all_text]

    if len(high_cpc_matches) >= 3:
        score = 20
        potential = "HIGH ($3-8 CPC)"
    elif len(high_cpc_matches) >= 1:
        score = 12
        potential = "MEDIUM ($1.50-3 CPC)"
    else:
        score = 5
        potential = "STANDARD ($0.50-1.50 CPC)"

    return potential, score, high_cpc_matches


def analyze_search_intent(topic, keywords):
    """Evaluate commercial/transactional search intent."""
    all_text = topic.lower() + " " + " ".join(k.lower() for k in keywords)

    transactional = ["best","open","apply","get","find","compare","top","cheapest","free","vs"]
    informational = ["what is","how does","why","when","where","definition"]
    navigational = ["login","contact","sign in","website","official"]

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
        "banking": ["bank account", "checking account", "savings account"],
        "credit": ["credit score", "credit card", "credit history"],
        "taxes": ["tax", "ITIN", "IRS", "CRA"],
        "money_transfer": ["send money", "wire transfer", "remittance"],
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
    prompt = f"""You are the Revenue Intelligence Analyst for MoneyAbroadGuide.com — a financial education platform for immigrants, newcomers, and international students in the USA and Canada.

TOPIC TO EVALUATE: {topic}
KEYWORDS: {', '.join(keywords)}
PRELIMINARY REVENUE SCORE: {preliminary_score}/100

Analyze this topic's revenue potential for:
1. Affiliate marketing (financial products, banking, credit cards, money transfer)
2. Ebook/digital product sales
3. AdSense revenue (CPC rates for financial keywords)
4. Long-term topical authority value

Return JSON:
{{"ai_score_adjustment": -10 to +10, "affiliate_rating": "HIGH|MEDIUM|LOW", "ebook_viability": "YES|MAYBE|NO", "adsense_cpc_estimate": "$X.XX-$X.XX", "commercial_intent": "HIGH|MEDIUM|LOW", "audience_fit": "PERFECT|GOOD|POOR", "reasoning": "2-3 sentence analysis", "top_affiliate_recommendation": "specific partner name", "revenue_maximization_tip": "actionable advice"}}"""

    try:
        msg = client.messages.create(model="claude-opus-4-5", max_tokens=512,
            messages=[{"role": "user", "content": prompt}])
        text = msg.content[0].text.strip()
        m = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(m.group()) if m else {"ai_score_adjustment": 0}
    except Exception as e:
        return {"ai_score_adjustment": 0, "error": str(e)}


def run_revenue_analysis(topic, keywords, output_path="output/agent_18/revenue_score.json"):
    """Run full revenue intelligence analysis."""
    start = datetime.utcnow()
    logger.info(f"AGENT 18 - REVENUE INTELLIGENCE: {topic}")

    affiliate_opps, affiliate_score = analyze_affiliate_opportunities(topic, keywords)
    ebook_opps, ebook_score = analyze_ebook_opportunities(topic, keywords)
    adsense_potential, adsense_score, adsense_kws = analyze_adsense_potential(topic, keywords)
    search_intent, intent_score = analyze_search_intent(topic, keywords)
    link_opps, link_score = analyze_internal_linking(topic, keywords)

    preliminary_score = affiliate_score + ebook_score + adsense_score + intent_score + link_score
    preliminary_score = min(100, preliminary_score)

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
        "version": "V3",
        "timestamp": start.isoformat(),
        "topic": topic,
        "keywords": keywords,
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
            "optional_60_70": f"{REVENUE_THRESHOLDS['REJECT']}-{REVENUE_THRESHOLDS['OPTIONAL']}",
            "prioritize_70_85": f"{REVENUE_THRESHOLDS['OPTIONAL']}-{REVENUE_THRESHOLDS['PRIORITIZE']}",
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
    args = parser.parse_args()
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    result = run_revenue_analysis(args.topic, keywords, args.output)

    print(f"Revenue Score: {result['revenue_score']}/100")
    print(f"Decision: {result['decision']}")
    sys.exit(1 if result["blocking"] else 0)


if __name__ == "__main__":
    main()
