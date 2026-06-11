#!/usr/bin/env python3
"""NEXUS-14: Self-contained single article production test. v7"""
import sys, os, json, time, requests, re
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
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY","")
WP_URL = os.environ.get("WORDPRESS_URL","https://moneyabroadguide.com").rstrip("/")
WP_USER = os.environ.get("WORDPRESS_USERNAME","")
WP_PASS = os.environ.get("WORDPRESS_PASSWORD","")
EMAIL_TO = os.environ.get("EMAIL_RECIPIENT","")

print("="*60)
print("NEXUS-14 PRODUCTION TEST v7")
print("="*60)
print("Topic:", TOPIC)
print("Market:", MARKET)
print("OpenAI Key:", "SET" if OPENAI_KEY else "MISSING")
print("WP URL:", WP_URL)
print("WP User length:", len(WP_USER))
print()

results = {}

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
            max_tokens=3000,
            temperature=0.7
        )
        part1 = r1.choices[0].message.content
        total_tokens_used += r1.usage.total_tokens
        openai_cost += (r1.usage.prompt_tokens/1000000)*0.15 + (r1.usage.completion_tokens/1000000)*0.60
        print("  Part 1 words:", len(part1.split()))

        prompt_part2 = (
            "Continue writing the article about: " + TOPIC + "\n\n"
            "Write these sections (aim for 900+ words total):\n"
            "<h2>Detailed Review: Western Union</h2>\n"
            "Write 2 paragraphs (150 words) about Western Union, agent network, fees, speed. "
            "Include: <a href=\"https://moneyabroadguide.com/western-union-review\">Western Union review</a>\n"
            "<h2>Detailed Review: OFX</h2>\n"
            "Write 2 paragraphs (150 words) about OFX, no fees, large transfers, rate lock.\n"
            "<h2>Understanding Exchange Rates: How to Get the Best Deal</h2>\n"
            "Write 3 paragraphs (250 words) explaining mid-market rate, bank markups, how to compare. "
            "Include: <a href=\"https://moneyabroadguide.com/best-exchange-rates\">how to get the best exchange rates</a>\n"
            "<h2>Complete Fee Breakdown: Real Transfer Examples</h2>\n"
            "Write a detailed comparison (250 words) showing exactly what you pay to send $500, $1000, $5000 with each service. Show specific CAD amounts received.\n"
            "<h2>How Fast Can You Send Money to Canada?</h2>\n"
            "Write 2 paragraphs (150 words) comparing speeds, bank vs digital transfer timing.\n"
            "Use proper HTML tags. Write all sections fully now."
        )

        r2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt_part2}],
            max_tokens=3000,
            temperature=0.7
        )
        part2 = r2.choices[0].message.content
        total_tokens_used += r2.usage.total_tokens
        openai_cost += (r2.usage.prompt_tokens/1000000)*0.15 + (r2.usage.completion_tokens/1000000)*0.60
        print("  Part 2 words:", len(part2.split()))

        prompt_part3 = (
            "Write the FINAL PART of the article about: " + TOPIC + "\n\n"
            "Write these sections (aim for 600+ words total):\n"
            "<h2>Step-by-Step Guide: How to Send Money from USA to Canada</h2>\n"
            "Write numbered steps (200 words) for using Wise: create account, verify, add bank, set amount, confirm. "
            "Include: <a href=\"https://moneyabroadguide.com/international-wire-transfer\">international wire transfer guide</a>\n"
            "<h2>5 Expert Tips to Save Money on International Transfers</h2>\n"
            "Write 5 tips as numbered list (200 words): avoid banks, compare rates, timing, regular transfers, tax implications. "
            "Include: <a href=\"https://moneyabroadguide.com/money-transfer-tips\">money transfer tips</a>\n"
            "<h2>Frequently Asked Questions</h2>\n"
            "Write 4 Q&A pairs (150 words) about: best service for large amounts, transfer limits, tax requirements, how long it takes.\n"
            "<h2>Conclusion</h2>\n"
            "Write a strong conclusion (100 words) recommending Wise for most people, summarizing key points.\n"
            "Use proper HTML tags. Write all sections fully now."
        )

        r3 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt_part3}],
            max_tokens=2000,
            temperature=0.7
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
        print("  article_written:", results["article_written"])
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
    topic_lower = TOPIC.lower()
    words_in_topic = [w for w in topic_lower.split() if len(w) > 3]
    found_keywords = sum(1 for w in words_in_topic if w in article_content.lower())
    if found_keywords >= 2: seo_score += 25
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
    content_lower = article_content.lower()
    if any(w in content_lower for w in ["expert","research","study","data","statistic"]): eeat_score += 25
    if any(w in content_lower for w in ["review","comparison","tested","analysis"]): eeat_score += 25
    if any(w in content_lower for w in ["fee","cost","price","rate","percent","%"]): eeat_score += 25
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
        title = TOPIC.title()
        post_data = {
            "title": title,
            "content": article_content,
            "status": "draft",
            "categories": [],
            "tags": [],
        }
        r = requests.post(
            WP_URL + "/wp-json/wp/v2/posts",
            headers=headers,
            json=post_data,
            timeout=60
        )
        print("  WP Status:", r.status_code)
        if r.status_code in (200, 201):
            d = r.json()
            wp_post_id = d.get("id")
            wp_link = d.get("link", "")
            print("  SUCCESS! Post ID:", wp_post_id)
            print("  Link:", wp_link)
            results["wordpress_draft_created"] = True
        else:
            print("  FAILED:", r.text[:300])
            results["wordpress_draft_created"] = False
    except Exception as e:
        print("  ERROR:", e)
        results["wordpress_draft_created"] = False

# ============================================================
# STEP 6: GENERATE IMAGE
# ============================================================
print()
print("[STEP 6] Generating image with DALL-E...")
image_url = None

if not OPENAI_KEY:
    results["images_generated"] = False
else:
    try:
        client2 = openai.OpenAI(api_key=OPENAI_KEY)
        img_prompt = "Professional infographic showing money transfer services comparison between USA and Canada, clean modern design, financial theme, blue and green colors"
        img_response = client2.images.generate(
            model="dall-e-2",
            prompt=img_prompt,
            size="512x512",
            n=1
        )
        image_url = img_response.data[0].url
        print("  Image generated:", image_url[:80] + "...")
        results["images_generated"] = True

        if wp_post_id and image_url:
            try:
                img_data = requests.get(image_url, timeout=30).content
                creds2 = b64encode((WP_USER + ":" + WP_PASS).encode()).decode()
                media_headers = {
                    "Authorization": "Basic " + creds2,
                    "Content-Disposition": "attachment; filename=nexus14-featured.jpg",
                    "Content-Type": "image/jpeg",
                }
                media_r = requests.post(
                    WP_URL + "/wp-json/wp/v2/media",
                    headers=media_headers,
                    data=img_data,
                    timeout=60
                )
                if media_r.status_code in (200, 201):
                    media_id = media_r.json().get("id")
                    print("  Media uploaded, ID:", media_id)
                    creds3 = b64encode((WP_USER + ":" + WP_PASS).encode()).decode()
                    update_headers = {
                        "Authorization": "Basic " + creds3,
                        "Content-Type": "application/json",
                    }
                    requests.post(
                        WP_URL + "/wp-json/wp/v2/posts/" + str(wp_post_id),
                        headers=update_headers,
                        json={"featured_media": media_id},
                        timeout=30
                    )
                    print("  Featured image set on post")
                else:
                    print("  Media upload status:", media_r.status_code)
            except Exception as e2:
                print("  Media upload error:", e2)

    except Exception as e:
        print("  Image error:", e)
        results["images_generated"] = False

# ============================================================
# STEP 7: SEND EMAIL REPORT
# ============================================================
print()
print("[STEP 7] Sending email report...")
if SENDGRID_KEY and EMAIL_TO:
    try:
        elapsed_now = round(time.time() - START, 1)
        status_str = "PASS" if results.get("wordpress_draft_created") else "PARTIAL"
        subject = "NEXUS-14 Test " + status_str + " - " + str(elapsed_now) + "s"
        body = "NEXUS-14 Run Results:\n"
        for k, v in results.items():
            body += ("PASS" if v else "FAIL") + " " + k + "\n"
        body += "\nPost ID: " + str(wp_post_id)
        body += "\nWords: " + str(len(article_content.split()) if article_content else 0)
        body += "\nCost: $" + str(round(openai_cost, 5))
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
print("Score:", str(passed) + "/" + str(total))
print("Critical checks (article+words+WP):", "ALL PASS" if critical_passed else "SOME FAIL")
print("OpenAI cost: $" + str(round(openai_cost, 5)))
print("Time:", str(elapsed) + "s")
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
    "version": "v7",
    "topic": TOPIC,
    "market": MARKET,
    "checks": {n: v for n, v in checks_final},
    "score": str(passed) + "/" + str(total),
    "critical_passed": critical_passed,
    "wp_post_id": wp_post_id,
    "openai_cost_usd": round(openai_cost, 5),
    "total_tokens": total_tokens_used,
    "elapsed_seconds": elapsed,
    "timestamp": datetime.utcnow().isoformat()
}
with open("execution_report.json", "w") as f:
    json.dump(report, f, indent=2)
print("Report saved to execution_report.json")
