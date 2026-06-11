#!/usr/bin/env python3
"""
NEXUS-14: Social Video Agent  — Agent 15
agents/social_video_agent.py

Auto-generates for every approved article:
  3 TikTok scripts         (15-30s, 9:16 vertical)
  3 YouTube Shorts scripts (15-30s, 9:16 vertical)
  3 Instagram Reels scripts(15-30s, 9:16 vertical)
  3 Higgsfield AI prompts  (CLI-ready, production-grade)
  Captions + hashtags for all platforms

Audience  : Newcomers / immigrants / international students in USA & Canada
Language  : Native American English only -- no French, no robotic AI tone
Higgsfield: CLI integration (npm install -g @higgsfield/cli)
            MCP integration (https://mcp.higgsfield.ai/mcp)
"""

import os, sys, json, time
from datetime import datetime

try:
    import openai
except ImportError:
    os.system("pip install openai -q")
    import openai

# ─── CONFIG ──────────────────────────────────────────────────
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY", "")
ARTICLE_INDEX = os.environ.get("ARTICLE_INDEX", "0")
TOPIC         = (os.environ.get("TOPIC_OVERRIDE") or "").strip()
MARKET        = (os.environ.get("TARGET_MARKET") or "usa").lower().strip()
OUTPUT_BASE   = os.environ.get("SOCIAL_OUTPUT_DIR", "output/social")

PLATFORM_DIRS = {
    "tiktok":      os.path.join(OUTPUT_BASE, "tiktok"),
    "shorts":      os.path.join(OUTPUT_BASE, "shorts"),
    "reels":       os.path.join(OUTPUT_BASE, "reels"),
    "higgsfield":  os.path.join(OUTPUT_BASE, "higgsfield"),
}

# ─── HELPERS ─────────────────────────────────────────────────
def ensure_dirs():
    for d in PLATFORM_DIRS.values():
        os.makedirs(d, exist_ok=True)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")

def save_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  Saved: {path}")

def call_llm(client, prompt, max_tokens=2000):
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an elite social media content strategist for MoneyAbroadGuide.com. "
                    "Write viral short-form video scripts for TikTok, YouTube Shorts, and Instagram Reels. "
                    "Audience: new immigrants, international students, and foreign workers in USA or Canada. "
                    "Rules: "
                    "1. Native American English only. No French. No robotic AI tone. "
                    "2. Hook in first 3 seconds. "
                    "3. Scripts 15-30 seconds when read aloud (40-75 spoken words). "
                    "4. End every script with a CTA pointing to moneyabroadguide.com. "
                    "5. Format: 9:16 vertical video."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.85,
    )
    return resp.choices[0].message.content.strip()

def parse_json_response(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(raw)


# ─── STEP 1: EXTRACT INSIGHTS ────────────────────────────────
def extract_insights(client, article_text, topic):
    print("\n[STEP 1] Extracting top 3 viral insights...")
    prompt = f"""Analyze this financial article: {topic}

ARTICLE (first 3000 chars):
{article_text[:3000]}

Extract the TOP 3 most emotionally engaging insights for a newcomer scrolling TikTok.
Return a JSON array of exactly 3 objects with keys:
  insight_number   (1 / 2 / 3)
  core_fact        (the single most shocking or valuable fact, 1 sentence)
  emotional_hook   (why it hits hard for newcomers, 1 sentence)
  content_angle    (mistake story | secret tip | myth bust | before-after | surprise reveal)

Raw JSON array only, no markdown."""
    try:
        raw  = call_llm(client, prompt, 800)
        data = parse_json_response(raw)
        print(f"  Extracted {len(data)} insights.")
        return data
    except Exception as e:
        print(f"  Warning: insight extraction failed ({e}), using defaults.")
        return [
            {"insight_number": 1,
             "core_fact": f"Most newcomers lose hundreds of dollars on {topic} in their first year.",
             "emotional_hook": "No one warns you before you land.",
             "content_angle": "mistake story"},
            {"insight_number": 2,
             "core_fact": f"There is a legal workaround for {topic} that most immigrants never discover.",
             "emotional_hook": "Banks and government websites bury this information.",
             "content_angle": "secret tip"},
            {"insight_number": 3,
             "core_fact": f"The number one myth about {topic} costs newcomers money every single month.",
             "emotional_hook": "You probably believe this right now.",
             "content_angle": "myth bust"},
        ]


# ─── STEP 2: TIKTOK SCRIPTS ──────────────────────────────────
def generate_tiktok_scripts(client, insights, topic, market):
    print("\n[STEP 2] Generating 3 TikTok scripts...")
    scripts = []
    for ins in insights:
        prompt = f"""Write a TikTok video script (15-30 seconds) for newcomer finance content.

Topic        : {topic}
Core Insight : {ins.get('core_fact', '')}
Hook Style   : {ins.get('content_angle', '')}
Emotional    : {ins.get('emotional_hook', '')}
Market       : {market.upper()}

Return this exact JSON structure:
{{
  "hook":              "Opening line (3 seconds) -- must stop the scroll immediately",
  "body":              "Main content (10-20 seconds spoken, conversational)",
  "cta":               "Call-to-action (3-5 seconds, mention moneyabroadguide.com)",
  "caption":           "TikTok caption (150 chars max, punchy and native English)",
  "hashtags":          ["10", "relevant", "hashtags", "without", "hash", "symbol"],
  "on_screen_text":    "Bold text overlay for the video (max 8 words)",
  "duration_estimate": "e.g. 22 seconds",
  "content_angle":     "{ins.get('content_angle', '')}"
}}
Raw JSON only, no markdown."""
        try:
            raw    = call_llm(client, prompt, 600)
            script = parse_json_response(raw)
        except Exception:
            script = {
                "hook":              f"Nobody tells you this when you land in the {market.upper()}...",
                "body":              ins.get('core_fact', topic),
                "cta":               "Save this. Full guide at moneyabroadguide.com",
                "caption":           f"The {topic} truth they never teach in orientation. Link in bio.",
                "hashtags":          ["newcomerusa","immigrantfinance","newtousa","moneyabroadguide",
                                      "creditscore","newcomercanada","financetips","immigrantlife",
                                      "internationalstudent","expattips"],
                "on_screen_text":    "They never told you this",
                "duration_estimate": "20 seconds",
                "content_angle":     ins.get('content_angle', ''),
            }
        script["insight_number"] = ins.get("insight_number", 1)
        scripts.append(script)
        print(f"  TikTok script #{ins.get('insight_number','?')} done.")
        time.sleep(0.4)
    return scripts


# ─── STEP 3: YOUTUBE SHORTS ──────────────────────────────────
def generate_shorts_scripts(client, insights, topic, market):
    print("\n[STEP 3] Generating 3 YouTube Shorts scripts...")
    scripts = []
    for ins in insights:
        prompt = f"""Write a YouTube Shorts script (15-30 seconds) for newcomer finance.

Topic   : {topic}
Insight : {ins.get('core_fact', '')}
Angle   : {ins.get('content_angle', '')}
Market  : {market.upper()}

YouTube Shorts specifics: slightly more educational, search-optimized, subscribe CTA.
Audience: 25-40yo immigrants, more professional tone than TikTok.

Return this exact JSON:
{{
  "hook":              "Opening hook (3 seconds)",
  "body":              "Educational content (15-22 seconds spoken)",
  "cta":               "Subscribe + moneyabroadguide.com CTA (3-5 seconds)",
  "title":             "YouTube Shorts title (60 chars max, SEO-optimized)",
  "description":       "Description (200 chars, include moneyabroadguide.com)",
  "hashtags":          ["8", "youtube", "hashtags"],
  "chapters":          ["00:00 Hook", "00:03 Main Tip", "00:22 CTA"],
  "duration_estimate": "e.g. 25 seconds"
}}
Raw JSON only."""
        try:
            raw    = call_llm(client, prompt, 600)
            script = parse_json_response(raw)
        except Exception:
            script = {
                "hook":              f"Here is what no one tells you about {topic} in the {market.upper()}.",
                "body":              ins.get('core_fact', ''),
                "cta":               "Subscribe for more newcomer finance tips. Full guide at moneyabroadguide.com",
                "title":             f"{topic.title()} for Newcomers — What They Never Tell You",
                "description":       f"Complete guide to {topic} for immigrants. Visit moneyabroadguide.com for the full breakdown.",
                "hashtags":          ["newcomers","immigrantfinance","moneyabroadguide","creditscore",
                                      "bankingusa","newcomercanada","expat","financetips"],
                "chapters":          ["00:00 Hook", "00:03 Main Content", "00:22 CTA"],
                "duration_estimate": "25 seconds",
            }
        script["insight_number"] = ins.get("insight_number", 1)
        scripts.append(script)
        print(f"  Shorts script #{ins.get('insight_number','?')} done.")
        time.sleep(0.4)
    return scripts


# ─── STEP 4: INSTAGRAM REELS ─────────────────────────────────
def generate_reels_scripts(client, insights, topic, market):
    print("\n[STEP 4] Generating 3 Instagram Reels scripts...")
    scripts = []
    for ins in insights:
        prompt = f"""Write an Instagram Reels script (15-30 seconds) for newcomer finance.

Topic   : {topic}
Insight : {ins.get('core_fact', '')}
Angle   : {ins.get('content_angle', '')}
Market  : {market.upper()}

Instagram Reels specifics: aspirational + practical, visual-first storytelling,
save-worthy, profile link CTA, community feel.

Return this exact JSON:
{{
  "hook":                  "Visual hook + opening line (3 seconds)",
  "body":                  "Main value content (15-20 seconds spoken)",
  "cta":                   "Save this + link in bio CTA",
  "caption":               "Instagram caption (300 chars max, storytelling native English)",
  "hashtags":              ["15", "instagram", "hashtags"],
  "on_screen_text_sequence": [
    "Screen text 0-3s",
    "Screen text 3-15s",
    "Screen text 15-25s",
    "CTA 25-30s"
  ],
  "visual_notes":          "Brief direction for visuals (background, font, transitions)",
  "duration_estimate":     "e.g. 28 seconds"
}}
Raw JSON only."""
        try:
            raw    = call_llm(client, prompt, 700)
            script = parse_json_response(raw)
        except Exception:
            script = {
                "hook":                  "POV: You just landed in the USA and nobody told you this...",
                "body":                  ins.get('core_fact', ''),
                "cta":                   "Save this post! Link in bio for the full free guide.",
                "caption":               f"The {topic} truth every newcomer needs to know. I wish someone had told me this on day one. Save this for later. Full guide at moneyabroadguide.com",
                "hashtags":              ["newcomerusa","immigrantlife","movingtous","internationalstudent",
                                          "expatliving","financetips","creditscore","newcomercanada",
                                          "moneyabroadguide","immigrantfinance","usalife","canadalife",
                                          "newtousa","foreignworker","financialfreedom"],
                "on_screen_text_sequence": [
                    "Nobody told me this...",
                    ins.get('core_fact','')[:60],
                    "Here is what to do instead",
                    "Full guide at moneyabroadguide.com",
                ],
                "visual_notes":          "Dark background, bold white text (Montserrat), zoom transitions between cards",
                "duration_estimate":     "25 seconds",
            }
        script["insight_number"] = ins.get("insight_number", 1)
        scripts.append(script)
        print(f"  Reels script #{ins.get('insight_number','?')} done.")
        time.sleep(0.4)
    return scripts


# ─── STEP 5: HIGGSFIELD PROMPTS ──────────────────────────────
def generate_higgsfield_prompts(client, insights, topic, market):
    print("\n[STEP 5] Generating 3 Higgsfield video prompts...")
    models = [
        ("seedance_2_0",         "Seedance 2.0",         "cinematic urban realism, 30+ fps"),
        ("cinematic_studio_3_0", "Cinematic Studio 3.0", "professional documentary, controlled lighting"),
        ("veo3_1",               "Google Veo 3.1",       "hyper-realistic, emotional storytelling"),
    ]
    prompts = []
    for i, ins in enumerate(insights):
        model_id, model_name, style = models[i % len(models)]
        prompt_req = f"""Create a Higgsfield AI video generation prompt for a 15-30 second social video.

Topic    : {topic}
Insight  : {ins.get('core_fact', '')}
Angle    : {ins.get('content_angle', '')}
Audience : Newcomers and immigrants in {market.upper()}
Model    : {model_name} ({style})
Format   : 9:16 vertical, mobile-first, TikTok/Reels/Shorts

Describe in rich cinematic detail:
1. Opening shot (exact framing, what the viewer sees in frame 1)
2. Subject (diverse person 25-35yo, immigrant background, specific appearance and emotion)
3. Environment (apartment, city street, bank, office -- realistic USA/Canada setting)
4. Camera movement (push in / pull out / handheld / static / orbit)
5. Lighting (golden hour / fluorescent office / night city glow / etc.)
6. Key visual action or transition
7. Text overlay instructions (font: Montserrat Bold, large, white with dark outline)
8. Ending frame

Return this exact JSON:
{{
  "model":                  "{model_id}",
  "model_name":             "{model_name}",
  "prompt":                 "Full Higgsfield generation prompt (200-300 words, highly descriptive, cinematic language)",
  "aspect_ratio":           "9:16",
  "duration":               10,
  "mode":                   "pro",
  "negative_prompt":        "blurry, low quality, watermark, text errors, distorted faces, oversaturated",
  "post_production_notes":  "Step-by-step CapCut editing instructions for this clip",
  "platform_use":           ["tiktok", "reels", "shorts"]
}}
Raw JSON only."""
        try:
            raw = call_llm(client, prompt_req, 800)
            hf  = parse_json_response(raw)
        except Exception:
            hf = {
                "model":       model_id,
                "model_name":  model_name,
                "prompt": (
                    f"Vertical 9:16 cinematic short video. Opening frame: a diverse young person "
                    f"(mid-20s, immigrant background, professional casual clothing) staring at "
                    f"official paperwork with visible stress in a modern North American city apartment. "
                    f"Close-up on face, worried eyes. Slow cinematic push-in. Warm golden-hour window "
                    f"light from the right side. Bold white text overlay fades in: 'Nobody told me this.' "
                    f"Camera gradually pulls back to reveal the city skyline through the window. "
                    f"The subject looks up with sudden realization -- eyebrows raise, slight smile. "
                    f"Text changes to: '{topic.title()}'. Emotional documentary style, shallow depth of "
                    f"field. Final frame: subject looking at phone screen, relieved smile, subtle nod. "
                    f"Text overlay: 'moneyabroadguide.com'. Fade to black. "
                    f"Color grade: warm tones with slight filmic grain."
                ),
                "aspect_ratio":          "9:16",
                "duration":              10,
                "mode":                  "pro",
                "negative_prompt":       "blurry, low quality, watermark, text errors, distorted faces, oversaturated",
                "post_production_notes": (
                    "1. Import 3 generated clips into CapCut (each ~10s). "
                    "2. Trim to best 7-8 seconds per clip (total 22-25s). "
                    "3. Add bold white text overlay: Montserrat Bold 48pt, dark stroke outline. "
                    "4. Select trending audio (CapCut library, emotional/uplifting). "
                    "5. Add auto-captions (CapCut built-in, white text black outline). "
                    "6. Export: 1080x1920, 30fps, H.264, high quality. "
                    "7. Upload directly to TikTok, Reels, and Shorts."
                ),
                "platform_use": ["tiktok", "reels", "shorts"],
            }
        hf["insight_number"] = ins.get("insight_number", i + 1)
        hf["topic"]  = topic
        hf["market"] = market.upper()
        hf["cli_command"] = (
            f'higgsfield generate create {model_id} '
            f'--prompt "$(cat {PLATFORM_DIRS["higgsfield"]}/higgsfield_prompt_{ARTICLE_INDEX}_v{i+1}.txt)" '
            f'--aspect_ratio 9:16 --duration 10 --mode pro --wait'
        )
        prompts.append(hf)
        print(f"  Higgsfield prompt #{i+1} done (model: {model_id}).")
        time.sleep(0.4)
    return prompts


# ─── STEP 6: SAVE OUTPUTS ────────────────────────────────────
def save_all_outputs(article_index, tiktok, shorts, reels, hf_prompts, insights, topic, market):
    slug = article_index.lower().replace(" ", "-")

    # TikTok
    for i, s in enumerate(tiktok):
        save_json(os.path.join(PLATFORM_DIRS["tiktok"], f"tiktok_{slug}_v{i+1}.json"), s)
    save_json(os.path.join(PLATFORM_DIRS["tiktok"], f"tiktok_{slug}_all.json"),
              {"article_index": article_index, "platform": "tiktok", "scripts": tiktok})

    # YouTube Shorts
    for i, s in enumerate(shorts):
        save_json(os.path.join(PLATFORM_DIRS["shorts"], f"shorts_{slug}_v{i+1}.json"), s)
    save_json(os.path.join(PLATFORM_DIRS["shorts"], f"shorts_{slug}_all.json"),
              {"article_index": article_index, "platform": "youtube_shorts", "scripts": shorts})

    # Instagram Reels
    for i, s in enumerate(reels):
        save_json(os.path.join(PLATFORM_DIRS["reels"], f"reels_{slug}_v{i+1}.json"), s)
    save_json(os.path.join(PLATFORM_DIRS["reels"], f"reels_{slug}_all.json"),
              {"article_index": article_index, "platform": "instagram_reels", "scripts": reels})

    # Higgsfield
    for i, p in enumerate(hf_prompts):
        save_json(os.path.join(PLATFORM_DIRS["higgsfield"], f"higgsfield_{slug}_v{i+1}.json"), p)
        # Raw prompt text for CLI piping
        save_text(
            os.path.join(PLATFORM_DIRS["higgsfield"], f"higgsfield_prompt_{slug}_v{i+1}.txt"),
            p.get("prompt", "")
        )
        # Ready-to-run shell script
        model = p.get("model", "seedance_2_0")
        sh = (
            "#!/bin/bash\n"
            f"# Higgsfield CLI — Article {article_index} v{i+1}\n"
            f"# Model : {p.get('model_name', model)}\n"
            f"# Topic : {topic}\n\n"
            f'PROMPT_FILE="$(dirname "$0")/higgsfield_prompt_{slug}_v{i+1}.txt"\n\n'
            f"higgsfield generate create {model} \\\n"
            f'  --prompt "$(cat $PROMPT_FILE)" \\\n'
            f"  --aspect_ratio 9:16 \\\n"
            f"  --duration 10 \\\n"
            f"  --mode pro \\\n"
            f"  --wait\n"
        )
        save_text(os.path.join(PLATFORM_DIRS["higgsfield"], f"generate_{slug}_v{i+1}.sh"), sh)

    save_json(os.path.join(PLATFORM_DIRS["higgsfield"], f"higgsfield_{slug}_all.json"), {
        "article_index": article_index,
        "higgsfield_integration": {
            "method_primary":   "CLI",
            "method_secondary": "MCP (Claude Desktop)",
            "cli_install":      "npm install -g @higgsfield/cli",
            "cli_auth":         "higgsfield auth login",
            "mcp_url":          "https://mcp.higgsfield.ai/mcp",
            "docs":             "https://github.com/higgsfield-ai/cli",
            "available_models": {
                "seedance_2_0":         "Cinematic urban realism",
                "cinematic_studio_3_0": "Professional documentary",
                "veo3_1":               "Hyper-realistic storytelling",
                "kling3_0":             "Smooth motion alternative",
                "nano_banana_2":        "Fast image generation",
            },
        },
        "prompts": hf_prompts,
    })

    # Master social bundle
    master = os.path.join(OUTPUT_BASE, f"social_assets_{slug}.json")
    save_json(master, {
        "generated_at":       datetime.utcnow().isoformat(),
        "article_index":      article_index,
        "topic":              topic,
        "market":             market.upper(),
        "insights_extracted": len(insights),
        "tiktok_scripts":     len(tiktok),
        "shorts_scripts":     len(shorts),
        "reels_scripts":      len(reels),
        "higgsfield_prompts": len(hf_prompts),
        "total_assets":       len(tiktok) + len(shorts) + len(reels) + len(hf_prompts),
        "output_dirs":        PLATFORM_DIRS,
    })
    return master


# ─── MAIN ────────────────────────────────────────────────────
def main():
    START = time.time()
    print("=" * 60)
    print("NEXUS-14 SOCIAL VIDEO AGENT (Agent 15)")
    print("=" * 60)
    print(f"Article : {ARTICLE_INDEX}")
    print(f"Topic   : {TOPIC or '(reading from article file)'}")
    print(f"Market  : {MARKET.upper()}")
    print(f"OpenAI  : {'SET' if OPENAI_KEY else 'MISSING'}")
    print()

    if not OPENAI_KEY:
        print("ERROR: OPENAI_API_KEY is required.")
        sys.exit(1)

    ensure_dirs()
    client = openai.OpenAI(api_key=OPENAI_KEY)

    # Load article content
    article_text = ""
    topic = TOPIC
    article_file = f"article_{ARTICLE_INDEX}.md"
    if os.path.exists(article_file):
        with open(article_file, "r", encoding="utf-8") as f:
            article_text = f.read()
        print(f"  Loaded: {article_file} ({len(article_text.split())} words)")
    else:
        report_file = f"execution_report_{ARTICLE_INDEX}.json"
        if os.path.exists(report_file):
            with open(report_file, "r") as f:
                rpt = json.load(f)
                if not topic:
                    topic = rpt.get("topic", "")
        article_text = f"Financial guide: {topic} for {MARKET.upper()} newcomers and immigrants."
        print(f"  No article file — using topic: {topic}")

    topic = topic or "financial tips for newcomers in USA and Canada"

    insights   = extract_insights(client, article_text, topic)
    tiktok     = generate_tiktok_scripts(client, insights, topic, MARKET)
    shorts     = generate_shorts_scripts(client, insights, topic, MARKET)
    reels      = generate_reels_scripts(client, insights, topic, MARKET)
    hf_prompts = generate_higgsfield_prompts(client, insights, topic, MARKET)

    master = save_all_outputs(ARTICLE_INDEX, tiktok, shorts, reels, hf_prompts, insights, topic, MARKET)

    elapsed = round(time.time() - START, 1)
    total   = len(tiktok) + len(shorts) + len(reels) + len(hf_prompts)

    print()
    print("=" * 60)
    print("SOCIAL VIDEO AGENT -- PRODUCTION REPORT")
    print("=" * 60)
    print(f"[PASS] Insights extracted      : {len(insights)}")
    print(f"[PASS] TikTok scripts          : {len(tiktok)}")
    print(f"[PASS] YouTube Shorts scripts  : {len(shorts)}")
    print(f"[PASS] Instagram Reels scripts : {len(reels)}")
    print(f"[PASS] Higgsfield prompts      : {len(hf_prompts)}")
    print(f"[PASS] Total assets generated  : {total}")
    print(f"       Output : {OUTPUT_BASE}")
    print(f"       Time   : {elapsed}s")
    print("=" * 60)

    report = {
        "agent":              "social_video_agent",
        "article_index":      ARTICLE_INDEX,
        "topic":              topic,
        "market":             MARKET.upper(),
        "insights_extracted": len(insights),
        "tiktok_scripts":     len(tiktok),
        "shorts_scripts":     len(shorts),
        "reels_scripts":      len(reels),
        "higgsfield_prompts": len(hf_prompts),
        "total_assets":       total,
        "elapsed_seconds":    elapsed,
        "timestamp":          datetime.utcnow().isoformat(),
        "status":             "SUCCESS",
    }
    with open(f"social_report_{ARTICLE_INDEX}.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved: social_report_{ARTICLE_INDEX}.json")


if __name__ == "__main__":
    main()
