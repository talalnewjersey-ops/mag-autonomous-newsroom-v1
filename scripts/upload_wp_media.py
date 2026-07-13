"""Write action: uploads a local image file to the WordPress media library via
POST /wp-json/wp/v2/media, and sets alt text + caption (photographer credit).
Reads the file from MEDIA_FILE, uses MEDIA_TITLE/MEDIA_ALT/MEDIA_CAPTION.
Prints the resulting media id and source_url on success.
"""
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request


def upload_media(wp_url, user, app_password, file_path, title, alt_text, caption):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/media"
    filename = os.path.basename(file_path)
    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "application/octet-stream"

    with open(file_path, "rb") as f:
        data = f.read()

    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": mime,
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status, result = resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

    if status not in (200, 201):
        return status, result

    media_id = result.get("id")
    patch_url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/media/{media_id}"
    patch_payload = json.dumps({
        "title": title,
        "alt_text": alt_text,
        "caption": caption,
    }).encode("utf-8")
    patch_req = urllib.request.Request(
        patch_url, data=patch_payload, method="POST",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(patch_req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return status, result


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    file_path = os.environ["MEDIA_FILE"]
    title = os.environ.get("MEDIA_TITLE", os.path.basename(file_path))
    alt_text = os.environ.get("MEDIA_ALT", "")
    caption = os.environ.get("MEDIA_CAPTION", "")

    status, result = upload_media(wp_url, user, app_pw, file_path, title, alt_text, caption)
    if status not in (200, 201):
        print(f"UPLOAD FAILED: HTTP {status}: {result}")
        sys.exit(1)

    print(f"SUCCESS: media_id={result.get('id')} source_url={result.get('source_url')}")


if __name__ == "__main__":
    main()
