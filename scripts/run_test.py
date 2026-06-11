#!/usr/bin/env python3
"""NEXUS-14: Self-contained single article production test. v4"""
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
print("NEXUS-14 PRODUCTION TEST v4")
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
Your articles are detailed, practical, and follow EEAT guidelines (Experience, Expertise, Authoritativeness, Trustworthiness).
You ALWAYS write at least 2200 words. Never write less than 2200 words."""

        user_prompt = """Write a comprehensive, detailed, SEO-optimized article about: """ + TOPIC + """

TARGET MARKET: """ + MARKET + """

CRITICAL REQUIREMENTS:
- MINIMUM 2200 WORDS - this is mandatory, do not write less
- Include H2 and H3 subheadings throughout
- Write exactly 10+ internal links using format: <a href="https://moneyabroadguide.com/RELEVANT-SLUG">anchor text</a>
- Include comparison tables for fees, exchange rates, transfer speeds
- Add practical tips, real examples with specific dollar amounts
- Cover: top 5-7 transfer services (Wise, Remitly, Western Union, PayPal, Xoom, OFX, banks)
- Include sections on: fees, exchange rates, transfer speed, limits, pros/cons
- Add FAQ section with 5+ questions and detailed answers
- Include a "Bottom Line" or "Expert Recommendation" section
- Use HTML formatting: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <table>
- Target keyword: """ + TOPIC + """
- LSI keywords: international wire transfer, forex, remittance, exchange rate, transfer fee

STRUCTURE (must include all sections):
1. Introduction with hook (150+ words)
2. Why Transfer Money from USA to Canada? (200+ words)  
3. Top 7 Money Transfer Services Compared (500+ words with table)
4. Exchange Rates Explained (200+ words)
5. Fees Deep Dive (200+ words)
6. Transfer Speed Comparison (150+ words)
7. Step-by-Step Guide (200+ words)
8. Tips to Save Money (200+ words)
9. FAQ Section - 5 questions (300+ words)
10. Conclusion/Expert Recommendation (150+ words)

Remember: MINIMUM 2200 WORDS. Count your words before finishing."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=6000,
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
        "has_h3": "<h3" in article_content,
        "topic_in_content": topic_lower[:20] in text_lower,
        "has_links": "<a href" in article_content,
        "has_lists": "<ul>" in article_content or "<li>" in article_content,
        "has_strong": "<strong>" in article_content,
        "has_table": "<table" in article_content,
        "word_count_ok": len(article_content.split()) >= 1500,
        "has_faq": "faq" in text_lower or "frequently asked" in text_lower,
        "has_intro": "introduction" in text_lower or article_content[:200].strip() != ""
    }
    
    seo_score = int((sum(seo_checks.values()) / len(seo_checks)) * 100)
    
    # EEAT checks
    eeat_checks = {
        "has_expert_language": any(w in text_lower for w in ["expert", "recommend", "according to", "research"]),
        "has_specific_numbers": bool(re.search(r'\$[0-9]', article_content)),
        "has_comparisons": "compared" in text_lower or "versus" in text_lower or " vs " in text_lower,
        "has_practical_advice": "tip" in text_lower or "advice" in text_lower or "guide" in text_lower,
        "has_conclusion": "conclusion" in text_lower or "bottom line" in text_lower or "recommendation" in text_lower,
        "has_faq": "faq" in text_lower or "question" in text_lower,
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
    print("  SEO checks:", seo_checks)
    print("  EEAT checks:", eeat_checks)

print()

# ============================================================
# STEP 3: GENERATE IMAGE WITH DALL-E 2
# ============================================================
print("[STEP 3] Generating image with DALL-E 2...")
image_url = ""
image_b64 = ""

if OPENAI_KEY and article_content:
    try:
        client = openai.OpenAI(api_key=OPENAI_KEY)
        img_prompt = "Professional infographic showing money transfer from USA to Canada, financial services, clean modern design, blue and green colors, dollar signs and maple leaf symbols"
        
        img_response = client.images.generate(
            model="dall-e-2",
            prompt=img_prompt,
            size="512x512",
            n=1,
            response_format="url"
        )
        
        image_url = img_response.data[0].url
        print("  SUCCESS: Image generated with DALL-E 2")
        print("  Image URL:", image_url[:80] + "...")
        results["images_generated"] = True
        results["image_url"] = image_url
        
    except Exception as e:
        print("  DALL-E 2 Error:", str(e))
        print("  Skipping image generation")
        results["images_generated"] = False
        results["image_error"] = str(e)
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
    print("  WP_URL:", WP_URL)
    print("  WP_USER:", WP_USER)
    print("  WP_PASS:", "SET" if WP_PASS else "MISSING")
    results["wordpress_draft_created"] = False
else:
    # Build auth header
    credentials = WP_USER + ":" + WP_PASS
    token = b64encode(credentials.encode()).decode("utf-8")
    auth_header = "Basic " + token
    
    # Test authentication first
    wp_api_base = WP_URL.rstrip("/") + "/wp-json/wp/v2"
    test_url = wp_api_base + "/users/me"
    
    print("  Testing WP auth at:", test_url)
    print("  WP_USER:", WP_USER)
    
    try:
        test_resp = requests.get(
            test_url,
            headers={"Authorization": auth_header},
            timeout=30
        )
        print("  Auth test status:", test_resp.status_code)
        if test_resp.status_code == 200:
            user_data = test_resp.json()
            print("  Authenticated as:", user_data.get("name", "unknown"))
            wp_user_id = user_data.get("id", 1)
        elif test_resp.status_code == 401:
            print("  Auth FAILED 401 - checking response:", test_resp.text[:200])
            results["wordpress_draft_created"] = False
            results["wp_auth_error"] = test_resp.text[:200]
        else:
            print("  Auth test returned:", test_resp.status_code, test_resp.text[:200])
            wp_user_id = 1
    except Exception as e:
        print("  Auth test error:", str(e))
        wp_user_id = 1
    
    # Create the post title
    title_words = TOPIC.replace("best way", "Best Way").replace("from", "from").title()
    post_title = title_words + " | MoneyAbroadGuide"
    
    # Build post content
    post_body = article_content if article_content else "<p>Test article content for NEXUS-14 pipeline verification.</p>"
    
    # Build post data
    post_data = {
        "title": post_title,
        "content": post_body,
        "status": "draft",
        "categories": [],
        "tags": [],
        "meta": {
            "_yoast_wpseo_focuskw": TOPIC,
            "_yoast_wpseo_metadesc": "Learn the best ways to send money from USA to Canada in 2026. Compare fees, rates, and speeds of top services like Wise, Remitly, and more."
        }
    }
    
    posts_url = wp_api_base + "/posts"
    print("  Creating post at:", posts_url)
    
    try:
        create_resp = requests.post(
            posts_url,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json"
            },
            json=post_data,
            timeout=60
        )
        
        print("  Create post status:", create_resp.status_code)
        
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
            print("  FAILED:", create_resp.status_code)
            print("  Response:", create_resp.text[:500])
            results["wordpress_draft_created"] = False
            results["wp_error"] = create_resp.text[:300]
            
    except Exception as e:
        print("  Exception creating post:", str(e))
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
        # Build pass/fail summary
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
        
        if passed >= 6:
            verdict = "PASS"
        elif passed >= 4:
            verdict = "PARTIAL_PASS"
        else:
            verdict = "FAIL"
        
        lines = []
        lines.append("<h2>NEXUS-14 Test Report - " + verdict + "</h2>")
        lines.append("<p>Time: " + str(elapsed) + "s | Checks: " + str(passed) + "/" + str(total) + "</p>")
        lines.append("<h3>Results:</h3><ul>")
        for k, v in checks.items():
            icon = "PASS" if v else "FAIL"
            lines.append("<li>" + icon + " - " + k + "</li>")
        lines.append("</ul>")
        lines.append("<p>Word count: " + str(results.get('word_count', 0)) + "</p>")
        lines.append("<p>SEO: " + str(results.get('seo_score', 0)) + "/100</p>")
        lines.append("<p>EEAT: " + str(results.get('eeat_score', 0)) + "/100</p>")
        lines.append("<p>WP Post ID: " + str(results.get('wp_post_id', 'N/A')) + "</p>")
        lines.append("<p>OpenAI cost: $" + str(round(results.get('openai_cost', 0), 6)) + "</p>")
        
        html_body = "".join(lines)
        
        email_payload = {
            "personalizations": [{"to": [{"email": EMAIL_TO}]}],
            "from": {"email": "talalnewjersey@gmail.com", "name": "NEXUS-14 System"},
            "subject": "NEXUS-14 Test " + verdict + " - " + str(passed) + "/" + str(total) + " checks passed",
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
print("Critical checks (article + words + WP):", "PASS" if critical_passed else "FAIL")
print("Word count:", results.get("word_count", 0))
print("SEO score:", results.get("seo_score", 0), "/100")
print("EEAT score:", results.get("eeat_score", 0), "/100")
print("WP Post ID:", results.get("wp_post_id", "N/A"))
print("WP Post Link:", results.get("wp_post_link", "N/A"))
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
