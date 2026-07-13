"""Read-only diagnostic: fetches a WordPress page's full edit-context data
(raw content + all registered meta, including Elementor's _elementor_data,
_elementor_edit_mode, _elementor_template_type, _elementor_page_settings,
_elementor_conditions) and writes it to a JSON file. Never writes to
WordPress -- pure backup, used before disabling Elementor on a page
(2026-07-13, Start Here redesign).
"""
import base64
import json
import os
import urllib.request


def fetch_page_full(wp_url, user, app_password, page_id):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/pages/{page_id}?context=edit"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    page_id = os.environ["PAGE_ID"]
    output_path = os.environ["OUTPUT_PATH"]

    data = fetch_page_full(wp_url, user, app_pw, page_id)

    backup = {
        "id": data.get("id"),
        "slug": data.get("slug"),
        "status": data.get("status"),
        "link": data.get("link"),
        "template": data.get("template"),
        "title": data.get("title", {}).get("raw"),
        "content_raw": data.get("content", {}).get("raw"),
        "meta": data.get("meta", {}),
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)

    print(f"Backed up page {page_id} ({backup['slug']}) to {output_path}")
    print(f"content_raw length: {len(backup['content_raw'] or '')}")
    elementor_data = backup["meta"].get("_elementor_data")
    print(f"_elementor_data present: {bool(elementor_data)} (length: {len(elementor_data or '')})")
    print(f"_elementor_edit_mode: {backup['meta'].get('_elementor_edit_mode')!r}")


if __name__ == "__main__":
    main()
