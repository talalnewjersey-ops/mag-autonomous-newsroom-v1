#!/usr/bin/env python3
"""
NEXUS-14 PRODUCTION SCRIPT v2 - FIXED ENGINE
scripts/produce_article.py

FIXES v2:
  - WP retry with exponential backoff (3 attempts)
  - HTML cleanup: remove backtick markdown fences
  - Word count: 6-pass generation -> 5000+ words (BLOCKING gate)
  - Images: 4 per article, featured image required
  - Correct categories: USA=17 / Canada=18
  - Yoast SEO: SEO title + meta desc + focus keyphrase
  - Author: user ID 4 (talal-eddaouahiri with bio)
  - Quality gates BLOCKING: word<5000 -> abort
"""
import sys, os, json, time, requests, re, base64
from base64 import b64encode
from datetime import datetime

try:
    import openai
except ImportError:
    os.system("pip install openai -q")
    import openai


def md_to_html(md_text):
    """Convert Markdown headers to HTML. Wrap lines in paragraphs."""
    if not md_text:
        return ""
    result = []
    for line in md_text.split('\n'):
        if line.startswith('###### '):
            result.append('<h6>' + line[7:] + '</h6>')
        elif line.startswith('##### '):
            result.append('<h5>' + line[6:] + '</h5>')
        elif line.startswith('#### '):
            result.append('<h4>' + line[5:] + '</h4>')
        elif line.startswith('### '):
            result.append('<h3>' + line[4:] + '</h3>')
        elif line.startswith('## '):
            result.append('<h2>' + line[3:] + '</h2>')
        elif line.startswith('# '):
            result.append('<h1>' + line[2:] + '</h1>')
        elif not line.strip():
            continue
        elif line.strip().startswith('<') or line.strip().startswith('|'):
            result.append(line)
        else:
            result.append('<p>' + line + '</p>')
    return '\n'.join(result)
START = time.time()
ARTICLE_INDEX = os.environ.get("ARTICLE_INDEX", "0")
MARKET = (os.environ.get("TARGET_MARKET") or "usa").lower()
TOPIC = (os.environ.get("TOPIC_OVERRIDE") or "").strip()
if not TOPIC:
    TOPIC = "best way to send money internationally 2026"

OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")
NANO_KEY     = os.environ.get("NANO_BANANA_API_KEY", "")
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY", "")
WP_URL       = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER      = os.environ.get("WORDPRESS_USERNAME", "")
WP_PASS      = os.environ.get("WORDPRESS_APP_PASSWORD", "") or os.environ.get("WORDPRESS_PASSWORD", "")
EMAIL_TO     = os.environ.get("EMAIL_RECIPIENT", "")

WP_CAT_USA    = 17  # Newcomers to the USA (confirmed WP ID)
WP_CAT_CANADA = 18  # Newcomers to Canada (confirmed WP ID)
WP_AUTHOR_ID  = 4   # talal-eddaouahiri (with bio, confirmed WP ID)

print("=" * 60)
print("NEXUS-14 PRODUCTION v2 -- Article #" + ARTICLE_INDEX)
print("=" * 60)
print("Topic  :", TOPIC)
print("Market :", MARKET.upper())
print("OpenAI :", "SET" if OPENAI_KEY else "MISSING")
print("WP URL :", WP_URL)
print()

results = {}
image_report = {
    "images_generated": False,
    "provider_used": None,
    "attempts": [],
    "image_urls": [],
    "generation_time_s": 0,
    "cost_usd": 0.0,
    "error": None,
    "media_ids": [],
    "featured_media_id": None
}
generated_images = []
media_ids = []

def clean_html(text):
    text = re.sub(r"^```[a-z]*\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    text = re.sub(r"```[a-z]*", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()

creds_wp = b64encode((WP_USER + ":" + WP_PASS).encode()).decode() if WP_USER and WP_PASS else ""
WP_JSON_HEADERS = {
    "Authorization": "Basic " + creds_wp,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; NEXUS14/2.0)",
}

def wp_request(method, path, headers, json_data=None, data=None, timeout=60, max_retries=3):
    url = WP_URL + path
    for attempt in range(1, max_retries + 1):
        try:
            if method == "POST":
                r = requests.post(url, headers=headers, json=json_data, data=data, timeout=timeout)
            else:
                r = requests.get(url, headers=headers, timeout=timeout)
            print(f"    WP {method} -> {r.status_code} (attempt {attempt})")
            if r.status_code in (200, 201):
                return r
            if r.status_code == 403:
                wait = 2 ** attempt
                print(f"    WP 403 -> backoff {wait}s")
                time.sleep(wait)
                continue
            if r.status_code == 401:
                print("    WP 401 auth error")
                return r
            time.sleep(2)
        except Exception as e:
            print(f"    WP error attempt {attempt}: {e}")
            time.sleep(2 ** attempt)
    return None

print("[STEP 1] Generating article (6-pass for 5000+ words)...")
article_content = ""
openai_cost = 0.0
total_tokens = 0

def gpt(client, prompt, max_tokens=3000):
    global total_tokens, openai_cost
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens, temperature=0.7
    )
    total_tokens += r.usage.total_tokens
    openai_cost += (r.usage.prompt_tokens/1000000)*0.15 + (r.usage.completion_tokens/1000000)*0.60
    return r.choices[0].message.content

if not OPENAI_KEY:
    print("  ERROR: OPENAI_API_KEY not set")
    results["article_written"] = False
else:
    try:
        client = openai.OpenAI(api_key=OPENAI_KEY)
        mkt = MARKET.upper()

        part1 = gpt(client,
            "Write PART 1 of an expert article titled: " + TOPIC + " for market: " + mkt + "\n\n"
            "<h2>Introduction</h2>\n4 paragraphs (300+ words) on importance, target audience, 2026 context.\n\n"
            "<h2>Why This Matters for " + mkt + " Residents</h2>\n3 paragraphs (250+ words) on expat/immigrant needs.\n\n"
            "<h2>Top 8 Services Compared</h2>\nDetailed HTML table: Service/Fees/Speed/Exchange Rate/Rating.\n"
            "Include Wise, Remitly, Western Union, MoneyGram, OFX, TransferGo, WorldRemit, XE.\n"
            "Then 2 analysis paragraphs (200+ words).\n"
            "Link: <a href=\"https://moneyabroadguide.com/best-services\">full guide</a>\nMin 900 words.", 3000)
        print("  Part 1 words:", len(part1.split()))

        part2 = gpt(client,
            "Write PART 2 of the article about: " + TOPIC + " (market: " + mkt + ")\n\n"
            "<h2>Detailed Review: Wise</h2>\n4 paragraphs (300+ words): pros/cons, fees, speed.\n\n"
            "<h2>Detailed Review: Remitly</h2>\n4 paragraphs (300+ words): pros/cons, fees, speed.\n\n"
            "<h2>Detailed Review: OFX vs Western Union</h2>\n3 paragraphs (200+ words): best use cases.\n"
            "Link: <a href=\"https://moneyabroadguide.com/compare\">comparison page</a>\nMin 900 words.", 3000)
        print("  Part 2 words:", len(part2.split()))

        part3 = gpt(client,
            "Write PART 3 of the article about: " + TOPIC + " (market: " + mkt + ")\n\n"
            "<h2>Understanding Fees and Exchange Rates 2026</h2>\n4 paragraphs (300+ words) with real examples.\n\n"
            "<h2>Complete Fee Breakdown: Real Transfer Examples</h2>\nHTML table: 5 scenarios ($500/$1000/$2500/$5000/$10000) per provider.\n"
            "2 analysis paragraphs (200+ words).\n\n"
            "<h2>Transfer Speed in 2026</h2>\n3 paragraphs (200+ words) on instant vs 1-3 day options.\n"
            "Link: <a href=\"https://moneyabroadguide.com/exchange-rates\">exchange rate guide</a>\nMin 900 words.", 3000)
        print("  Part 3 words:", len(part3.split()))

        part4 = gpt(client,
            "Write PART 4 of the article about: " + TOPIC + " (market: " + mkt + ")\n\n"
            "<h2>Regulations and Legal Requirements in " + mkt + " 2026</h2>\n4 paragraphs (300+ words): IRS/CRA, FINTRAC, compliance.\n\n"
            "<h2>Safety, Security and Fraud Protection</h2>\n3 paragraphs (250+ words): FDIC/CDIC, 2FA, scam protection.\n\n"
            "<h2>Special Situations: Large Transfers, Business, Emergency</h2>\n3 paragraphs (200+ words).\n"
            "Link: <a href=\"https://moneyabroadguide.com/regulations\">regulations guide</a>\nMin 900 words.", 3000)
        print("  Part 4 words:", len(part4.split()))

        part5 = gpt(client,
            "Write PART 5 of the article about: " + TOPIC + " (market: " + mkt + ")\n\n"
            "<h2>Step-by-Step Guide: How to Make Your First Transfer</h2>\nNumbered 8 steps (300+ words).\n\n"
            "<h2>10 Expert Money-Saving Tips for 2026</h2>\n10 numbered tips (300+ words).\n\n"
            "<h2>Common Mistakes to Avoid</h2>\n5 mistakes (200+ words).\n"
            "Links: <a href=\"https://moneyabroadguide.com/tips\">money saving tips</a> and <a href=\"https://moneyabroadguide.com/how-to-guide\">how-to guide</a>\nMin 900 words.", 3000)
        print("  Part 5 words:", len(part5.split()))

        part6 = gpt(client,
            "Write PART 6 (FINAL) of the article about: " + TOPIC + " (market: " + mkt + ")\n\n"
            "<h2>Our Top Affiliate Recommendations</h2>\n3 paragraphs (200+ words) with CTAs.\n\n"
            "<h2>Free eBook: The Complete " + mkt + " Expat Money Guide</h2>\n3 paragraphs (150+ words) promoting free ebook.\n"
            "Include: <a href=\"https://moneyabroadguide.com/free-ebook\">Download your FREE guide</a>\n\n"
            "<h2>Frequently Asked Questions (FAQ)</h2>\n8 detailed Q&A pairs (400+ words) on fees, safety, speed, limits, tax.\n\n"
            "<h2>Conclusion</h2>\nStrong 3-paragraph conclusion (150+ words).\n"
            "Links: <a href=\"https://moneyabroadguide.com/security\">security tips</a> and <a href=\"https://moneyabroadguide.com/faq\">FAQ page</a>\nMin 900 words.", 3000)
        print("  Part 6 words:", len(part6.split()))

        raw = part1 + "\n\n" + part2 + "\n\n" + part3 + "\n\n" + part4 + "\n\n" + part5 + "\n\n" + part6
        article_content = clean_html(raw)
        total_words = len(article_content.split())
        print("  TOTAL words:", total_words)
        results["article_written"] = len(article_content) > 500
        results["word_count_5000plus"] = total_words >= 5000
        print("  word_count_5000plus:", results["word_count_5000plus"])
    except Exception as e:
        print("  ERROR:", e)
        import traceback; traceback.print_exc()
        results["article_written"] = False
        results["word_count_5000plus"] = False

print()
print("[STEP 2] SEO scoring...")
seo_score = 0
if article_content:
    words_in_topic = [w for w in TOPIC.lower().split() if len(w) > 3]
    found_kw = sum(1 for w in words_in_topic if w in article_content.lower())
    kw_density = found_kw / max(len(words_in_topic), 1)
    if kw_density >= 0.7: seo_score += 25
    if article_content.count("<h2>") >= 5: seo_score += 20
    if "<table" in article_content: seo_score += 15
    if len(article_content.split()) >= 5000: seo_score += 20
    if "href=" in article_content: seo_score += 15
    if "faq" in article_content.lower() or "frequently asked" in article_content.lower(): seo_score += 5
results["seo_score_95plus"] = seo_score >= 95
print("  SEO score:", seo_score)

print()
print("[STEP 3] EEAT scoring...")
eeat_score = 0
if article_content:
    cl = article_content.lower()
    if any(w in cl for w in ["expert", "research", "study", "data", "statistic", "analysis"]): eeat_score += 20
    if any(w in cl for w in ["review", "comparison", "tested", "versus", "vs"]): eeat_score += 20
    if any(w in cl for w in ["fee", "cost", "price", "rate", "percent", "%"]): eeat_score += 20
    if len(article_content.split()) >= 5000: eeat_score += 20
    if "faq" in cl or "frequently asked" in cl: eeat_score += 10
    if "ebook" in cl or "free guide" in cl or "download" in cl: eeat_score += 10
results["eeat_score_95plus"] = eeat_score >= 95
print("  EEAT score:", eeat_score)

print()
print("[STEP 4] Counting internal links...")
if article_content:
    links = re.findall(r"href=\"(https?://[^\"]+)\"", article_content)
    internal_links = sum(1 for l in links if "moneyabroadguide.com" in l)
else:
    internal_links = 0
results["internal_links_5plus"] = internal_links >= 5
print("  Internal links:", internal_links)

print()
print("[QUALITY GATE CHECK]")
gate_word = results.get("word_count_5000plus", False)
print("  word_count_5000plus:", gate_word)
print("  seo_score_95plus   :", results.get("seo_score_95plus", False))
print("  eeat_score_95plus  :", results.get("eeat_score_95plus", False))

if not gate_word:
    print("  [BLOCKED] Word count < 5000 - ABORT")
    results["wordpress_draft_created"] = False
    results["images_generated"] = False
    results["quality_gate_passed"] = False
    elapsed_g = round(time.time() - START, 1)
    report_g = {"article_index": ARTICLE_INDEX, "topic": TOPIC, "market": MARKET,
                "abort_reason": "word_count_below_5000", "word_count": len(article_content.split()),
                "seo_score": seo_score, "eeat_score": eeat_score, "timestamp": datetime.utcnow().isoformat()}
    with open("execution_report_" + ARTICLE_INDEX + ".json", "w") as f:
        json.dump(report_g, f, indent=2)
    print("STATUS : BLOCKED (word count gate)")
    sys.exit(1)

results["quality_gate_passed"] = True
print("  [OK] Quality gates passed")

print()
print("[STEP 5] Creating WordPress draft (with retry + backoff)...")
wp_post_id = None
wp_category = WP_CAT_USA if MARKET == "usa" else WP_CAT_CANADA
print("  Category ID:", wp_category, "(" + ("Newcomers to the USA" if MARKET == "usa" else "Newcomers to Canada") + ")")

focus_kw = TOPIC.replace(" 2026", "").strip()
seo_title = TOPIC.title() + " | MoneyAbroadGuide"
meta_desc = ("Complete guide to " + TOPIC + ". Compare top services, fees, exchange rates and expert tips "
             "for " + MARKET.upper() + " residents in 2026.")

if not WP_USER or not WP_PASS:
    print("  ERROR: WP credentials missing")
    results["wordpress_draft_created"] = False
else:
    wp_payload = {
        "title": TOPIC.title(),
        "content": md_to_html(article_content),
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
        print("  SUCCESS! Post ID:", wp_post_id)
        results["wordpress_draft_created"] = True
    else:
        status = r.status_code if r else "no response"
        body = r.text[:300] if r else "timeout/error"
        print("  FAILED after retries. Status:", status)
        print("  Response:", body)
        results["wordpress_draft_created"] = False

print()
print("[STEP 6] IMAGE PIPELINE -- 4 images")
print("  Chain: Gemini -> Nano Banana -> OpenAI gpt-image-1")
print("-" * 50)

img_t_start = time.time()
img_cost = 0.0
image_report = {
    "images_generated": False,
    "count": 0,
    "media_ids": [],
    "featured_media_id": None,
    "errors": [],
    "provider_used": "none"
}
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
NANO_KEY = os.environ.get("NANO_BANANA_KEY", os.environ.get("NANO_BANANA_API_KEY", ""))
image_prompts = [
    f"Professional editorial photo: {TOPIC} in the USA, modern healthcare setting, photorealistic",
    f"Infographic about health insurance costs and coverage in America, clean modern design",
    f"Diverse immigrants at a healthcare office in the USA, professional documentary photography",
    f"Health insurance documents, stethoscope and American flag on desk, professional photo"
]

def upload_img_to_wp(img_bytes, filename):
    from io import BytesIO
    auth_headers = {"Authorization": WP_JSON_HEADERS["Authorization"]}
    files = {"file": (filename, BytesIO(img_bytes), "image/png")}
    r = requests.post(f"{WP_URL}/media", headers=auth_headers, files=files, timeout=60)
    if r.status_code in (200, 201):
        data = r.json()
        return data.get("id"), data.get("source_url", "")
    return None, None

def try_gemini(prompt, key):
    for model in ["gemini-2.0-flash-preview-image-generation", "gemini-1.5-flash"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}, timeout=60)
            if r.status_code == 200:
                for cand in r.json().get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if "inlineData" in part and part["inlineData"].get("data"):
                            import base64
                            return base64.b64decode(part["inlineData"]["data"]), model
        except Exception as e:
            print(f"    Gemini {model}: {e}")
    return None, None

def try_openai(prompt, key):
    try:
        import openai as oa
        c = oa.OpenAI(api_key=key)
        res = c.images.generate(model="gpt-image-1", prompt=prompt, size="1024x1024", n=1)
        if res.data:
            if res.data[0].b64_json:
                import base64
                return base64.b64decode(res.data[0].b64_json), "gpt-image-1"
            elif res.data[0].url:
                r = requests.get(res.data[0].url, timeout=30)
                if r.status_code == 200:
                    return r.content, "gpt-image-1"
    except Exception as e:
        print(f"    OpenAI gpt-image-1: {e}")
    try:
        import openai as oa
        c = oa.OpenAI(api_key=key)
        res = c.images.generate(model="dall-e-3", prompt=prompt[:1000], size="1024x1024", n=1)
        if res.data and res.data[0].url:
            r = requests.get(res.data[0].url, timeout=30)
            if r.status_code == 200:
                return r.content, "dall-e-3"
    except Exception as e2:
        print(f"    OpenAI dall-e-3: {e2}")
    return None, None

generated_images = []
pstats = {"gemini": 0, "openai": 0}

for i, prompt in enumerate(image_prompts):
    print(f"\n  Image {i+1}/4: {prompt[:55]}...")
    img_bytes = None
    provider = "none"
    if GEMINI_KEY:
        print("    Trying Gemini...")
        img_bytes, m = try_gemini(prompt, GEMINI_KEY)
        if img_bytes:
            provider = f"gemini:{m}"
            pstats["gemini"] += 1
            print(f"    Gemini SUCCESS ({m}): {len(img_bytes)} bytes")
    if not img_bytes and OPENAI_KEY:
        print("    Trying OpenAI...")
        img_bytes, m = try_openai(prompt, OPENAI_KEY)
        if img_bytes:
            provider = f"openai:{m}"
            pstats["openai"] += 1
            img_cost += 0.04
            print(f"    OpenAI SUCCESS ({m}): {len(img_bytes)} bytes")
    if img_bytes:
        fn = f"nexus14-img-{i+1}-{int(time.time())}.png"
        mid, murl = upload_img_to_wp(img_bytes, fn)
        if mid:
            generated_images.append({"index": i+1, "media_id": mid, "url": murl, "provider": provider})
            image_report["media_ids"].append(mid)
            print(f"    WP Media: ID={mid}")
        else:
            print(f"    WP upload failed image {i+1}")
            image_report["errors"].append(f"WP upload failed {i+1}")
    else:
        print(f"    ALL failed for image {i+1}")
        image_report["errors"].append(f"All providers failed {i+1}")

if generated_images:
    image_report["images_generated"] = True
    image_report["count"] = len(generated_images)
    image_report["featured_media_id"] = generated_images[0]["media_id"]
    image_report["provider_used"] = f"gemini={pstats['gemini']}, openai={pstats['openai']}"
    print(f"\n  Images: {len(generated_images)}/4 | Provider: {image_report['provider_used']}")
    if wp_post_id and image_report["featured_media_id"]:
        try:
            rf = requests.post(f"{WP_URL}/posts/{wp_post_id}", headers=WP_JSON_HEADERS, json={"featured_media": image_report["featured_media_id"]}, timeout=30)
            if rf.status_code in (200, 201):
                print(f"  Featured image set: {image_report['featured_media_id']}")
        except Exception as e:
            print(f"  Featured image error: {e}")
else:
    print("  No images generated")

print()
print("[STEP 7] Email notification (non-bloquant)...")
try:
    if SENDGRID_KEY and EMAIL_TO:
        passed_count = sum(1 for v in results.values() if v is True)
        subject = "NEXUS-14 v2 #" + ARTICLE_INDEX + " - " + TOPIC[:50] + " - " + str(passed_count) + "/8"
        body = ("NEXUS-14 v2 Production\nArticle #" + ARTICLE_INDEX + "\nTopic: " + TOPIC +
                "\nMarket: " + MARKET.upper() + "\nWords: " + str(len(article_content.split())) +
                "\nImages: " + str(len(generated_images)) + "/4\n\n")
        for k, v in results.items():
            body += ("PASS" if v else "FAIL") + " " + k + "\n"
        body += "\nPost ID: " + str(wp_post_id)
        sg_data = {
            "personalizations": [{"to": [{"email": EMAIL_TO}]}],
            "from": {"email": "noreply@moneyabroadguide.com"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }
        sg_r = requests.post("https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": "Bearer " + SENDGRID_KEY, "Content-Type": "application/json"},
            json=sg_data, timeout=30)
        print("  Email status:", sg_r.status_code)
        if sg_r.status_code not in (200, 201, 202):
            print("  Email failed (non-bloquant, ignore)")
    else:
        print("  Skipped (no SendGrid key or recipient)")
except Exception as e:
    print("  Email error (ignore):", e)

elapsed = round(time.time() - START, 1)
checks = [
    ("article_written",         results.get("article_written", False)),
    ("word_count_5000plus",     results.get("word_count_5000plus", False)),
    ("seo_score_95plus",        results.get("seo_score_95plus", False)),
    ("eeat_score_95plus",       results.get("eeat_score_95plus", False)),
    ("internal_links_5plus",    results.get("internal_links_5plus", False)),
    ("wordpress_draft_created", results.get("wordpress_draft_created", False)),
    ("images_generated",        results.get("images_generated", False)),
    ("featured_image_set",      results.get("featured_image_set", False)),
]
passed = sum(1 for _, v in checks if v)
total_checks = len(checks)
critical = ["article_written", "word_count_5000plus", "wordpress_draft_created"]
critical_ok = all(results.get(c, False) for c in critical)

print()
print("=" * 60)
print("PRODUCTION REPORT v2 -- Article #" + ARTICLE_INDEX)
print("=" * 60)
for name, val in checks:
    print(("[PASS] " if val else "[FAIL] ") + name)
print()
print("Score  :", str(passed) + "/" + str(total_checks))
print("Words  :", len(article_content.split()) if article_content else 0)
print("Images :", len(generated_images), "/ 4 generated,", len(media_ids), "uploaded")
print("Topic  :", TOPIC)
print("Market :", MARKET.upper())
print("Cat    :", "Newcomers to the USA" if MARKET == "usa" else "Newcomers to Canada")
print("Author : Talal Eddaouahiri (ID=" + str(WP_AUTHOR_ID) + ")")
print("Post ID:", wp_post_id)
print("Img IDs:", media_ids)
print("Featured:", image_report.get("featured_media_id", "none"))
print("Provider:", image_report.get("provider_used", "none"))
print("Cost   : $" + str(round(openai_cost + img_cost, 4)))
print("Time   :", str(elapsed) + "s")

if passed >= 7 and critical_ok and results.get("word_count_5000plus") and results.get("images_generated"):
    print("STATUS : PUBLISHED (draft) - ALL GATES PASS")
elif passed >= 6 and critical_ok:
    print("STATUS : PARTIAL - REVIEW REQUIRED")
else:
    print("STATUS : FAIL")
print("=" * 60)

report = {
    "version": "v2",
    "article_index": ARTICLE_INDEX,
    "topic": TOPIC,
    "market": MARKET,
    "category": "Newcomers to the USA" if MARKET == "usa" else "Newcomers to Canada",
    "word_count": len(article_content.split()) if article_content else 0,
    "seo_score": seo_score,
    "eeat_score": eeat_score,
    "internal_links": internal_links,
    "checks": {n: v for n, v in checks},
    "score": str(passed) + "/" + str(total_checks),
    "critical_ok": critical_ok,
    "wp_post_id": wp_post_id,
    "images_generated": len(generated_images),
    "media_ids": media_ids,
    "featured_media_id": image_report.get("featured_media_id"),
    "image_provider": image_report.get("provider_used"),
    "yoast_configured": True if wp_post_id else False,
    "openai_cost_usd": round(openai_cost, 5),
    "total_cost_usd": round(openai_cost + img_cost, 5),
    "total_tokens": total_tokens,
    "elapsed_seconds": elapsed,
    "timestamp": datetime.utcnow().isoformat()
}

report_file = "execution_report_" + ARTICLE_INDEX + ".json"
with open(report_file, "w") as f:
    json.dump(report, f, indent=2)
print("Report:", report_file)

if not critical_ok:
    sys.exit(1)
if not results.get("word_count_5000plus", False):
    sys.exit(1)
