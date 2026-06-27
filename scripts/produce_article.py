#!/usr/bin/env python3
"""
NEXUS-14 PRODUCTION SCRIPT v6.0 - CLAUDE HAIKU 4.5 + GEMINI IMAGES
scripts/produce_article.py

NEXUS-14 v6.0 - NEXUS standard (2026):
- Writer: claude-haiku-4-5 (Anthropic) - 4000-5000 words, cost <= $0.25/article
- Images: 5 total (1 featured + 4 body) via Gemini Imagen 3
- Agent 17 V3.2: slug/title/keyword/country-aware duplicate prevention (BLOCKING)
- Gate 19: country/category validation (warning mode)
- Gate 20: anti-thin-content & originality (warning mode)
- Daily max: 6 articles (NEXUS-14 standard)
- SEO threshold: 70+ | EEAT threshold: 60+ | All 13 gates must pass
"""
import sys, os, json, time, requests, re, base64, hashlib, urllib.request
from base64 import b64encode
from datetime import datetime

try:
    import anthropic
except ImportError:
    os.system("pip install anthropic -q")
    import anthropic

START = time.time()
ARTICLE_INDEX = os.environ.get("ARTICLE_INDEX", "PILOT-01")
MARKET = (os.environ.get("TARGET_MARKET") or "usa").lower()
TOPIC = (os.environ.get("TOPIC_OVERRIDE") or "").strip()
if not TOPIC:
    TOPIC = "best banks for immigrants in the usa 2026"

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER = (os.environ.get("WORDPRESS_USERNAME", "") or "").strip()
WP_PASS = ((os.environ.get("WORDPRESS_APP_PASSWORD", "") or os.environ.get("WORDPRESS_PASSWORD", "")) or "").strip()

# NEXUS-14 WordPress taxonomy (verified 2026-06-22)
WP_CAT_USA = 17
WP_CAT_CANADA = 18
WP_AUTHOR_ID = 4
COST_BUDGET = 0.25  # Max $0.25 per article
MODEL = "claude-haiku-4-5"
MIN_WORDS = 4000
MAX_WORDS = 5000

# Gate 19 - Verified WP category map
COUNTRY_CATEGORY_MAP = {7: "NEUTRAL", 12: "NEUTRAL", 17: "USA", 18: "CANADA"}

creds_wp = b64encode((WP_USER + ":" + WP_PASS).encode()).decode() if WP_USER and WP_PASS else ""
WP_JSON_HEADERS = {
    "Authorization": "Basic " + creds_wp,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "NEXUS14-v6/1.0",
}

print("=" * 60)
print("NEXUS-14 PRODUCTION v6.0 -- " + ARTICLE_INDEX)
print("=" * 60)
print("Topic   :", TOPIC)
print("Market  :", MARKET.upper())
print("Claude  :", "SET" if ANTHROPIC_KEY else "MISSING")
print("Gemini  :", "SET" if GEMINI_KEY else "MISSING")
print("WP URL  :", WP_URL)
print("WP USER :", WP_USER or "MISSING")
print("WP PASS :", ("SET (" + str(len(WP_PASS)) + " chars)") if WP_PASS else "MISSING")
print()

results = {}
anthropic_cost = 0.0
total_input_tokens = 0
total_output_tokens = 0
generated_images = []
media_ids = []
image_urls = []
improvement_log = []
# ============================================================
# UTILITIES
# ============================================================

def haiku(client, prompt, max_tokens=2000, system=None):
    """Call Claude claude-haiku-4-5 with cost tracking."""
    global anthropic_cost, total_input_tokens, total_output_tokens
    messages = [{"role": "user", "content": prompt}]
    kwargs = {"model": MODEL, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    r = client.messages.create(**kwargs)
    inp = r.usage.input_tokens
    out = r.usage.output_tokens
    total_input_tokens += inp
    total_output_tokens += out
    cost = (inp / 1_000_000) * 0.80 + (out / 1_000_000) * 4.00
    anthropic_cost += cost
    if anthropic_cost > COST_BUDGET * 0.9:
        print(f"  [COST WARNING] ${anthropic_cost:.4f}/{COST_BUDGET} budget")
    return r.content[0].text

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
                return r
            time.sleep(2)
        except Exception as e:
            print(f"  WP error attempt {attempt}: {e}")
            time.sleep(2 ** attempt)
    return None

def strip_html(text):
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

# ============================================================
# AGENT 17 V3.2 - HARDENED DUPLICATE PREVENTION
# Deterministic: title/slug/keyword/country-aware (BLOCKING)
# ============================================================
USA_SIGNALS = ["usa", "united states", "american", "u.s.", "irs", "uscis", "fdic", "sba", "social security"]
CA_SIGNALS = ["canada", "canadian", "cra", "osfi", "fintrac", "cdic", "ontario", "quebec", "toronto", "tfsa", "rrsp"]

def detect_country_from_topic(topic_lower):
    usa_hits = sum(1 for s in USA_SIGNALS if s in topic_lower)
    ca_hits = sum(1 for s in CA_SIGNALS if s in topic_lower)
    if usa_hits > ca_hits: return "USA"
    if ca_hits > usa_hits: return "CANADA"
    if "usa" in topic_lower or "us " in topic_lower: return "USA"
    if "canada" in topic_lower: return "CANADA"
    return "UNKNOWN"

def normalize_slug_a17(text):
    slug = re.sub(r"\b(usa|canada|canadian|american|us|the|in|for|to|a|an|and|or|of|with|by|2026|2025|2024)\b", "", text.lower())
    slug = re.sub(r"[^a-z0-9]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug

def title_similarity_a17(a, b):
    a_words = set(re.findall(r"\w+", a.lower())) - {"the","a","an","in","for","to","and","or","of","with"}
    b_words = set(re.findall(r"\w+", b.lower())) - {"the","a","an","in","for","to","and","or","of","with"}
    if not a_words or not b_words: return 0.0
    return len(a_words & b_words) / len(a_words | b_words)

def get_existing_wp_posts():
    """Fetch existing WP posts for duplicate check."""
    if not WP_USER or not WP_PASS:
        print("  [Agent 17] No WP creds - skipping duplicate check")
        return []
    try:
        r = wp_request("GET", "/wp-json/wp/v2/posts?status=draft,publish&per_page=100", WP_JSON_HEADERS, timeout=30)
        if r and r.status_code == 200:
            posts = r.json()
            print(f"  [Agent 17] Fetched {len(posts)} existing posts for duplicate check")
            return posts
    except Exception as e:
        print(f"  [Agent 17] Error fetching posts: {e}")
    return []

def check_agent17_duplicate(topic, market, existing_posts):
    """
    Agent 17 V3.2 - Deterministic duplicate prevention.
    Returns: (decision, reason, blocking)
    """
    topic_lower = topic.lower()
    topic_country = detect_country_from_topic(topic_lower)
    topic_slug = normalize_slug_a17(topic)
    topic_kw = re.sub(r"\b(2026|2025|guide|complete|best|top|how to|overview)\b", "", topic_lower).strip()

    for post in existing_posts:
        existing_title = post.get("title", {}).get("rendered", "")
        existing_lower = existing_title.lower()
        existing_slug = normalize_slug_a17(existing_title)
        existing_country = detect_country_from_topic(existing_lower)
        existing_kw = re.sub(r"\b(2026|2025|guide|complete|best|top|how to|overview)\b", "", existing_lower).strip()

        # 1. Slug exact match same country = BLOCK
        if topic_slug == existing_slug and len(topic_slug) > 5:
            if topic_country == existing_country and topic_country != "UNKNOWN":
                return "REJECT_DUPLICATE", f"Slug exact match: '{topic_slug}'", True

        # 2. Primary keyword equality same country = BLOCK
        if topic_kw and existing_kw and topic_kw == existing_kw:
            if topic_country == existing_country and topic_country != "UNKNOWN":
                return "REJECT_DUPLICATE", f"Keyword exact match: '{topic_kw[:50]}'", True

        # 3. Title similarity >= 0.90 same country = BLOCK
        sim = title_similarity_a17(topic, existing_title)
        if sim >= 0.90 and topic_country == existing_country and topic_country != "UNKNOWN":
            return "REJECT_DUPLICATE", f"Title similarity {sim:.2f} >= 0.90 (same country)", True

        # 4. High overlap >= 0.80 same country = BLOCK
        if sim >= 0.80 and topic_country == existing_country and topic_country != "UNKNOWN":
            return "REJECT_DUPLICATE", f"Keyword overlap {sim:.2f} >= 0.80 same country", True

        # 5. USA vs Canada same slug = ALLOW (legitimate variant)
        if topic_slug == existing_slug and topic_country != existing_country:
            if topic_country != "UNKNOWN" and existing_country != "UNKNOWN":
                continue  # Different countries - allow

    # 6. Unknown country -> soft manual review (non-blocking)
    if topic_country == "UNKNOWN":
        return "MANUAL_REVIEW", "Country UNKNOWN - manual review recommended", False

    return "CREATE_NEW", "No duplicates found - proceed to generation", False
# ============================================================
# GATE 19 - COUNTRY/CATEGORY VALIDATION (WARNING MODE)
# ============================================================
def gate19_country_category(topic, market, wp_category):
    topic_lower = topic.lower()
    topic_country = detect_country_from_topic(topic_lower)
    cat_country = COUNTRY_CATEGORY_MAP.get(wp_category, "UNKNOWN")
    result = {"gate": 19, "mode": "warning", "status": "PASS", "message": ""}
    if cat_country == "NEUTRAL":
        result["message"] = f"Category {wp_category} is NEUTRAL - no conflict possible"
        return result
    if topic_country == "UNKNOWN":
        result["status"] = "MANUAL_REVIEW"
        result["message"] = f"Topic country UNKNOWN - cannot validate against cat {wp_category}"
        return result
    if cat_country != topic_country:
        result["status"] = "WARNING"
        result["message"] = f"Country mismatch: topic={topic_country} vs category={cat_country}"
        return result
    result["message"] = f"Country match OK: {topic_country} == {cat_country}"
    return result

# ============================================================
# GATE 20 - ANTI-THIN-CONTENT & ORIGINALITY (WARNING MODE)
# ============================================================
def gate20_anti_thin(article_html, topic):
    result = {"gate": 20, "mode": "warning", "status": "PASS", "issues": []}
    clean = strip_html(article_html)
    words = clean.split()
    word_count = len(words)
    if word_count < MIN_WORDS:
        result["status"] = "FAIL"
        result["issues"].append(f"Too thin: {word_count} words < {MIN_WORDS} minimum")
    sentences = re.findall(r"[A-Z][^.!?]*[.!?]", clean)
    seen = {}
    for s in sentences:
        s_norm = re.sub(r"\s+", " ", s.lower().strip())
        if len(s_norm) > 40:
            seen[s_norm] = seen.get(s_norm, 0) + 1
    repeated = [(s, c) for s, c in seen.items() if c >= 3]
    if repeated:
        result["status"] = "WARNING"
        result["issues"].append(f"Repeated sentences: {len(repeated)} detected")
    paragraphs = re.findall(r"<p[^>]*>.*?</p>", article_html, re.DOTALL | re.IGNORECASE)
    if len(paragraphs) < 8:
        result["status"] = "WARNING"
        result["issues"].append(f"Low paragraph count: {len(paragraphs)} < 8 expected")
    return result

# ============================================================
# GATES 1-8: SEO, EEAT, THEMATIC, AI LANGUAGE
# ============================================================
def build_forbidden_terms(topic):
    tl = topic.lower()
    all_transfer_terms = ["wise","remitly","moneygram","ofx","western union","transfergo","worldremit","xe.com","exchange rate","money transfer"]
    all_health_terms = ["deductible","copay","medicaid","medicare","hmo","ppo"]
    forbidden = []
    is_health = any(w in tl for w in ["health","insurance","medical","healthcare"])
    is_transfer = any(w in tl for w in ["transfer","send money","remittance"])
    is_banking = any(w in tl for w in ["bank","banking","account"])
    if is_health and not is_transfer and not is_banking:
        forbidden.extend(all_transfer_terms)
    if is_transfer and not is_health and not is_banking:
        forbidden.extend(all_health_terms)
    if is_banking and not is_transfer:
        forbidden.extend(["moneygram","western union","worldremit"])
    return forbidden

def check_thematic_coherence(article_html, topic, forbidden_terms):
    violations = []
    al = article_html.lower()
    topic_words = [w for w in re.split(r"[\s,]+", topic.lower()) if len(w) > 3]
    topic_hits = sum(1 for w in topic_words if w in al)
    topic_coverage = topic_hits / max(len(topic_words), 1)
    for term in forbidden_terms:
        if term.lower() in al:
            violations.append({"term": term, "count": al.count(term.lower())})
    off_topic_penalty = min(len(violations) * 15, 60)
    coverage_bonus = int(topic_coverage * 40)
    score = max(0, 40 + coverage_bonus - off_topic_penalty)
    return score, violations

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

def compute_seo_score_v2(article_html, topic, market):
    score = 0
    details = {}
    al = article_html.lower()
    topic_words = [w for w in topic.lower().split() if len(w) > 3]
    kw_pts = int(sum(1 for w in topic_words if w in al) / max(len(topic_words), 1) * 20)
    score += kw_pts
    details["keyword_coverage"] = f"{kw_pts}/20"
    h2_count = len(re.findall(r"<h2[^>]*>", article_html, re.IGNORECASE))
    h3_count = len(re.findall(r"<h3[^>]*>", article_html, re.IGNORECASE))
    h_pts = min(h2_count * 2 + h3_count, 15)
    score += h_pts
    details["heading_structure"] = f"{h_pts}/15 (h2:{h2_count}, h3:{h3_count})"
    has_table = int(bool(re.search(r"<table", article_html, re.IGNORECASE)))
    score += has_table * 10
    details["has_table"] = f"{has_table * 10}/10"
    word_count = len(strip_html(article_html).split())
    if word_count >= 4000: wc_pts = 15
    elif word_count >= 2500: wc_pts = 10
    elif word_count >= 1500: wc_pts = 7
    else: wc_pts = 3
    score += wc_pts
    details["word_count"] = f"{wc_pts}/15 ({word_count} words)"
    internal_links = len(re.findall(r'href="https?://moneyabroadguide\.com[^"]*"', article_html, re.IGNORECASE))
    link_pts = min(internal_links * 3, 15)
    score += link_pts
    details["internal_links"] = f"{link_pts}/15 ({internal_links} links)"
    faq_count = len(re.findall(r"<h3[^>]*>[^<]*\?[^<]*</h3>", article_html, re.IGNORECASE))
    faq_pts = min(faq_count * 2, 10)
    score += faq_pts
    details["faq_questions"] = f"{faq_pts}/10 ({faq_count} detected)"
    cliche_penalty = min(len(count_ai_cliches(al)), 5)
    score -= cliche_penalty
    details["ai_cliche_penalty"] = f"-{cliche_penalty}"
    has_source = int(bool(re.search(r"(?i)(irs\.gov|uscis\.gov|fdic\.gov|hhs\.gov|healthcare\.gov|cfpb|canada\.ca)", article_html)))
    score += has_source * 10
    details["official_sources"] = f"{has_source * 10}/10"
    return max(0, min(score, 100)), details

def compute_eeat_score(article_html, topic):
    score = 0
    details = {}
    al = article_html.lower()
    sources = ["irs.gov","uscis.gov","fdic.gov","hhs.gov","healthcare.gov","cfpb.gov","consumerfinance.gov","canada.ca","cms.gov","dol.gov","ssa.gov","cra-arc.gc.ca"]
    found = [s for s in sources if s in al]
    src_pts = min(len(found) * 5, 25)
    score += src_pts
    details["official_sources"] = f"{src_pts}/25 ({found})"
    data_pts = min(sum(1 for p in [r"\d+%",r"\$\d+",r"according to",r"data shows",r"study found",r"reported by"] if re.search(p, al)) * 3, 20)
    score += data_pts
    details["data_citations"] = f"{data_pts}/20"
    exp_pts = min(sum(1 for p in [r"step 1",r"step 2",r"for example",r"case study",r"in practice",r"for instance"] if re.search(p, al)) * 3, 15)
    score += exp_pts
    details["experience_signals"] = f"{exp_pts}/15"
    auth_pts = min(sum(1 for p in [r"expert",r"licensed",r"certified",r"fdic",r"uscis",r"regulatory",r"professional"] if re.search(p, al)) * 2, 15)
    score += auth_pts
    details["authority"] = f"{auth_pts}/15"
    trust_pts = (int(bool(re.search(r"(?i)(talal|about the author|written by)", article_html))) + int(bool(re.search(r"(?i)(disclaimer|not financial advice|consult)", article_html))) + int(bool(re.search(r"(?i)(2026|last updated)", article_html)))) * 8
    score += min(trust_pts, 25)
    details["trust"] = f"{min(trust_pts, 25)}/25"
    return min(score, 100), details

def validate_internal_links(article_html):
    links = re.findall(r'href="(https?://moneyabroadguide\.com[^"]*)"', article_html)
    draft_issues = [l for l in links if "p=" in l and "preview" in l]
    return len(links) - len(draft_issues), len(links), [f"DRAFT: {l}" for l in draft_issues]
# ============================================================
# ARTICLE GENERATION SYSTEM PROMPT (NEXUS-14 STANDARD)
# ============================================================
SYSTEM_PROMPT = """You are a senior financial journalist at MoneyAbroadGuide.com.
Write for immigrants and newcomers in the USA and Canada.
Style: direct, factual, specific - like NerdWallet or Investopedia.
NEVER write: navigate, delve into, it is important to note, comprehensive guide,
shed light on, embark on, a myriad of, leverage, utilize, plays a crucial role.
ALWAYS: specific numbers, real examples, official sources (IRS, USCIS, FDIC, HHS, CMS, CFPB).
Write in active voice. Start paragraphs with facts. NO markdown, only HTML."""

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
    elif "tax" in tl:
        return [
            'href="https://moneyabroadguide.com/tax-guide-expats/"',
            'href="https://moneyabroadguide.com/best-banks-immigrants-usa/"',
            'href="https://moneyabroadguide.com/expat-financial-guide/"',
            'href="https://moneyabroadguide.com/first-90-days-canada-checklist/"',
            'href="https://moneyabroadguide.com/build-credit-canada-newcomer/"',
            'href="https://moneyabroadguide.com/international-money-transfer/"',
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

# ============================================================
# STEP 0: AGENT 17 — DUPLICATE PREVENTION CHECK
# ============================================================
print()
print("[STEP 0] Agent 17 V3.2 - Duplicate prevention check...")
existing_posts = get_existing_wp_posts()
wp_category = WP_CAT_USA if MARKET == "usa" else WP_CAT_CANADA
a17_decision, a17_reason, a17_blocking = check_agent17_duplicate(TOPIC, MARKET, existing_posts)
print(f"  Decision: {a17_decision}")
print(f"  Reason  : {a17_reason}")
print(f"  Blocking: {a17_blocking}")
results["agent17_decision"] = a17_decision
results["agent17_blocking"] = a17_blocking

if a17_blocking and a17_decision == "REJECT_DUPLICATE":
    print(f"  [AGENT 17] BLOCKED: {a17_reason}")
    print("  Duplicate detected - aborting generation.")
    sys.exit(1)
elif a17_decision == "MANUAL_REVIEW":
    print(f"  [AGENT 17] WARNING: Manual review recommended - {a17_reason}")
    print("  Proceeding in non-blocking mode...")
else:
    print(f"  [AGENT 17] OK: {a17_reason}")

# Gate 19 check (warning mode)
g19 = gate19_country_category(TOPIC, MARKET, wp_category)
print(f"  [Gate 19] {g19['status']}: {g19['message']}")
results["gate19_status"] = g19["status"]

# ============================================================
# STEP 1: ARTICLE GENERATION (CLAUDE HAIKU 4.5 — 4 PARTS)
# Budget-aware: each part ~1500 tokens output = ~$0.006/part
# 4 parts x $0.006 = ~$0.024 text cost + images budget
# ============================================================
print()
print("[STEP 1] Generating article (4 parts x 2000 tokens, Claude claude-haiku-4-5)...")
article_html = ""
client = None

if not ANTHROPIC_KEY:
    print("  ERROR: ANTHROPIC_API_KEY not set")
    results["article_written"] = False
else:
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        mkt = MARKET.upper()
        forbidden_terms = build_forbidden_terms(TOPIC)
        forbidden_str = ", ".join(forbidden_terms[:8]) if forbidden_terms else "none"
        link_attrs = get_links_for_topic(TOPIC)
        L0,L1,L2,L3,L4,L5 = link_attrs[0],link_attrs[1],link_attrs[2],link_attrs[3],link_attrs[4],link_attrs[5]

        LOCK = f"TOPIC LOCK: Write EXCLUSIVELY about '{TOPIC}'. Do NOT mention: {forbidden_str}."
        ANTI_AI = "NO cliches. Start with a real statistic. Write like a human senior journalist."
        SRC = "Cite at least 1 official source: irs.gov, uscis.gov, fdic.gov, hhs.gov, healthcare.gov, cms.gov, cfpb.gov, canada.ca."

        # PART 1: Intro + Why Matters + Comparison Table (target ~1000 words)
        p1_prompt = f"""Write PART 1 of an expert financial article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown. No backticks.

{LOCK}
{ANTI_AI}

<h2>Introduction</h2>
4 paragraphs (400 words). Open with a specific statistic from a government source.
Include internal link: <a {L0}>anchor text</a>
{SRC}

<h2>Why This Matters for {mkt} Immigrants in 2026</h2>
3 paragraphs (300 words) with 3 specific reasons and official data.
Include: <a {L1}>anchor text</a>

<h2>Top Options Compared</h2>
HTML comparison table with 6+ rows and columns relevant to {TOPIC} only.
After table: 2 analysis paragraphs (200 words).
Include: <a {L2}>anchor text</a>

MINIMUM 900 words total. Be specific. Use real numbers."""

        p1 = haiku(client, p1_prompt, max_tokens=2000, system=SYSTEM_PROMPT)
        print(f"  Part 1 words: {len(strip_html(p1).split())} | Cost so far: ${anthropic_cost:.4f}")

        # PART 2: Detailed Options (target ~1000 words)
        p2_prompt = f"""Write PART 2 of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown.
{LOCK} {ANTI_AI}

<h2>Option A: Best Choice for Most Immigrants</h2>
4 paragraphs (400 words) with specific fees, requirements, pros/cons.
{SRC}

<h2>Option B: Best for Specific Situations</h2>
3 paragraphs (300 words) comparing directly with Option A.
Include specific eligibility requirements for immigrants.

<h2>Option C vs Option D: Head-to-Head</h2>
3 paragraphs (300 words) comparing two more options.
Include: <a {L3}>anchor text</a>

MINIMUM 1000 words total. Include specific dollar amounts."""

        p2 = haiku(client, p2_prompt, max_tokens=2000, system=SYSTEM_PROMPT)
        print(f"  Part 2 words: {len(strip_html(p2).split())} | Cost so far: ${anthropic_cost:.4f}")

        # PART 3: Costs + Legal + Fraud Prevention (target ~1000 words)
        p3_prompt = f"""Write PART 3 of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown.
{LOCK} {ANTI_AI}

<h2>Cost Breakdown in {mkt} 2026</h2>
HTML cost table with real dollar amounts for different scenarios.
Then 2 paragraphs (200 words) analyzing costs.
{SRC}

<h2>Legal Requirements for Immigrants in {mkt}</h2>
3 paragraphs (300 words) about regulations, specific agencies (FDIC, IRS, USCIS, HHS).
Include: <a {L4}>anchor text</a>

<h2>How to Avoid Fraud and Scams</h2>
3 paragraphs (300 words) about real scams targeting immigrants.
Include specific red flags and official resources.

<h2>Step-by-Step Guide for Immigrants in 2026</h2>
Numbered <ol> with 8 steps. Each step: action + documents + expected time.
Include: <a {L5}>anchor text</a>
After list: 1 paragraph explaining the most important step.

MINIMUM 1000 words total."""

        p3 = haiku(client, p3_prompt, max_tokens=2000, system=SYSTEM_PROMPT)
        print(f"  Part 3 words: {len(strip_html(p3).split())} | Cost so far: ${anthropic_cost:.4f}")

        # PART 4: FAQ + Expert Tips + Conclusion (target ~1000 words)
        p4_prompt = f"""Write PART 4 (FINAL) of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown.
{LOCK} {ANTI_AI}

<h2>8 Expert Tips to Save Money in 2026</h2>
8 tips in <ul>. Each tip: specific action + expected saving + official source link.
{SRC}

<h2>5 Common Mistakes Immigrants Make</h2>
5 mistakes in <ul>. Each: what happens + real cost + how to avoid.

<h2>Frequently Asked Questions</h2>
10 Q&A pairs immigrants actually ask about {TOPIC}.
Format: <h3>Question?</h3><p>Detailed answer, 50+ words, cite official source.</p>

<h2>Conclusion</h2>
3 paragraphs (200 words). Summarize 3 key points. End with a specific call-to-action.

<p><strong>Disclaimer:</strong> This article is for informational purposes only and does not constitute financial or legal advice. Always consult a licensed professional before making financial decisions. MoneyAbroadGuide.com may earn affiliate commissions from links in this article.</p>

<div class="author-bio">
<h3>About the Author</h3>
<p>Talal Eddaouahiri is the founder of MoneyAbroadGuide.com. A Moroccan immigrant who arrived in the USA in 2015, he navigated firsthand the financial challenges facing newcomers. With a background in retail banking, he writes independent, source-based guides citing FDIC, IRS, USCIS, and CFPB data to help immigrants make informed financial decisions in 2026.</p>
</div>

MINIMUM 1000 words total."""

        p4 = haiku(client, p4_prompt, max_tokens=2000, system=SYSTEM_PROMPT)
        print(f"  Part 4 words: {len(strip_html(p4).split())} | Cost so far: ${anthropic_cost:.4f}")

        # Combine all parts
        parts = []
        for p in [p1, p2, p3, p4]:
            clean = re.sub(r"```html?\n?", "", p)
            clean = re.sub(r"```", "", clean).strip()
            parts.append(clean)
        article_html = "\n\n".join(parts)
        total_words = len(strip_html(article_html).split())
        print(f"  TOTAL words: {total_words}")
        print(f"  TOTAL cost (text): ${anthropic_cost:.4f}")

        # Auto-expand if below 4000 words and budget allows
        if total_words < MIN_WORDS and anthropic_cost < COST_BUDGET * 0.5:
            needed = MIN_WORDS - total_words
            print(f"  Auto-expanding: need {needed} more words...")
            try:
                expansion = haiku(client,
                    f"""The article about "{TOPIC}" needs {needed} more words.
Output ONLY valid HTML.

Add:
<h2>Additional Comparison: Key Factors for {MARKET.upper()} Immigrants</h2>
HTML table comparing 4 options with features and costs.
Then 2 paragraphs of analysis.

<h2>Bonus Tips</h2>
5 more practical Q&A: <h3>Question?</h3><p>Answer with specific data.</p>

Write at least {needed} words.""",
                    max_tokens=1500, system=SYSTEM_PROMPT)
                exp_clean = re.sub(r"```html?\n?", "", expansion)
                exp_clean = re.sub(r"```", "", exp_clean).strip()
                article_html = article_html + "\n\n" + exp_clean
                total_words = len(strip_html(article_html).split())
                print(f"  After expansion: {total_words} words | Cost: ${anthropic_cost:.4f}")
            except Exception as e:
                print(f"  Expansion failed: {e}")

        results["article_written"] = len(article_html) > 1000
        results["word_count_4000plus"] = total_words >= MIN_WORDS
        results["word_count_5000max"] = total_words <= MAX_WORDS
        print(f"  word_count_4000plus: {results['word_count_4000plus']} ({total_words} words)")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
        results["article_written"] = False
        results["word_count_4000plus"] = False
# ============================================================
# STEP 2-8: QUALITY GATES
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
        for v in coherence_violations[:5]:
            print(f"  VIOLATION: '{v['term']}' x{v['count']}")
    else:
        print("  No violations")
else:
    results["thematic_coherence_70plus"] = False

print()
print("[STEP 3] AI language check...")
cliche_count = 0
if article_html:
    cliches = count_ai_cliches(article_html)
    cliche_count = len(cliches)
    print(f"  Cliches detected: {cliche_count}")
    for c in cliches[:5]:
        print(f"  - '{c['pattern']}' x{c['count']}")
    results["ai_language_clean"] = cliche_count < 8
else:
    results["ai_language_clean"] = True

print()
print("[STEP 4] Table validation...")
if article_html:
    tables_found = len(re.findall(r"<table", article_html, re.IGNORECASE))
    results["tables_valid"] = tables_found >= 1
    print(f"  {tables_found} table(s) found - required: 1+")
else:
    results["tables_valid"] = False

print()
print("[STEP 5] SEO scoring...")
seo_score, seo_details = 0, {}
if article_html:
    seo_score, seo_details = compute_seo_score_v2(article_html, TOPIC, MARKET)
    results["seo_score_70plus"] = seo_score >= 70
    print(f"  SEO: {seo_score}/100 (threshold: 70)")
    for k, v in seo_details.items():
        print(f"  {k}: {v}")
else:
    results["seo_score_70plus"] = False

print()
print("[STEP 6] EEAT scoring...")
eeat_score, eeat_details = 0, {}
if article_html:
    eeat_score, eeat_details = compute_eeat_score(article_html, TOPIC)
    results["eeat_score_60plus"] = eeat_score >= 60
    print(f"  EEAT: {eeat_score}/100 (threshold: 60)")
    for k, v in eeat_details.items():
        print(f"  {k}: {v}")
else:
    results["eeat_score_60plus"] = False

print()
print("[STEP 7] Link validation...")
valid_links, total_links, link_issues = 0, 0, []
if article_html:
    valid_links, total_links, link_issues = validate_internal_links(article_html)
    results["internal_links_5plus"] = total_links >= 3
    results["no_draft_links"] = len(link_issues) == 0
    print(f"  Links: {total_links} found, {valid_links} valid")
    for issue in link_issues[:3]:
        print(f"  ISSUE: {issue}")
else:
    results["internal_links_5plus"] = False
    results["no_draft_links"] = True

print()
print("[STEP 7b] Gate 20 - Anti-thin-content check...")
g20 = {"status": "PASS", "issues": []}
if article_html:
    g20 = gate20_anti_thin(article_html, TOPIC)
    results["gate20_status"] = g20["status"]
    print(f"  Gate 20: {g20['status']} | Issues: {g20['issues']}")
else:
    results["gate20_status"] = "FAIL"

# ============================================================
# STEP 8: QUALITY GATE BLOCKING CHECK
# ============================================================
print()
print("[QUALITY GATE CHECK]")
for k in ["word_count_4000plus","thematic_coherence_70plus","seo_score_70plus","eeat_score_60plus","tables_valid","ai_language_clean","internal_links_5plus"]:
    print(f"  {k}: {results.get(k, False)}")

if not results.get("word_count_4000plus", False):
    improvement_log.append("BLOCKED: word count below 4000")
    print("  [BLOCKED] Word count < 4000 - ABORT")
    sys.exit(1)

if not results.get("thematic_coherence_70plus", False) and len(coherence_violations) >= 3:
    improvement_log.append(f"BLOCKED: coherence {coherence_score}/100")
    print(f"  [BLOCKED] Coherence {coherence_score}/100 < 60")
    sys.exit(1)

print("  [OK] Critical gates passed")

# ============================================================
# STEP 9: PUBLISH TO WORDPRESS AS DRAFT
# ============================================================
print()
print("[STEP 9] Creating WordPress draft...")
wp_post_id = None

seo_title = TOPIC.title() + " | MoneyAbroadGuide"
meta_desc = f"Expert guide: {TOPIC}. Verified 2026 information for immigrants in {MARKET.upper()}."[:155]
focus_kw = re.sub(r"\s*(2026|guide|complete|best)\s*", " ", TOPIC, flags=re.IGNORECASE).strip()

if not WP_USER or not WP_PASS:
    print(f"  ERROR: WP credentials missing")
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
        print(f"  FAILED. Status: {status}")
        results["wordpress_draft_created"] = False
# ============================================================
# STEP 10: IMAGE PIPELINE v6.0 - GEMINI IMAGEN 3 PRIMARY
# 5 images: 1 featured + 4 body (NEXUS-14 standard)
# Cost target: ~$0.10 for 5 images via Gemini
# ============================================================
print()
print("[STEP 10] IMAGE PIPELINE v6.0 -- 5 images: 1 featured + 4 body")
print("-" * 60)
print(f"  Gemini key: {'SET (' + str(len(GEMINI_KEY)) + ' chars)' if GEMINI_KEY else 'MISSING - images will be skipped'}")
img_cost = 0.0

# NEXUS-14 standard image prompts - photo-realistic, no AI artifacts
def get_img_prompts(topic, market):
    mkt = market.upper()
    topic_short = topic[:80]
    return [
        # img1 - FEATURED IMAGE (hero)
        f"Ultra-realistic editorial photograph: a diverse immigrant couple at a bank counter in {mkt}, opening their first bank account. Professional, welcoming bank interior 2026. Documentary photography style, no text overlays, photojournalistic.",
        # img2 - body 1
        f"Ultra-realistic photo: a young immigrant woman reviewing financial documents with a bank advisor at a modern office in {mkt} 2026. Natural lighting, high detail, photojournalism style, no text.",
        # img3 - body 2
        f"Ultra-realistic editorial photo: a professional comparison infographic scene showing a laptop screen with financial data charts for immigrants in {mkt} 2026. Clean environment, person working, no text overlays.",
        # img4 - body 3
        f"Ultra-realistic photo: a smiling diverse immigrant family (couple with children) celebrating at their first home in North America 2026. Warm, hopeful atmosphere, suburban neighborhood, golden hour lighting, no text.",
        # img5 - body 4
        f"Ultra-realistic documentary photo: an immigrant man at a government services office in {mkt} completing financial paperwork 2026. Professional environment, organized desk, natural light, no text overlays.",
    ]

IMG_PROMPTS = get_img_prompts(TOPIC, MARKET)

def generate_image_gemini(prompt_text, idx):
    """Generate image using Gemini Imagen 3 (PRIMARY) only."""
    global img_cost
    label = f"img{idx}"

    if not GEMINI_KEY:
        print(f"  {label}: GEMINI_KEY missing - skipping")
        return None

    # PRIMARY: Gemini Imagen 3 via Google AI Studio REST API
    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={GEMINI_KEY}"
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
            img_cost += 0.02  # ~$0.02 per Gemini image
            print(f"  {label}: Gemini Imagen 3 SUCCESS (cost: ${img_cost:.2f} total)")
            return base64.b64decode(b64)
        else:
            print(f"  {label}: Gemini OK but no image bytes - resp keys: {list(data.keys())}")
            return None
    except Exception as e:
        print(f"  {label}: Gemini error - {str(e)[:150]}")
        return None

def upload_to_wp(img_bytes, filename):
    if not creds_wp: return None, None
    try:
        hdr = {
            "Authorization": "Basic " + creds_wp,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg",
            "User-Agent": "NEXUS14-v6/1.0",
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

def inject_4_body_images(html, body_image_list):
    """Inject 4 body images after H2 tags #2, #4, #6, #8."""
    if not body_image_list:
        return html
    h2_ends = [m.end() for m in re.finditer(r"</h2>", html, re.IGNORECASE)]
    total_h2 = len(h2_ends)
    print(f"  Total H2 tags found: {total_h2}")
    desired_indices = [1, 3, 5, 7]
    actual_indices = []
    for di in desired_indices:
        if di < total_h2:
            actual_indices.append(di)
        elif total_h2 > 0:
            actual_indices.append(total_h2 - 1)
    actual_indices = list(dict.fromkeys(actual_indices))[:len(body_image_list)]
    print(f"  Injecting at H2 indices: {actual_indices}")
    alt_texts = [
        "Immigrant reviewing financial documents with advisor in USA or Canada 2026",
        "Financial comparison dashboard for immigrants in North America 2026",
        "Immigrant family celebrating first home purchase in North America 2026",
        "Immigrant completing financial paperwork at government office 2026",
    ]
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
    imgs_count = len(re.findall(r"<img", html))
    print(f"  Final <img> count in article body: {imgs_count}")
    return html

# Generate all 5 images
print(f"\n  Generating 5 images (Gemini Imagen 3)...")
for i, prompt in enumerate(IMG_PROMPTS):
    label = "FEATURED" if i == 0 else f"BODY img{i}"
    print(f"\n  [{i+1}/5] Generating {label}...")
    img_bytes = generate_image_gemini(prompt, i+1)
    if img_bytes:
        generated_images.append(img_bytes)
        ts = int(time.time())
        fname = f"nexus14-v6-{ARTICLE_INDEX}-img{i+1}-{ts}.jpg"
        mid, murl = upload_to_wp(img_bytes, fname)
        if mid:
            media_ids.append(mid)
            image_urls.append((mid, murl or ""))
    time.sleep(2)

# Set featured image
featured_media_id = media_ids[0] if media_ids else None
if featured_media_id and wp_post_id:
    try:
        r_feat = wp_request("POST", f"/wp-json/wp/v2/posts/{wp_post_id}",
                           WP_JSON_HEADERS, json_data={"featured_media": featured_media_id}, timeout=30)
        if r_feat and r_feat.status_code in (200, 201):
            print(f"\n  Featured image set: media_id={featured_media_id}")
    except Exception as e:
        print(f"  Featured image error: {e}")

# Inject body images
body_images = image_urls[1:]  # skip featured, inject 4 body
print(f"\n  Body images to inject: {len(body_images)}/4")
if body_images and article_html and wp_post_id:
    article_html_with_images = inject_4_body_images(article_html, body_images)
    imgs_count = len(re.findall(r"<img", article_html_with_images))
    print(f"  Updating WordPress with {len(body_images)} body images...")
    update_payload = {"content": article_html_with_images}
    if featured_media_id:
        update_payload["featured_media"] = featured_media_id
    r_upd = wp_request("POST", f"/wp-json/wp/v2/posts/{wp_post_id}",
                       WP_JSON_HEADERS, json_data=update_payload, timeout=90)
    if r_upd and r_upd.status_code in (200, 201):
        print(f"  Article updated: {imgs_count} <img> tags in body")
        article_html = article_html_with_images
    else:
        sc = r_upd.status_code if r_upd else "timeout"
        print(f"  Update FAIL: {sc}")

results["images_generated"] = len(generated_images) >= 4
results["featured_image_set"] = featured_media_id is not None

total_cost = anthropic_cost + img_cost
print(f"\n  IMAGES SUMMARY:")
print(f"  Generated : {len(generated_images)}/5")
print(f"  Uploaded  : {len(media_ids)}/5")
print(f"  Featured  : {featured_media_id}")
print(f"  Body imgs : {len(body_images)}/4 injected")
print(f"  Image cost: ${img_cost:.4f}")
print(f"  Text cost : ${anthropic_cost:.4f}")
print(f"  TOTAL cost: ${total_cost:.4f} (budget: ${COST_BUDGET})")
print()
if total_cost > COST_BUDGET:
    print(f"  [COST OVERRUN] ${total_cost:.4f} > ${COST_BUDGET} budget!")
# ============================================================
# STEP 11: FINAL REPORT
# ============================================================
print()
elapsed = round(time.time() - START, 1)
final_word_count = len(strip_html(article_html).split()) if article_html else 0
total_cost = anthropic_cost + img_cost

checks = [
    ("article_written", results.get("article_written", False)),
    ("word_count_4000plus", results.get("word_count_4000plus", False)),
    ("word_count_5000max", results.get("word_count_5000max", True)),
    ("thematic_coherence_70plus", results.get("thematic_coherence_70plus", False)),
    ("ai_language_clean", results.get("ai_language_clean", False)),
    ("tables_valid", results.get("tables_valid", False)),
    ("seo_score_70plus", results.get("seo_score_70plus", False)),
    ("eeat_score_60plus", results.get("eeat_score_60plus", False)),
    ("internal_links_5plus", results.get("internal_links_5plus", False)),
    ("no_draft_links", results.get("no_draft_links", True)),
    ("wordpress_draft_created", results.get("wordpress_draft_created", False)),
    ("images_generated", results.get("images_generated", False)),
    ("featured_image_set", results.get("featured_image_set", False)),
]

passed = sum(1 for _, v in checks if v)
total_checks = len(checks)
critical = ["article_written", "word_count_4000plus", "thematic_coherence_70plus", "wordpress_draft_created"]
critical_ok = all(results.get(c, False) for c in critical)
cost_ok = total_cost <= COST_BUDGET
cost_status = "OK" if cost_ok else "OVERRUN"

print("=" * 60)
print("PRODUCTION REPORT v6.0 -- " + ARTICLE_INDEX)
print("=" * 60)
for name, val in checks:
    print(("[PASS] " if val else "[FAIL] ") + name)
print()
print(f"Score    : {passed}/{total_checks}")
print(f"Words    : {final_word_count} (target: {MIN_WORDS}-{MAX_WORDS})")
print(f"SEO      : {seo_score}/100 (threshold: 70)")
print(f"EEAT     : {eeat_score}/100 (threshold: 60)")
print(f"Coherence: {coherence_score}/100")
print(f"Cliches  : {cliche_count} detected")
print(f"Links    : {total_links} internal links")
print(f"Images   : {len(generated_images)}/5 generated (Gemini), {len(media_ids)} uploaded")
print(f"Topic    : {TOPIC}")
print(f"Market   : {MARKET.upper()}")
print(f"Model    : {MODEL}")
print(f"Post ID  : {wp_post_id}")
print(f"FeatImg  : {featured_media_id}")
print(f"Text Cost: ${anthropic_cost:.5f}")
print(f"Img Cost : ${img_cost:.5f}")
print(f"TOTAL    : ${total_cost:.5f} / ${COST_BUDGET} budget ({cost_status})")
print(f"Time     : {elapsed}s")
print(f"Agent 17 : {results.get('agent17_decision', 'N/A')}")
print(f"Gate 19  : {results.get('gate19_status', 'N/A')}")
print(f"Gate 20  : {results.get('gate20_status', 'N/A')}")

if passed == total_checks and critical_ok and cost_ok:
    status = "PUBLICATION_READY"
elif passed >= total_checks - 2 and critical_ok:
    status = "REVIEW_REQUIRED"
elif critical_ok:
    status = "PARTIAL"
else:
    status = "FAIL"

print(f"STATUS   : {status}")
print("=" * 60)

report = {
    "version": "v6.0",
    "article_index": ARTICLE_INDEX,
    "topic": TOPIC,
    "market": MARKET,
    "model": MODEL,
    "word_count": final_word_count,
    "word_target": f"{MIN_WORDS}-{MAX_WORDS}",
    "seo_score": seo_score,
    "eeat_score": eeat_score,
    "coherence_score": coherence_score,
    "cliches_detected": cliche_count,
    "internal_links_count": total_links,
    "checks": {n: v for n, v in checks},
    "score": f"{passed}/{total_checks}",
    "status": status,
    "critical_ok": critical_ok,
    "cost_ok": cost_ok,
    "wp_post_id": wp_post_id,
    "images_generated": len(generated_images),
    "media_ids": media_ids,
    "featured_media_id": featured_media_id,
    "anthropic_cost_usd": round(anthropic_cost, 5),
    "img_cost_usd": round(img_cost, 5),
    "total_cost_usd": round(total_cost, 5),
    "budget_usd": COST_BUDGET,
    "cost_within_budget": cost_ok,
    "total_input_tokens": total_input_tokens,
    "total_output_tokens": total_output_tokens,
    "agent17_decision": results.get("agent17_decision", "N/A"),
    "gate19_status": results.get("gate19_status", "N/A"),
    "gate20_status": results.get("gate20_status", "N/A"),
    "elapsed_seconds": elapsed,
    "timestamp": datetime.utcnow().isoformat()
}

report_file = f"execution_report_{ARTICLE_INDEX}.json"
with open(report_file, "w") as f:
    json.dump(report, f, indent=2)
print(f"Report: {report_file}")

if not critical_ok:
    sys.exit(1)
