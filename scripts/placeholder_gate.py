"""Standalone anti-placeholder pipeline gate (2026-07-18, AUDIT-LOG.md).

Runs the same agents/_placeholder_scan.py detectors agent_12_quality_
assurance.py uses to hard-cap its score, but as an independent BLOCKING
gate positioned AFTER agent_11 (WordPress draft creation) and BEFORE
agent_12 (QA scoring) -- "Phase 11.5" in scripts/production_batch_loop.sh.

Two reasons this exists as a SEPARATE gate instead of relying on agent_12's
hard cap alone:

  1. Defense in depth. agent_12's cap only runs inside agent_12 itself --
     anything that calls agent_12 a different way (e.g. rescore_article.yml,
     a future ad-hoc script) still benefits from the cap, but a dedicated
     gate in the main production loop fails loudly and early, before any
     more pipeline work (QA, editor, production_gate.py) is wasted on an
     article that's going to be rejected anyway.

  2. Title coverage agent_12 CANNOT provide. agent_12's title comes from
     the agent_04 markdown draft / agent_03 outline / article_metadata.json
     -- NOT from agent_11's wordpress_report.json. Confirmed on 48854: the
     markdown title was already correct ("...Checklist USA...") and the
     "Checklist Usa" corruption happened downstream, at or after agent_11.
     agent_12 never sees the broken title and can't catch it. This gate
     runs after agent_11 and reads --wordpress-report for the REAL,
     WordPress-bound title, so it's the only place in the pipeline that can
     catch this specific bug class.

Exit 0 (pass, no findings) / exit 1 (fail, findings present) -- same
convention as every other gate in production_batch_loop.sh (structure_
completeness_gate.py, production_gate.py, etc). Writes a JSON report either
way for the retry-feedback machinery (scripts/gate_feedback.py) to consume,
mirroring GATE A/B/LENGTH/G3's existing --gate flag ("placeholder" is not
yet wired into gate_feedback.py's choices -- deliberately not done here,
since this gate runs AFTER the retry-eligible section of the pipeline; a
placeholder-gate failure goes straight to mark_qa_failed.py like GATE QA/
EDITOR failures do, not back through agent_04 regeneration).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents._placeholder_scan import scan_body, scan_title, scan_alt_texts


def main():
    ap = argparse.ArgumentParser(description="Anti-placeholder pipeline gate (Phase 11.5)")
    ap.add_argument("--article", required=True, help="agent_04 article draft (markdown)")
    ap.add_argument("--wordpress-report", required=True,
                     help="agent_11 wordpress_report.json (source of the REAL published title)")
    ap.add_argument("--image-prompts", required=False, default="",
                     help="agent_09 image_prompts.json -- optional; checks alt_text values for "
                          "leaked internal labels (e.g. 'Comparison guide: ...'). $DRAFT never "
                          "contains these strings (agent_11 writes them straight into WordPress "
                          "media alt=\"\", bypassing the draft entirely), so this is the only place "
                          "in the pipeline that can catch that specific bug (added 2026-07-23).")
    ap.add_argument("--output", required=True, help="Path to write the gate's JSON report")
    args = ap.parse_args()

    body_text = Path(args.article).read_text(encoding="utf-8")

    wp_report = {}
    wp_path = Path(args.wordpress_report)
    if wp_path.exists():
        try:
            wp_report = json.loads(wp_path.read_text(encoding="utf-8"))
        except Exception:
            wp_report = {}
    title = wp_report.get("title", "")

    alt_findings = []
    if args.image_prompts:
        img_path = Path(args.image_prompts)
        if img_path.exists():
            try:
                img_data = json.loads(img_path.read_text(encoding="utf-8"))
                alt_texts = [p.get("alt_text", "") for p in img_data.get("prompts", [])]
                alt_findings = scan_alt_texts(alt_texts)
            except Exception:
                alt_findings = []

    body_findings = scan_body(body_text)
    title_findings = scan_title(title) if title else []
    all_findings = body_findings + title_findings + alt_findings

    report = {
        "gate": "placeholder_gate",
        "article": args.article,
        "title_checked": title,
        "body_findings": body_findings,
        "title_findings": title_findings,
        "alt_text_findings": alt_findings,
        "finding_count": len(all_findings),
        "status": "PASS" if not all_findings else "FAIL",
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if all_findings:
        print(f"GATE PLACEHOLDER FAIL: {len(all_findings)} finding(s)")
        for f in all_findings:
            print(f"  [{f['type']}] {f['match']!r} -- {f['context']!r}")
    else:
        print("GATE PLACEHOLDER PASS: no placeholder artifacts detected")

    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
