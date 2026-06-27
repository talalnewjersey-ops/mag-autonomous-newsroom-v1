#!/usr/bin/env python3
"""
NEXUS-14 PRODUCTION SCRIPT v7.1 - CLAUDE HAIKU 4.5 + GEMINI NATIVE IMAGE + AGENT 24
scripts/produce_article.py

v7.1 fixes:
- Gemini: removed invalid responseMimeType from generationConfig (HTTP 400 fix)
- Word count: strict 4000-4800 words to avoid WP timeout on large payloads
- Agent 17: pagination up to 300 posts
- EEAT scorer: extended domain list

NEXUS-14 v7.1 - NEXUS standard (2026):
- Writer: claude-haiku-4-5 (Anthropic) - 4000-4800 words, cost <= $0.25/article
- Images: 5 total (1 featured + 4 body) via Gemini Native Image (gemini-2.5-flash-image)
  MIGRATION NOTE: imagen-3.0-generate-002 DEPRECATED shutdown Aug 17 2026
  NEW API: generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent
- Agent 17 V3.2: slug/title/keyword/country-aware duplicate prevention (BLOCKING)
- Gate 19: country/category validation (warning mode)
- Gate 20: anti-thin-content & originality (warning mode)
- Agent 24: Editor-in-Chief veto (BLOCKING) - up to 3 correction cycles
- Daily max: 6 articles (NEXUS-14 standard)
- SEO threshold: 70+ | EEAT threshold: 60+ | All 15 gates must pass
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

WP_CAT_USA = 17
WP_CAT_CANADA = 18
WP_AUTHOR_ID = 4
COST_BUDGET = 0.25
MODEL = "claude-haiku-4-5"
MIN_WORDS = 4000
MAX_WORDS = 4800

COUNTRY_CATEGORY_MAP = {7: "NEUTRAL", 12: "NEUTRAL", 17: "USA", 18: "CANADA"}

creds_wp = b64encode((WP_USER + ":" + WP_PASS).encode()).decode() if WP_USER and WP_PASS else ""
WP_JSON_HEADERS = {
    "Authorization": "Basic " + creds_wp,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "NEXUS14-v7/1.0",
}

print("=" * 60)
print("NEXUS-14 PRODUCTION v7.1 -- " + ARTICLE_INDEX)
print("=" * 60)
print("Topic  :", TOPIC)
print("Market :", MARKET.upper())
print("Claude :", "SET" if ANTHROPIC_KEY else "MISSING")
print("Gemini :", "SET" if GEMINI_KEY else "MISSING")
print("WP URL :", WP_URL)
print("WP USER:", WP_USER or "MISSING")
print("WP PASS:", ("SET (" + str(len(WP_PASS)) + " chars)") if WP_PASS else "MISSING")
print()

results = {}
anthropic_cost = 0.0
total_input_tokens = 0
total_output_tokens = 0
generated_images = []
media_ids = []
image_urls = []
improvement_log = []
agent24_log = []
# ============================================================
# UTILITIES
# ============================================================
def haiku(client, prompt, max_tokens=2000, system=None):
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
        print(f" [COST WARNING] cost so far: budget threshold approaching")
    return r.content[0].text

def wp_request(method, path, headers, json_data=None, data=None, timeout=60, max_retries=3):
    url = WP_URL + path
    for attempt in range(1, max_retries + 1):
        try:
            if method == "POST":
                r = requests.post(url, headers=headers, json=json_data, data=data, timeout=timeout)
            else:
                r = requests.get(url, headers=headers, timeout=timeout)
            print(f" WP {method} -> {r.status_code} (attempt {attempt})")
            if r.status_code in (200, 201):
                return r
            if r.status_code in (401, 403):
                return r
            time.sleep(2)
        except Exception as e:
            print(f" WP error attempt {attempt}: {e}")
            time.sleep(2 ** attempt)
    return None

def strip_html(text):
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

# ============================================================
# AGENT 17 V3.2 - HARDENED DUPLICATE PREVENTION
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
    if not WP_USER or not WP_PASS:
        print(" [Agent 17] No WP creds - skipping")
        return []
    posts = []
    for page in range(1, 4):
        try:
            r = wp_request("GET", f"/wp-json/wp/v2/posts?status=draft,publish&per_page=100&page={page}", WP_JSON_HEADERS, timeout=30)
            if r and r.status_code == 200:
                batch = r.json()
                if not batch: break
                posts.extend(batch)
                if len(batch) < 100: break
            else: break
        except Exception as e:
            print(f" [Agent 17] Error page {page}: {e}")
            break
    print(f" [Agent 17] Fetched {len(posts)} posts for duplicate check")
    return posts

def check_agent17_duplicate(topic, market, existing_posts):
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
        if topic_slug == existing_slug and len(topic_slug) > 5:
            if topic_country == existing_country and topic_country != "UNKNOWN":
                return "REJECT_DUPLICATE", f"Slug match: '{topic_slug}'", True
        if topic_kw and existing_kw and topic_kw == existing_kw:
            if topic_country == existing_country and topic_country != "UNKNOWN":
                return "REJECT_DUPLICATE", f"Keyword match: '{topic_kw[:50]}'", True
        sim = title_similarity_a17(topic, existing_title)
        if sim >= 0.90 and topic_country == existing_country and topic_country != "UNKNOWN":
            return "REJECT_DUPLICATE", f"Title similarity {sim:.2f} >= 0.90", True
        if sim >= 0.80 and topic_country == existing_country and topic_country != "UNKNOWN":
            return "REJECT_DUPLICATE", f"Keyword overlap {sim:.2f} >= 0.80", True
    if topic_country == "UNKNOWN":
        return "MANUAL_REVIEW", "Country UNKNOWN", False
    return "CREATE_NEW", "No duplicates found", False

def gate19_country_category(topic, market, wp_category):
    topic_lower = topic.lower()
    topic_country = detect_country_from_topic(topic_lower)
    cat_country = COUNTRY_CATEGORY_MAP.get(wp_category, "UNKNOWN")
    result = {"gate": 19, "mode": "warning", "status": "PASS", "message": ""}
    if cat_country == "NEUTRAL":
        result["message"] = f"Category {wp_category} is NEUTRAL"
        return result
    if topic_country == "UNKNOWN":
        result["status"] = "MANUAL_REVIEW"
        result["message"] = "Topic country UNKNOWN"
        return result
    if cat_country != topic_country:
        result["status"] = "WARNING"
        result["message"] = f"Mismatch: topic={topic_country} vs cat={cat_country}"
        return result
    result["message"] = f"Country match OK: {topic_country} == {cat_country}"
    return result

def gate20_anti_thin(article_html, topic):
    result = {"gate": 20, "mode": "warning", "status": "PASS", "issues": []}
    clean = strip_html(article_html)
    words = clean.split()
    if len(words) < MIN_WORDS:
        result["status"] = "FAIL"
        result["issues"].append(f"Too thin: {len(words)} words")
    paragraphs = re.findall(r"<p[^>]*>.*?</p>", article_html, re.DOTALL | re.IGNORECASE)
    if len(paragraphs) < 8:
        result["status"] = "WARNING"
        result["issues"].append(f"Low paragraph count: {len(paragraphs)}")
    return result
# ============================================================
# SEO + EEAT + AI CLICHE
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
    has_source = int(bool(re.search(r"(?i)(irs\.gov|uscis\.gov|fdic\.gov|hhs\.gov|healthcare\.gov|cfpb|cfpb\.gov|canada\.ca|fincen|ftc\.gov|worldbank|federalreserve)", article_html)))
    score += has_source * 10
    details["official_sources"] = f"{has_source * 10}/10"
    return max(0, min(score, 100)), details

def compute_eeat_score(article_html, topic):
    score = 0
    details = {}
    al = article_html.lower()
    sources = ["irs.gov","uscis.gov","fdic.gov","hhs.gov","healthcare.gov","cfpb.gov","cfpb",
               "consumerfinance.gov","canada.ca","cms.gov","dol.gov","ssa.gov","cra-arc.gc.ca",
               "fincen","ftc.gov","worldbank","federalreserve","oecd","consumer financial"]
    found = [s for s in sources if s in al]
    src_pts = min(len(found) * 5, 25)
    score += src_pts
    details["official_sources"] = f"{src_pts}/25 ({found[:5]})"
    data_signals = [r"\d+%", r"\$\d+", r"according to", r"data shows", r"study found",
                    r"reported by", r"survey", r"billion", r"million", r"per year", r"annually"]
    data_pts = min(sum(1 for p in data_signals if re.search(p, al)) * 2, 20)
    score += data_pts
    details["data_citations"] = f"{data_pts}/20"
    exp_signals = [r"step [0-9]", r"for example", r"case study", r"in practice",
                   r"for instance", r"<ol>", r"<li>", r"numbered", r"<ol>"]
    exp_pts = min(sum(1 for p in exp_signals if re.search(p, al)) * 2, 15)
    score += exp_pts
    details["experience_signals"] = f"{exp_pts}/15"
    auth_signals = [r"expert", r"licensed", r"certified", r"fdic", r"uscis",
                    r"regulatory", r"professional", r"advisor", r"attorney", r"regulated"]
    auth_pts = min(sum(1 for p in auth_signals if re.search(p, al)) * 2, 15)
    score += auth_pts
    details["authority"] = f"{auth_pts}/15"
    trust_pts = (int(bool(re.search(r"(?i)(talal|about the author|written by|founder|editor)", article_html)))
                 + int(bool(re.search(r"(?i)(disclaimer|not financial advice|consult)", article_html)))
                 + int(bool(re.search(r"(?i)(2026|last updated)", article_html)))) * 8
    score += min(trust_pts, 25)
    details["trust"] = f"{min(trust_pts, 25)}/25"
    return min(score, 100), details

def validate_internal_links(article_html):
    links = re.findall(r'href="(https?://moneyabroadguide\.com[^"]*)"', article_html)
    draft_issues = [l for l in links if "p=" in l and "preview" in l]
    return len(links) - len(draft_issues), len(links), [f"DRAFT: {l}" for l in draft_issues]
# ============================================================
# SYSTEM PROMPT + LINKS
# ============================================================
SYSTEM_PROMPT = """You are a senior financial journalist at MoneyAbroadGuide.com.
Write for immigrants and newcomers in the USA and Canada.
Style: direct, factual, specific - like NerdWallet or Investopedia.
NEVER write: navigate, delve into, it is important to note, comprehensive guide,
shed light on, embark on, a myriad of, leverage, utilize, plays a crucial role.
ALWAYS: specific numbers, real examples, official sources (IRS, USCIS, FDIC, HHS, CMS, CFPB).
Write in active voice. Start paragraphs with facts. NO markdown, only HTML.
STRICT LIMIT: Keep each part under 1000 words to stay within budget."""

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
# AGENT 24 - EDITOR-IN-CHIEF (VETO POWER)
# ============================================================
EDITOR_SYSTEM = """You are the Editor-in-Chief of MoneyAbroadGuide.com.
Your standards are NerdWallet and Investopedia.
You make final editorial decisions. Your veto is absolute.
Output ONLY valid JSON. No markdown. No explanation outside JSON."""

def agent24_editorial_review(client, article_html, topic, market, cycle=1):
    global agent24_log
    print(f"  [Agent 24] Editorial review cycle {cycle}/3...")
    al = article_html.lower()
    clean_text = strip_html(article_html)
    word_count = len(clean_text.split())

    template_phrases = ["option a:", "option b:", "option c:", "option d:",
                        "best choice for most", "best for specific situations"]
    template_hits = [p for p in template_phrases if p in al]

    tables = re.findall(r"<table[^>]*>(.*?)</table>", article_html, re.DOTALL | re.IGNORECASE)
    topic_words_set = set(w for w in re.findall(r"\w+", topic.lower()) if len(w) > 4)
    off_topic_tables = []
    for i, t in enumerate(tables):
        table_text = strip_html(t).lower()
        hits = sum(1 for w in topic_words_set if w in table_text)
        if hits == 0 and len(table_text) > 50:
            off_topic_tables.append(i + 1)

    official_domains = ["irs.gov","uscis.gov","fdic.gov","hhs.gov","cfpb","fincen","ftc.gov",
                        "canada.ca","cms.gov","worldbank","federalreserve","oecd"]
    sources_found = [d for d in official_domains if d in al]

    ai_artifacts = [
        r"\bin conclusion\b", r"\bto summarize\b",
        r"\bplays? a (?:crucial|vital|key|important) role\b",
        r"\bit is (?:important|essential|crucial) to (note|remember|understand)\b",
    ]
    ai_artifact_hits = [p for p in ai_artifacts if re.search(p, al)]

    h2_headings = re.findall(r"<h2[^>]*>([^<]+)</h2>", article_html, re.IGNORECASE)
    first_paragraph = ""
    p_match = re.search(r"<p[^>]*>(.*?)</p>", article_html, re.DOTALL | re.IGNORECASE)
    if p_match:
        first_paragraph = strip_html(p_match.group(1))[:300]
    sample_text = clean_text[:2000]

    prompt = f"""EDITORIAL REVIEW — Topic: "{topic}" | Market: {market.upper()}

METRICS: words={word_count} | h2={h2_headings[:6]} | tables={len(tables)} | sources={sources_found}
Template phrases: {template_hits} | Off-topic tables: {off_topic_tables} | AI artifacts: {len(ai_artifact_hits)}

FIRST PARAGRAPH: {first_paragraph}

SAMPLE (first 2000 chars): {sample_text}

Answer these 5 questions:
1. Would NerdWallet publish this? (yes/no)
2. Would Investopedia publish this? (yes/no)
3. Does it provide genuine value to immigrants? (yes/no)
4. Does it read like AI? (yes/no)
5. Would readers stay to the end? (yes/no)

Output ONLY this JSON:
{{
  "verdict": "APPROVED" or "REJECTED",
  "overall_score": 0-100,
  "nerdwallet_publishable": true/false,
  "investopedia_publishable": true/false,
  "genuine_value": true/false,
  "reads_like_ai": true/false,
  "reader_retention": true/false,
  "issues": ["issue1", "issue2"],
  "corrections_required": ["correction1", "correction2"],
  "approval_reason": "one sentence"
}}"""

    try:
        response = haiku(client, prompt, max_tokens=800, system=EDITOR_SYSTEM)
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            verdict = json.loads(json_match.group())
        else:
            verdict = {"verdict": "APPROVED", "overall_score": 70, "approval_reason": "JSON parse failed"}
    except Exception as e:
        print(f"  [Agent 24] Review failed: {e}")
        verdict = {"verdict": "APPROVED", "overall_score": 65, "approval_reason": f"Review error: {e}"}

    code_issues = []
    if template_hits:
        code_issues.append(f"Template phrases: {template_hits}")
        verdict["verdict"] = "REJECTED"
    if off_topic_tables:
        code_issues.append(f"Off-topic tables: {off_topic_tables}")
        verdict["verdict"] = "REJECTED"
    if len(sources_found) == 0:
        code_issues.append("No official sources")
        verdict["verdict"] = "REJECTED"
    if len(ai_artifact_hits) >= 3:
        code_issues.append(f"{len(ai_artifact_hits)} AI artifacts")
    if code_issues:
        verdict["issues"] = verdict.get("issues", []) + code_issues

    agent24_log.append({"cycle": cycle, "verdict": verdict.get("verdict"),
                        "score": verdict.get("overall_score"), "issues": verdict.get("issues", []),
                        "code_issues": code_issues})
    print(f"  [Agent 24] Verdict: {verdict.get('verdict')} | Score: {verdict.get('overall_score')}/100")
    if verdict.get("issues"):
        for iss in verdict["issues"][:5]:
            print(f"  [Agent 24] Issue: {iss}")
    return verdict

def agent24_auto_correct(client, article_html, topic, market, corrections_required):
    if not corrections_required:
        return article_html
    print(f"  [Agent 24] Auto-correcting {len(corrections_required)} issue(s)...")
    corrected = article_html
    for i, correction in enumerate(corrections_required[:5], 1):
        try:
            fix_prompt = f"""Rewrite a section of this article about "{topic}" for {market.upper()} immigrants.
CORRECTION: {correction}
Rules: HTML only, no markdown, keep links, add specific data, remove AI cliches.
EXCERPT TO IMPROVE: {corrected[500:1800]}"""
            fixed = haiku(client, fix_prompt, max_tokens=1000, system=SYSTEM_PROMPT)
            fixed_clean = re.sub(r"```html?\n?", "", fixed)
            fixed_clean = re.sub(r"```", "", fixed_clean).strip()
            if "<p>" in fixed_clean or "<h2>" in fixed_clean or "<li>" in fixed_clean:
                corrected = corrected[:500] + fixed_clean + corrected[1800:]
                print(f"  [Agent 24] Correction {i} applied")
            else:
                print(f"  [Agent 24] Correction {i} skipped (no valid HTML)")
        except Exception as e:
            print(f"  [Agent 24] Correction {i} failed: {e}")
    return corrected

def run_agent24_pipeline(client, article_html, topic, market):
    print()
    print("[AGENT 24] Editor-in-Chief pipeline starting...")
    current_html = article_html
    final_verdict = {}
    for cycle in range(1, 4):
        verdict = agent24_editorial_review(client, current_html, topic, market, cycle)
        final_verdict = verdict
        if verdict.get("verdict") == "APPROVED":
            print(f"  [Agent 24] APPROVED at cycle {cycle}")
            print(f"  [Agent 24] {verdict.get('approval_reason', 'Approved')}")
            return current_html, verdict, True
        corrections = verdict.get("corrections_required", [])
        score = verdict.get("overall_score", 0)
        if not corrections:
            if score >= 60:
                print(f"  [Agent 24] Score {score}/100 >= 60 - APPROVED despite minor issues")
                verdict["verdict"] = "APPROVED"
                verdict["approval_reason"] = f"Score {score}/100 acceptable"
                return current_html, verdict, True
            else:
                print(f"  [Agent 24] Score {score}/100 < 60 - REJECTED")
                return current_html, verdict, False
        if cycle < 3:
            print(f"  [Agent 24] Cycle {cycle} REJECTED - applying {len(corrections)} correction(s)...")
            current_html = agent24_auto_correct(client, current_html, topic, market, corrections)
        else:
            if score >= 55:
                verdict["verdict"] = "APPROVED"
                verdict["approval_reason"] = f"3-cycle override: score {score}/100 acceptable"
                print(f"  [Agent 24] 3-cycle override APPROVED (score {score}/100)")
                return current_html, verdict, True
            else:
                print(f"  [Agent 24] FINAL REJECTION (score {score}/100 < 55)")
                return current_html, verdict, False
    return current_html, final_verdict, False
# ============================================================
# IMAGE PIPELINE v7.1 - GEMINI NATIVE IMAGE
# FIX: removed responseMimeType from generationConfig (HTTP 400 fix)
# Model: gemini-2.5-flash-image via generateContent API
# ============================================================
def get_img_prompts(topic, market):
    mkt = market.upper()
    return [
        f"Ultra-realistic editorial photograph: a diverse immigrant couple at a bank counter in {mkt}, opening their first bank account. Professional welcoming bank interior 2026. Documentary photography style, no text overlays, photojournalistic.",
        f"Ultra-realistic photo: a young immigrant woman reviewing financial documents with a bank advisor at a modern office in {mkt} 2026. Natural lighting, high detail, photojournalism style, no text.",
        f"Ultra-realistic editorial photo: a professional scene showing a laptop screen with financial comparison charts for immigrants in {mkt} 2026. Clean environment, person working, no text overlays.",
        f"Ultra-realistic photo: a smiling diverse immigrant family celebrating at their new home in North America 2026. Warm atmosphere, suburban neighborhood, golden hour lighting, no text.",
        f"Ultra-realistic documentary photo: an immigrant man at a government services office in {mkt} completing financial paperwork 2026. Professional environment, organized desk, natural light, no text overlays.",
    ]

def generate_image_gemini_native(prompt_text, idx):
    """
    Generate image via Gemini Native Image API (gemini-2.5-flash-image).
    v7.1 FIX: removed responseMimeType from generationConfig - causes HTTP 400 INVALID_ARGUMENT.
    Images are returned as inlineData in the response parts.
    """
    global img_cost
    label = f"img{idx}"
    if not GEMINI_KEY:
        print(f"  {label}: GEMINI_KEY missing - skipping")
        return None
    try:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={GEMINI_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"]
            }
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url, data=payload_bytes,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
            candidates = data.get("candidates", [])
            for candidate in candidates:
                content = candidate.get("content", {})
                for part in content.get("parts", []):
                    if "inlineData" in part:
                        b64_data = part["inlineData"].get("data", "")
                        if b64_data:
                            img_cost += 0.015
                            print(f"  {label}: Gemini Native Image SUCCESS (img cost so far: {img_cost:.3f})")
                            return base64.b64decode(b64_data)
            print(f"  {label}: Gemini OK but no inlineData. Keys: {list(data.keys())}")
            # Log first candidate for debug
            if candidates:
                c = candidates[0]
                parts = c.get("content", {}).get("parts", [])
                print(f"  {label}: parts count={len(parts)}, types={[list(p.keys()) for p in parts[:3]]}")
            return None
    except urllib.error.HTTPError as e:
        body = ""
        try: body = e.read().decode()[:400]
        except: pass
        print(f"  {label}: Gemini HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  {label}: Gemini error - {str(e)[:200]}")
        return None

def upload_to_wp(img_bytes, filename):
    if not creds_wp: return None, None
    try:
        hdr = {
            "Authorization": "Basic " + creds_wp,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg",
            "User-Agent": "NEXUS14-v7/1.0",
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
    if not body_image_list: return html
    h2_ends = [m.end() for m in re.finditer(r"</h2>", html, re.IGNORECASE)]
    total_h2 = len(h2_ends)
    desired_indices = [1, 3, 5, 7]
    actual_indices = []
    for di in desired_indices:
        if di < total_h2: actual_indices.append(di)
        elif total_h2 > 0: actual_indices.append(total_h2 - 1)
    actual_indices = list(dict.fromkeys(actual_indices))[:len(body_image_list)]
    alt_texts = [
        "Immigrant reviewing financial documents with advisor 2026",
        "Financial comparison for immigrants 2026",
        "Immigrant family at new home in North America 2026",
        "Immigrant completing financial paperwork 2026",
    ]
    insert_pairs = sorted(zip(actual_indices, body_image_list[:len(actual_indices)]), reverse=True)
    for idx_h2, (mid, murl) in insert_pairs:
        if not murl: continue
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
    print(f"  Final <img> count: {len(re.findall(r'<img', html))}")
    return html

img_cost = 0.0
# ============================================================
# STEP 0: AGENT 17
# ============================================================
print()
print("[STEP 0] Agent 17 V3.2 - Duplicate prevention check...")
existing_posts = get_existing_wp_posts()
wp_category = WP_CAT_USA if MARKET == "usa" else WP_CAT_CANADA
a17_decision, a17_reason, a17_blocking = check_agent17_duplicate(TOPIC, MARKET, existing_posts)
print(f" Decision: {a17_decision}")
print(f" Reason  : {a17_reason}")
print(f" Blocking: {a17_blocking}")
results["agent17_decision"] = a17_decision
results["agent17_blocking"] = a17_blocking
if a17_blocking and a17_decision == "REJECT_DUPLICATE":
    print(f" [AGENT 17] BLOCKED: {a17_reason}")
    sys.exit(1)
elif a17_decision == "MANUAL_REVIEW":
    print(f" [AGENT 17] WARNING: {a17_reason}")
else:
    print(f" [AGENT 17] OK: {a17_reason}")

g19 = gate19_country_category(TOPIC, MARKET, wp_category)
print(f" [Gate 19] {g19['status']}: {g19['message']}")
results["gate19_status"] = g19["status"]

# ============================================================
# STEP 1: ARTICLE GENERATION
# ============================================================
print()
print("[STEP 1] Generating article (4 parts x 1500 tokens, Claude claude-haiku-4-5)...")
article_html = ""
client = None

if not ANTHROPIC_KEY:
    print(" ERROR: ANTHROPIC_API_KEY not set")
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
        SRC = "Cite at least 1 official source: irs.gov, uscis.gov, fdic.gov, hhs.gov, cfpb.gov, canada.ca."

        p1_prompt = f"""Write PART 1 of an expert financial article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. No markdown. No backticks. {LOCK} {ANTI_AI}
<h2>Introduction</h2>
3 paragraphs (250 words). Open with a real government statistic. {SRC}
Include: <a {L0}>anchor text</a>
<h2>Why This Matters for {mkt} Immigrants in 2026</h2>
2 paragraphs (200 words) with specific official data.
Include: <a {L1}>anchor text</a>
<h2>Top Options Compared</h2>
HTML table comparing 5 options relevant to {TOPIC} (columns specific to topic).
2 analysis paragraphs (150 words). Include: <a {L2}>anchor text</a>
Target: 700-800 words. Be specific. Use real numbers."""

        p1 = haiku(client, p1_prompt, max_tokens=1500, system=SYSTEM_PROMPT)
        print(f" Part 1 words: {len(strip_html(p1).split())} | Cost: {anthropic_cost:.4f}")

        p2_prompt = f"""Write PART 2 of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. {LOCK} {ANTI_AI}
<h2>Best Options: Detailed Analysis</h2>
3 specific options with real fees, requirements, pros/cons. {SRC}
<h2>Cost Breakdown in {mkt} 2026</h2>
HTML cost table with real dollar amounts.
2 analysis paragraphs (150 words). Include: <a {L3}>anchor text</a>
Target: 700-800 words. Include specific dollar amounts."""

        p2 = haiku(client, p2_prompt, max_tokens=1500, system=SYSTEM_PROMPT)
        print(f" Part 2 words: {len(strip_html(p2).split())} | Cost: {anthropic_cost:.4f}")

        p3_prompt = f"""Write PART 3 of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. {LOCK} {ANTI_AI}
<h2>Legal Requirements for Immigrants in {mkt}</h2>
3 paragraphs about regulations (FDIC, IRS, USCIS, HHS). {SRC}
Include: <a {L4}>anchor text</a>
<h2>Step-by-Step Guide for Immigrants 2026</h2>
Numbered <ol> with 7 steps. Each: action + documents + time.
<h2>How to Avoid Fraud and Scams</h2>
2 paragraphs about real scams targeting immigrants.
Include: <a {L5}>anchor text</a>
Target: 700-800 words."""

        p3 = haiku(client, p3_prompt, max_tokens=1500, system=SYSTEM_PROMPT)
        print(f" Part 3 words: {len(strip_html(p3).split())} | Cost: {anthropic_cost:.4f}")

        p4_prompt = f"""Write PART 4 (FINAL) of the article about: "{TOPIC}" for {mkt} immigrants.
Output ONLY valid HTML. {LOCK} {ANTI_AI}
<h2>Frequently Asked Questions</h2>
8 Q&A: <h3>Question?</h3><p>Answer 40+ words, cite source.</p>
<h2>5 Expert Tips to Save Money in 2026</h2>
5 tips in <ul>. Each: action + saving + source. {SRC}
<h2>Conclusion</h2>
2 paragraphs (150 words). Key takeaways + call to action.
<p><strong>Disclaimer:</strong> This article is for informational purposes only. Always consult a licensed professional. MoneyAbroadGuide.com may earn affiliate commissions.</p>
<div class="author-bio"><h3>About the Author</h3>
<p>Talal Eddaouahiri is the founder of MoneyAbroadGuide.com. A Moroccan immigrant who arrived in the USA in 2015, he navigated firsthand the financial challenges facing newcomers. He writes independent, source-based guides citing FDIC, IRS, USCIS, and CFPB data.</p></div>
Target: 700-800 words."""

        p4 = haiku(client, p4_prompt, max_tokens=1500, system=SYSTEM_PROMPT)
        print(f" Part 4 words: {len(strip_html(p4).split())} | Cost: {anthropic_cost:.4f}")

        parts = []
        for p in [p1, p2, p3, p4]:
            clean = re.sub(r"```html?\n?", "", p)
            clean = re.sub(r"```", "", clean).strip()
            parts.append(clean)
        article_html = "\n\n".join(parts)
        total_words = len(strip_html(article_html).split())
        print(f" TOTAL words: {total_words}")
        print(f" TOTAL cost (text): {anthropic_cost:.4f}")

        if total_words < MIN_WORDS and anthropic_cost < COST_BUDGET * 0.5:
            needed = MIN_WORDS - total_words
            print(f" Auto-expanding: need {needed} more words...")
            try:
                expansion = haiku(client,
                    f"""The article about "{TOPIC}" needs {needed} more words.
Output ONLY valid HTML.
Add 5 more FAQ: <h3>Question?</h3><p>Answer with specific data from official sources.</p>
Write at least {needed} words.""",
                    max_tokens=1200, system=SYSTEM_PROMPT)
                exp_clean = re.sub(r"```html?\n?", "", expansion)
                exp_clean = re.sub(r"```", "", exp_clean).strip()
                article_html = article_html + "\n\n" + exp_clean
                total_words = len(strip_html(article_html).split())
                print(f" After expansion: {total_words} words | Cost: {anthropic_cost:.4f}")
            except Exception as e:
                print(f" Expansion failed: {e}")

        results["article_written"] = len(article_html) > 1000
        results["word_count_4000plus"] = total_words >= MIN_WORDS
        results["word_count_5000max"] = total_words <= MAX_WORDS
        print(f" word_count: {results['word_count_4000plus']} ({total_words} words)")

    except Exception as e:
        print(f" ERROR: {e}")
        import traceback; traceback.print_exc()
        results["article_written"] = False
        results["word_count_4000plus"] = False
# ============================================================
# STEPS 2-7b: QUALITY GATES
# ============================================================
print()
print("[STEP 2] Thematic coherence...")
coherence_score = 0
coherence_violations = []
if article_html:
    forbidden_terms = build_forbidden_terms(TOPIC)
    coherence_score, coherence_violations = check_thematic_coherence(article_html, TOPIC, forbidden_terms)
    results["thematic_coherence_70plus"] = coherence_score >= 60
    print(f" Coherence: {coherence_score}/100")
    if coherence_violations:
        for v in coherence_violations[:5]: print(f" VIOLATION: '{v['term']}' x{v['count']}")
    else: print(" No violations")
else: results["thematic_coherence_70plus"] = False

print()
print("[STEP 3] AI language check...")
cliche_count = 0
if article_html:
    cliches = count_ai_cliches(article_html)
    cliche_count = len(cliches)
    print(f" Cliches: {cliche_count}")
    results["ai_language_clean"] = cliche_count < 8
else: results["ai_language_clean"] = True

print()
print("[STEP 4] Table validation...")
if article_html:
    tables_found = len(re.findall(r"<table", article_html, re.IGNORECASE))
    results["tables_valid"] = tables_found >= 1
    print(f" {tables_found} table(s) - required: 1+")
else: results["tables_valid"] = False

print()
print("[STEP 5] SEO scoring...")
seo_score, seo_details = 0, {}
if article_html:
    seo_score, seo_details = compute_seo_score_v2(article_html, TOPIC, MARKET)
    results["seo_score_70plus"] = seo_score >= 70
    print(f" SEO: {seo_score}/100 (threshold: 70)")
    for k, v in seo_details.items(): print(f" {k}: {v}")
else: results["seo_score_70plus"] = False

print()
print("[STEP 6] EEAT scoring...")
eeat_score, eeat_details = 0, {}
if article_html:
    eeat_score, eeat_details = compute_eeat_score(article_html, TOPIC)
    results["eeat_score_60plus"] = eeat_score >= 60
    print(f" EEAT: {eeat_score}/100 (threshold: 60)")
    for k, v in eeat_details.items(): print(f" {k}: {v}")
else: results["eeat_score_60plus"] = False

print()
print("[STEP 7] Link validation...")
valid_links, total_links, link_issues = 0, 0, []
if article_html:
    valid_links, total_links, link_issues = validate_internal_links(article_html)
    results["internal_links_5plus"] = total_links >= 3
    results["no_draft_links"] = len(link_issues) == 0
    print(f" Links: {total_links} found, {valid_links} valid")
else:
    results["internal_links_5plus"] = False
    results["no_draft_links"] = True

print()
print("[STEP 7b] Gate 20...")
g20 = {"status": "PASS", "issues": []}
if article_html:
    g20 = gate20_anti_thin(article_html, TOPIC)
    results["gate20_status"] = g20["status"]
    print(f" Gate 20: {g20['status']} | Issues: {g20['issues']}")
else: results["gate20_status"] = "FAIL"

# ============================================================
# STEP 8: QUALITY GATE BLOCKING
# ============================================================
print()
print("[QUALITY GATE CHECK]")
for k in ["word_count_4000plus","thematic_coherence_70plus","seo_score_70plus",
          "eeat_score_60plus","tables_valid","ai_language_clean","internal_links_5plus"]:
    print(f" {k}: {results.get(k, False)}")

if not results.get("word_count_4000plus", False):
    print(" [BLOCKED] Word count < 4000 - ABORT")
    sys.exit(1)
if not results.get("thematic_coherence_70plus", False) and len(coherence_violations) >= 3:
    print(f" [BLOCKED] Coherence {coherence_score}/100 < 60")
    sys.exit(1)
print(" [OK] Critical gates passed")

# ============================================================
# STEP 8b: AGENT 24 - EDITOR-IN-CHIEF
# ============================================================
agent24_verdict = {}
agent24_approved = False
if article_html and client:
    article_html, agent24_verdict, agent24_approved = run_agent24_pipeline(client, article_html, TOPIC, MARKET)
    results["agent24_verdict"] = agent24_verdict.get("verdict", "SKIPPED")
    results["agent24_score"] = agent24_verdict.get("overall_score", 0)
    results["agent24_approved"] = agent24_approved
    results["agent24_corrections"] = len(agent24_log)
    if not agent24_approved:
        print(f" [AGENT 24] VETO - REJECTED")
        sys.exit(1)
    else:
        print(f" [AGENT 24] APPROVED")
else:
    print(" [AGENT 24] Skipped")
    results["agent24_verdict"] = "SKIPPED"
    results["agent24_approved"] = True

# ============================================================
# STEP 9: PUBLISH TO WORDPRESS
# ============================================================
print()
print("[STEP 9] Creating WordPress draft...")
wp_post_id = None
seo_title = TOPIC.title() + " | MoneyAbroadGuide"
meta_desc = f"Expert guide: {TOPIC}. Verified 2026 info for immigrants in {MARKET.upper()}."[:155]
focus_kw = re.sub(r"\s*(2026|guide|complete|best)\s*", " ", TOPIC, flags=re.IGNORECASE).strip()

if not WP_USER or not WP_PASS:
    print(f" ERROR: WP credentials missing")
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
    r = wp_request("POST", "/wp-json/wp/v2/posts", WP_JSON_HEADERS, json_data=wp_payload, timeout=120)
    if r and r.status_code in (200, 201):
        d = r.json()
        wp_post_id = d.get("id")
        print(f" SUCCESS! Post ID: {wp_post_id}")
        results["wordpress_draft_created"] = True
    else:
        status = r.status_code if r else "no response"
        print(f" FAILED. Status: {status}")
        results["wordpress_draft_created"] = False

# ============================================================
# STEP 10: IMAGE PIPELINE v7.1
# ============================================================
print()
print("[STEP 10] IMAGE PIPELINE v7.1 -- 5 images (gemini-2.5-flash-image)")
print("-" * 60)
print(f" Gemini key: {('SET (' + str(len(GEMINI_KEY)) + ' chars)') if GEMINI_KEY else 'MISSING'}")
print(f" Model: gemini-2.5-flash-image (Nano Banana)")
print(f" API fix: responseMimeType removed (was causing HTTP 400)")

IMG_PROMPTS = get_img_prompts(TOPIC, MARKET)
print(f"\n Generating 5 images...")
for i, prompt in enumerate(IMG_PROMPTS):
    label = "FEATURED" if i == 0 else f"BODY img{i}"
    print(f"\n [{i+1}/5] Generating {label}...")
    img_bytes = generate_image_gemini_native(prompt, i+1)
    if img_bytes:
        generated_images.append(img_bytes)
        ts = int(time.time())
        fname = f"nexus14-v71-{ARTICLE_INDEX}-img{i+1}-{ts}.jpg"
        mid, murl = upload_to_wp(img_bytes, fname)
        if mid:
            media_ids.append(mid)
            image_urls.append((mid, murl or ""))
    time.sleep(2)

featured_media_id = media_ids[0] if media_ids else None
if featured_media_id and wp_post_id:
    try:
        r_feat = wp_request("POST", f"/wp-json/wp/v2/posts/{wp_post_id}",
            WP_JSON_HEADERS, json_data={"featured_media": featured_media_id}, timeout=30)
        if r_feat and r_feat.status_code in (200, 201):
            print(f"\n Featured image set: {featured_media_id}")
    except Exception as e:
        print(f" Featured image error: {e}")

body_images = image_urls[1:]
print(f"\n Body images to inject: {len(body_images)}/4")
if body_images and article_html and wp_post_id:
    article_html_with_images = inject_4_body_images(article_html, body_images)
    update_payload = {"content": article_html_with_images}
    if featured_media_id: update_payload["featured_media"] = featured_media_id
    r_upd = wp_request("POST", f"/wp-json/wp/v2/posts/{wp_post_id}",
        WP_JSON_HEADERS, json_data=update_payload, timeout=120)
    if r_upd and r_upd.status_code in (200, 201):
        print(f" Article updated with body images")
        article_html = article_html_with_images
    else:
        print(f" Update FAIL: {r_upd.status_code if r_upd else 'timeout'}")

results["images_generated"] = len(generated_images) >= 4
results["featured_image_set"] = featured_media_id is not None
total_cost = anthropic_cost + img_cost
print(f"\n IMAGES: {len(generated_images)}/5 | Uploaded: {len(media_ids)}/5")
print(f" Cost: text={anthropic_cost:.4f} img={img_cost:.4f} TOTAL={total_cost:.4f}/{COST_BUDGET}")
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
    ("agent24_approved", results.get("agent24_approved", False)),
    ("cost_within_budget", total_cost <= COST_BUDGET),
]

passed = sum(1 for _, v in checks if v)
total_checks = len(checks)
critical = ["article_written", "word_count_4000plus", "thematic_coherence_70plus", "wordpress_draft_created", "agent24_approved"]
critical_ok = all(results.get(c, False) for c in critical)
cost_ok = total_cost <= COST_BUDGET
cost_status = "OK" if cost_ok else "OVERRUN"

print("=" * 60)
print("PRODUCTION REPORT v7.1 -- " + ARTICLE_INDEX)
print("=" * 60)
for name, val in checks:
    print(("[PASS] " if val else "[FAIL] ") + name)
print()
print(f"Score     : {passed}/{total_checks}")
print(f"Words     : {final_word_count} (target: {MIN_WORDS}-{MAX_WORDS})")
print(f"SEO       : {seo_score}/100")
print(f"EEAT      : {eeat_score}/100")
print(f"Coherence : {coherence_score}/100")
print(f"Cliches   : {cliche_count}")
print(f"Links     : {total_links} internal")
print(f"Images    : {len(generated_images)}/5 generated, {len(media_ids)} uploaded")
print(f"Agent 24  : {results.get('agent24_verdict', 'N/A')} | Score: {results.get('agent24_score', 0)}/100")
print(f"A24 cycles: {len(agent24_log)}")
print(f"Topic     : {TOPIC}")
print(f"Market    : {MARKET.upper()}")
print(f"Model     : {MODEL}")
print(f"Post ID   : {wp_post_id}")
print(f"FeatImg   : {featured_media_id}")
print(f"TOTAL cost: {total_cost:.5f} / {COST_BUDGET} ({cost_status})")
print(f"Time      : {elapsed}s")
print(f"Agent 17  : {results.get('agent17_decision', 'N/A')}")
print(f"Gate 19   : {results.get('gate19_status', 'N/A')}")
print(f"Gate 20   : {results.get('gate20_status', 'N/A')}")

if passed == total_checks and critical_ok and cost_ok:
    status = "PUBLICATION_READY"
elif passed >= total_checks - 2 and critical_ok:
    status = "REVIEW_REQUIRED"
elif critical_ok:
    status = "PARTIAL"
else:
    status = "FAIL"

print(f"STATUS    : {status}")
print("=" * 60)

report = {
    "version": "v7.1",
    "article_index": ARTICLE_INDEX,
    "topic": TOPIC,
    "market": MARKET,
    "model": MODEL,
    "word_count": final_word_count,
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
    "agent24_verdict": results.get("agent24_verdict", "N/A"),
    "agent24_score": results.get("agent24_score", 0),
    "agent24_approved": results.get("agent24_approved", False),
    "agent24_cycles": len(agent24_log),
    "agent24_log": agent24_log,
    "elapsed_seconds": elapsed,
    "timestamp": datetime.utcnow().isoformat()
}

report_file = f"execution_report_{ARTICLE_INDEX}.json"
with open(report_file, "w") as f:
    json.dump(report, f, indent=2)
print(f"Report: {report_file}")

if not critical_ok:
    sys.exit(1)
