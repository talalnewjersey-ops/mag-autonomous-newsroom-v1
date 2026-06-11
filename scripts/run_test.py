#!/usr/bin/env python3
"""NEXUS-14: Self-contained single article production test. v9
IMAGE PIPELINE: Nano Banana -> OpenAI gpt-image-1 -> OpenAI dall-e-3 (fallback chain)
FIXES: correct NB endpoint, correct DALLE params, WP auth stable
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
print("NEXUS-14 PRODUCTION TEST v9")
print("="*60)
print("Topic:", TOPIC)
print("Market:", MARKET)
print("OpenAI Key:", "SET" if OPENAI_KEY else "MISSING")
print("Nano Banana Key:", "SET (" + str(len(NANO_KEY)) + " chars)" if NANO_KEY else "MISSING")
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
            "Write 2 paragraphs (150 words).\n"
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
# STEP 6: IMAGE PIPELINE - FALLBACK CHAIN
# ============================================================
print()
print("[STEP 6] IMAGE PIPELINE")
print("  Chain: Nano Banana -> OpenAI gpt-image-1 -> OpenAI dall-e-3")
print("-"*60)

img_t_start = time.time()
img_prompt = (
    "Professional financial infographic comparing money transfer services "
    "from USA to Canada. Shows exchange rates and fees comparison. "
    "Clean modern design, blue and green colors, white background, "
    "no people, purely data visualization style."
)
image_bytes = None
image_url_final = None
provider_used = None
img_cost = 0.0

def try_upload_to_wp(img_bytes, post_id):
    """Upload image bytes to WordPress media and set as featured image."""
    try:
        media_headers = {
            "Authorization": "Basic " + creds_wp,
            "Content-Disposition": "attachment; filename=nexus14-" + str(int(time.time())) + ".jpg",
            "Content-Type": "image/jpeg",
        }
        mr = requests.post(WP_URL + "/wp-json/wp/v2/media", headers=media_headers, data=img_bytes, timeout=60)
        print("  WP Media upload:", mr.status_code)
        if mr.status_code in (200, 201):
            media_id = mr.json().get("id")
            media_src = mr.json().get("source_url","")
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

# ---- PROVIDER 1: NANO BANANA ----
print()
print("  [Provider 1] Nano Banana...")
attempt1 = {"provider": "nano_banana", "status": "skipped", "error": None, "time_s": 0}
if NANO_KEY:
    t1 = time.time()
    # Nano Banana uses OpenAI-compatible API at app.nano-banana.com
    nb_endpoints = [
        "https://api.nano-banana.com/v1/images/generations",
        "https://app.nano-banana.com/api/v1/images/generations",
        "https://www.nano-banana.com/api/v1/images/generations",
    ]
    nb_payload = {"prompt": img_prompt, "n": 1, "size": "1024x1024"}
    nb_headers = {"Authorization": "Bearer " + NANO_KEY, "Content-Type": "application/json"}
    
    nb_success = False
    for nb_ep in nb_endpoints:
        try:
            print("  Trying:", nb_ep)
            nb_r = requests.post(nb_ep, headers=nb_headers, json=nb_payload, timeout=30)
            print("  Status:", nb_r.status_code, "CT:", nb_r.headers.get("Content-Type","")[:40])
            if nb_r.status_code in (200, 201):
                try:
                    nb_data = nb_r.json()
                    print("  Response keys:", list(nb_data.keys())[:8])
                    # OpenAI format: data[0].url or data[0].b64_json
                    if "data" in nb_data and nb_data["data"]:
                        item = nb_data["data"][0]
                        if "b64_json" in item:
                            image_bytes = base64.b64decode(item["b64_json"])
                            provider_used = "nano_banana"
                            img_cost += 0.002
                            attempt1["status"] = "success"
                            print("  -> Nano Banana SUCCESS (b64_json)")
                            nb_success = True
                            break
                        elif "url" in item:
                            img_resp = requests.get(item["url"], timeout=30)
                            image_bytes = img_resp.content
                            image_url_final = item["url"]
                            provider_used = "nano_banana"
                            img_cost += 0.002
                            attempt1["status"] = "success"
                            print("  -> Nano Banana SUCCESS (url)")
                            nb_success = True
                            break
                    # Other formats
                    elif "images" in nb_data and nb_data["images"]:
                        image_bytes = base64.b64decode(nb_data["images"][0])
                        provider_used = "nano_banana"
                        img_cost += 0.002
                        attempt1["status"] = "success"
                        print("  -> Nano Banana SUCCESS (images[])")
                        nb_success = True
                        break
                    else:
                        print("  Unknown format:", str(nb_data)[:200])
                except Exception as parse_e:
                    print("  Parse error:", parse_e)
                    print("  Raw:", nb_r.text[:200])
            else:
                print("  Response:", nb_r.text[:200])
        except Exception as ep_e:
            print("  Endpoint error:", str(ep_e)[:100])
    
    attempt1["time_s"] = round(time.time() - t1, 2)
    if not nb_success and attempt1["status"] == "skipped":
        attempt1["status"] = "failed"
        attempt1["error"] = "All NB endpoints failed"
else:
    attempt1["status"] = "skipped"
    attempt1["error"] = "NANO_BANANA_API_KEY not set"
    print("  -> Skipped (no NANO_BANANA_API_KEY)")
image_pipeline_report["attempts"].append(attempt1)

# ---- PROVIDER 2: OPENAI gpt-image-1 (if Nano Banana failed) ----
if not provider_used:
    print()
    print("  [Provider 2] OpenAI gpt-image-1...")
    attempt2 = {"provider": "openai_gpt_image_1", "status": "skipped", "error": None, "time_s": 0}
    if OPENAI_KEY:
        t2 = time.time()
        try:
            client_img = openai.OpenAI(api_key=OPENAI_KEY)
            # gpt-image-1 is the newest model, returns b64_json by default
            img_resp2 = client_img.images.generate(
                model="gpt-image-1",
                prompt=img_prompt,
                size="1024x1024",
                n=1
            )
            attempt2["time_s"] = round(time.time() - t2, 2)
            if img_resp2.data[0].b64_json:
                image_bytes = base64.b64decode(img_resp2.data[0].b64_json)
                provider_used = "openai_gpt_image_1"
                img_cost += 0.04
                attempt2["status"] = "success"
                print("  -> gpt-image-1 SUCCESS (b64_json)")
            elif img_resp2.data[0].url:
                img_resp_dl = requests.get(img_resp2.data[0].url, timeout=30)
                image_bytes = img_resp_dl.content
                image_url_final = img_resp2.data[0].url
                provider_used = "openai_gpt_image_1"
                img_cost += 0.04
                attempt2["status"] = "success"
                print("  -> gpt-image-1 SUCCESS (url)")
        except Exception as e:
            attempt2["time_s"] = round(time.time() - t2, 2)
            attempt2["status"] = "error"
            attempt2["error"] = str(e)
            print("  -> gpt-image-1 ERROR:", e)
    else:
        attempt2["status"] = "skipped"
        attempt2["error"] = "OPENAI_API_KEY not set"
        print("  -> Skipped (no OPENAI_API_KEY)")
    image_pipeline_report["attempts"].append(attempt2)

# ---- PROVIDER 3: OPENAI dall-e-3 (final fallback) ----
if not provider_used:
    print()
    print("  [Provider 3] OpenAI dall-e-3 (final fallback)...")
    attempt3 = {"provider": "openai_dalle3", "status": "skipped", "error": None, "time_s": 0}
    if OPENAI_KEY:
        t3 = time.time()
        try:
            client_img3 = openai.OpenAI(api_key=OPENAI_KEY)
            dalle_prompt = (
                "A clean professional infographic for a financial website. "
                "Shows a comparison chart of money transfer services. "
                "Blue and green color scheme. Modern flat design. No text or words."
            )
            # dall-e-3: do NOT pass response_format - returns URL by default
            img_resp3 = client_img3.images.generate(
                model="dall-e-3",
                prompt=dalle_prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            attempt3["time_s"] = round(time.time() - t3, 2)
            url3 = img_resp3.data[0].url
            if url3:
                img_dl = requests.get(url3, timeout=30)
                image_bytes = img_dl.content
                image_url_final = url3
                provider_used = "openai_dalle3"
                img_cost += 0.04
                attempt3["status"] = "success"
                print("  -> dall-e-3 SUCCESS, URL:", url3[:80])
        except Exception as e:
            attempt3["time_s"] = round(time.time() - t3, 2)
            attempt3["status"] = "error"
            attempt3["error"] = str(e)
            print("  -> dall-e-3 ERROR:", e)
    else:
        attempt3["status"] = "skipped"
        attempt3["error"] = "OPENAI_API_KEY not set"
    image_pipeline_report["attempts"].append(attempt3)

img_total_time = round(time.time() - img_t_start, 2)

# ---- UPLOAD TO WORDPRESS ----
if provider_used and image_bytes:
    print()
    print("  Uploading image to WordPress...")
    wp_media_url = try_upload_to_wp(image_bytes, wp_post_id)
    if wp_media_url:
        image_pipeline_report["image_urls"].append(wp_media_url)
    elif image_url_final:
        image_pipeline_report["image_urls"].append(image_url_final)
    image_pipeline_report["images_generated"] = True
    image_pipeline_report["provider_used"] = provider_used
    image_pipeline_report["generation_time_s"] = img_total_time
    image_pipeline_report["cost_usd"] = img_cost
else:
    print()
    print("  ALL IMAGE PROVIDERS FAILED")
    err_list = [a.get("provider","?") + ":" + str(a.get("error",""))[:60] for a in image_pipeline_report["attempts"]]
    image_pipeline_report["error"] = "All failed: " + " | ".join(err_list)

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
        subject = "NEXUS-14 v9 - " + str(passed_count) + "/7 - img:" + str(image_pipeline_report.get("provider_used","none"))
        body = "NEXUS-14 v9 Results:\n\n"
        for k, v in results.items():
            body += ("PASS" if v else "FAIL") + " " + k + "\n"
        body += "\nIMAGE PIPELINE:\n"
        body += "Provider: " + str(image_pipeline_report.get("provider_used")) + "\n"
        body += "Time: " + str(image_pipeline_report.get("generation_time_s")) + "s\n"
        body += "Cost: $" + str(image_pipeline_report.get("cost_usd")) + "\n"
        body += "URLs: " + str(image_pipeline_report.get("image_urls")) + "\n"
        body += "\nPost ID: " + str(wp_post_id) + "\nTotal: " + str(elapsed_now) + "s"
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
    err = ("(" + str(a.get("error",""))[:80] + ")") if a.get("error") else ""
    print("  - " + a["provider"] + " -> " + a["status"] + " " + str(a.get("time_s",0)) + "s " + err)
print("="*60)
print()
print("Score:", str(passed) + "/" + str(total))
print("Critical (article+words+WP):", "ALL PASS" if critical_passed else "SOME FAIL")
print("OpenAI cost: $" + str(round(openai_cost, 5)))
print("Total time:", str(elapsed) + "s")
print("WP Post ID:", wp_post_id)
print()
if passed >= 6 and critical_passed:
    print("VERDICT: PASS - VERIFIED PRODUCTION READY")
elif passed >= 5 and critical_passed:
    print("VERDICT: PARTIAL_PASS - Almost ready")
else:
    print("VERDICT: FAIL - NOT VERIFIED")
print("="*60)

report = {
    "version": "v9",
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
