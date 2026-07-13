"""Read-only diagnostic: lists every installed WordPress plugin via the REST
API (requires an authenticated user with manage_options) -- slug/name/status/
version/description/plugin_uri -- plus a direct by-slug lookup for a specific
plugin. Never writes anything.

Used to investigate the Bloc 3 "double menu" issue (2026-07-13, AUDIT-LOG.md):
identify what's actively rendering the front end (Elementor, header/footer
builders, Astra addons) and inspect the "Astra Header Fix" plugin's metadata
before any activation decision. The REST API only exposes plugin metadata,
not source code -- it cannot substitute for reading the plugin's PHP files.
"""
import base64
import json
import os
import urllib.error
import urllib.request


def fetch_all_plugins(wp_url, user, app_password):
    auth = base64.b64encode(f"{user}:{app_password}".encode()).decode()
    url = f"{wp_url.rstrip('/')}/wp-json/wp/v2/plugins?per_page=100"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return None, {"error": str(e)}


def _text(field):
    return field.get("rendered", "") if isinstance(field, dict) else (field or "")


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    search_terms = os.environ.get("SEARCH_TERMS", "header,footer,elementor,astra,menu,builder")

    status_code, data = fetch_all_plugins(wp_url, user, app_pw)
    if status_code != 200:
        print(f"ERROR: HTTP {status_code}: {data}")
        return

    plugins = data
    plugins.sort(key=lambda p: (p.get("status") != "active", _text(p.get("name")).lower()))

    print(f"\n===== {len(plugins)} PLUGIN(S) FOUND =====\n")
    for p in plugins:
        print(
            f"status={p.get('status'):<10} | name={_text(p.get('name'))} | "
            f"plugin={p.get('plugin')} | version={p.get('version')} | "
            f"plugin_uri={p.get('plugin_uri')}"
        )

    terms = [t.strip().lower() for t in search_terms.split(",") if t.strip()]
    print(f"\n===== MATCHES for {terms} (name, plugin path, or description) =====\n")
    for p in plugins:
        name = _text(p.get("name")).lower()
        plugin_path = (p.get("plugin") or "").lower()
        desc = _text(p.get("description")).lower()
        if any(t in name or t in plugin_path or t in desc for t in terms):
            print(
                f"status={p.get('status'):<10} | name={_text(p.get('name'))} | "
                f"plugin={p.get('plugin')} | version={p.get('version')}"
            )
            desc_full = _text(p.get("description"))
            if desc_full:
                print(f"  description: {desc_full}")
            print()

    print("\n===== FULL RAW JSON (for anything not covered above) =====\n")
    print(json.dumps(plugins, indent=2))


if __name__ == "__main__":
    main()
