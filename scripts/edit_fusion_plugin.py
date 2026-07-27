"""Write action: reads and optionally writes the raw source of the
'MoneyAbroadGuide Fusion Uploaded HTML' plugin file (the homepage's raw-HTML
template, which bypasses wp_head/wp_footer/the_content entirely -- see
project memory) via the existing 'MAG Plugin RW' Code Snippet (id 22,
normally inactive). Temporarily activates that snippet just long enough to
call its read-plugin/write-plugin REST routes, then deactivates it again --
same "minimize standing PHP execution surface" pattern as
purge_litespeed_cache.py.

SAFETY (this file has a documented history of REST/JSON round-trip fragility
-- a past attempt produced a live/reported hash mismatch, suspected non-UTF8
byte somewhere in the source):
  - decodes the read response with errors="strict", not "replace" -- if the
    live file contains a byte that isn't valid UTF-8, this FAILS LOUDLY here
    (mode=read) instead of silently swapping it for U+FFFD and writing that
    corruption back permanently later (mode=write).
  - mode=write requires OLD_TEXT to be found EXACTLY ONCE in the freshly-read
    live content before writing anything (same convention as
    apply_single_post_fix.py) -- refuses otherwise.
  - the write-plugin route itself already makes its own timestamped
    server-side backup before overwriting (see the snippet's own code).
  - prints before/after length so a truncation is visible immediately.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

RW_SNIPPET_ID = "22"


def _auth_header(user, app_password):
    return "Basic " + base64.b64encode(f"{user}:{app_password}".encode()).decode()


def set_active(wp_url, user, app_password, snippet_id, active):
    url = f"{wp_url.rstrip('/')}/wp-json/code-snippets/v1/snippets/{snippet_id}"
    payload = json.dumps({"active": active}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def read_plugin(wp_url, user, app_password, plugin):
    url = f"{wp_url.rstrip('/')}/wp-json/mag/v1/read-plugin?plugin={plugin}"
    req = urllib.request.Request(url, headers={"Authorization": _auth_header(user, app_password)})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    # strict: fail loudly on any non-UTF8 byte rather than silently mangling it
    decoded = json.loads(raw.decode("utf-8", errors="strict"))
    return decoded


def write_plugin(wp_url, user, app_password, plugin, content):
    url = f"{wp_url.rstrip('/')}/wp-json/mag/v1/write-plugin"
    payload = json.dumps({"plugin": plugin, "content": content}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST",
        headers={"Authorization": _auth_header(user, app_password), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    wp_url = os.environ["WORDPRESS_URL"]
    user = os.environ["WORDPRESS_USERNAME"]
    app_pw = os.environ["WORDPRESS_APP_PASSWORD"]
    plugin = os.environ.get("PLUGIN", "fusion-v51")
    mode = os.environ["MODE"]  # "read" or "write"
    old_text_file = os.environ.get("OLD_TEXT_FILE", "")
    new_text_file = os.environ.get("NEW_TEXT_FILE", "")
    confirm = os.environ.get("CONFIRM", "").lower() == "yes"

    print(f"Activating snippet {RW_SNIPPET_ID} (MAG Plugin RW)...")
    set_active(wp_url, user, app_pw, RW_SNIPPET_ID, True)
    time.sleep(2)

    try:
        result = read_plugin(wp_url, user, app_pw, plugin)
        if "error" in result:
            print(f"READ FAILED: {result['error']}")
            sys.exit(1)
        content = result["content"]
        print(f"READ OK: plugin={plugin} size={result.get('size')} decoded_length={len(content)}")

        with open("plugin_current.php", "w", encoding="utf-8") as f:
            f.write(content)
        print("Saved live content to plugin_current.php")

        if mode == "write":
            if not confirm:
                print("REFUSING: CONFIRM=yes not set. Aborting without writing.")
                sys.exit(1)
            with open(old_text_file, encoding="utf-8") as f:
                old_text = f.read()
            with open(new_text_file, encoding="utf-8") as f:
                new_text = f.read()

            count = content.count(old_text)
            if count != 1:
                print(f"REFUSING TO WRITE: expected exactly 1 occurrence of OLD_TEXT, found {count}.")
                sys.exit(1)

            new_content = content.replace(old_text, new_text)
            print(f"Writing: old_length={len(content)} new_length={len(new_content)} "
                  f"delta={len(new_content) - len(content)}")
            write_result = write_plugin(wp_url, user, app_pw, plugin, new_content)
            print(f"WRITE result: success={write_result.get('success')} "
                  f"bytes={write_result.get('bytes')} backup={write_result.get('backup')}")
            if not write_result.get("success"):
                print("WRITE FAILED")
                sys.exit(1)
    finally:
        print(f"Deactivating snippet {RW_SNIPPET_ID}...")
        set_active(wp_url, user, app_pw, RW_SNIPPET_ID, False)

    print("DONE")


if __name__ == "__main__":
    main()
