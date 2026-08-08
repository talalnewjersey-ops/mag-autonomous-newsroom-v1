"""One-off: generate ONE image via Gemini and upload it to the WordPress media
library as a standalone media item (no post attached, no featured_media set,
no content swap). Used for the published-content audit workstream when a
NEW image is needed inside a hand-edited article body, before the full
content (with the real media URL now known) is written back via a separate
content-update call. Reuses the exact same Gemini/upload logic as
scripts/regenerate_article_images.py, extracted for a single-image case
that isn't tied to an existing post's old_url.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent"


def _req(method, url, headers, data=None, timeout=90):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def generate_image(prompt, gemini_key, attempts=3):
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
        except Exception as e:  # noqa: BLE001
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
    auth_headers = {"Authorization": auth, "Content-Type": "application/json"}
    _req("POST", f"{wp_url.rstrip('/')}/wp-json/wp/v2/media/{media_id}", auth_headers,
         {"alt_text": alt_text}, timeout=30)
    return media_id, media.get("source_url", "")


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"].replace(" ", "")
    gemini_key = os.environ["GEMINI_API_KEY"]
    prompt = os.environ["IMAGE_PROMPT"]
    alt_text = os.environ["IMAGE_ALT_TEXT"]
    name_prefix = os.environ.get("IMAGE_NAME_PREFIX", "audit_image")

    auth = "Basic " + base64.b64encode(f"{user}:{app_pw}".encode()).decode()

    print("--- generating image ---")
    img_bytes = generate_image(prompt, gemini_key)
    print(f"  generated {len(img_bytes)} bytes")
    filename = f"{name_prefix}_{int(time.time())}.jpg"
    media_id, source_url = upload_media(wp_url, auth, img_bytes, filename, alt_text, "image/jpeg")
    print(f"  uploaded media_id={media_id} url={source_url}")

    result = {"media_id": media_id, "url": source_url, "bytes": len(img_bytes)}
    with open("single_image_upload_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
