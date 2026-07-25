"""Minimal, standalone Gemini image-generation smoke test -- ONE request, no
WordPress upload, no article pipeline. Built 2026-07-25 to check whether a
credit top-up on Google AI Studio actually reached the project this pipeline
authenticates against, without burning a full production run to find out
(agents/agent_10_image_production.py's real call, same endpoint/auth/model,
reproduced standalone here for a single request rather than 5+ per article).

Exit 0 + prints "GEMINI OK" on a real image byte response; exit 1 with the
raw error otherwise (rate limit, quota/billing, auth) so a human can tell a
propagation delay/wrong-project mismatch from an actual code problem.
"""
import base64
import json
import os
import sys
import urllib.request

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"


def main():
    key = os.environ["GEMINI_API_KEY"]
    payload = {
        "contents": [{"parts": [{"text": "a simple blue circle on a white background"}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"GEMINI FAIL: HTTP {e.code}")
        print(body[:2000])
        sys.exit(1)

    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    img_part = next((p for p in parts if "inlineData" in p), None)
    if not img_part:
        print("GEMINI FAIL: no image in response")
        print(json.dumps(data, indent=2)[:2000])
        sys.exit(1)

    img_bytes = base64.b64decode(img_part["inlineData"]["data"])
    with open("gemini_test_image.png", "wb") as f:
        f.write(img_bytes)
    print(f"GEMINI OK: received {len(img_bytes)} image bytes, saved gemini_test_image.png")


if __name__ == "__main__":
    main()
