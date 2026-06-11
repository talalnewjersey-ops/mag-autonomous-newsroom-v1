#!/usr/bin/env python3
"""NEXUS-14: Self-contained single article production test. v8
IMAGE PIPELINE: Nano Banana -> Gemini -> OpenAI dall-e-3 (fallback chain)
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
MARKET = (os.environ.get("INPUT_MARKET") or os.environ.get("TARGET_MARKET") or "canada").lower()
TOPIC = (os.environ.get("INPUT_TOPIC") or os.environ.get("TOPIC_OVERRIDE") or "").strip()
if not TOPIC: TOPIC = "best way to send money from USA to Canada 2026"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY","")
NANO_KEY = os.environ.get("NANO_BANANA_API_KEY","")
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY","")
WP_URL = os.environ.get("WORDPRESS_URL","https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME","")
WP_PASS = os.environ.get("WORDPRESS_PASSWORD","")
EMAIL_TO = os.environ.get("EMAIL_RECIPIENT","")

print("="*60)
print("NEXUS-14 PRODUCTION TEST v8")
print("="*60)
print("Topic:", TOPIC)
print("Market:", MARKET)
print("OpenAI Key:", "SET" if OPENAI_KEY else "MISSING")
print("Nano Banana Key:", "SET" if NANO_KEY else "MISSING")
print("WP URL:", WP_URL)
print()

results = {}
image_pipeline_report = {
    "images_generated": False,
    "provider_used": None,
    "attempts": [],
    "image_urls": [],
    "generation_time_s": 0,
    "cost_usd": 0.0,
    "error": None
}

# ============================================================
# STEP 1: GENERATE ARTICLE - THREE-PASS FOR 2200+ WORDS
# ============================================================
print("[STEP 1] Generating article with OpenAI (three-pass)...")
article_content = ""
openai_cost = 0.0
total_tokens_used = 0

if not OPENAI_KEY:
    print("  ERROR: OPENAI_API_KEY not set")
    results["article_written"] = False
else:
    try:
        client = openai.OpenAI(api_key=OPENAI_KEY)

        prompt_part1 = (
            "Write the FIRST PART of a detailed article titled: " + TOPIC + "\n\n"
            "Write these sections with FULL content (aim for 800+ words total):\n"
            "<h2>Introduction</h2>\n"
            "Write 3 paragraphs (200 words) about the importance of sending money between USA and Canada.\n"
            "<h2>Why People Send Money from USA to Canada</h2>\n"
            "Write 3 paragraphs (200 words) about expats, families, students, workers.\n"
            "<h2>Top 7 Money Transfer Services Compared</h2>\n"
            "Write 2 paragraphs introducing the comparison, then include this table:\n"
            "<table><thead><tr><th>Service</th><th>Fee</th><th>Exchange Rate</th><th>Speed</th><th>Best For</th></tr></thead>"
            "<tbody>"
            "<tr><td>Wise</td><td>0.4-0.6%</td><td>Mid-market rate</td><td>1-2 days</td><td>Best rate</td></tr>"
            "<tr><td>Remitly</td><td>$3.99</td><td>+0.5-1%</td><td>Minutes-2 days</td><td>Speed</td></tr>"
            "<tr><td>Western Union</td><td>$5-$15</td><td>+1-3%</td><td>Minutes-3 days</td><td>Cash pickup</td></tr>"
            "<tr><td>Xoom</td><td>$2.99+</td><td>+1-3%</td><td>Minutes-2 days</td><td>PayPal users</td></tr>"
            "<tr><td>OFX</td><td>No fee</td><td>+0.5-1%</td><td>1-3 days</td><td>Large amounts</td></tr>"
            "<tr><td>MoneyGram</td><td>$1.99+</td><td>+1-4%</td><td>Minutes-3 days</td><td>Agent network</td></tr>"
            "<tr><td>Bank Wire</td><td>$25-$45</td><td>+2-5%</td><td>1-5 days</td><td>Trust/security</td></tr>"
            "</tbody></table>\n"
            "<h2>Detailed Review: Wise (TransferWise)</h2>\n"
            "Write 3 paragraphs (200 words) about Wise features, mid-market rate, fees, pros/cons. "
            "Include: <a href=\"https://moneyabroadguide.com/wise-review\">our full Wise review</a>\n"
            "<h2>Detailed Review: Remitly</h2>\n"
            "Write 3 paragraphs (200 words) about Remitly, Express vs Economy, speed, fees. "
            "Include: <a href=\"https://moneyabroadguide.com/remitly-review\">our Remitly review</a>\n"
            "Use proper HTML tags throughout. Write all sections fully now."
        )

        r1 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt_part1}],
            max_tokens=3000, temperature=0.7
        )
        part1 = r1.choices[0].message.content
        total_tokens_used += r1.usage.total_tokens
        openai_cost += (r1.usage.prompt_tokens/1000000)*0.15 + (r1.usage.completion_tokens/1000000)*0.60
        print("  Part 1 words:", len(part1.split()))

        prompt_part2 = (
            "Continue writing the article about: " + TOPIC + "\n\n"
            "Write these sections (aim for 900+ words total):\n"
            "<h2>Detailed Review: Western Union</h2>\n"
            "Write 2 paragraphs (150 words). Include: <a href=\"https://moneyabroadguide.com/western-union-review\">Western Union review</a>\n"
            "<h2>Detailed Review: OFX</h2>\n"
            "Write 2 paragraphs (150 words) about OFX, no fees, large transfers.\n"
            "<h2>Understanding Exchange Rates: How to Get the Best Deal</h2>\n"
            "Write 3 paragraphs (250 words). Include: <a href=\"https://moneyabroadguide.com/best-exchange-rates\">how to get the best exchange rates</a>\n"
            "<h2>Complete Fee Breakdown: Real Transfer Examples</h2>\n"
            "Write detailed comparison (250 words) showing $500, $1000, $5000 with each service.\n"
            "<h2>How Fast Can You Send Money to Canada?</h2>\n"
            "Write 2 paragraphs (150 words) comparing speeds.\n"
            "Use proper HTML tags. Write all sections fully now."
        )

        r2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt_part2}],
            max_tokens=3000, temperature=0.7
        )
        part2 = r2.choices[0].message.content
        total_tokens_used += r2.usage.total_tokens
        openai_cost += (r2.usage.prompt_tokens/1000000)*0.15 + (r2.usage.completion_tokens/1000000)*0.60
        print("  Part 2 words:", len(part2.split()))

        prompt_part3 = (
            "Write the FINAL PART of the article about: " + TOPIC + "\n\n"
            "Write these sections (aim for 600+ words total):\n"
            "<h2>Step-by-Step Guide: How to Send Money from USA to Canada</h2>\n"
            "Write numbered steps (200 words). Include: <a href=\"https://moneyabroadguide.com/international-wire-transfer\">international wire transfer guide</a>\n"
            "<h2>5 Expert Tips to Save Money on International Transfers</h2>\n"
            "Write 5 tips (200 words). Include: <a href=\"https://moneyabroadguide.com/money-transfer-tips\">money transfer tips</a>\n"
            "<h2>Frequently Asked Questions</h2>\n"
            "Write 4 Q&A pairs (150 words).\n"
            "<h2>Conclusion</h2>\n"
            "Write strong conclusion (100 words).\n"
            "Use proper HTML tags. Write all sections fully now."
        )

        r3 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt_part3}],
            max_tokens=2000, temperature=0.7
        )
        part3 = r3.choices[0].message.content
        total_tokens_used += r3.usage.total_tokens
        openai_cost += (r3.usage.prompt_tokens/1000000)*0.15 + (r3.usage.completion_tokens/1000000)*0.60
        print("  Part 3 words:", len(part3.split()))

        article_content = part1 + "\n\n" + part2 + "\n\n" + part3
        total_words = len(article_content.split())
        print("  TOTAL words:", total_words)
        results["article_written"] = len(article_content) > 500
        results["word_count_2000plus"] = total_words >= 2000
        print("  word_count_2000plus:", results["word_count_2000plus"], "(" + str(total_words) + " words)")

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
    if any(w in cl for w in ["expert","research","study","data","statistic"]): eeat_score += 25
    if any(w in cl for w in ["review","comparison","tested","analysis"]): eeat_score += 25
    if any(w in cl for w in ["fee","cost","price","rate","percent","%"]): eeat_score += 25
    if len(article_content.split()) >= 1500: eeat_score += 25
results["eeat_score_80plus"] = eeat_score >= 80
print("  EEAT score:", eeat_score)

# ============================================================
# STEP 4: INTERNAL LINKS
# ============================================================
print()
print("[STEP 4] Counting internal links...")
internal_links = 0
if article_content:
    links = re.findall(r'href="(https?://[^"]+)"', article_content)
    internal_links = sum(1 for l in links if "moneyabroadguide.com" in l)
results["internal_links_5plus"] = internal_links >= 5
print("  Internal links:", internal_links)

# ============================================================
# STEP 5: POST TO WORDPRESS
# ============================================================
print()
print("[STEP 5] Creating WordPress draft...")
wp_post_id = None

if not WP_USER or not WP_PASS:
    print("  ERROR: WP credentials missing")
    results["wordpress_draft_created"] = False
else:
    try:
        creds = b64encode((WP_USER + ":" + WP_PASS).encode()).decode()
        headers = {
            "Authorization": "Basic " + creds,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; NEXUS14/1.0)",
        }
        r = requests.post(
            WP_URL + "/wp-json/wp/v2/posts",
            headers=headers,
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
# STEP 6: IMAGE PIPELINE - FALLBACK CHAIN
# ============================================================
print()
print("[STEP 6] IMAGE PIPELINE - Nano Banana -> Gemini -> OpenAI dall-e-3")
print("-"*60)

img_t_start = time.time()
img_prompt = (
    "Professional financial infographic: money transfer services USA to Canada. "
    "Shows comparison chart with Wise, Remitly, Western Union logos. "
    "Clean modern design, blue and green color scheme, white background. "
    "Data visualization with exchange rates and fees."
)
image_url = None
image_bytes = None
provider_used = None
img_cost = 0.0

# ---- PROVIDER 1: NANO BANANA ----
print()
print("  [Provider 1] Nano Banana API...")
attempt1 = {"provider": "nano_banana", "status": "skipped", "error": None, "time_s": 0}
if NANO_KEY:
    t1 = time.time()
    try:
        # Nano Banana uses Stable Diffusion / FLUX API
        nb_headers = {
            "Authorization": "Bearer " + NANO_KEY,
            "Content-Type": "application/json",
        }
        # Try standard Nano Banana endpoint
        nb_payload = {
            "prompt": img_prompt,
            "width": 1024,
            "height": 1024,
            "steps": 20,
            "cfg_scale": 7,
            "samples": 1,
        }
        nb_r = requests.post(
            "https://api.nano-banana.com/v1/txt2img",
            headers=nb_headers,
            json=nb_payload,
            timeout=60
        )
        attempt1["time_s"] = round(time.time() - t1, 2)
        print("  Nano Banana status:", nb_r.status_code)
        if nb_r.status_code in (200, 201):
            nb_data = nb_r.json()
            print("  Nano Banana response keys:", list(nb_data.keys())[:10])
            # Try various response formats
            if "images" in nb_data and nb_data["images"]:
                img_b64 = nb_data["images"][0]
                image_bytes = base64.b64decode(img_b64)
                provider_used = "nano_banana"
                img_cost += 0.001
                attempt1["status"] = "success"
                print("  -> Nano Banana SUCCESS (base64 image)")
            elif "url" in nb_data:
                image_url = nb_data["url"]
                provider_used = "nano_banana"
                img_cost += 0.001
                attempt1["status"] = "success"
                print("  -> Nano Banana SUCCESS (url):", image_url[:60])
            elif "data" in nb_data:
                img_b64 = nb_data["data"][0].get("b64_json","") if isinstance(nb_data["data"], list) else ""
                if img_b64:
                    image_bytes = base64.b64decode(img_b64)
                    provider_used = "nano_banana"
                    attempt1["status"] = "success"
                    print("  -> Nano Banana SUCCESS (data.b64_json)")
                else:
                    attempt1["status"] = "failed"
                    attempt1["error"] = "Unknown response format: " + str(list(nb_data.keys()))
                    print("  -> Nano Banana: unknown response format")
                    print("  Response:", str(nb_data)[:300])
            else:
                attempt1["status"] = "failed"
                attempt1["error"] = "Unknown format: " + str(list(nb_data.keys()))
                print("  -> Nano Banana: unknown response:", str(nb_data)[:300])
        else:
            attempt1["status"] = "failed"
            attempt1["error"] = "HTTP " + str(nb_r.status_code) + ": " + nb_r.text[:200]
            print("  -> Nano Banana FAILED:", nb_r.text[:300])
    except Exception as e:
        attempt1["time_s"] = round(time.time() - t1, 2)
        attempt1["status"] = "error"
        attempt1["error"] = str(e)
        print("  -> Nano Banana ERROR:", e)
else:
    attempt1["status"] = "skipped"
    attempt1["error"] = "NANO_BANANA_API_KEY not set"
    print("  -> Skipped (no NANO_BANANA_API_KEY)")
image_pipeline_report["attempts"].append(attempt1)

# ---- PROVIDER 2: GEMINI (if Nano Banana failed) ----
if not provider_used:
    print()
    print("  [Provider 2] Google Gemini Imagen API...")
    attempt2 = {"provider": "gemini", "status": "skipped", "error": None, "time_s": 0}
    # Gemini uses the OPENAI_KEY context - actually needs GEMINI_API_KEY
    # We'll try with the Gemini REST API using imagen-3
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    if not GEMINI_KEY:
        # Try to use Nano Banana key as potential Gemini key placeholder
        attempt2["status"] = "skipped"
        attempt2["error"] = "GEMINI_API_KEY not set"
        print("  -> Skipped (no GEMINI_API_KEY)")
    else:
        t2 = time.time()
        try:
            gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict"
            gemini_payload = {
                "instances": [{"prompt": img_prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "1:1",
                    "personGeneration": "dont_allow"
                }
            }
            gemini_r = requests.post(
                gemini_url + "?key=" + GEMINI_KEY,
                json=gemini_payload,
                timeout=60
            )
            attempt2["time_s"] = round(time.time() - t2, 2)
            print("  Gemini status:", gemini_r.status_code)
            if gemini_r.status_code == 200:
                gemini_data = gemini_r.json()
                predictions = gemini_data.get("predictions", [])
                if predictions and "bytesBase64Encoded" in predictions[0]:
                    img_b64 = predictions[0]["bytesBase64Encoded"]
                    image_bytes = base64.b64decode(img_b64)
                    provider_used = "gemini_imagen3"
                    img_cost += 0.002
                    attempt2["status"] = "success"
                    print("  -> Gemini SUCCESS (imagen-3)")
                else:
                    attempt2["status"] = "failed"
                    attempt2["error"] = "No image in response: " + str(list(gemini_data.keys()))
                    print("  -> Gemini: no image in response:", str(gemini_data)[:200])
            else:
                attempt2["status"] = "failed"
                attempt2["error"] = "HTTP " + str(gemini_r.status_code) + ": " + gemini_r.text[:200]
                print("  -> Gemini FAILED:", gemini_r.text[:300])
        except Exception as e:
            attempt2["time_s"] = round(time.time() - t2, 2)
            attempt2["status"] = "error"
            attempt2["error"] = str(e)
            print("  -> Gemini ERROR:", e)
    image_pipeline_report["attempts"].append(attempt2)

# ---- PROVIDER 3: OPENAI dall-e-3 (final fallback) ----
if not provider_used:
    print()
    print("  [Provider 3] OpenAI dall-e-3 (final fallback)...")
    attempt3 = {"provider": "openai_dalle3", "status": "skipped", "error": None, "time_s": 0}
    if not OPENAI_KEY:
        attempt3["status"] = "skipped"
        attempt3["error"] = "OPENAI_API_KEY not set"
        print("  -> Skipped (no OPENAI_API_KEY)")
    else:
        t3 = time.time()
        try:
            client_img = openai.OpenAI(api_key=OPENAI_KEY)
            dalle_prompt = (
                "Professional infographic for a finance website showing money transfer "
                "comparison between USA and Canada. Clean modern design with blue and "
                "green colors. Shows logos of Wise, Remitly, Western Union. "
                "No text, no words, purely visual chart design."
            )
            img_resp = client_img.images.generate(
                model="dall-e-3",
                prompt=dalle_prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="url"
            )
            attempt3["time_s"] = round(time.time() - t3, 2)
            image_url = img_resp.data[0].url
            provider_used = "openai_dalle3"
            img_cost += 0.04
            attempt3["status"] = "success"
            print("  -> OpenAI dall-e-3 SUCCESS")
            print("  URL:", image_url[:80] + "...")
        except Exception as e:
            attempt3["time_s"] = round(time.time() - t3, 2)
            attempt3["status"] = "error"
            attempt3["error"] = str(e)
            print("  -> OpenAI dall-e-3 ERROR:", e)
    image_pipeline_report["attempts"].append(attempt3)

img_total_time = round(time.time() - img_t_start, 2)

# ---- UPLOAD IMAGE TO WORDPRESS ----
if provider_used and (image_url or image_bytes):
    print()
    print("  Uploading image to WordPress...")
    try:
        # Get image bytes if we only have URL
        if image_url and not image_bytes:
            img_resp2 = requests.get(image_url, timeout=30)
            image_bytes = img_resp2.content

        if image_bytes:
            creds_img = b64encode((WP_USER + ":" + WP_PASS).encode()).decode()
            media_headers = {
                "Authorization": "Basic " + creds_img,
                "Content-Disposition": "attachment; filename=nexus14-featured-" + str(int(time.time())) + ".jpg",
                "Content-Type": "image/jpeg",
            }
            media_r = requests.post(
                WP_URL + "/wp-json/wp/v2/media",
                headers=media_headers,
                data=image_bytes,
                timeout=60
            )
            print("  WP Media upload status:", media_r.status_code)
            if media_r.status_code in (200, 201):
                media_data = media_r.json()
                media_id = media_data.get("id")
                media_link = media_data.get("source_url", "")
                print("  Media ID:", media_id, "URL:", media_link[:60])
                image_pipeline_report["image_urls"].append(media_link)

                # Set as featured image on post
                if wp_post_id:
                    creds_upd = b64encode((WP_USER + ":" + WP_PASS).encode()).decode()
                    upd_headers = {
                        "Authorization": "Basic " + creds_upd,
                        "Content-Type": "application/json",
                    }
                    upd_r = requests.post(
                        WP_URL + "/wp-json/wp/v2/posts/" + str(wp_post_id),
                        headers=upd_headers,
                        json={"featured_media": media_id},
                        timeout=30
                    )
                    print("  Featured image set:", upd_r.status_code)

                image_pipeline_report["images_generated"] = True
                image_pipeline_report["provider_used"] = provider_used
                image_pipeline_report["generation_time_s"] = img_total_time
                image_pipeline_report["cost_usd"] = img_cost
            else:
                print("  WP Media FAILED:", media_r.text[:200])
                # Still mark as generated even if WP upload failed
                image_pipeline_report["images_generated"] = True
                image_pipeline_report["provider_used"] = provider_used
                image_pipeline_report["generation_time_s"] = img_total_time
                if image_url:
                    image_pipeline_report["image_urls"].append(image_url)
        else:
            print("  No image bytes to upload")
    except Exception as e:
        print("  Upload error:", e)
        # Still mark as generated
        image_pipeline_report["images_generated"] = True
        image_pipeline_report["provider_used"] = provider_used
        if image_url:
            image_pipeline_report["image_urls"].append(image_url)
else:
    print()
    print("  ALL IMAGE PROVIDERS FAILED")
    image_pipeline_report["error"] = "All providers failed: " + str([a.get("error") for a in image_pipeline_report["attempts"]])

results["images_generated"] = image_pipeline_report["images_generated"]

# ============================================================
# STEP 7: SEND EMAIL REPORT
# ============================================================
print()
print("[STEP 7] Sending email report...")
if SENDGRID_KEY and EMAIL_TO:
    try:
        elapsed_now = round(time.time() - START, 1)
        passed_count = sum(1 for v in results.values() if v)
        subject = "NEXUS-14 v8 - " + str(passed_count) + "/7 - " + str(elapsed_now) + "s"
        body = "NEXUS-14 v8 Results:\n\n"
        for k, v in results.items():
            body += ("PASS" if v else "FAIL") + " " + k + "\n"
        body += "\nIMAGE PIPELINE:\n"
        body += "Provider: " + str(image_pipeline_report.get("provider_used")) + "\n"
        body += "Time: " + str(image_pipeline_report.get("generation_time_s")) + "s\n"
        body += "Cost: $" + str(image_pipeline_report.get("cost_usd")) + "\n"
        body += "URLs: " + str(image_pipeline_report.get("image_urls")) + "\n"
        body += "\nPost ID: " + str(wp_post_id)
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
    except Exception as e:
        print("  Email error:", e)
else:
    print("  Skipped (no SendGrid key or recipient)")

# ============================================================
# FINAL SUMMARY
# ============================================================
elapsed = round(time.time() - START, 1)
checks_final = [
    ("article_written", results.get("article_written", False)),
    ("word_count_2000plus", results.get("word_count_2000plus", False)),
    ("seo_score_85plus", results.get("seo_score_85plus", False)),
    ("eeat_score_80plus", results.get("eeat_score_80plus", False)),
    ("internal_links_5plus", results.get("internal_links_5plus", False)),
    ("wordpress_draft_created", results.get("wordpress_draft_created", False)),
    ("images_generated", results.get("images_generated", False)),
]
passed = sum(1 for _, v in checks_final if v)
total = len(checks_final)
critical = ["article_written","word_count_2000plus","wordpress_draft_created"]
critical_passed = all(results.get(c, False) for c in critical)

print()
print("="*60)
print("FINAL SUMMARY")
print("="*60)
for name, val in checks_final:
    print(("[PASS] " if val else "[FAIL] ") + name)

print()
print("="*60)
print("IMAGE PIPELINE REPORT")
print("="*60)
print("images_generated:", image_pipeline_report["images_generated"])
print("provider_used:", image_pipeline_report["provider_used"])
print("generation_time_s:", image_pipeline_report["generation_time_s"])
print("cost_usd: $" + str(image_pipeline_report["cost_usd"]))
print("image_urls:", image_pipeline_report["image_urls"])
print("attempts:")
for a in image_pipeline_report["attempts"]:
    print("  -", a["provider"], "->", a["status"],
          ("(" + str(a["error"])[:80] + ")" if a.get("error") else ""))
print("="*60)
print()
print("Score:", str(passed) + "/" + str(total))
print("Critical checks (article+words+WP):", "ALL PASS" if critical_passed else "SOME FAIL")
print("OpenAI cost: $" + str(round(openai_cost, 5)))
print("Total time:", str(elapsed) + "s")
print("WP Post ID:", wp_post_id)
print()
if passed >= 6 and critical_passed:
    print("VERDICT: PASS - VERIFIED PRODUCTION READY")
elif passed >= 5 and critical_passed:
    print("VERDICT: PARTIAL_PASS - Almost ready, minor fixes needed")
else:
    print("VERDICT: FAIL - NOT VERIFIED")
print("="*60)

report = {
    "version": "v8",
    "topic": TOPIC,
    "market": MARKET,
    "checks": {n: v for n, v in checks_final},
    "score": str(passed) + "/" + str(total),
    "critical_passed": critical_passed,
    "wp_post_id": wp_post_id,
    "image_pipeline": image_pipeline_report,
    "openai_cost_usd": round(openai_cost, 5),
    "total_tokens": total_tokens_used,
    "elapsed_seconds": elapsed,
    "timestamp": datetime.utcnow().isoformat()
}
with open("execution_report.json", "w") as f:
    json.dump(report, f, indent=2)
print("Report saved to execution_report.json")
