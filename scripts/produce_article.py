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
    """Convert Markdown to clean HTML for WordPress publication."""
    import re
    html = md_text if md_text else ""
    # Remove YAML front matter
    html = re.sub(r'^---[\s\S]*?---\n?', '', html)
    # Remove triple backtick code fences
    html = re.sub(r'```[^\n]*\n', '<pre><code>', html)
    html = re.sub(r'```', '</code></pre>', html)
    # Headings H6 to H1 (order matters)
    for lvl in range(6, 0, -1):
        pattern = '^' + '#' * lvl + r' +(.+)$'
        html = re.sub(pattern, f'<h{lvl}>\\1</h{lvl}>', html, flags=re.MULTILINE)
    # Bold + Italic
    html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # Inline code
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    # Horizontal rules
    html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)
    # Blockquotes
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    # Convert lines to paragraphs (skip HTML tags and table rows)
    lines = html.split('\n')
    out = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('<') or s.startswith('|') or s == '<hr>':
            out.append(s)
        else:
            out.append(f'<p>{s}</p>')
    return '\n'.join(out)



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
image_report = {
    "images_generated": False,
    "count": 0,
    "media_ids": [],
    "featured_media_id": None,
    "image_prompts": [],
    "errors": [],
    "provider_used": "none"
}

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
NANO_KEY   = os.environ.get("NANO_BANANA_KEY", os.environ.get("NANO_BANANA_API_KEY", ""))
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

image_prompts = [
    f"Professional editorial photo: {TOPIC} in the USA, modern healthcare setting, photorealistic, high quality",
    f"Infographic style illustration about health insurance costs and coverage in America, clean modern design",
    f"Diverse group of immigrants and newcomers at a healthcare office in the USA, professional documentary photography",
    f"Health insurance documents, stethoscope and American flag on desk, professional business photo"
]

def upload_image_to_wp(img_bytes, filename, wp_url, wp_headers):
    """Upload image bytes to WordPress Media Library."""
    from io import BytesIO
    files = {"file": (filename, BytesIO(img_bytes), "image/png")}
    r = requests.post(f"{wp_url}/media", headers=wp_headers, files=files, timeout=60)
    if r.status_code in (200, 201):
        data = r.json()
        return data.get("id"), data.get("source_url", "")
    return None, None

def try_gemini_image(prompt, gemini_key):
    """Try Gemini image generation - returns PNG bytes or None."""
    gemini_models = [
        "gemini-2.0-flash-preview-image-generation",
        "gemini-2.5-flash-preview-05-20",
        "gemini-1.5-flash"
    ]
    for model in gemini_models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"]
                }
            }
            r = requests.post(url, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                for cand in candidates:
                    for part in cand.get("content", {}).get("parts", []):
                        if "inlineData" in part:
                            import base64
                            img_data = part["inlineData"].get("data", "")
                            if img_data:
                                return base64.b64decode(img_data), model
        except Exception as e:
            print(f"  Gemini {model} error: {e}")
    return None, None

def try_nano_banana_image(prompt, nano_key):
    """Try Nano Banana image generation - returns PNG bytes or None."""
    endpoints = [
        "https://api.nanobanana.ai/v1/generate",
        "https://api.nanobanana.ai/v1/images/generate",
        "https://nanobanana.ai/api/v1/generate"
    ]
    for endpoint in endpoints:
        try:
            headers = {"Authorization": f"Bearer {nano_key}", "Content-Type": "application/json"}
            payload = {"prompt": prompt, "size": "1024x1024", "format": "png"}
            r = requests.post(endpoint, json=payload, headers=headers, timeout=60)
            if r.status_code in (200, 201):
                data = r.json()
                # Handle different response formats
                if "image" in data:
                    import base64
                    return base64.b64decode(data["image"]), endpoint
                elif "url" in data:
                    img_r = requests.get(data["url"], timeout=30)
                    if img_r.status_code == 200:
                        return img_r.content, endpoint
                elif "data" in data and isinstance(data["data"], list):
                    item = data["data"][0]
                    if "b64_json" in item:
                        import base64
                        return base64.b64decode(item["b64_json"]), endpoint
                    elif "url" in item:
                        img_r = requests.get(item["url"], timeout=30)
                        if img_r.status_code == 200:
                            return img_r.content, endpoint
        except Exception as e:
            print(f"  Nano Banana {endpoint} error: {e}")
    return None, None

def try_openai_image(prompt, openai_key):
    """Try OpenAI image generation - returns PNG bytes or None."""
    try:
        import openai as openai_mod
        client = openai_mod.OpenAI(api_key=openai_key)
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024",
            n=1
        )
        if result.data and result.data[0].b64_json:
            import base64
            return base64.b64decode(result.data[0].b64_json), "gpt-image-1"
        elif result.data and result.data[0].url:
            r = requests.get(result.data[0].url, timeout=30)
            if r.status_code == 200:
                return r.content, "gpt-image-1"
    except Exception as e:
        print(f"  OpenAI gpt-image-1 error: {e}")
    # Fallback to dall-e-3
    try:
        import openai as openai_mod
        client = openai_mod.OpenAI(api_key=openai_key)
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt[:1000],
            size="1024x1024",
            n=1
        )
        if result.data and result.data[0].url:
            r = requests.get(result.data[0].url, timeout=30)
            if r.status_code == 200:
                return r.content, "dall-e-3"
    except Exception as e2:
        print(f"  OpenAI dall-e-3 error: {e2}")
    return None, None

# Generate images using priority chain
generated_images = []
provider_stats = {"gemini": 0, "nano_banana": 0, "openai": 0}

for i, prompt in enumerate(image_prompts):
    print(f"\n  Image {i+1}/4: {prompt[:60]}...")
    img_bytes = None
    provider = None

    # Try 1: Gemini
    if GEMINI_KEY and img_bytes is None:
        print(f"    Trying Gemini...")
        img_bytes, model_used = try_gemini_image(prompt, GEMINI_KEY)
        if img_bytes:
            provider = f"gemini:{model_used}"
            provider_stats["gemini"] += 1
            print(f"    Gemini SUCCESS ({model_used}): {len(img_bytes)} bytes")

    # Try 2: Nano Banana
    if NANO_KEY and img_bytes is None:
        print(f"    Trying Nano Banana...")
        img_bytes, endpoint_used = try_nano_banana_image(prompt, NANO_KEY)
        if img_bytes:
            provider = f"nano_banana:{endpoint_used}"
            provider_stats["nano_banana"] += 1
            print(f"    Nano Banana SUCCESS: {len(img_bytes)} bytes")

    # Try 3: OpenAI (final fallback)
    if OPENAI_KEY and img_bytes is None:
        print(f"    Trying OpenAI...")
        img_bytes, model_used = try_openai_image(prompt, OPENAI_KEY)
        if img_bytes:
            provider = f"openai:{model_used}"
            provider_stats["openai"] += 1
            print(f"    OpenAI SUCCESS ({model_used}): {len(img_bytes)} bytes")

    if img_bytes:
        # Upload to WordPress
        filename = f"nexus14-img-{i+1}-{int(time.time())}.png"
        media_id, media_url = upload_image_to_wp(img_bytes, filename, WP_URL, WP_HEADERS)
        if media_id:
            generated_images.append({
                "index": i+1,
                "media_id": media_id,
                "url": media_url,
                "prompt": prompt,
                "provider": provider,
                "size_bytes": len(img_bytes)
            })
            image_report["media_ids"].append(media_id)
            print(f"    Uploaded to WP Media: ID={media_id}, URL={media_url}")
        else:
            print(f"    WP upload failed for image {i+1}")
            image_report["errors"].append(f"WP upload failed for image {i+1}")
    else:
        print(f"    ALL providers failed for image {i+1}")
        image_report["errors"].append(f"All providers failed for image {i+1}")

# Set results
if generated_images:
    image_report["images_generated"] = True
    image_report["count"] = len(generated_images)
    image_report["featured_media_id"] = generated_images[0]["media_id"]
    image_report["provider_used"] = f"gemini={provider_stats['gemini']}, nano_banana={provider_stats['nano_banana']}, openai={provider_stats['openai']}"
    print(f"\n  Total images: {len(generated_images)}/4")
    print(f"  Provider breakdown: {image_report['provider_used']}")
    print(f"  Featured image ID: {image_report['featured_media_id']}")

    # Set featured image on the post
    if results.get("post_id") and image_report["featured_media_id"]:
        try:
            r_feat = requests.post(
                f"{WP_URL}/posts/{results['post_id']}",
                headers=WP_HEADERS,
                json={"featured_media": image_report["featured_media_id"]},
                timeout=30
            )
            if r_feat.status_code in (200, 201):
                print(f"  Featured image set: media_id={image_report['featured_media_id']}")
        except Exception as e_feat:
            print(f"  Featured image set error: {e_feat}")
else:
    print("  No images generated by any provider")

results["images_generated"] = image_report["images_generated"]
results["image_count"]      = image_report["count"]
results["media_ids"]        = image_report["media_ids"]
results["featured_image_set"] = image_report.get("featured_media_id") is not None

img_duration = round(time.time() - img_t_start, 2)
print(f"  Image pipeline duration: {img_duration}s")


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
        "content": article_content,
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
print("  Chain: gpt-image-1 -> dall-e-3")
print("-" * 50)

img_t_start = time.time()
img_cost = 0.0

IMG_PROMPTS = [
    "Professional financial infographic comparing international money transfer services for topic: " + TOPIC + ". Blue green palette, white background, data visualization, no people.",
    "Modern flat design: world map with money transfer arrows. " + MARKET.upper() + " to international destinations. Blue green corporate style.",
    "Clean infographic: fee comparison chart for international wire transfers. Green bars, white background, professional financial.",
    "Professional financial banner: smartphone showing money transfer app with currency symbols USD CAD. Blue and green theme, minimal."
]

def generate_one_image(prompt_text, idx):
    global img_cost
    if OPENAI_KEY:
        try:
            ci = openai.OpenAI(api_key=OPENAI_KEY)
            ir = ci.images.generate(model="gpt-image-1", prompt=prompt_text, size="1024x1024", n=1)
            b64 = ir.data[0].b64_json if ir.data else None
            if b64:
                img_cost += 0.04
                print(f"    Image {idx}: gpt-image-1 SUCCESS")
                return base64.b64decode(b64), "gpt-image-1"
            elif ir.data[0].url:
                resp = requests.get(ir.data[0].url, timeout=30)
                img_cost += 0.04
                print(f"    Image {idx}: gpt-image-1 SUCCESS (url)")
                return resp.content, "gpt-image-1"
        except Exception as e:
            print(f"    Image {idx}: gpt-image-1 ERROR: {str(e)[:80]}")
    if OPENAI_KEY:
        try:
            ci3 = openai.OpenAI(api_key=OPENAI_KEY)
            dalle_p = "Professional financial services infographic. Blue green color scheme, modern flat design, no text overlay, no people."
            ir3 = ci3.images.generate(model="dall-e-3", prompt=dalle_p, size="1024x1024", quality="standard", n=1)
            url3 = ir3.data[0].url if ir3.data else None
            if url3:
                img_bytes = requests.get(url3, timeout=30).content
                img_cost += 0.04
                print(f"    Image {idx}: dall-e-3 SUCCESS")
                return img_bytes, "dall-e-3"
        except Exception as e:
            print(f"    Image {idx}: dall-e-3 ERROR: {str(e)[:80]}")
    print(f"    Image {idx}: ALL PROVIDERS FAILED")
    return None, None

def upload_image_to_wp(img_bytes, filename, post_id, set_featured=False):
    if not creds_wp:
        return None
    try:
        hdr = {
            "Authorization": "Basic " + creds_wp,
            "Content-Disposition": "attachment; filename=" + filename,
            "Content-Type": "image/jpeg",
            "User-Agent": "Mozilla/5.0 (compatible; NEXUS14/2.0)",
        }
        mr = requests.post(WP_URL + "/wp-json/wp/v2/media", headers=hdr, data=img_bytes, timeout=60)
        print("    WP Media upload:", mr.status_code)
        if mr.status_code in (200, 201):
            mid = mr.json().get("id")
            murl = mr.json().get("source_url", "")
            print("    Media ID:", mid, "URL:", murl[:60])
            if set_featured and post_id:
                upd = wp_request("POST", "/wp-json/wp/v2/posts/" + str(post_id),
                                 WP_JSON_HEADERS, json_data={"featured_media": mid}, timeout=30)
                if upd:
                    print("    Featured image set -> post", post_id)
                    image_report["featured_media_id"] = mid
            return mid
        else:
            print("    Media upload FAILED:", mr.text[:100])
            return None
    except Exception as e:
        print("    Media upload error:", e)
        return None

provider_used = None
for i, prompt in enumerate(IMG_PROMPTS):
    print(f"  Generating image {i+1}/4...")
    img_bytes, prov = generate_one_image(prompt, i+1)
    if img_bytes:
        generated_images.append(img_bytes)
        if not provider_used:
            provider_used = prov
        fname = f"nexus14-{ARTICLE_INDEX}-img{i+1}-{int(time.time())}.jpg"
        is_featured = (i == 0)
        mid = upload_image_to_wp(img_bytes, fname, wp_post_id, set_featured=is_featured)
        if mid:
            media_ids.append(mid)
    time.sleep(1)

img_total_time = round(time.time() - img_t_start, 2)
image_report["images_generated"] = len(generated_images) >= 4
image_report["provider_used"] = provider_used
image_report["generation_time_s"] = img_total_time
image_report["cost_usd"] = img_cost
image_report["media_ids"] = media_ids
image_report["image_count"] = len(generated_images)
print(f"  Images: {len(generated_images)}/4 generated, {len(media_ids)}/4 uploaded to WP")

results["images_generated"] = image_report["images_generated"]
results["featured_image_set"] = image_report.get("featured_media_id") is not None

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
