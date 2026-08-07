"""GATE D connector-scar repair -- ONE targeted attempt, narrow scope (2026-08-07).

WHY THIS EXISTS: scripts/soften_claims.py's own module docstring documents a
DELIBERATE tradeoff in its CASE 4/5a scaffold handling -- when stripping an
unsourced number would otherwise force deleting a whole informative clause,
it keeps the clause instead and accepts that two connector words may end up
sitting next to each other (e.g. "at 18% of the prior year's" -> "at of the
prior year's" once "18%" is stripped). scripts/placeholder_gate.py's own
docstring documents the other half of this design: a GATE D failure "goes
straight to mark_qa_failed.py ... not back through agent_04 regeneration" --
deliberately, because GATE D runs after the pipeline's retry-eligible
section.

Both of those choices are reasonable in isolation. Combined, they mean this
specific, well-catalogued residue shape (tests/test_placeholder_gate.py has
named regression fixtures for it going back to 2026-07-13) has NO path back
to a healthy article -- one occurrence anywhere in ~4000 words kills the
whole article, with zero retry. Live evidence (2026-08-07): the last 15
scheduled production runs all failed, and the two most recent WordPress
drafts (49200, 49240) both died on exactly this pattern
("at of"/"of in"/"within of").

This module adds a narrow, ADDITIVE repair step that runs strictly AFTER a
GATE D failure and BEFORE mark_qa_failed.py -- NOT a retry through agent_04
(respects placeholder_gate.py's documented reasoning above; nothing is
regenerated). It engages ONLY when the gate report's findings are 100%
adjacent_connector_pair, nothing else (no title finding, no alt-text
finding, no other body finding type) -- any other mix is a different bug
class this script does not attempt to fix and falls straight through to the
pre-existing mark_qa_failed.py path, unchanged.

For each qualifying finding: extract just the ONE flagged sentence, ask the
LLM to rewrite THAT sentence so it reads naturally -- under the SAME
anti-fabrication constraint agent_04 itself is bound by (no reintroduced
number/%/$  amount) -- and verify with agents._placeholder_scan.scan_body
that the repaired sentence is actually clean before splicing it back. Fails
CLOSED: if any single finding can't be cleanly repaired, the whole draft is
left untouched and the caller falls through to the normal GATE D failure
path -- never a partial, silently-worse rewrite.

CLI usage (wired into scripts/production_batch_loop.sh, Phase 11.5 fallback):
    python scripts/repair_connector_scars.py \\
      --article "$DRAFT" \\
      --gate-report "${ARTICLE_DIR}/agent_11/placeholder_gate_report.json" \\
      --wordpress-report "${ARTICLE_DIR}/agent_11/wordpress_report.json"
Exit 0 if every finding was repaired (draft rewritten in place, and -- best
effort, never fatal -- the live WordPress draft's content is synced too).
Exit 1 (draft untouched) if not repairable or any single repair attempt
failed its own post-check.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents._placeholder_scan import scan_body  # noqa: E402

# Same figure-shape the anti-fabrication rule (agent_04's _anti_fab) and
# soften_claims.py's own _NUM_RE both guard against -- a repaired sentence
# must not reintroduce any of these, or the repair defeats the entire point
# of the original strip.
_FABRICATED_NUMBER_RE = re.compile(
    r"(?<![\w.])(?:\$\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?%|\b\d[\d,]*(?:\.\d+)?\b)"
)
# A handful of ordinary non-figure numbers are fine and common in prose
# (years like "2026", ordinal-adjacent digits already elsewhere in the
# sentence) -- but this repair path only ever touches SHORT, single
# sentences where the original defect was precisely "an unsourced figure
# was here"; erring toward strict (reject any bare digit run) is the safe
# default given how narrow and low-volume this path is.
_SENT_END = re.compile(r"[.!?](?=\s|$)")


def is_repairable(report: dict) -> bool:
    """True iff every finding anywhere in the gate report is a body-level
    adjacent_connector_pair -- any title or alt-text finding, or any other
    body finding type, is a different bug class this script does not touch."""
    if report.get("title_findings") or report.get("alt_text_findings"):
        return False
    body = report.get("body_findings", [])
    if not body:
        return False
    return all(f.get("type") == "adjacent_connector_pair" for f in body)


def extract_sentence(text: str, position: int) -> Tuple[str, int, int]:
    """Return (sentence, start, end) -- the sentence containing `position`,
    bounded by the nearest '.'/'!'/'?' (followed by whitespace or end of
    text) on either side. Pure text-slicing, same simple convention
    soften_claims.py's own per-line sentence split already uses."""
    ends = [m.end() for m in _SENT_END.finditer(text)]
    start = 0
    for e in ends:
        if e <= position:
            start = e
        else:
            break
    while start < len(text) and text[start].isspace():
        start += 1
    end = len(text)
    for e in ends:
        if e > position:
            end = e
            break
    return text[start:end], start, end


def build_repair_prompt(sentence: str) -> str:
    return (
        "The following sentence from a financial article has a grammar defect: a "
        "specific number, percentage, or dollar amount was removed (because it lacked "
        "a citation) but the surrounding words were not adjusted, leaving two "
        "prepositions/connector words stuck together (e.g. 'at of', 'within of', "
        "'of in').\n\n"
        f"Broken sentence: {sentence!r}\n\n"
        "Rewrite ONLY this sentence so it reads naturally and grammatically, WITHOUT "
        "reintroducing any specific number, percentage, or dollar figure -- stay exactly "
        "as qualitative as the broken version already is (e.g. 'a portion of', 'shortly "
        "after', 'once', 'contribution room' -- whatever fits, but never a fabricated "
        "figure). Preserve the sentence's original meaning and every other detail. "
        "Return ONLY the corrected sentence, nothing else -- no quotes, no explanation."
    )


def _is_clean_repair(original: str, repaired: str) -> bool:
    repaired = repaired.strip().strip('"').strip("'")
    if not repaired:
        return False
    if _FABRICATED_NUMBER_RE.search(repaired):
        return False
    if scan_body(repaired):
        return False
    return True


def repair_draft(
    text: str,
    report: dict,
    call_llm: Callable[[str], str],
) -> Tuple[str, bool, list]:
    """Attempt to repair every adjacent_connector_pair finding in `report`
    against `text`. Returns (new_text, True, applied_fixes) only if EVERY
    finding was cleanly repaired; otherwise returns (text, False, []) --
    untouched, fail closed. `applied_fixes` is
    [{"old_sentence": ..., "new_sentence": ...}, ...] in the order repaired
    -- captured HERE, while offsets are still known-good, so callers never
    need to re-derive sentence positions against the final patched text
    (findings are applied highest-position-first so earlier splices don't
    invalidate not-yet-processed lower positions, but the REVERSE is not
    true -- a lower-position splice shifts every position after it, which
    is exactly why this is captured during the loop, not reconstructed
    afterward). `call_llm` is injected (prompt: str) -> str so this stays
    offline-testable; the real CLI entrypoint below wires it to the same
    Claude API call agent_04 itself uses."""
    if not is_repairable(report):
        return text, False, []

    findings = sorted(report["body_findings"], key=lambda f: f["position"], reverse=True)
    patched = text
    applied_fixes = []
    for finding in findings:
        sentence, start, end = extract_sentence(patched, finding["position"])
        if not sentence.strip():
            return text, False, []
        repaired = call_llm(build_repair_prompt(sentence))
        repaired = repaired.strip().strip('"').strip("'")
        if not _is_clean_repair(sentence, repaired):
            return text, False, []
        patched = patched[:start] + repaired + patched[end:]
        applied_fixes.append({"old_sentence": sentence.strip(), "new_sentence": repaired})

    applied_fixes.reverse()  # report in document order, not repair order
    return patched, True, applied_fixes


# ---------------------------------------------------------------------------
# Real CLI entrypoint -- network calls live here only, everything above is
# pure and unit-tested without a key.
# ---------------------------------------------------------------------------

def _real_call_llm(prompt: str, api_key: str) -> str:
    import urllib.error
    import urllib.request

    model = os.getenv("ARTICLE_WRITER_MODEL", "claude-sonnet-4-6")
    payload = json.dumps({
        "model": model, "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["content"][0]["text"]


def _sync_wordpress_content(old_sentence: str, new_sentence: str, wp_report_path: str) -> None:
    """Best-effort: push the same sentence-level fix into the live WordPress
    draft's content, so a human reviewing the draft in wp-admin sees the
    repaired text too, not just the local $DRAFT used for scoring. NEVER
    raises -- a WP API hiccup here must not fail the batch loop (same
    philosophy as scripts/mark_qa_failed.py's own `|| true` callers), and a
    post that is not currently draft/pending/private is skipped outright
    (same safety check as scripts/update_wp_post_content.py)."""
    try:
        wp_report = json.loads(Path(wp_report_path).read_text(encoding="utf-8"))
        post_id = wp_report.get("post_id")
        wp_url = os.environ.get("WORDPRESS_URL")
        user = os.environ.get("WORDPRESS_USERNAME")
        app_pw = os.environ.get("WORDPRESS_APP_PASSWORD")
        if not (post_id and wp_url and user and app_pw):
            print(f"[repair-connector-scars] WP sync skipped: missing post_id/credentials")
            return
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from update_wp_post_content import get_post, update_post_content  # noqa

        before = get_post(wp_url, user, app_pw, post_id)
        status = before.get("status")
        if status not in ("draft", "pending", "private"):
            print(f"[repair-connector-scars] WP sync skipped: post {post_id} status={status!r}, not draft-like")
            return
        content = before.get("content", {}).get("raw", "")
        if old_sentence not in content:
            print(f"[repair-connector-scars] WP sync skipped: post {post_id} content does not contain the "
                  f"exact flagged sentence verbatim (likely HTML-formatting drift from the markdown draft) -- "
                  f"local $DRAFT is repaired, but the live WordPress draft still needs a manual "
                  f"apply_single_post_fix.py-style follow-up before publish.")
            return
        new_content = content.replace(old_sentence, new_sentence)
        code, result = update_post_content(wp_url, user, app_pw, post_id, new_content, status)
        if code in (200, 201):
            print(f"[repair-connector-scars] WP sync OK: post {post_id} content updated")
        else:
            print(f"[repair-connector-scars] WP sync FAILED (non-fatal): HTTP {code}: {result}")
    except Exception as e:  # noqa: BLE001 -- best-effort, must never raise
        print(f"[repair-connector-scars] WP sync FAILED (non-fatal): {e}")


def main():
    ap = argparse.ArgumentParser(description="GATE D connector-scar repair (Phase 11.5 fallback)")
    ap.add_argument("--article", required=True, help="agent_04 article draft (markdown), rewritten in place on success")
    ap.add_argument("--gate-report", required=True, help="placeholder_gate.py's JSON report (the FAILED run)")
    ap.add_argument("--wordpress-report", required=False, default="",
                     help="agent_11 wordpress_report.json -- if given, best-effort sync the same fix to the live WP draft")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[repair-connector-scars] No ANTHROPIC_API_KEY -- cannot attempt repair")
        sys.exit(1)

    text = Path(args.article).read_text(encoding="utf-8")
    report = json.loads(Path(args.gate_report).read_text(encoding="utf-8"))

    if not is_repairable(report):
        print("[repair-connector-scars] Not repairable: finding mix includes something other than "
              "adjacent_connector_pair -- leaving GATE D failure as-is")
        sys.exit(1)

    def call_llm(prompt):
        return _real_call_llm(prompt, api_key)

    patched, ok, applied_fixes = repair_draft(text, report, call_llm)
    if not ok:
        print("[repair-connector-scars] Repair attempt failed its own post-check -- leaving GATE D failure as-is")
        sys.exit(1)

    Path(args.article).write_text(patched, encoding="utf-8")
    print(f"[repair-connector-scars] Repaired {len(applied_fixes)} finding(s) in {args.article}")

    if args.wordpress_report and Path(args.wordpress_report).exists():
        for fix in applied_fixes:
            _sync_wordpress_content(fix["old_sentence"], fix["new_sentence"], args.wordpress_report)

    sys.exit(0)


if __name__ == "__main__":
    main()
