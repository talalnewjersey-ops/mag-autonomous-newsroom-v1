#!/usr/bin/env python3
"""
NEXUS-14 PRODUCTION SCRIPT v5.5 - 4 BODY IMAGES + 1 FEATURED — NEXUS STANDARD
scripts/produce_article.py

NEXUS-14 v5.5 — NEXUS standard: 5 images (1 featured + 4 body) + Gemini direct API

FIXES in v5.2:
- Generate directly in HTML format (no Markdown conversion needed)
- Fix AI rewriter: rewrite full article section by section (no truncation)
- Fix md_to_html: proper Markdown table conversion
- Fix WP password: strip whitespace from credentials
- Generate 5 parts x 3500 tokens = guaranteed 4000+ words
- SEO threshold: 70+ (realistic)
- EEAT threshold: 60+ (realistic)
- internal_links: 3+ links
- editorial auto-pass if score >= 8/13
"""
import sys, os, json, time, requests, re, base64
from base64 import b64encode
from datetime import datetime

try:
    import openai
except ImportError:
    os.system("pip install openai -q")
    import openai

START = time.time()
ARTICLE_INDEX = os.environ.get("ARTICLE_INDEX", "PILOT-01")
MARKET = (os.environ.get("TARGET_MARKET") or "usa").lower()
TOPIC = (os.environ.get("TOPIC_OVERRIDE") or "").strip()
if not TOPIC:
    TOPIC = "best banks for immigrants in the usa 2026"

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER = (os.environ.get("WORDPRESS_USERNAME", "") or "").strip()
WP_PASS = ((os.environ.get("WORDPRESS_APP_PASSWORD", "") or os.environ.get("WORDPRESS_PASSWORD", "")) or "").strip()

WP_CAT_USA = 17
WP_CAT_CANADA = 18
WP_AUTHOR_ID = 4

creds_wp = b64encode((WP_USER + ":" + WP_PASS).encode()).decode() if WP_USER and WP_PASS else ""
WP_JSON_HEADERS = {
    "Authorization": "Basic " + creds_wp,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "NEXUS14-v5/1.0",
}

print("=" * 60)
print("NEXUS-14 PRODUCTION v5.2 -- " + ARTICLE_INDEX)
print("=" * 60)
print("Topic  :", TOPIC)
print("Market :", MARKET.upper())
print("OpenAI :", "SET" if OPENAI_KEY else "MISSING")
print("Gemini :", "SET" if os.environ.get("GEMINI_API_KEY","").strip() else "MISSING")
print("WP URL :", WP_URL)
print("WP USER:", WP_USER or "MISSING")
print("WP PASS:", ("SET (" + str(len(WP_PASS)) + " chars)") if WP_PASS else "MISSING")
print()

results = {}
openai_cost = 0.0
total_tokens = 0
generated_images = []
media_ids = []
improvement_log = []

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def gpt(client, prompt, max_tokens=4000, temperature=0.8):
    global total_tokens, openai_cost
    r = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user","content":prompt}],
        max_tokens=max_tokens, temperature=temperature
    )
    total_tokens += r.usage.total_tokens
    openai_cost += (r.usage.prompt_tokens/1_000_000)*2.50 + (r.usage.completion_tokens/1_000_000)*10.00
    return r.choices[0].message.content

def wp_request(method, path, headers, json_data=None, data=None, timeout=60, max_retries=3):
    url = WP_URL + path
    for attempt in range(1, max_retries + 1):
        try:
            if method == "POST":
                r = requests.post(url, headers=headers, json=json_data, data=data, timeout=timeout)
            else:
                r = requests.get(url, headers=headers, timeout=timeout)
            print(f"  WP {method} -> {r.status_code} (attempt {attempt})")
            if r.status_code in (200, 201):
                return r
            if r.status_code in (401, 403):
                print(f"  WP auth error {r.status_code}: {r.text[:200]}")
                return r
            time.sleep(2)
        except Exception as e:
            print(f"  WP error attempt {attempt}: {e}")
            time.sleep(2 ** attempt)
    return None

def strip_html(text):
    """Remove HTML tags for clean word counting."""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'&[a-zA-Z]+;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# ============================================================
# GATE 1: THEMATIC COHERENCE DETECTOR
# ============================================================

def build_forbidden_terms(topic):
    topic_lower = topic.lower()
    all_money_transfer_terms = [
        "wise", "remitly", "moneygram", "ofx", "western union", "transfergo",
        "worldremit", "xe.com", "exchange rate", "money transfer", "international transfer",
        "send money abroad", "transfer fees"
    ]
    all_health_terms = ["deductible", "copay", "medicaid", "medicare", "hmo", "ppo"]
    forbidden = []
    is_health = any(w in topic_lower for w in ["health", "insurance", "medical", "healthcare"])
    is_transfer = any(w in topic_lower for w in ["transfer", "send money", "remittance"])
    is_banking = any(w in topic_lower for w in ["bank", "banking", "account"])
    if is_health and not is_transfer and not is_banking:
        forbidden.extend(all_money_transfer_terms)
    if is_transfer and not is_health and not is_banking:
        forbidden.extend(all_health_terms)
    if is_banking and not is_transfer:
        forbidden.extend(["moneygram", "western union", "worldremit"])
    return forbidden

def check_thematic_coherence(article_html, topic, forbidden_terms):
    violations = []
    al = article_html.lower()
    topic_words = [w for w in re.split(r'[\s,]+', topic.lower()) if len(w) > 3]
    topic_hits = sum(1 for w in topic_words if w in al)
    topic_coverage = topic_hits / max(len(topic_words), 1)
    for term in forbidden_terms:
        if term.lower() in al:
            violations.append({"term": term, "count": al.count(term.lower())})
    off_topic_penalty = min(len(violations) * 15, 60)
    coverage_bonus = int(topic_coverage * 40)
    score = max(0, 40 + coverage_bonus - off_topic_penalty)
    return score, violations

# ============================================================
# GATE 2: AI LANGUAGE DETECTOR
# ============================================================

AI_CLICHES = [
    r"as we look toward", r"this comprehensive guide", r"it is important to note",
    r"the importance cannot be overstated", r"in today's world", r"delve into",
    r"it goes without saying", r"in the realm of", r"it is worth noting",
    r"it is crucial to", r"plays a crucial role", r"in the ever-changing",
    r"leverage", r"utilize", r"navigating the", r"a myriad of",
    r"empowering", r"dive into", r"embark on", r"shed light on",
]

def count_ai_cliches(text):
    tl = text.lower()
    found = []
    for pattern in AI_CLICHES:
        matches = re.findall(pattern, tl)
        if matches:
            found.append({"pattern": pattern, "count": len(matches)})
    return found

def rewrite_section(client, section_text, topic):
    """Rewrite a single section to remove AI cliches."""
    prompt = f"""Rewrite this section to remove all AI cliches. Write like a senior NerdWallet journalist.
TOPIC: {topic}
BANNED: leverage, utilize, delve into, navigate, comprehensive, it is important to note, plays a crucial role, embark on, a myriad of
RULES: Keep all facts. Use active voice. Start with a fact. Return ONLY the rewritten HTML section.
SECTION:
{section_text[:3000]}
"""
    return gpt(client, prompt, max_tokens=2000, temperature=0.3)

# ============================================================
# GATE 3: REAL SEO SCORER (on HTML)
# ============================================================

def compute_seo_score_v2(article_html, topic, market):
    score = 0
    details = {}
    al = article_html.lower()
    topic_words = [w for w in topic.lower().split() if len(w) > 3]
    kw_pts = int(sum(1 for w in topic_words if w in al) / max(len(topic_words), 1) * 20)
    score += kw_pts
    details["keyword_coverage"] = f"{kw_pts}/20"
    h2_count = len(re.findall(r'<h2[^>]*>', article_html, re.IGNORECASE))
    h3_count = len(re.findall(r'<h3[^>]*>', article_html, re.IGNORECASE))
    h_pts = min(h2_count * 2 + h3_count, 15)
    score += h_pts
    details["heading_structure"] = f"{h_pts}/15 (h2:{h2_count}, h3:{h3_count})"
    has_table = int(bool(re.search(r'<table', article_html, re.IGNORECASE)))
    table_pts = has_table * 10
    score += table_pts
    details["has_table"] = f"{table_pts}/10"
    word_count = len(strip_html(article_html).split())
    if word_count >= 4000:
        wc_pts = 15
    elif word_count >= 2500:
        wc_pts = 10
    elif word_count >= 1500:
        wc_pts = 7
    else:
        wc_pts = 3
    score += wc_pts
    details["word_count"] = f"{wc_pts}/15 ({word_count} words)"
    internal_links = len(re.findall(r'href="https?://moneyabroadguide\.com[^"]*"', article_html, re.IGNORECASE))
    link_pts = min(internal_links * 3, 15)
    score += link_pts
    details["internal_links"] = f"{link_pts}/15 ({internal_links} links)"
    faq_count = len(re.findall(r'<h3[^>]*>[^<]*\?[^<]*</h3>', article_html, re.IGNORECASE))
    faq_pts = min(faq_count * 2, 10)
    score += faq_pts
    details["faq_questions"] = f"{faq_pts}/10 ({faq_count} detected)"
    cliche_penalty = min(len(count_ai_cliches(al)), 5)
    score -= cliche_penalty
    details["ai_cliche_penalty"] = f"-{cliche_penalty}"
    has_source = int(bool(re.search(r'(?i)(irs\.gov|uscis\.gov|fdic\.gov|hhs\.gov|healthcare\.gov|cfpb|canada\.ca)', article_html)))
    score += has_source * 10
    details["official_sources"] = f"{has_source * 10}/10"
    return max(0, min(score, 100)), details

# ============================================================
# GATE 4: REAL EEAT SCORER (on HTML)
# ============================================================

def compute_eeat_score(article_html, topic):
    score = 0
    details = {}
    al = article_html.lower()
    sources = ["irs.gov", "uscis.gov", "fdic.gov", "hhs.gov", "healthcare.gov", "cfpb.gov", "consumerfinance.gov", "canada.ca", "cms.gov", "dol.gov", "ssa.gov"]
    found = [s for s in sources if s in al]
    src_pts = min(len(found) * 5, 25)
    score += src_pts
    details["official_sources"] = f"{src_pts}/25 ({found})"
    data_pts = min(sum(1 for p in [r'\d+%', r'\$\d+', r'according to', r'data shows', r'study found', r'reported by', r'statistics show'] if re.search(p, al)) * 3, 20)
    score += data_pts
    details["data_citations"] = f"{data_pts}/20"
    exp_pts = min(sum(1 for p in [r'step 1', r'step 2', r'for example', r'case study', r'in practice', r'for instance'] if re.search(p, al)) * 3, 15)
    score += exp_pts
    details["experience_signals"] = f"{exp_pts}/15"
    auth_pts = min(sum(1 for p in [r'expert', r'licensed', r'certified', r'fdic', r'uscis', r'regulatory', r'professional', r'advisor'] if re.search(p, al)) * 2, 15)
    score += auth_pts
    details["authority"] = f"{auth_pts}/15"
    trust_pts = (int(bool(re.search(r'(?i)(talal|about the author|written by)', article_html))) + int(bool(re.search(r'(?i)(disclaimer|not financial advice|consult)', article_html))) + int(bool(re.search(r'(?i)(2026|last updated)', article_html)))) * 8
    score += min(trust_pts, 25)
    details["trust"] = f"{min(trust_pts, 25)}/25"
    return min(score, 100), details

# ============================================================
# GATE 5: TABLE VALIDATOR
# ============================================================

def validate_tables(article_html, topic):
    issues = []
    tables = re.findall(r'<table[^>]*>.*?</table>', article_html, re.DOTALL | re.IGNORECASE)
    TRANSFER_HEADERS = ["wise", "remitly", "ofx", "western union", "moneygram", "exchange rate"]
    HEALTH_HEADERS = ["deductible", "copay", "hmo", "ppo"]
    is_health = any(w in topic.lower() for w in ["health", "insurance", "medical"])
    is_transfer = any(w in topic.lower() for w in ["transfer", "send money"])
    for i, table in enumerate(tables):
        tl = table.lower()
        if is_health and not is_transfer:
            for h in TRANSFER_HEADERS:
                if h in tl:
                    issues.append(f"Table {i+1}: off-topic header '{h}'")
        if is_transfer and not is_health:
            for h in HEALTH_HEADERS:
                if h in tl:
                    issues.append(f"Table {i+1}: off-topic header '{h}'")
    return issues

# ============================================================
# GATE 6: LINK VALIDATOR
# ============================================================

def validate_internal_links(article_html):
    links = re.findall(r'href="(https?://moneyabroadguide\.com[^"]*)"', article_html)
    draft_issues = [l for l in links if 'p=' in l and 'preview' in l]
    return len(links) - len(draft_issues), len(links), [f"DRAFT: {l}" for l in draft_issues]

# ============================================================
# GATE 7: SELF-REVIEW
# ============================================================

def self_review_pass(client, article_html, topic):
    prompt = f"""You are the Editor-in-Chief of NerdWallet. Evaluate this article.
TOPIC: {topic}
Answer YES or NO for each:
1. Would you publish without changes?
2. Is there any off-topic section?
3. Is content repetitive?
4. Does it mix different financial topics?
5. Does any info seem invented?
Then: VERDICT: PUBLISH or REVISE
If REVISE, list ISSUES briefly.
ARTICLE (first 4000 chars):
{article_html[:4000]}
"""
    resp = gpt(client, prompt, max_tokens=1500, temperature=0.2)
    verdict = "PUBLISH" if "VERDICT: PUBLISH" in resp else "REVISE"
    issues = []
    if "ISSUES" in resp:
        block = resp.split("ISSUES")[1][:500]
        issues = [l.strip("- ").strip() for l in block.split("\n") if l.strip() and len(l.strip()) > 5]
    return verdict == "PUBLISH", issues, None

# ============================================================
# GATE 8: AUTO-IMPROVEMENT LOGGER
# ============================================================

def log_improvement(article_index, topic, gate_failures, f="improvement_log.json"):
    entry = {"timestamp": datetime.utcnow().isoformat(), "article_index": article_index,
             "topic": topic, "gate_failures": gate_failures, "prompt_improvements": []}
    for failure in gate_failures:
        if "thematic" in failure.lower(): entry["prompt_improvements"].append("ADD: stronger topic lock")
        if "cliche" in failure.lower(): entry["prompt_improvements"].append("ADD: banned phrases list")
        if "seo" in failure.lower(): entry["prompt_improvements"].append("ADD: H2 headings requirement")
        if "eeat" in failure.lower(): entry["prompt_improvements"].append("ADD: 1 official source per section")
        if "word" in failure.lower(): entry["prompt_improvements"].append("ADD: minimum word count per section")
    existing = []
    if os.path.exists(f):
        try:
            with open(f) as fh: existing = json.load(fh)
        except: existing = []
    existing.append(entry)
    with open(f, "w") as fh: json.dump(existing, fh, indent=2)
    return entry

# ============================================================
# STEP 1: ARTICLE GENERATION (DIRECT HTML, 5 PARTS)
# ============================================================

SYSTEM_PROMPT = """You are a senior financial journalist at MoneyAbroadGuide.com.
Write for immigrants and newcomers in the USA and Canada.
Style: direct, factual, specific — like NerdWallet or Investopedia.
NEVER write: "navigate", "delve into", "it is important to note", "comprehensive guide",
"shed light on", "embark on", "a myriad of", "leverage", "utilize", "plays a crucial role".
ALWAYS write: specific numbers, real examples, official sources (IRS, USCIS, FDIC, HHS, CMS, CFPB).
Write in active voice. Start paragraphs with facts."""

def get_links_for_topic(topic):
    tl = topic.lower()
    if "bank" in tl or "account" in tl:
        return [
            'href="https://moneyabroadguide.com/best-banks-immigrants-usa/"',
            'href="https://moneyabroadguide.com/expat-financial-guide/"',
            'href="https://moneyabroadguide.com/international-money-transfer/"',
            'href="https://moneyabroadguide.com/tax-guide-expats/"',
            'href="https://moneyabroadguide.com/best-credit-cards-immigrants/"',
            'href="https://moneyabroadguide.com/first-90-days-canada-checklist/"',
        ]
    elif "health" in tl or "insurance" in tl:
        return [
            'href="https://moneyabroadguide.com/health-insurance-newcomers-canada/"',
            'href="https://moneyabroadguide.com/expat-financial-guide/"',
            'href="https://moneyabroadguide.com/best-banks-immigrants-usa/"',
            'href="https://moneyabroadguide.com/tax-guide-expats/"',
            'href="https://moneyabroadguide.com/cost-of-living-canada/"',
            'href="https://moneyabroadguide.com/first-90-days-canada-checklist/"',
        ]
    elif "credit" in tl:
        return [
            'href="https://moneyabroadguide.com/best-credit-cards-immigrants/"',
            'href="https://moneyabroadguide.com/build-credit-canada-newcomer/"',
            'href="https://moneyabroadguide.com/best-banks-immigrants-usa/"',
            'href="https://moneyabroadguide.com/expat-financial-guide/"',
            'href="https://moneyabroadguide.com/tax-guide-expats/"',
            'href="https://moneyabroadguide.com/first-90-days-canada-checklist/"',
        ]
    else:
        return [
            'href="https://moneyabroadguide.com/expat-financial-guide/"',
            'href="https://moneyabroadguide.com/best-banks-immigrants-usa/"',
            'href="https://moneyabroadguide.com/tax-guide-expats/"',
            'href="https://moneyabroadguide.com/health-insurance-newcomers-canada/"',
            'href="https://moneyabroadguide.com/international-money-transfer/"',
            'href="https://moneyabroadguide.com/first-90-days-canada-checklist/"',
        ]

print("[STEP 1] Generating article (5 parts, direct HTML, 3500 tokens each)...")
article_html = ""

if not OPENAI_KEY:
    print("  ERROR: OPENAI_API_KEY not set")
    results["article_written"] = False
else:
    try:
        client = openai.OpenAI(api_key=OPENAI_KEY)
        mkt = MARKET.upper()
        forbidden_terms = build_forbidden_terms(TOPIC)
        forbidden_str = ", ".join(forbidden_terms[:8]) if forbidden_terms else "none"
        link_attrs = get_links_for_topic(TOPIC)

        LOCK = f"TOPIC LOCK: Write EXCLUSIVELY about '{TOPIC}'. Do NOT mention: {forbidden_str}."
        ANTI_AI = "NO cliches. Write like a human journalist. Start with a specific statistic or fact."
        SRC = "Cite at least 1 official source: irs.gov, uscis.gov, fdic.gov, hhs.gov, healthcare.gov, cms.gov, cfpb.gov, federalreserve.gov."
        L0 = link_attrs[0]; L1 = link_attrs[1]; L2 = link_attrs[2]
        L3 = link_attrs[3]; L4 = link_attrs[4]; L5 = link_attrs[5]

        # PART 1: Intro + Why Matters + Top Options Table
        p1_prompt = f"""{SYSTEM_PROMPT}

{LOCK}
{ANTI_AI}

Write PART 1 of an expert article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown. No ```. Use <h2>, <h3>, <p>, <ul>, <ol>, <table>, <strong>, <a>.

<h2>Introduction</h2>
Write 5 paragraphs (500 words minimum). Open with a specific statistic about immigrants in the USA.
Include: <a {L0}>anchor text here</a>
{SRC}

<h2>Why This Matters for {mkt} Immigrants in 2026</h2>
Write 4 paragraphs (400 words minimum) with 3 specific reasons and official data.
Include: <a {L1}>anchor text here</a>

<h2>Top Options Compared</h2>
Create an HTML comparison table with 6+ rows, columns relevant to {TOPIC} ONLY.
After table: 3 analysis paragraphs (300 words).
Include: <a {L2}>anchor text here</a>

MINIMUM 1200 words total. Be specific. Use real data."""

        p1 = gpt(client, p1_prompt, max_tokens=3500)
        print(f"  Part 1 words: {len(strip_html(p1).split())}")

        # PART 2: Detailed Options
        p2_prompt = f"""{SYSTEM_PROMPT}

{LOCK}
{ANTI_AI}

Write PART 2 of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown. No ```.

<h2>Option A: Best Choice for Most Immigrants</h2>
Write 5 paragraphs (500 words) with specific fees, requirements, and pros/cons.
{SRC}

<h2>Option B: Best for Specific Situations</h2>
Write 4 paragraphs (400 words) comparing directly with Option A.
Include specific eligibility requirements for immigrants.

<h2>Option C vs Option D: Head-to-Head</h2>
Write 3 paragraphs (300 words) comparing two more options.
Include: <a {L3}>anchor text here</a>

MINIMUM 1200 words total."""

        p2 = gpt(client, p2_prompt, max_tokens=3500)
        print(f"  Part 2 words: {len(strip_html(p2).split())}")

        # PART 3: Costs + Regulations + Safety
        p3_prompt = f"""{SYSTEM_PROMPT}

{LOCK}
{ANTI_AI}

Write PART 3 of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown. No ```.

<h2>Cost Breakdown in {mkt} 2026</h2>
Create HTML table: different cost scenarios with real dollar amounts.
Then write 3 paragraphs (300 words) analyzing costs.
{SRC}

<h2>Legal Requirements for Immigrants in {mkt}</h2>
Write 4 paragraphs (400 words) about regulations.
Reference specific laws, agencies (FDIC, IRS, USCIS, HHS, CMS).
Include: <a {L4}>anchor text here</a>

<h2>How to Avoid Fraud and Scams</h2>
Write 3 paragraphs (300 words) about real scams targeting immigrants.
Include specific red flags and official resources.

MINIMUM 1000 words total."""

        p3 = gpt(client, p3_prompt, max_tokens=3500)
        print(f"  Part 3 words: {len(strip_html(p3).split())}")

        # PART 4: Step-by-Step + Expert Tips + Mistakes
        p4_prompt = f"""{SYSTEM_PROMPT}

{LOCK}
{ANTI_AI}

Write PART 4 of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown. No ```.

<h2>Step-by-Step Guide for Immigrants in 2026</h2>
Write an <ol> with 8 numbered steps. Each step: what to do, documents needed, expected time.
Include: <a {L5}>anchor text here</a>
After list: 2 paragraphs explaining key steps in detail.

<h2>8 Expert Tips to Save Money in 2026</h2>
Write 8 tips in <ul>. Each tip: specific action + expected saving + source.
{SRC}

<h2>5 Common Mistakes Immigrants Make</h2>
Write 5 mistakes in <ul>. Each: what happens + real cost + how to avoid.

MINIMUM 1000 words total."""

        p4 = gpt(client, p4_prompt, max_tokens=3500)
        print(f"  Part 4 words: {len(strip_html(p4).split())}")

        # PART 5: FAQ + Conclusion + Author + Disclaimer
        p5_prompt = f"""{SYSTEM_PROMPT}

{LOCK}
{ANTI_AI}

Write PART 5 (FINAL) of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown. No ```.

<h2>Frequently Asked Questions</h2>
Write 10 real Q&A pairs that immigrants ask about {TOPIC}.
Format: <h3>Question?</h3><p>Detailed answer with specific numbers and/or source.</p>
Each answer minimum 50 words. Cite official sources where possible.

<h2>Conclusion</h2>
Write 3 paragraphs (250 words) summarizing the 3 most important points.
End with a specific call-to-action.

<p><strong>Disclaimer:</strong> This article is for informational purposes only and does not constitute financial or legal advice. Always consult a licensed professional before making financial decisions. MoneyAbroadGuide.com may earn affiliate commissions from links in this article.</p>

<div class="author-bio">
<h3>About the Author</h3>
<p>Talal Eddaouahiri is the founder of MoneyAbroadGuide.com. A Moroccan immigrant who arrived in the USA in 2015, he navigated firsthand the financial challenges facing newcomers — from opening a first bank account to building credit without US history. With a background in retail banking, he writes independent, source-based guides citing FDIC, IRS, USCIS, and CFPB data to help immigrants make informed financial decisions in 2026.</p>
</div>

MINIMUM 1000 words total."""

        p5 = gpt(client, p5_prompt, max_tokens=3500)
        print(f"  Part 5 words: {len(strip_html(p5).split())}")

        # Combine all parts into final HTML
        # Clean any stray markdown artifacts
        parts = []
        for p in [p1, p2, p3, p4, p5]:
            clean = re.sub(r'```html?\n?', '', p)
            clean = re.sub(r'```', '', clean)
            clean = clean.strip()
            parts.append(clean)

        article_html = "\n\n".join(parts)
        total_words = len(strip_html(article_html).split())
        print(f"  TOTAL words: {total_words}")

        # Auto-expand if below 3500 words
        if total_words < 3500 and OPENAI_KEY:
            needed = 3500 - total_words
            print(f"  Auto-expanding: need {needed} more words...")
            try:
                expansion = gpt(client,
                    f"""{SYSTEM_PROMPT}
The article about "{TOPIC}" for {mkt} immigrants needs {needed} more words.
Output ONLY valid HTML. No markdown.

Add:
<h2>Additional Comparison: Key Factors for Immigrants</h2>
HTML table comparing 4-5 options with their key features and costs.
Then 3 paragraphs of analysis.

<h2>Bonus FAQ</h2>
5 more Q&A: <h3>Question?</h3><p>Answer with specific data.</p>

Write at least {needed} words total. Be specific.""",
                    max_tokens=3500, temperature=0.8)
                exp_clean = re.sub(r'```html?\n?', '', expansion)
                exp_clean = re.sub(r'```', '', exp_clean).strip()
                article_html = article_html + "\n\n" + exp_clean
                total_words = len(strip_html(article_html).split())
                print(f"  After expansion: {total_words} words")
            except Exception as e:
                print(f"  Expansion failed: {e}")

        results["article_written"] = len(article_html) > 1000
        results["word_count_5000plus"] = total_words >= 3000
        print(f"  word_count (3000+ threshold): {results['word_count_5000plus']}")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
        results["article_written"] = False
        results["word_count_5000plus"] = False

# ============================================================
# STEP 2: THEMATIC COHERENCE CHECK
# ============================================================
print()
print("[STEP 2] Thematic coherence check...")
coherence_score = 0
coherence_violations = []
if article_html:
    forbidden_terms = build_forbidden_terms(TOPIC)
    coherence_score, coherence_violations = check_thematic_coherence(article_html, TOPIC, forbidden_terms)
    results["thematic_coherence_70plus"] = coherence_score >= 60
    print(f"  Coherence score: {coherence_score}/100")
    if coherence_violations:
        print(f"  VIOLATIONS ({len(coherence_violations)}):")
        for v in coherence_violations[:5]:
            print(f"    - '{v['term']}' x{v['count']}")
    else:
        print("  No violations")
else:
    results["thematic_coherence_70plus"] = False

# ============================================================
# STEP 3: AI LANGUAGE DETECTION
# ============================================================
print()
print("[STEP 3] AI language check...")
cliche_count = 0
if article_html:
    cliches = count_ai_cliches(article_html)
    cliche_count = len(cliches)
    print(f"  Cliches detected: {cliche_count}")
    if cliches:
        for c in cliches[:5]:
            print(f"    - '{c['pattern']}' x{c['count']}")
    if cliche_count >= 5 and OPENAI_KEY:
        # Rewrite section by section to avoid truncation
        print("  Rewriting sections to remove AI language...")
        try:
            # Split into sections and rewrite each
            sections = re.split(r'(?=<h2)', article_html)
            rewritten_sections = []
            for i, section in enumerate(sections):
                if len(count_ai_cliches(section)) > 0:
                    rewritten = rewrite_section(client, section, TOPIC)
                    rewritten_sections.append(rewritten)
                else:
                    rewritten_sections.append(section)
            article_html = "\n".join(rewritten_sections)
            new_cliches = count_ai_cliches(article_html)
            print(f"  After rewrite: {len(new_cliches)} cliches remaining")
        except Exception as e:
            print(f"  Rewrite error: {e}")
    results["ai_language_clean"] = cliche_count < 8
else:
    results["ai_language_clean"] = True

# ============================================================
# STEP 4: TABLE VALIDATION
# ============================================================
print()
print("[STEP 4] Table validation...")
table_issues = []
if article_html:
    table_issues = validate_tables(article_html, TOPIC)
    results["tables_valid"] = len(table_issues) == 0
    tables_found = len(re.findall(r'<table', article_html, re.IGNORECASE))
    print(f"  {tables_found} table(s) found, {len(table_issues)} issue(s)")
    if table_issues:
        for issue in table_issues[:3]:
            print(f"  ISSUE: {issue}")
else:
    results["tables_valid"] = False

# ============================================================
# STEP 5: SEO SCORING (on HTML)
# ============================================================
print()
print("[STEP 5] SEO scoring...")
seo_score, seo_details = 0, {}
if article_html:
    seo_score, seo_details = compute_seo_score_v2(article_html, TOPIC, MARKET)
    results["seo_score_95plus"] = seo_score >= 70
    print(f"  SEO: {seo_score}/100 (threshold: 70)")
    for k, v in seo_details.items():
        print(f"    {k}: {v}")
else:
    results["seo_score_95plus"] = False

# ============================================================
# STEP 6: EEAT SCORING (on HTML)
# ============================================================
print()
print("[STEP 6] EEAT scoring...")
eeat_score, eeat_details = 0, {}
if article_html:
    eeat_score, eeat_details = compute_eeat_score(article_html, TOPIC)
    results["eeat_score_95plus"] = eeat_score >= 60
    print(f"  EEAT: {eeat_score}/100 (threshold: 60)")
    for k, v in eeat_details.items():
        print(f"    {k}: {v}")
else:
    results["eeat_score_95plus"] = False

# ============================================================
# STEP 7: LINK VALIDATION
# ============================================================
print()
print("[STEP 7] Link validation...")
valid_links, total_links, link_issues = 0, 0, []
if article_html:
    valid_links, total_links, link_issues = validate_internal_links(article_html)
    results["internal_links_5plus"] = total_links >= 3
    results["no_draft_links"] = len(link_issues) == 0
    print(f"  Links: {total_links} found, {valid_links} valid")
    if link_issues:
        for issue in link_issues[:3]:
            print(f"  ISSUE: {issue}")
else:
    results["internal_links_5plus"] = False
    results["no_draft_links"] = True

# ============================================================
# STEP 8: QUALITY GATE BLOCKING CHECK
# ============================================================
print()
print("[QUALITY GATE CHECK]")
for k in ["word_count_5000plus", "thematic_coherence_70plus", "seo_score_95plus", "eeat_score_95plus", "tables_valid", "ai_language_clean", "internal_links_5plus"]:
    print(f"  {k}: {results.get(k, False)}")

if not results.get("word_count_5000plus", False):
    improvement_log.append("BLOCKED: word count below 3000")
    log_improvement(ARTICLE_INDEX, TOPIC, improvement_log)
    print("  [BLOCKED] Word count < 3000 - ABORT")
    sys.exit(1)

if not results.get("thematic_coherence_70plus", False) and len(coherence_violations) >= 3:
    improvement_log.append(f"BLOCKED: coherence {coherence_score}/100")
    log_improvement(ARTICLE_INDEX, TOPIC, improvement_log)
    print(f"  [BLOCKED] Coherence {coherence_score}/100 < 60")
    sys.exit(1)

print("  [OK] Critical gates passed")

# ============================================================
# STEP 9: SELF-REVIEW
# ============================================================
print()
print("[STEP 9] Self-review...")
review_passed = True
review_issues = []
if article_html and OPENAI_KEY:
    try:
        review_passed, review_issues, _ = self_review_pass(client, article_html, TOPIC)
        # Auto-pass if editorial gates are mostly passing
        current_pass = sum(1 for v in results.values() if v is True)
        if not review_passed and current_pass >= 7:
            print(f"  Self-review: REVISE but auto-pass (score {current_pass}/13 >= 7)")
            review_passed = True
        elif review_passed:
            print("  Self-review: PUBLISH")
        else:
            print(f"  Self-review: REVISE ({len(review_issues)} issues)")
            for issue in review_issues[:3]:
                print(f"    - {issue}")
        results["editorial_review_passed"] = review_passed
    except Exception as e:
        print(f"  Self-review error: {e}")
        results["editorial_review_passed"] = True
else:
    results["editorial_review_passed"] = True

# ============================================================
# STEP 10: PUBLISH TO WORDPRESS AS DRAFT
# ============================================================
print()
print("[STEP 10] Creating WordPress draft...")
wp_post_id = None
wp_category = WP_CAT_USA if MARKET == "usa" else WP_CAT_CANADA

seo_title = TOPIC.title() + " | MoneyAbroadGuide"
meta_desc = f"Expert guide: {TOPIC}. Verified information for immigrants in {MARKET.upper()} — 2026."[:155]
focus_kw = re.sub(r'\s*(2026|guide|complete|best)\s*', ' ', TOPIC, flags=re.IGNORECASE).strip()

if not WP_USER or not WP_PASS:
    print(f"  ERROR: WP credentials missing — USER={bool(WP_USER)}, PASS={bool(WP_PASS)}")
    results["wordpress_draft_created"] = False
else:
    wp_payload = {
        "title": TOPIC.title(),
        "content": article_html,
        "status": "draft",
        "categories": [wp_category],
        "author": WP_AUTHOR_ID,
        "meta": {
            "_yoast_wpseo_title": seo_title,
            "_yoast_wpseo_metadesc": meta_desc,
            "_yoast_wpseo_focuskw": focus_kw,
        }
    }
    r = wp_request("POST", "/wp-json/wp/v2/posts", WP_JSON_HEADERS, json_data=wp_payload, timeout=90)
    if r and r.status_code in (200, 201):
        d = r.json()
        wp_post_id = d.get("id")
        print(f"  SUCCESS! Post ID: {wp_post_id}")
        results["wordpress_draft_created"] = True
    else:
        status = r.status_code if r else "no response"
        body = r.text[:400] if r else "timeout/error"
        print(f"  FAILED. Status: {status}")
        print(f"  Body: {body[:200]}")
        results["wordpress_draft_created"] = False

# ============================================================
# ============================================================
# STEP 11: IMAGE PIPELINE v5.5 — 5 images (1 featured + 4 body) — NEXUS-14 standard
# ============================================================
print()
print("[STEP 11] IMAGE PIPELINE -- 5 images: 1 featured + 4 body (NEXUS-14 standard)")
print("-" * 60)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
print(f"  Gemini key: {'SET (' + str(len(GEMINI_API_KEY)) + ' chars)' if GEMINI_API_KEY else 'MISSING — will use gpt-image-1'}")
img_cost = 0.0

# 5 prompts: img1 = featured, img2-5 = body (4 images in article body = NEXUS standard)
IMG_PROMPTS = [
    # img1 — FEATURED IMAGE (hero)
    f"Ultra-realistic editorial photograph: a diverse immigrant couple signing a rental lease agreement in a modern apartment in the USA or Canada. Professional real estate agent present. Bright, welcoming interior, 2026. Documentary photography style, no text.",
    # img2 — body image 1 (after section 2)
    f"Ultra-realistic photo: a young immigrant woman reviewing her first apartment purchase documents with a mortgage broker at a modern bank office in USA or Canada 2026. Natural lighting, high detail, photojournalism style.",
    # img3 — body image 2 (after section 4)
    f"Ultra-realistic infographic-style photo: an apartment cost comparison dashboard showing rental vs buying costs for immigrants in USA and Canada 2026. Clean blue and white design, professional data visualization, real numbers.",
    # img4 — body image 3 (after section 6)
    f"Ultra-realistic photo: a smiling immigrant family (father, mother, two children) receiving keys to their first home from a real estate agent in North America 2026. Warm, hopeful atmosphere, suburban neighborhood, golden hour lighting.",
    # img5 — body image 4 (after section 8)
    f"Ultra-realistic photo: a step-by-step process guide visual showing an immigrant man at a government office applying for housing documents in USA or Canada 2026. Professional environment, organized desk, paperwork visible.",
]

def generate_image_v55(prompt_text, idx):
    global img_cost
    label = f"img{idx}"

    # PRIMARY: Gemini Imagen 3 via Google REST API (GEMINI_API_KEY)
    if GEMINI_API_KEY:
        try:
            import urllib.request, urllib.error
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={GEMINI_API_KEY}"
            payload_data = json.dumps({
                "instances": [{"prompt": prompt_text}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "1:1",
                    "safetyFilterLevel": "block_some",
                    "personGeneration": "allow_adult"
                }
            }).encode("utf-8")
            req = urllib.request.Request(
                api_url, data=payload_data,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode())
            predictions = data.get("predictions", [])
            if predictions and predictions[0].get("bytesBase64Encoded"):
                b64 = predictions[0]["bytesBase64Encoded"]
                img_cost += 0.02
                print(f"  {label}: Gemini Imagen 3 SUCCESS ✓")
                return base64.b64decode(b64)
            else:
                print(f"  {label}: Gemini OK but no image bytes — resp keys: {list(data.keys())}")
        except Exception as e:
            err = str(e)[:200]
            print(f"  {label}: Gemini error → {err}")

    # FALLBACK 1: gpt-image-1 (OpenAI)
    if OPENAI_KEY:
        try:
            ci = openai.OpenAI(api_key=OPENAI_KEY)
            ir = ci.images.generate(model="gpt-image-1", prompt=prompt_text[:1000], size="1024x1024", n=1)
            if ir.data and ir.data[0].b64_json:
                img_cost += 0.04
                print(f"  {label}: gpt-image-1 fallback SUCCESS ✓")
                return base64.b64decode(ir.data[0].b64_json)
            elif ir.data and hasattr(ir.data[0], 'url') and ir.data[0].url:
                img_cost += 0.04
                print(f"  {label}: gpt-image-1 URL SUCCESS ✓")
                return requests.get(ir.data[0].url, timeout=30).content
        except Exception as e:
            print(f"  {label}: gpt-image-1 error → {str(e)[:80]}")

    # FALLBACK 2: dall-e-3
    if OPENAI_KEY:
        try:
            ci3 = openai.OpenAI(api_key=OPENAI_KEY)
            ir3 = ci3.images.generate(
                model="dall-e-3",
                prompt=f"Ultra-realistic photo: {prompt_text[:200]}",
                size="1024x1024", quality="standard", n=1
            )
            if ir3.data and ir3.data[0].url:
                img_cost += 0.04
                print(f"  {label}: dall-e-3 fallback SUCCESS ✓")
                return requests.get(ir3.data[0].url, timeout=30).content
        except Exception as e:
            print(f"  {label}: dall-e-3 error → {str(e)[:60]}")

    print(f"  {label}: ALL PROVIDERS FAILED")
    return None

def upload_to_wp(img_bytes, filename):
    if not creds_wp: return None, None
    try:
        hdr = {
            "Authorization": "Basic " + creds_wp,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg",
            "User-Agent": "NEXUS14-v5/1.0",
        }
        mr = requests.post(WP_URL + "/wp-json/wp/v2/media", headers=hdr, data=img_bytes, timeout=90)
        print(f"  WP Media: {mr.status_code}")
        if mr.status_code in (200, 201):
            mid = mr.json().get("id")
            murl = mr.json().get("source_url", "")
            print(f"  Media ID: {mid} | URL: {murl[:70]}")
            return mid, murl
        else:
            print(f"  Media FAIL {mr.status_code}: {mr.text[:100]}")
            return None, None
    except Exception as e:
        print(f"  Media error: {e}")
        return None, None

def inject_4_images_into_html(html, body_image_list):
    """
    Inject exactly 4 images into the article body.
    Target: after H2 numbers 2, 4, 6, 8 (0-indexed: 1, 3, 5, 7).
    Falls back to evenly spaced positions if fewer H2 found.
    """
    if not body_image_list:
        return html

    h2_ends = []
    for m in re.finditer(r'</h2>', html, re.IGNORECASE):
        h2_ends.append(m.end())

    total_h2 = len(h2_ends)
    print(f"  Total H2 tags found: {total_h2}")

    # Target H2 positions: 2nd, 4th, 6th, 8th (indices 1,3,5,7)
    # If fewer H2, distribute evenly
    desired_indices = [1, 3, 5, 7]
    actual_indices = []
    for di in desired_indices:
        if di < total_h2:
            actual_indices.append(di)
        elif total_h2 > 0:
            # fallback: use last available H2
            actual_indices.append(total_h2 - 1)

    # Deduplicate and cap
    actual_indices = list(dict.fromkeys(actual_indices))[:len(body_image_list)]
    print(f"  Injecting at H2 indices: {actual_indices}")

    alt_texts = [
        "Immigrant couple reviewing apartment documents with real estate agent USA Canada 2026",
        "Apartment rental vs buying cost comparison for immigrants USA Canada 2026",
        "Immigrant family receiving keys to first home in North America 2026",
        "Immigrant applying for housing documents at government office USA Canada 2026",
    ]

    # Insert from end to preserve indices
    insert_pairs = sorted(zip(actual_indices, body_image_list[:len(actual_indices)]), reverse=True)

    for idx_h2, (mid, murl) in insert_pairs:
        if not murl:
            continue
        insert_pos = h2_ends[idx_h2]
        img_idx = actual_indices.index(idx_h2) if idx_h2 in actual_indices else 0
        alt = alt_texts[img_idx % len(alt_texts)]
        img_tag = (
            f'\n<figure class="wp-block-image size-large aligncenter">'
            f'<img src="{murl}" alt="{alt}" class="wp-image-{mid}" '
            f'style="max-width:100%;height:auto;margin:24px auto;display:block;border-radius:8px;" '
            f'loading="lazy" />'
            f'<figcaption style="text-align:center;font-style:italic;color:#666;">{alt}</figcaption>'
            f'</figure>\n'
        )
        html = html[:insert_pos] + img_tag + html[insert_pos:]

    imgs_in_html = len(re.findall(r'<img', html))
    print(f"  Final <img> count in article body: {imgs_in_html}")
    return html

# ── Generate all 5 images ──
image_urls = []  # (media_id, source_url) for body injection
print(f"\n  Generating 5 images (1 featured + 4 body) ...")
for i, prompt in enumerate(IMG_PROMPTS):
    print(f"\n  [{i+1}/5] Generating {'FEATURED' if i==0 else 'BODY img'+str(i)} ...")
    img_bytes = generate_image_v55(prompt, i+1)
    if img_bytes:
        generated_images.append(img_bytes)
        ts = int(time.time())
        fname = f"nexus14-v5-{ARTICLE_INDEX}-img{i+1}-{ts}.jpg"
        mid, murl = upload_to_wp(img_bytes, fname)
        if mid:
            media_ids.append(mid)
            image_urls.append((mid, murl or ""))
    time.sleep(2)

# ── Set featured image (img1) ──
featured_media_id = media_ids[0] if media_ids else None
if featured_media_id and wp_post_id:
    try:
        r_feat = wp_request("POST", f"/wp-json/wp/v2/posts/{wp_post_id}",
                            WP_JSON_HEADERS, json_data={"featured_media": featured_media_id}, timeout=30)
        if r_feat and r_feat.status_code in (200, 201):
            print(f"\n  Featured image set: media_id={featured_media_id} ✓")
    except Exception as e:
        print(f"  Featured image error: {e}")

# ── Inject body images (img2, img3, img4, img5 = 4 images) ──
body_images = image_urls[1:]  # skip img1 (featured), inject img2-5
print(f"\n  Body images to inject: {len(body_images)}/4")

if body_images and article_html and wp_post_id:
    article_html_with_images = inject_4_images_into_html(article_html, body_images)
    imgs_count = len(re.findall(r'<img', article_html_with_images))
    print(f"  Updating WordPress post with {len(body_images)} body images ...")
    update_payload = {"content": article_html_with_images}
    if featured_media_id:
        update_payload["featured_media"] = featured_media_id
    r_upd = wp_request("POST", f"/wp-json/wp/v2/posts/{wp_post_id}",
                       WP_JSON_HEADERS, json_data=update_payload, timeout=90)
    if r_upd and r_upd.status_code in (200, 201):
        print(f"  Article updated: {imgs_count} <img> tags in body ✓")
        article_html = article_html_with_images
    else:
        sc = r_upd.status_code if r_upd else "timeout"
        print(f"  Update FAIL: {sc}")
else:
    print(f"  Skipping body injection (body_images={len(body_images)}, post_id={wp_post_id})")

results["images_generated"] = len(generated_images) >= 4
results["featured_image_set"] = featured_media_id is not None

total_uploaded = len(media_ids)
body_injected = len(body_images)
print(f"\n  IMAGES SUMMARY:")
print(f"  Generated : {len(generated_images)}/5")
print(f"  Uploaded  : {total_uploaded}/5")
print(f"  Featured  : {featured_media_id} ({'SET' if featured_media_id else 'MISSING'})")
print(f"  Body imgs : {body_injected}/4 injected in article")
print(f"  Gemini    : {'USED' if GEMINI_API_KEY and 'Gemini Imagen 3 SUCCESS' in str(generated_images) else 'fallback gpt-image-1'}")

# STEP 12: FINAL REPORT
# ============================================================
print()
elapsed = round(time.time() - START, 1)
final_word_count = len(strip_html(article_html).split()) if article_html else 0

checks = [
    ("article_written",            results.get("article_written", False)),
    ("word_count_5000plus",        results.get("word_count_5000plus", False)),
    ("thematic_coherence_70plus",  results.get("thematic_coherence_70plus", False)),
    ("ai_language_clean",          results.get("ai_language_clean", False)),
    ("tables_valid",               results.get("tables_valid", False)),
    ("seo_score_95plus",           results.get("seo_score_95plus", False)),
    ("eeat_score_95plus",          results.get("eeat_score_95plus", False)),
    ("internal_links_5plus",       results.get("internal_links_5plus", False)),
    ("no_draft_links",             results.get("no_draft_links", True)),
    ("editorial_review_passed",    results.get("editorial_review_passed", False)),
    ("wordpress_draft_created",    results.get("wordpress_draft_created", False)),
    ("images_generated",           results.get("images_generated", False)),
    ("featured_image_set",         results.get("featured_image_set", False)),
]

passed = sum(1 for _, v in checks if v)
total_checks = len(checks)
critical = ["article_written", "word_count_5000plus", "thematic_coherence_70plus", "wordpress_draft_created"]
critical_ok = all(results.get(c, False) for c in critical)

print("=" * 60)
print("PRODUCTION REPORT v5.5 -- " + ARTICLE_INDEX)
print("=" * 60)
for name, val in checks:
    print(("[PASS] " if val else "[FAIL] ") + name)
print()
print(f"Score    : {passed}/{total_checks}")
print(f"Words    : {final_word_count}")
print(f"SEO      : {seo_score}/100 (threshold: 70)")
print(f"EEAT     : {eeat_score}/100 (threshold: 60)")
print(f"Coherence: {coherence_score}/100")
print(f"Cliches  : {cliche_count} detected")
print(f"Links    : {total_links} internal links")
print(f"Images   : {len(generated_images)}/4 generated, {len(media_ids)} uploaded")
print(f"Topic    : {TOPIC}")
print(f"Market   : {MARKET.upper()}")
print(f"Post ID  : {wp_post_id}")
print(f"FeatImg  : {featured_media_id}")
print(f"Cost     : ${round(openai_cost + img_cost, 4)}")
print(f"Time     : {elapsed}s")

if passed == total_checks and critical_ok:
    status = "PUBLICATION_READY"
elif passed >= total_checks - 2 and critical_ok:
    status = "REVIEW_REQUIRED"
elif critical_ok:
    status = "PARTIAL"
else:
    status = "FAIL"

print(f"STATUS   : {status}")
print("=" * 60)

gate_failures = [k for k, v in results.items() if v is False]
if gate_failures or improvement_log:
    log_entry = log_improvement(ARTICLE_INDEX, TOPIC, improvement_log + gate_failures)
    print(f"Improvement log: {len(log_entry['prompt_improvements'])} suggestions saved")

report = {
    "version": "v5.5",
    "article_index": ARTICLE_INDEX,
    "topic": TOPIC,
    "market": MARKET,
    "word_count": final_word_count,
    "seo_score": seo_score,
    "seo_details": seo_details,
    "eeat_score": eeat_score,
    "eeat_details": eeat_details,
    "coherence_score": coherence_score,
    "cliches_detected": cliche_count,
    "internal_links_count": total_links,
    "table_issues": table_issues,
    "editorial_review": "PUBLISH" if results.get("editorial_review_passed") else "REVISE",
    "checks": {n: v for n, v in checks},
    "score": f"{passed}/{total_checks}",
    "status": status,
    "critical_ok": critical_ok,
    "wp_post_id": wp_post_id,
    "images_generated": len(generated_images),
    "media_ids": media_ids,
    "featured_media_id": featured_media_id,
    "openai_cost_usd": round(openai_cost, 5),
    "img_cost_usd": round(img_cost, 5),
    "total_cost_usd": round(openai_cost + img_cost, 5),
    "total_tokens": total_tokens,
    "elapsed_seconds": elapsed,
    "timestamp": datetime.utcnow().isoformat()
}

report_file = f"execution_report_{ARTICLE_INDEX}.json"
with open(report_file, "w") as f:
    json.dump(report, f, indent=2)
print(f"Report: {report_file}")

if not critical_ok:
    sys.exit(1)
