"""Regenerate a post's 5 images via Gemini and swap out placeholder images --
without touching article text. Built 2026-07-25: agent_10_image_production.py
silently falls back to a tiny generic placeholder PNG whenever Gemini errors
(rate limit, depleted billing), and posts 48945/48957 both shipped that way
while the Gemini account was out of credit. The article text itself is
unaffected by this -- a full article regeneration would be wasted work (and
would discard 48945's already-reviewed, hand-fixed body text) when only the
images need a retry now that the credit is restored.

Reuses the SAME endpoint/payload/model as agents/agent_10_image_production.py
(gemini-3.1-flash-image via generateContent), reproduced standalone so this
doesn't need the full agent framework or an article_draft.md on disk.

Fix-file input ({"post_id": ..., "images": {<type>: {"prompt", "alt_text",
"format", "width", "height"}}}), same "checked-in, versioned, auditable"
convention as audit/pending_fixes/*.json for scripts/apply_single_post_fix.py
-- prompts are real historical values from agent_09's own output, not
reconstructed guesses.

Per image type:
  - Calls Gemini, saves the PNG/JPG locally.
  - Uploads to the WordPress media library, sets alt text.
  - "featured_image": sets the post's featured_media to the new attachment.
  - Any other type: replaces the post's CURRENT embedded placeholder <img>
    src URL with the new one in post content -- exact-count-verified, same
    safety contract as apply_single_post_fix.py (refuses to write if the old
    URL isn't found exactly once).

Never touches article text, title, or any field besides content/
featured_media (and only the image src within content).
"""
import base64
import json
import os
import sys
import time
import urllib.request

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"


def _req(method, url, headers, data=None, timeout=90):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def generate_image(prompt, gemini_key, attempts=3):
    """Real transient network errors ("Network is unreachable", read
    timeouts) hit this exact runner environment repeatedly this session,
    unrelated to Gemini/billing itself -- retry a few times before giving up,
    same defense agent_10_image_production.py already has for its own calls."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }
    headers = {"x-goog-api-key": gemini_key, "Content-Type": "application/json"}
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            data = _req("POST", GEMINI_ENDPOINT, headers, payload, timeout=90)
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            img_part = next((p for p in parts if "inlineData" in p), None)
            if not img_part:
                raise RuntimeError(f"no image in Gemini response: {json.dumps(data)[:300]}")
            return base64.b64decode(img_part["inlineData"]["data"])
        except Exception as e:  # noqa: BLE001 -- retry on ANY transient error, then re-raise
            last_err = e
            print(f"  attempt {attempt}/{attempts} failed: {e}")
            if attempt < attempts:
                time.sleep(5)
    raise last_err


def upload_media(wp_url, auth, img_bytes, filename, alt_text, mime):
    headers = {
        "Authorization": auth,
        "Content-Type": mime,
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    req = urllib.request.Request(
        f"{wp_url.rstrip('/')}/wp-json/wp/v2/media", data=img_bytes, method="POST",
        headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        media = json.loads(resp.read().decode())
    media_id = media["id"]
    # set alt text
    auth_headers = {"Authorization": auth, "Content-Type": "application/json"}
    _req("POST", f"{wp_url.rstrip('/')}/wp-json/wp/v2/media/{media_id}", auth_headers,
         {"alt_text": alt_text}, timeout=30)
    return media_id, media.get("source_url", "")


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"].replace(" ", "")
    gemini_key = os.environ["GEMINI_API_KEY"]
    fix_path = os.environ["FIX_FILE"]

    auth = "Basic " + base64.b64encode(f"{user}:{app_pw}".encode()).decode()
    auth_headers = {"Authorization": auth, "Content-Type": "application/json"}

    spec = json.loads(open(fix_path, encoding="utf-8").read())
    post_id = spec["post_id"]

    post = _req("GET", f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}?context=edit", auth_headers)
    content = post["content"]["raw"]

    results = {}
    for img_type, spec_img in spec["images"].items():
        print(f"--- {img_type} ---")
        img_bytes = generate_image(spec_img["prompt"], gemini_key)
        print(f"  generated {len(img_bytes)} bytes")
        fmt = spec_img.get("format", "jpg")
        mime = "image/png" if fmt == "png" else "image/jpeg"
        filename = f"{img_type}_regen_{int(time.time())}.{fmt}"
        media_id, source_url = upload_media(wp_url, auth, img_bytes, filename, spec_img["alt_text"], mime)
        print(f"  uploaded media_id={media_id} url={source_url}")
        results[img_type] = {"media_id": media_id, "url": source_url, "bytes": len(img_bytes)}

        if img_type == "featured_image":
            _req("POST", f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}", auth_headers,
                 {"featured_media": media_id})
            print(f"  set featured_media={media_id}")
        else:
            old_url = spec_img["old_url"]
            count = content.count(old_url)
            if count != 1:
                raise SystemExit(
                    f"REFUSING TO WRITE {img_type}: expected old_url exactly once, found {count}")
            content = content.replace(old_url, source_url)

    _req("POST", f"{wp_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}", auth_headers,
         {"content": content})
    print("Updated post content with new image URLs.")

    with open(f"post_{post_id}_image_regen_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
