#!/usr/bin/env python3
"""
NEXUS-14 PRODUCTION SCRIPT v1
scripts/produce_article.py

Produit UN article complet pour un topic/market donnés.
Basé sur run_test.py v9 (7/7 PASS vérifié).
- Email non-bloquant (ignoré si erreur)
- Image pipeline: Nano Banana -> gpt-image-1 -> dall-e-3
- WordPress: draft créé automatiquement
- Rapport JSON sauvegardé
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
MARKET = (os.environ.get("TARGET_MARKET") or os.environ.get("INPUT_MARKET") or "usa").lower()
TOPIC = (os.environ.get("TOPIC_OVERRIDE") or os.environ.get("INPUT_TOPIC") or "").strip()
if not TOPIC:
    TOPIC = "best way to send money internationally 2026"

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
NANO_KEY = os.environ.get("NANO_BANANA_API_KEY", "")
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY", "")
WP_URL = os.environ.get("WORDPRESS_URL", "https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME", "")
WP_PASS = os.environ.get("WORDPRESS_PASSWORD", "")
EMAIL_TO = os.environ.get("EMAIL_RECIPIENT", "")

print("=" * 60)
print("NEXUS-14 PRODUCTION v1 — Article #" + ARTICLE_INDEX)
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
    "error": None
}

# ============================================================
# STEP 1: ARTICLE GENERATION — THREE-PASS
# ============================================================
print("[STEP 1] Generating article (three-pass)...")
article_content = ""
openai_cost = 0.0
total_tokens = 0

if not OPENAI_KEY:
    print("  ERROR: OPENAI_API_KEY not set")
    results["article_written"] = False
else:
    try:
        client = openai.OpenAI(api_key=OPENAI_KEY)
        mkt_label = MARKET.upper()

        p1 = (
            "Write the FIRST PART of a detailed article titled: " + TOPIC + "\n\n"
            "Target market: " + mkt_label + " (expats, immigrants, international workers)\n"
            "Write these sections with FULL content (aim for 800+ words total):\n"
            "<h2>Introduction</h2>\n"
            "Write 3 paragraphs (200 words) about the importance of the topic.\n"
            "<h2>Why People Need This Service</h2>\n"
            "Write 3 paragraphs (200 words) about the target audience needs.\n"
            "<h2>Top 7 Services Compared</h2>\n"
            "Write 2 paragraphs introducing the comparison, then a detailed HTML table comparing services.\n"
            "<h2>Detailed Review: Best Option #1</h2>\n"
            "Write 3 paragraphs (200 words). Include: <a href=\"https://moneyabroadguide.com/best-services\">our full guide</a>\n"
            "<h2>Detailed Review: Best Option #2</h2>\n"
            "Write 3 paragraphs (200 words). Include: <a href=\"https://moneyabroadguide.com/compare\">comparison page</a>\n"
            "Use proper HTML tags throughout. Write all sections fully now."
        )
        r1 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": p1}],
            max_tokens=3000, temperature=0.7
        )
        part1 = r1.choices[0].message.content
        total_tokens += r1.usage.total_tokens
        openai_cost += (r1.usage.prompt_tokens / 1000000) * 0.15 + (r1.usage.completion_tokens / 1000000) * 0.60
        print("  Part 1 words:", len(part1.split()))

        p2 = (
            "Continue writing the article about: " + TOPIC + " (market: " + mkt_label + ")\n\n"
            "Write these sections (aim for 900+ words total):\n"
            "<h2>Understanding Fees and Exchange Rates</h2>\n"
            "Write 3 paragraphs (250 words). Include: <a href=\"https://moneyabroadguide.com/exchange-rates\">exchange rate guide</a>\n"
            "<h2>Complete Fee Breakdown: Real Examples</h2>\n"
            "Write detailed comparison (250 words) showing transfer examples with costs.\n"
            "<h2>How Fast Can You Transfer?</h2>\n"
            "Write 2 paragraphs (150 words).\n"
            "<h2>Regulations and Legal Requirements in " + mkt_label + "</h2>\n"
            "Write 3 paragraphs (200 words). Include: <a href=\"https://moneyabroadguide.com/regulations\">regulations guide</a>\n"
            "<h2>Safety and Security</h2>\n"
            "Write 2 paragraphs (150 words). Include: <a href=\"https://moneyabroadguide.com/security\">security tips</a>\n"
            "Use proper HTML tags. Write all sections fully now."
        )
        r2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": p2}],
            max_tokens=3000, temperature=0.7
        )
        part2 = r2.choices[0].message.content
        total_tokens += r2.usage.total_tokens
        openai_cost += (r2.usage.prompt_tokens / 1000000) * 0.15 + (r2.usage.completion_tokens / 1000000) * 0.60
        print("  Part 2 words:", len(part2.split()))

        p3 = (
            "Write the FINAL PART of the article about: " + TOPIC + " (market: " + mkt_label + ")\n\n"
            "Write these sections (aim for 600+ words total):\n"
            "<h2>Step-by-Step Guide</h2>\n"
            "Write numbered steps (200 words). Include: <a href=\"https://moneyabroadguide.com/how-to-guide\">how-to guide</a>\n"
            "<h2>5 Expert Tips to Save Money</h2>\n"
            "Write 5 tips (200 words). Include: <a href=\"https://moneyabroadguide.com/tips\">money saving tips</a>\n"
            "<h2>Frequently Asked Questions</h2>\n"
            "Write 5 Q&A pairs (200 words).\n"
            "<h2>Conclusion</h2>\n"
            "Write strong conclusion (100 words).\n"
            "Use proper HTML tags. Write all sections fully now."
        )
        r3 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": p3}],
            max_tokens=2000, temperature=0.7
        )
        part3 = r3.choices[0].message.content
        total_tokens += r3.usage.total_tokens
        openai_cost += (r3.usage.prompt_tokens / 1000000) * 0.15 + (r3.usage.completion_tokens / 1000000) * 0.60
        print("  Part 3 words:", len(part3.split()))

        article_content = part1 + "\n\n" + part2 + "\n\n" + part3
        total_words = len(article_content.split())
        print("  TOTAL words:", total_words)
        results["article_written"] = len(article_content) > 500
        results["word_count_2000plus"] = total_words >= 2000
        print("  word_count_2000plus:", results["word_count_2000plus"])
    except Exception as e:
        print("  ERROR:", e)
        results["article_written"] = False
        results["word_count_2000plus"] = False

# ============================================================
# STEP 2: SEO SCORING
# ============================================================
print()
print("[STEP 2] SEO scoring...")
seo_score = 0
if article_content:
    words_in_topic = [w for w in TOPIC.lower().split() if len(w) > 3]
    found_kw = sum(1 for w in words_in_topic if w in article_content.lower())
    if found_kw >= 2: seo_score += 25
    if "<h2>" in article_content: seo_score += 20
    if "<table" in article_content: seo_score += 15
    if len(article_content) > 5000: seo_score += 20
    if "href=" in article_content: seo_score += 20
results["seo_score_85plus"] = seo_score >= 85
print("  SEO score:", seo_score)

# ============================================================
# STEP 3: EEAT SCORING
# ============================================================
print()
print("[STEP 3] EEAT scoring...")
eeat_score = 0
if article_content:
    cl = article_content.lower()
    if any(w in cl for w in ["expert", "research", "study", "data", "statistic"]): eeat_score += 25
    if any(w in cl for w in ["review", "comparison", "tested", "analysis"]): eeat_score += 25
    if any(w in cl for w in ["fee", "cost", "price", "rate", "percent", "%"]): eeat_score += 25
    if len(article_content.split()) >= 1500: eeat_score += 25
results["eeat_score_80plus"] = eeat_score >= 80
print("  EEAT score:", eeat_score)

# ============================================================
# STEP 4: INTERNAL LINKS
# ============================================================
print()
print("[STEP 4] Counting internal links...")
if article_content:
    links = re.findall(r'href="(https?://[^"]+)"', article_content)
    internal_links = sum(1 for l in links if "moneyabroadguide.com" in l)
else:
    internal_links = 0
results["internal_links_5plus"] = internal_links >= 5
print("  Internal links:", internal_links)

# ============================================================
# STEP 5: POST TO WORDPRESS
# ============================================================
print()
print("[STEP 5] Creating WordPress draft...")
wp_post_id = None
creds_wp = b64encode((WP_USER + ":" + WP_PASS).encode()).decode() if WP_USER and WP_PASS else ""
wp_headers = {
    "Authorization": "Basic " + creds_wp,
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; NEXUS14/1.0)",
}
if not WP_USER or not WP_PASS:
    print("  ERROR: WP credentials missing")
    results["wordpress_draft_created"] = False
else:
    try:
        r = requests.post(
            WP_URL + "/wp-json/wp/v2/posts",
            headers=wp_headers,
            json={"title": TOPIC.title(), "content": article_content, "status": "draft"},
            timeout=60
        )
        print("  WP Status:", r.status_code)
        if r.status_code in (200, 201):
            d = r.json()
            wp_post_id = d.get("id")
            print("  SUCCESS! Post ID:", wp_post_id)
            results["wordpress_draft_created"] = True
        else:
            print("  FAILED:", r.text[:300])
            results["wordpress_draft_created"] = False
    except Exception as e:
        print("  ERROR:", e)
        results["wordpress_draft_created"] = False

# ============================================================
# STEP 6: IMAGE PIPELINE
# ============================================================
print()
print("[STEP 6] IMAGE PIPELINE")
print("  Chain: Nano Banana -> gpt-image-1 -> dall-e-3")
print("-" * 50)

img_t_start = time.time()
img_prompt = (
    "Professional financial infographic for " + TOPIC + ". "
    "Clean modern design, blue and green colors, white background, "
    "data visualization style, no people."
)
image_bytes = None
image_url_final = None
provider_used = None
img_cost = 0.0

def try_upload_to_wp(img_bytes, post_id):
    try:
        media_headers = {
            "Authorization": "Basic " + creds_wp,
            "Content-Disposition": "attachment; filename=nexus14-prod-" + str(int(time.time())) + ".jpg",
            "Content-Type": "image/jpeg",
        }
        mr = requests.post(WP_URL + "/wp-json/wp/v2/media", headers=media_headers, data=img_bytes, timeout=60)
        print("  WP Media:", mr.status_code)
        if mr.status_code in (200, 201):
            media_id = mr.json().get("id")
            media_src = mr.json().get("source_url", "")
            print("  Media ID:", media_id, "URL:", media_src[:60])
            if post_id:
                upd_h = {"Authorization": "Basic " + creds_wp, "Content-Type": "application/json"}
                requests.post(WP_URL + "/wp-json/wp/v2/posts/" + str(post_id),
                              headers=upd_h, json={"featured_media": media_id}, timeout=30)
                print("  Featured image set on post", post_id)
            return media_src
        else:
            print("  Media upload failed:", mr.text[:150])
            return None
    except Exception as e:
        print("  Media upload error:", e)
        return None

# Provider 1: Nano Banana
print()
print("  [P1] Nano Banana...")
att1 = {"provider": "nano_banana", "status": "skipped", "error": None, "time_s": 0}
if NANO_KEY:
    t1 = time.time()
    nb_endpoints = [
        "https://api.nano-banana.com/v1/images/generations",
        "https://app.nano-banana.com/api/v1/images/generations",
        "https://www.nano-banana.com/api/v1/images/generations",
    ]
    nb_payload = {"prompt": img_prompt, "n": 1, "size": "1024x1024"}
    nb_headers = {"Authorization": "Bearer " + NANO_KEY, "Content-Type": "application/json"}
    nb_ok = False
    for ep in nb_endpoints:
        try:
            print("  Trying:", ep)
            nb_r = requests.post(ep, headers=nb_headers, json=nb_payload, timeout=30)
            print("  Status:", nb_r.status_code)
            if nb_r.status_code in (200, 201):
                nb_data = nb_r.json()
                if "data" in nb_data and nb_data["data"]:
                    item = nb_data["data"][0]
                    if "b64_json" in item:
                        image_bytes = base64.b64decode(item["b64_json"])
                        provider_used = "nano_banana"
                        img_cost += 0.002
                        att1["status"] = "success"
                        nb_ok = True
                        break
                    elif "url" in item:
                        img_resp = requests.get(item["url"], timeout=30)
                        image_bytes = img_resp.content
                        image_url_final = item["url"]
                        provider_used = "nano_banana"
                        img_cost += 0.002
                        att1["status"] = "success"
                        nb_ok = True
                        break
        except Exception as ep_e:
            print("  EP error:", str(ep_e)[:80])
    att1["time_s"] = round(time.time() - t1, 2)
    if not nb_ok:
        att1["status"] = "failed"
        att1["error"] = "All NB endpoints failed"
else:
    att1["error"] = "NANO_BANANA_API_KEY not set"
image_report["attempts"].append(att1)

# Provider 2: gpt-image-1
if not provider_used:
    print()
    print("  [P2] OpenAI gpt-image-1...")
    att2 = {"provider": "openai_gpt_image_1", "status": "skipped", "error": None, "time_s": 0}
    if OPENAI_KEY:
        t2 = time.time()
        try:
            ci = openai.OpenAI(api_key=OPENAI_KEY)
            ir2 = ci.images.generate(model="gpt-image-1", prompt=img_prompt, size="1024x1024", n=1)
            att2["time_s"] = round(time.time() - t2, 2)
            if ir2.data[0].b64_json:
                image_bytes = base64.b64decode(ir2.data[0].b64_json)
                provider_used = "openai_gpt_image_1"
                img_cost += 0.04
                att2["status"] = "success"
                print("  -> gpt-image-1 SUCCESS")
            elif ir2.data[0].url:
                image_bytes = requests.get(ir2.data[0].url, timeout=30).content
                image_url_final = ir2.data[0].url
                provider_used = "openai_gpt_image_1"
                img_cost += 0.04
                att2["status"] = "success"
                print("  -> gpt-image-1 SUCCESS (url)")
        except Exception as e:
            att2["time_s"] = round(time.time() - t2, 2)
            att2["status"] = "error"
            att2["error"] = str(e)
            print("  -> gpt-image-1 ERROR:", e)
    else:
        att2["error"] = "OPENAI_API_KEY not set"
    image_report["attempts"].append(att2)

# Provider 3: dall-e-3
if not provider_used:
    print()
    print("  [P3] dall-e-3 (fallback)...")
    att3 = {"provider": "openai_dalle3", "status": "skipped", "error": None, "time_s": 0}
    if OPENAI_KEY:
        t3 = time.time()
        try:
            ci3 = openai.OpenAI(api_key=OPENAI_KEY)
            dalle_prompt = (
                "Professional financial infographic comparing services. "
                "Blue green color scheme, modern flat design, no text."
            )
            ir3 = ci3.images.generate(model="dall-e-3", prompt=dalle_prompt, size="1024x1024", quality="standard", n=1)
            att3["time_s"] = round(time.time() - t3, 2)
            url3 = ir3.data[0].url
            if url3:
                image_bytes = requests.get(url3, timeout=30).content
                image_url_final = url3
                provider_used = "openai_dalle3"
                img_cost += 0.04
                att3["status"] = "success"
                print("  -> dall-e-3 SUCCESS")
        except Exception as e:
            att3["time_s"] = round(time.time() - t3, 2)
            att3["status"] = "error"
            att3["error"] = str(e)
            print("  -> dall-e-3 ERROR:", e)
    else:
        att3["error"] = "OPENAI_API_KEY not set"
    image_report["attempts"].append(att3)

img_total_time = round(time.time() - img_t_start, 2)

if provider_used and image_bytes:
    print()
    print("  Uploading image to WordPress...")
    wp_media_url = try_upload_to_wp(image_bytes, wp_post_id)
    if wp_media_url:
        image_report["image_urls"].append(wp_media_url)
    elif image_url_final:
        image_report["image_urls"].append(image_url_final)
    image_report["images_generated"] = True
    image_report["provider_used"] = provider_used
    image_report["generation_time_s"] = img_total_time
    image_report["cost_usd"] = img_cost
else:
    print()
    print("  ALL IMAGE PROVIDERS FAILED — article not blocked")
    image_report["error"] = "All providers failed"

results["images_generated"] = image_report["images_generated"]

# ============================================================
# STEP 7: EMAIL (non-bloquant — ignoré si erreur)
# ============================================================
print()
print("[STEP 7] Email notification (non-bloquant)...")
try:
    if SENDGRID_KEY and EMAIL_TO:
        passed_count = sum(1 for v in results.values() if v)
        subject = "NEXUS-14 Article #" + ARTICLE_INDEX + " - " + TOPIC[:50] + " - " + str(passed_count) + "/7"
        body = "NEXUS-14 Production\nArticle #" + ARTICLE_INDEX + "\nTopic: " + TOPIC + "\nMarket: " + MARKET.upper() + "\n\n"
        for k, v in results.items():
            body += ("PASS" if v else "FAIL") + " " + k + "\n"
        body += "\nPost ID: " + str(wp_post_id)
        body += "\nImage: " + str(image_report.get("provider_used", "none"))
        sg_data = {
            "personalizations": [{"to": [{"email": EMAIL_TO}]}],
            "from": {"email": "noreply@moneyabroadguide.com"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }
        sg_r = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": "Bearer " + SENDGRID_KEY, "Content-Type": "application/json"},
            json=sg_data, timeout=30
        )
        print("  Email status:", sg_r.status_code)
        if sg_r.status_code not in (200, 201, 202):
            print("  Email failed (non-bloquant, ignoré)")
    else:
        print("  Skipped (no SendGrid key or recipient)")
except Exception as e:
    print("  Email error (ignoré):", e)

# ============================================================
# FINAL SUMMARY
# ============================================================
elapsed = round(time.time() - START, 1)
checks = [
    ("article_written", results.get("article_written", False)),
    ("word_count_2000plus", results.get("word_count_2000plus", False)),
    ("seo_score_85plus", results.get("seo_score_85plus", False)),
    ("eeat_score_80plus", results.get("eeat_score_80plus", False)),
    ("internal_links_5plus", results.get("internal_links_5plus", False)),
    ("wordpress_draft_created", results.get("wordpress_draft_created", False)),
    ("images_generated", results.get("images_generated", False)),
]
passed = sum(1 for _, v in checks if v)
total = len(checks)
critical = ["article_written", "word_count_2000plus", "wordpress_draft_created"]
critical_ok = all(results.get(c, False) for c in critical)

print()
print("=" * 60)
print("PRODUCTION REPORT — Article #" + ARTICLE_INDEX)
print("=" * 60)
for name, val in checks:
    print(("[PASS] " if val else "[FAIL] ") + name)
print()
print("Score  :", str(passed) + "/" + str(total))
print("Topic  :", TOPIC)
print("Market :", MARKET.upper())
print("Post ID:", wp_post_id)
print("Image  :", image_report.get("provider_used", "none"))
print("Cost   : $" + str(round(openai_cost + img_cost, 4)))
print("Time   :", str(elapsed) + "s")
if passed >= 6 and critical_ok:
    print("STATUS : PUBLISHED (draft)")
elif passed >= 5 and critical_ok:
    print("STATUS : PARTIAL")
else:
    print("STATUS : FAIL")
print("=" * 60)

report = {
    "article_index": ARTICLE_INDEX,
    "topic": TOPIC,
    "market": MARKET,
    "checks": {n: v for n, v in checks},
    "score": str(passed) + "/" + str(total),
    "critical_ok": critical_ok,
    "wp_post_id": wp_post_id,
    "image_pipeline": image_report,
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

if not (passed >= 6 and critical_ok):
    sys.exit(1)
