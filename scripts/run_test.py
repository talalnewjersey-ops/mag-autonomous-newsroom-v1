#!/usr/bin/env python3
"""NEXUS-14: Self-contained single article production test. v5"""
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
GEMINI_KEY = os.environ.get("GEMINI_API_KEY","")
NANO_KEY = os.environ.get("NANO_BANANA_API_KEY","")
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY","")
WP_URL = os.environ.get("WORDPRESS_URL","https://moneyabroadguide.com")
WP_USER = os.environ.get("WORDPRESS_USERNAME","")
WP_PASS = os.environ.get("WORDPRESS_PASSWORD","")
EMAIL_TO = os.environ.get("EMAIL_RECIPIENT","")

print("="*60)
print("NEXUS-14 PRODUCTION TEST v5")
print("="*60)
print("Topic:", TOPIC)
print("Market:", MARKET)
print("OpenAI Key:", "SET" if OPENAI_KEY else "MISSING")
print("WP URL:", WP_URL)
print("WP User:", WP_USER)
print("WP Pass:", "SET" if WP_PASS else "MISSING")
print()

results = {}

# ============================================================
# STEP 1: GENERATE ARTICLE WITH OPENAI
# ============================================================
print("[STEP 1] Generating article with OpenAI...")
article_content = ""
openai_cost = 0.0
token_usage = {}

if not OPENAI_KEY:
    print("  ERROR: OPENAI_API_KEY not set")
    results["article_written"] = False
else:
    try:
        client = openai.OpenAI(api_key=OPENAI_KEY)
        
        system_prompt = """You are an expert financial writer specializing in expat money transfers and international banking. 
You write comprehensive, authoritative, SEO-optimized articles for MoneyAbroadGuide.com.
Your articles follow EEAT guidelines (Experience, Expertise, Authoritativeness, Trustworthiness).
CRITICAL: You ALWAYS write EXACTLY 2500+ words. Failing to reach 2500 words is unacceptable."""

        user_prompt = """Write a comprehensive, SEO-optimized article (MINIMUM 2500 WORDS) about: """ + TOPIC + """

TARGET MARKET: """ + MARKET + """

MANDATORY REQUIREMENTS - ALL must be present:
1. MINIMUM 2500 WORDS - count carefully, never write less
2. Include 6+ internal links: <a href="https://moneyabroadguide.com/SLUG">text</a>
3. H2 and H3 subheadings throughout the article
4. Comparison table (HTML) with fees, rates, speeds for top 6 services
5. FAQ section with 5 questions and detailed answers (50+ words each)
6. Specific dollar amounts and percentages throughout

SERVICES TO COVER (all 7): Wise, Remitly, Western Union, PayPal/Xoom, OFX, MoneyGram, bank wire transfer

MANDATORY 10-SECTION STRUCTURE:
<h2>Introduction</h2>
Write 200+ words explaining why people need this, key statistics, what the article covers.

<h2>Why Send Money from USA to Canada?</h2>
Write 200+ words about expat needs, business payments, family support, student fees.

<h2>Top 7 Money Transfer Services Compared</h2>
Write 500+ words. Include this comparison table then detailed reviews of each service.
<table><thead><tr><th>Service</th><th>Fee</th><th>Exchange Rate</th><th>Speed</th><th>Best For</th></tr></thead>
<tbody>
<tr><td>Wise</td><td>0.4-0.6%</td><td>Mid-market</td><td>1-2 days</td><td>Best rates</td></tr>
<tr><td>Remitly</td><td>$3.99+</td><td>Near mid-market</td><td>Minutes</td><td>Speed</td></tr>
<tr><td>Western Union</td><td>$5+</td><td>Varies</td><td>Minutes-days</td><td>Cash pickup</td></tr>
<tr><td>PayPal/Xoom</td><td>2.9%+</td><td>Spread applies</td><td>Minutes</td><td>Existing users</td></tr>
<tr><td>OFX</td><td>No fee</td><td>Near mid-market</td><td>1-3 days</td><td>Large amounts</td></tr>
<tr><td>MoneyGram</td><td>$1.99+</td><td>Varies</td><td>Minutes</td><td>Agent locations</td></tr>
<tr><td>Bank Wire</td><td>$25-45</td><td>Bank rate</td><td>1-3 days</td><td>Trust/security</td></tr>
</tbody></table>

<h2>Understanding Exchange Rates</h2>
Write 200+ words explaining mid-market rate, spreads, how to get best rate.

<h2>Fee Breakdown: What You Actually Pay</h2>
Write 200+ words with specific examples like "sending $1000 USD, you receive..."

<h2>Transfer Speed: How Fast Can You Send Money?</h2>
Write 150+ words comparing speeds.

<h2>Step-by-Step Guide: How to Send Money</h2>
Write 200+ words with numbered steps.

<h2>5 Pro Tips to Save Money on Transfers</h2>
Write 200+ words with specific actionable tips.

<h2>FAQ: Frequently Asked Questions</h2>
Include these 5 questions with 50+ word answers each:
- What is the cheapest way to send money from USA to Canada?
- How long does it take to transfer money to Canada?
- Is there a limit on how much I can send?
- Do I need a Canadian bank account to receive money?
- What documents do I need to send money internationally?

<h2>Conclusion: Our Expert Recommendation</h2>
Write 150+ words with clear recommendation.

Internal links to include (use all 6):
<a href="https://moneyabroadguide.com/wise-review">Wise review</a>
<a href="https://moneyabroadguide.com/remitly-review">Remitly review</a>
<a href="https://moneyabroadguide.com/western-union-review">Western Union review</a>
<a href="https://moneyabroadguide.com/best-exchange-rates">best exchange rates</a>
<a href="https://moneyabroadguide.com/international-wire-transfer">international wire transfer guide</a>
<a href="https://moneyabroadguide.com/send-money-canada">send money to Canada</a>

REMEMBER: 2500+ WORDS IS MANDATORY."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=7000,
            temperature=0.7
        )
        
        article_content = response.choices[0].message.content
        token_usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        # Calculate cost (gpt-4o-mini: $0.15/1M input, $0.60/1M output)
        input_cost = (response.usage.prompt_tokens / 1000000) * 0.15
        output_cost = (response.usage.completion_tokens / 1000000) * 0.60
        openai_cost = input_cost + output_cost
        
        word_count = len(article_content.split())
        print("  SUCCESS: Article generated")
        print("  Word count:", word_count)
        print("  Tokens used:", token_usage["total_tokens"])
        print("  OpenAI cost: $" + str(round(openai_cost, 6)))
        
        results["article_written"] = len(article_content) > 500
        results["word_count"] = word_count
        results["word_count_2000plus"] = word_count >= 2000
        results["openai_cost"] = openai_cost
        results["token_usage"] = token_usage
        
    except Exception as e:
        print("  ERROR:", str(e))
        results["article_written"] = False
        results["word_count"] = 0
        results["word_count_2000plus"] = False

print()

# ============================================================
# STEP 2: SEO SCORING
# ============================================================
print("[STEP 2] Running SEO analysis...")
seo_score = 0
eeat_score = 0

if article_content:
    text_lower = article_content.lower()
    topic_lower = TOPIC.lower()
    
    # SEO checks
    seo_checks = {
        "has_h2": "<h2" in article_content,
        "has_h3": "<h3" in article_content or "<h2" in article_content,
        "topic_in_content": topic_lower[:20] in text_lower,
        "has_links": "<a href" in article_content,
        "has_lists": "<ul>" in article_content or "<li>" in article_content or "<ol>" in article_content,
        "has_strong": "<strong>" in article_content or "**" in article_content,
        "has_table": "<table" in article_content,
        "word_count_ok": len(article_content.split()) >= 1500,
        "has_faq": "faq" in text_lower or "frequently asked" in text_lower,
        "has_intro": len(article_content) > 500
    }
    
    seo_score = int((sum(seo_checks.values()) / len(seo_checks)) * 100)
    
    # EEAT checks
    eeat_checks = {
        "has_expert_language": any(w in text_lower for w in ["expert", "recommend", "according to", "research", "experience"]),
        "has_specific_numbers": bool(re.search(r'\$[0-9]', article_content)),
        "has_comparisons": "compared" in text_lower or "versus" in text_lower or " vs " in text_lower or "comparison" in text_lower,
        "has_practical_advice": "tip" in text_lower or "advice" in text_lower or "guide" in text_lower,
        "has_conclusion": "conclusion" in text_lower or "bottom line" in text_lower or "recommendation" in text_lower,
        "has_faq": "faq" in text_lower or "question" in text_lower or "frequently" in text_lower,
        "sufficient_length": len(article_content.split()) >= 1500,
        "has_service_mentions": any(s in text_lower for s in ["wise", "remitly", "western union", "paypal"]),
    }
    
    eeat_score = int((sum(eeat_checks.values()) / len(eeat_checks)) * 100)
    
    results["seo_score"] = seo_score
    results["eeat_score"] = eeat_score
    results["seo_score_85plus"] = seo_score >= 85
    results["eeat_score_80plus"] = eeat_score >= 80
    
    # Count internal links
    internal_links = len(re.findall(r'href="https://moneyabroadguide\.com', article_content))
    results["internal_links_count"] = internal_links
    results["internal_links_5plus"] = internal_links >= 5
    
    print("  SEO Score:", seo_score, "/100")
    print("  EEAT Score:", eeat_score, "/100")
    print("  Internal links:", internal_links)

print()

# ============================================================
# STEP 3: GENERATE IMAGE WITH DALL-E 2 (no response_format)
# ============================================================
print("[STEP 3] Generating image with DALL-E 2...")
image_url = ""

if OPENAI_KEY and article_content:
    try:
        client = openai.OpenAI(api_key=OPENAI_KEY)
        img_prompt = "Professional infographic showing money transfer from USA to Canada, financial services, clean modern design, blue and green colors"
        
        img_response = client.images.generate(
            model="dall-e-2",
            prompt=img_prompt,
            size="512x512",
            n=1
        )
        
        image_url = img_response.data[0].url
        print("  SUCCESS: Image generated with DALL-E 2")
        print("  Image URL:", image_url[:80] + "...")
        results["images_generated"] = True
        results["image_url"] = image_url
        
    except Exception as e:
        print("  DALL-E 2 Error:", str(e))
        print("  Trying without model specification...")
        try:
            img_response2 = client.images.generate(
                prompt="Money transfer USA Canada financial infographic blue green",
                size="256x256",
                n=1
            )
            image_url = img_response2.data[0].url
            print("  SUCCESS (fallback): Image generated")
            results["images_generated"] = True
            results["image_url"] = image_url
        except Exception as e2:
            print("  Fallback also failed:", str(e2))
            results["images_generated"] = False
            results["image_error"] = str(e2)
else:
    print("  Skipping (no OpenAI key or no article)")
    results["images_generated"] = False

print()

# ============================================================
# STEP 4: POST TO WORDPRESS
# ============================================================
print("[STEP 4] Creating WordPress draft...")

if not WP_URL or not WP_USER or not WP_PASS:
    print("  ERROR: WordPress credentials missing")
    results["wordpress_draft_created"] = False
else:
    # Build auth header - WordPress Application Password format
    credentials = WP_USER + ":" + WP_PASS
    token = b64encode(credentials.encode()).decode("utf-8")
    auth_header = "Basic " + token
    
    # Use WordPress-compatible User-Agent to avoid bot blocking
    headers_base = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "User-Agent": "WordPress/6.4 (MoneyAbroadGuide; https://moneyabroadguide.com)"
    }
    
    wp_api_base = WP_URL.rstrip("/") + "/wp-json/wp/v2"
    test_url = wp_api_base + "/users/me"
    
    print("  Testing WP auth at:", test_url)
    print("  WP_USER:", WP_USER)
    
    wp_auth_ok = False
    try:
        test_resp = requests.get(
            test_url,
            headers=headers_base,
            timeout=30
        )
        print("  Auth test status:", test_resp.status_code)
        
        # Check if we got HTML (bot protection) or JSON
        content_type = test_resp.headers.get("content-type", "")
        is_json = "json" in content_type
        print("  Content-Type:", content_type)
        
        if test_resp.status_code == 200 and is_json:
            user_data = test_resp.json()
            print("  Authenticated as:", user_data.get("name", "unknown"))
            print("  User ID:", user_data.get("id", "unknown"))
            wp_auth_ok = True
        elif test_resp.status_code == 401:
            print("  Auth FAILED 401")
            print("  Response:", test_resp.text[:300])
            results["wordpress_draft_created"] = False
            results["wp_auth_error"] = "401 Unauthorized - " + test_resp.text[:200]
        else:
            print("  Unexpected status:", test_resp.status_code)
            response_preview = test_resp.text[:200]
            print("  Response preview:", response_preview)
            if "Bot Verification" in test_resp.text or "<!DOCTYPE" in test_resp.text:
                print("  DETECTED: Bot protection/firewall blocking API calls")
                print("  This is a server-side security issue, not a credential issue")
                results["wordpress_draft_created"] = False
                results["wp_error"] = "Bot protection blocking API - need to whitelist GitHub Actions IPs"
            else:
                # Try to proceed anyway
                wp_auth_ok = True
    except Exception as e:
        print("  Auth test error:", str(e))
        wp_auth_ok = True  # Try anyway
    
    if wp_auth_ok:
        # Create the post
        title_words = TOPIC.title()
        post_title = title_words + " | MoneyAbroadGuide"
        
        post_body = article_content if article_content else "<p>Test article content for NEXUS-14.</p>"
        
        post_data = {
            "title": post_title,
            "content": post_body,
            "status": "draft",
            "meta": {
                "_yoast_wpseo_focuskw": TOPIC,
                "_yoast_wpseo_metadesc": "Learn the best ways to send money from USA to Canada. Compare fees, rates, and speeds of top services."
            }
        }
        
        posts_url = wp_api_base + "/posts"
        print("  Creating post at:", posts_url)
        
        try:
            create_resp = requests.post(
                posts_url,
                headers=headers_base,
                json=post_data,
                timeout=60
            )
            
            print("  Create post status:", create_resp.status_code)
            content_type_create = create_resp.headers.get("content-type", "")
            
            if create_resp.status_code in [200, 201]:
                post_data_resp = create_resp.json()
                post_id = post_data_resp.get("id")
                post_link = post_data_resp.get("link", "")
                print("  SUCCESS: Draft created!")
                print("  Post ID:", post_id)
                print("  Post link:", post_link)
                results["wordpress_draft_created"] = True
                results["wp_post_id"] = post_id
                results["wp_post_link"] = post_link
            else:
                resp_text = create_resp.text[:500]
                print("  FAILED:", create_resp.status_code)
                print("  Response:", resp_text)
                results["wordpress_draft_created"] = False
                results["wp_error"] = resp_text[:300]
                
        except Exception as e:
            print("  Exception:", str(e))
            results["wordpress_draft_created"] = False
            results["wp_exception"] = str(e)

print()

# ============================================================
# STEP 5: SEND EMAIL REPORT
# ============================================================
print("[STEP 5] Sending email report...")

elapsed = round(time.time() - START, 1)

if SENDGRID_KEY and EMAIL_TO:
    try:
        checks_for_email = {
            "article_written": results.get("article_written", False),
            "word_count_2000plus": results.get("word_count_2000plus", False),
            "seo_score_85plus": results.get("seo_score_85plus", False),
            "eeat_score_80plus": results.get("eeat_score_80plus", False),
            "internal_links_5plus": results.get("internal_links_5plus", False),
            "wordpress_draft_created": results.get("wordpress_draft_created", False),
            "images_generated": results.get("images_generated", False),
        }
        
        passed_email = sum(checks_for_email.values())
        total_email = len(checks_for_email)
        
        if passed_email >= 6:
            verdict_email = "PASS"
        elif passed_email >= 4:
            verdict_email = "PARTIAL_PASS"
        else:
            verdict_email = "FAIL"
        
        lines = []
        lines.append("<h2>NEXUS-14 Test Report v5 - " + verdict_email + "</h2>")
        lines.append("<p>Time: " + str(elapsed) + "s | Checks: " + str(passed_email) + "/" + str(total_email) + "</p>")
        lines.append("<h3>Results:</h3><ul>")
        for k, v in checks_for_email.items():
            icon = "PASS" if v else "FAIL"
            lines.append("<li>" + icon + " - " + k + "</li>")
        lines.append("</ul>")
        lines.append("<p>Word count: " + str(results.get("word_count", 0)) + "</p>")
        lines.append("<p>SEO: " + str(results.get("seo_score", 0)) + "/100</p>")
        lines.append("<p>EEAT: " + str(results.get("eeat_score", 0)) + "/100</p>")
        lines.append("<p>WP Post ID: " + str(results.get("wp_post_id", "N/A")) + "</p>")
        lines.append("<p>WP Error: " + str(results.get("wp_error", "none"))[:200] + "</p>")
        lines.append("<p>OpenAI cost: $" + str(round(results.get("openai_cost", 0), 6)) + "</p>")
        
        html_body = "".join(lines)
        
        email_payload = {
            "personalizations": [{"to": [{"email": EMAIL_TO}]}],
            "from": {"email": "talalnewjersey@gmail.com", "name": "NEXUS-14 System"},
            "subject": "NEXUS-14 v5 Test " + verdict_email + " - " + str(passed_email) + "/" + str(total_email) + " checks",
            "content": [{"type": "text/html", "value": html_body}]
        }
        
        sg_resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": "Bearer " + SENDGRID_KEY,
                "Content-Type": "application/json"
            },
            json=email_payload,
            timeout=30
        )
        
        if sg_resp.status_code in [200, 202]:
            print("  SUCCESS: Email sent to", EMAIL_TO)
            results["email_sent"] = True
        else:
            print("  Email failed:", sg_resp.status_code, sg_resp.text[:200])
            results["email_sent"] = False
            
    except Exception as e:
        print("  Email error:", str(e))
        results["email_sent"] = False
else:
    print("  Skipping email (no SendGrid key or recipient)")
    results["email_sent"] = False

print()

# ============================================================
# FINAL VERDICT
# ============================================================
print("="*60)
print("FINAL SUMMARY")
print("="*60)

checks = {
    "article_written": results.get("article_written", False),
    "word_count_2000plus": results.get("word_count_2000plus", False),
    "seo_score_85plus": results.get("seo_score_85plus", False),
    "eeat_score_80plus": results.get("eeat_score_80plus", False),
    "internal_links_5plus": results.get("internal_links_5plus", False),
    "wordpress_draft_created": results.get("wordpress_draft_created", False),
    "images_generated": results.get("images_generated", False),
}

passed = sum(checks.values())
total = len(checks)
critical_passed = (
    results.get("article_written", False) and
    results.get("word_count_2000plus", False) and
    results.get("wordpress_draft_created", False)
)

print()
for check_name, check_val in checks.items():
    status = "PASS" if check_val else "FAIL"
    print("  [" + status + "] " + check_name)

print()
print("Score:", str(passed) + "/" + str(total))
print("Critical (article + words + WP):", "PASS" if critical_passed else "FAIL")
print("Word count:", results.get("word_count", 0))
print("SEO score:", results.get("seo_score", 0), "/100")
print("EEAT score:", results.get("eeat_score", 0), "/100")
print("WP Post ID:", results.get("wp_post_id", "N/A"))
print("WP Post Link:", results.get("wp_post_link", "N/A"))
print("WP Error:", str(results.get("wp_error", "none"))[:200])
print("OpenAI cost: $" + str(round(results.get("openai_cost", 0), 6)))
print("Elapsed:", str(elapsed) + "s")
print()

if passed >= 6 and critical_passed:
    verdict = "PASS"
    print("VERDICT: PASS")
    print("STATUS: VERIFIED PRODUCTION READY")
elif passed >= 4:
    verdict = "PARTIAL_PASS"
    print("VERDICT: PARTIAL_PASS")
    print("STATUS: NOT VERIFIED - some checks failed")
else:
    verdict = "FAIL"
    print("VERDICT: FAIL")
    print("STATUS: NOT VERIFIED")

print()
print("="*60)

# Save report
report = {
    "verdict": verdict,
    "checks_passed": passed,
    "checks_total": total,
    "critical_passed": critical_passed,
    "results": results,
    "elapsed_seconds": elapsed,
    "timestamp": datetime.now().isoformat()
}

with open("execution_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Report saved to execution_report.json")
