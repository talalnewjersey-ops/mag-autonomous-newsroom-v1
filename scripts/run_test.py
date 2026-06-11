#!/usr/bin/env python3
"""
NEXUS-14: Single Article Production Test Script
MoneyAbroadGuide Autonomous Newsroom V1
Runs all 14 agents sequentially for one article.
"""
import asyncio
import sys
import os
import json
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

start_time = time.time()
results = {}
topic = None
article_content = ""
image_prompts = []
generated_images = []
wp_draft_id = None
wp_draft_url = None
eeat_score = 0
quality_score = 0
final_status = "UNKNOWN"

market = os.environ.get("TARGET_MARKET", "USA")
topic_override = os.environ.get("TOPIC_OVERRIDE", "")

print("=" * 60)
print("NEXUS-14 SINGLE ARTICLE TEST")
print(f"Start: {datetime.utcnow().isoformat()} UTC")
print(f"Market: {market}")
print(f"Topic override: {topic_override or '(auto)'}")
print("=" * 60)

# ── Agent 01: SEO Research ──────────────────────────────────
print("\n[01/14] SEO Research Agent...")
try:
    from agents.agent_01_seo_researcher import SEOResearcherAgent
    agent01 = SEOResearcherAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    if topic_override:
        topic = {"keyword": topic_override, "market": market, "search_volume": 0, "difficulty": 50}
        results["agent_01"] = {"status": "PASS", "topic": topic["keyword"]}
        print(f"  PASS - Using override: {topic['keyword']}")
    else:
        topics = asyncio.run(agent01.research_topics(market=market, count=1))
        topic = topics[0] if topics else None
        if topic:
            results["agent_01"] = {"status": "PASS", "topic": topic.get("keyword", str(topic))}
            print(f"  PASS - Topic: {topic.get('keyword', str(topic))}")
        else:
            raise Exception("No topics returned")
except Exception as e:
    results["agent_01"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")
    topic = {"keyword": "Best money transfer services USA 2025", "market": market}
    print(f"  Fallback topic: {topic['keyword']}")

# ── Agent 02: Content Planner ───────────────────────────────
print("\n[02/14] Content Planner Agent...")
plan = None
try:
    from agents.agent_02_content_planner import ContentPlannerAgent
    agent02 = ContentPlannerAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    plan = asyncio.run(agent02.create_plan(topic))
    n = len(plan.get("sections", []))
    results["agent_02"] = {"status": "PASS", "sections": n}
    print(f"  PASS - {n} sections planned")
except Exception as e:
    results["agent_02"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")
    plan = {"title": topic.get("keyword", "Article"), "sections": ["Introduction", "Main Content", "FAQ", "Conclusion"]}

# ── Agent 03: Writer ────────────────────────────────────────
print("\n[03/14] Writer Agent...")
try:
    from agents.agent_03_writer import WriterAgent
    agent03 = WriterAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    article = asyncio.run(agent03.write_article(topic, plan))
    article_content = article.get("content", "")
    wc = len(article_content.split())
    results["agent_03"] = {"status": "PASS", "word_count": wc}
    print(f"  PASS - {wc} words written")
except Exception as e:
    results["agent_03"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")
    article_content = f"# {topic.get('keyword', 'Article')}\n\n[Content generation failed: {e}]"

# ── Agent 04: SEO Optimizer ─────────────────────────────────
print("\n[04/14] SEO Optimizer Agent...")
try:
    from agents.agent_04_seo_optimizer import SEOOptimizerAgent
    agent04 = SEOOptimizerAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    seo = asyncio.run(agent04.optimize(article_content, topic))
    article_content = seo.get("content", article_content)
    results["agent_04"] = {"status": "PASS", "seo_score": seo.get("score", 0)}
    print(f"  PASS - SEO score: {seo.get('score', 0)}")
except Exception as e:
    results["agent_04"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 05: Fact Checker ──────────────────────────────────
print("\n[05/14] Fact Checker Agent...")
try:
    from agents.agent_05_fact_checker import FactCheckerAgent
    agent05 = FactCheckerAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    fc = asyncio.run(agent05.check_facts(article_content))
    results["agent_05"] = {"status": "PASS", "issues": fc.get("issues_found", 0)}
    print(f"  PASS - Issues found: {fc.get('issues_found', 0)}")
except Exception as e:
    results["agent_05"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 06: EEAT Validator ────────────────────────────────
print("\n[06/14] EEAT Validator Agent...")
try:
    from agents.agent_06_eeat_validator import EEATValidatorAgent
    agent06 = EEATValidatorAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    eeat = asyncio.run(agent06.validate(article_content))
    eeat_score = eeat.get("total_score", 0)
    results["agent_06"] = {"status": "PASS", "eeat_score": eeat_score}
    print(f"  PASS - EEAT score: {eeat_score}/100")
except Exception as e:
    results["agent_06"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 07: Internal Linking ──────────────────────────────
print("\n[07/14] Internal Linking Agent...")
try:
    from agents.agent_07_internal_linking import InternalLinkingAgent
    agent07 = InternalLinkingAgent({
        "openai_api_key": os.environ["OPENAI_API_KEY"],
        "wordpress_url": os.environ.get("WORDPRESS_URL", "")
    })
    links = asyncio.run(agent07.add_links(article_content, topic))
    article_content = links.get("content", article_content)
    results["agent_07"] = {"status": "PASS", "links_added": links.get("links_added", 0)}
    print(f"  PASS - Links added: {links.get('links_added', 0)}")
except Exception as e:
    results["agent_07"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 08: Affiliate Optimizer ───────────────────────────
print("\n[08/14] Affiliate Optimizer Agent...")
try:
    from agents.agent_08_affiliate_optimizer import AffiliateOptimizerAgent
    agent08 = AffiliateOptimizerAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    aff = asyncio.run(agent08.optimize(article_content, topic))
    article_content = aff.get("content", article_content)
    results["agent_08"] = {"status": "PASS", "blocks_added": aff.get("blocks_added", 0)}
    print(f"  PASS - Affiliate blocks: {aff.get('blocks_added', 0)}")
except Exception as e:
    results["agent_08"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 09: Image Prompt Generator ───────────────────────
print("\n[09/14] Image Prompt Generator Agent...")
try:
    from agents.agent_09_image_prompt_generator import ImagePromptGeneratorAgent
    agent09 = ImagePromptGeneratorAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    prompts_result = asyncio.run(agent09.generate_prompts(topic, article_content))
    image_prompts = prompts_result.get("prompts", [])
    results["agent_09"] = {"status": "PASS", "prompts": len(image_prompts)}
    print(f"  PASS - Prompts generated: {len(image_prompts)}")
except Exception as e:
    results["agent_09"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 10: Image Production ──────────────────────────────
print("\n[10/14] Image Production Agent...")
try:
    from agents.agent_10_image_production import ImageProductionAgent
    agent10 = ImageProductionAgent({
        "openai_api_key": os.environ["OPENAI_API_KEY"],
        "nano_banana_api_key": os.environ.get("NANO_BANANA_API_KEY", ""),
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", "")
    })
    imgs = asyncio.run(agent10.produce_images(image_prompts[:4] if image_prompts else []))
    generated_images = imgs.get("images", [])
    results["agent_10"] = {"status": "PASS", "images": len(generated_images)}
    print(f"  PASS - Images generated: {len(generated_images)}")
except Exception as e:
    results["agent_10"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 11: WordPress Integration ────────────────────────
print("\n[11/14] WordPress Integration Agent...")
try:
    from agents.agent_11_wordpress_integration import WordPressIntegrationAgent
    agent11 = WordPressIntegrationAgent({
        "wordpress_url": os.environ["WORDPRESS_URL"],
        "wordpress_username": os.environ["WORDPRESS_USERNAME"],
        "wordpress_password": os.environ["WORDPRESS_PASSWORD"]
    })
    wp = asyncio.run(agent11.create_draft(article_content, topic, generated_images))
    wp_draft_id = wp.get("post_id")
    wp_draft_url = wp.get("post_url")
    results["agent_11"] = {"status": "PASS", "draft_id": wp_draft_id, "url": wp_draft_url}
    print(f"  PASS - Draft ID: {wp_draft_id}")
    print(f"  URL: {wp_draft_url}")
except Exception as e:
    results["agent_11"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 12: Quality Auditor ───────────────────────────────
print("\n[12/14] Quality Auditor Agent...")
try:
    from agents.agent_12_quality_auditor import QualityAuditorAgent
    agent12 = QualityAuditorAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    qa = asyncio.run(agent12.audit(article_content, {"images": generated_images, "eeat_score": eeat_score}))
    quality_score = qa.get("score", 0)
    results["agent_12"] = {"status": "PASS", "quality_score": quality_score}
    print(f"  PASS - Quality score: {quality_score}")
except Exception as e:
    results["agent_12"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 13: Final Validator ───────────────────────────────
print("\n[13/14] Final Validator Agent...")
try:
    from agents.agent_13_final_validator import FinalValidatorAgent
    agent13 = FinalValidatorAgent({"openai_api_key": os.environ["OPENAI_API_KEY"]})
    val = asyncio.run(agent13.validate({
        "content": article_content,
        "images": generated_images,
        "eeat_score": eeat_score,
        "quality_score": quality_score,
        "wp_draft_id": wp_draft_id
    }))
    final_status = val.get("status", "UNKNOWN")
    results["agent_13"] = {"status": "PASS", "final_status": final_status}
    print(f"  PASS - Final status: {final_status}")
except Exception as e:
    results["agent_13"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── Agent 14: Reporting ─────────────────────────────────────
print("\n[14/14] Reporting Agent...")
try:
    from agents.agent_14_reporting import ReportingAgent
    agent14 = ReportingAgent({
        "sendgrid_api_key": os.environ.get("SENDGRID_API_KEY", ""),
        "email_recipient": os.environ.get("EMAIL_RECIPIENT", "")
    })
    elapsed = time.time() - start_time
    report_data = {
        "run_id": os.environ.get("GITHUB_RUN_ID", "test"),
        "topic": topic.get("keyword", str(topic)) if topic else "Unknown",
        "market": market,
        "results": results,
        "wp_draft_id": wp_draft_id,
        "wp_draft_url": wp_draft_url,
        "eeat_score": eeat_score,
        "quality_score": quality_score,
        "final_status": final_status,
        "elapsed_seconds": round(elapsed, 1)
    }
    rep = asyncio.run(agent14.send_report(report_data))
    results["agent_14"] = {"status": "PASS", "email_sent": rep.get("sent", False)}
    print(f"  PASS - Email sent: {rep.get('sent', False)}")
except Exception as e:
    results["agent_14"] = {"status": "FAIL", "error": str(e)}
    print(f"  FAIL - {e}")

# ── FINAL REPORT ────────────────────────────────────────────
elapsed = time.time() - start_time
passed = sum(1 for r in results.values() if r.get("status") == "PASS")
failed = sum(1 for r in results.values() if r.get("status") == "FAIL")
total = len(results)

print("\n" + "=" * 60)
print("NEXUS-14 EXECUTION REPORT")
print("=" * 60)
print(f"Topic    : {topic.get('keyword', str(topic)) if topic else 'Unknown'}")
print(f"Market   : {market}")
print(f"WP Draft : {wp_draft_id or 'NOT CREATED'}")
print(f"WP URL   : {wp_draft_url or 'N/A'}")
print(f"EEAT     : {eeat_score}/100")
print(f"Quality  : {quality_score}/100")
print(f"Time     : {round(elapsed, 1)}s ({round(elapsed/60, 1)} min)")
print(f"Agents   : {passed}/{total} PASSED, {failed}/{total} FAILED")
print()
print("AGENT RESULTS:")
for agent, result in results.items():
    status = result.get("status", "UNKNOWN")
    detail = {k: v for k, v in result.items() if k != "status"}
    status_icon = "OK" if status == "PASS" else "XX"
    print(f"  [{status_icon}] {agent}: {status} | {detail}")
print()

verdict = "PASS" if failed == 0 else ("PARTIAL" if passed >= 10 else "FAIL")
print(f">>> FINAL VERDICT: {verdict} ({passed}/{total} agents)")
if wp_draft_id:
    print(f">>> WordPress draft created: ID {wp_draft_id}")
print()
status_label = "VERIFIED PRODUCTION READY" if verdict == "PASS" else "NOT VERIFIED"
print(f"STATUS: {status_label}")
print("=" * 60)

# Save JSON report
report = {
    "verdict": verdict,
    "status": status_label,
    "topic": topic.get("keyword", str(topic)) if topic else "Unknown",
    "market": market,
    "wp_draft_id": wp_draft_id,
    "wp_draft_url": wp_draft_url,
    "eeat_score": eeat_score,
    "quality_score": quality_score,
    "elapsed_seconds": round(elapsed, 1),
    "agents_passed": passed,
    "agents_failed": failed,
    "agents_total": total,
    "results": {k: {str(ki): str(vi) for ki, vi in v.items()} for k, v in results.items()}
}
with open("execution_report.json", "w") as f:
    json.dump(report, f, indent=2, default=str)
print("Saved: execution_report.json")

if verdict == "FAIL":
    sys.exit(1)
