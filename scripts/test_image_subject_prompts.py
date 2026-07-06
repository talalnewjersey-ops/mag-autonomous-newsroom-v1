"""EMPIRICAL TEST (2026-07-06), NOT wired into production: verifies whether
injecting the REAL article subject (keyword) directly into an image prompt --
instead of the current hardcoded per-broad-category bucket -- produces a
relevant image for genuinely ABSTRACT financial topics (savings, credit
building), not just visually obvious ones (car insurance).

This is a throwaway diagnostic, run via a dedicated workflow_dispatch
workflow (not production_v2.yml), calling the SAME Gemini endpoint/payload
shape as agents/agent_10_image_production.py, so the result is representative
of what the real pipeline would actually produce. Writes each prompt + its
resulting image to --output-dir for manual inspection. Never touches
WordPress, never touches the production prompt-generation code.
"""
import argparse
import asyncio
import base64
import json
import os
from pathlib import Path

import aiohttp

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"

# The exact deterministic template proposed for agent_09's featured/supporting
# image prompts: inject the real keyword, ground it toward a concrete,
# photographable scene, keep the same style/guardrail language already used
# in production today.
STYLE_SUFFIX = (
    ", Ultra realistic magazine editorial photography, financial publication quality, "
    "soft natural lighting, professional color grading, "
    "No text overlays, no numbers, no watermarks, no logos, no brand names, no readable signage, "
    "no identifiable real individuals -- only anonymous, generic figures if a person appears, "
    "Avoid: cartoon style, illustration, 3D render, unrealistic proportions"
)


def build_prompt(keyword: str) -> str:
    subject = (
        f"an authentic, real-world editorial scene grounded in the everyday, tangible side of "
        f"'{keyword}' -- a person engaging with a relevant physical setting, device, app screen, "
        f"or document, photographed in a realistic, non-symbolic style"
    )
    return f"Subject: {subject}{STYLE_SUFFIX}"


TEST_CASES = [
    ("high_interest_savings", "high-interest savings account"),
    ("build_credit", "build credit as a newcomer"),
    ("send_money", "send money internationally"),
]


async def _generate_one(session, api_key, name, keyword, output_dir):
    prompt = build_prompt(keyword)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    result = {"name": name, "keyword": keyword, "prompt": prompt}
    try:
        async with session.post(GEMINI_ENDPOINT, json=payload, headers=headers,
                                 timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status != 200:
                text = await resp.text()
                result["status"] = "ERROR"
                result["error"] = f"{resp.status} {text[:300]}"
                return result
            data = await resp.json()
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            img_part = next((p for p in parts if "inlineData" in p), None)
            if not img_part:
                result["status"] = "ERROR"
                result["error"] = f"no image in response, parts={[list(p.keys()) for p in parts]}"
                return result
            img_b64 = img_part["inlineData"]["data"]
            mime = img_part["inlineData"].get("mimeType", "image/jpeg")
            ext = mime.split("/")[-1] if "/" in mime else "jpg"
            filepath = output_dir / f"{name}.{ext}"
            filepath.write_bytes(base64.b64decode(img_b64))
            result["status"] = "SUCCESS"
            result["filepath"] = str(filepath)
            result["file_size_bytes"] = filepath.stat().st_size
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
    return result


async def main_async(api_key, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    async with aiohttp.ClientSession() as session:
        for name, keyword in TEST_CASES:
            r = await _generate_one(session, api_key, name, keyword, output_dir)
            print(f"{name}: {r['status']}" + (f" -> {r.get('filepath')}" if r["status"] == "SUCCESS" else f" -- {r.get('error')}"))
            results.append(r)
    (output_dir / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="test_image_output")
    args = parser.parse_args()
    api_key = os.environ["GEMINI_API_KEY"]
    asyncio.run(main_async(api_key, Path(args.output_dir)))


if __name__ == "__main__":
    main()
