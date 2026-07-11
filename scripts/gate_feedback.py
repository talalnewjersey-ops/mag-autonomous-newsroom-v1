"""RETRY MECHANISM (2026-07-06): builds a short, gate-specific feedback string
for the writer's retry prompt, from that gate's own JSON report -- called from
production_v2.yml's retry loop instead of inlining Python in the YAML (a
multi-line python -c string inside a YAML block scalar is fragile: every
embedded line must independently satisfy YAML's block-indentation rule AND
Python's own column-0 module-level rule, which conflict).

Never raises -- a missing/malformed report still yields a usable, generic
fallback string, since this runs inside the workflow's retry loop and must
never break it.
"""
import argparse
import json


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def g_substance(report_path):
    d = _load(report_path)
    reasons = "; ".join(d.get("reasons", [])) or "hollow article"
    return (f"GATE G-SUBSTANCE (Couche 3, veracity): {reasons}. Every hard number must be "
            "either backed by one of the official links ON THE SAME SENTENCE with a MATCHING "
            "value, or stated qualitatively.")


def g3(report_path):
    d = _load(report_path)
    phrases = [p.get("phrase", "") for p in d.get("duplicate_phrases", []) if p.get("blocking")][:3]
    detail = "; ".join(phrases) if phrases else "repetition detected across body sections"
    # 2026-07-11 RECALIBRATED (AUDIT-LOG.md real-run finding): the old wording
    # only offered "reword it differently", which combined with agent_04's
    # retry prompt (previously forbidding any shortening) reliably grew the
    # article instead of fixing the duplicate. Removing/merging a duplicate is
    # the more natural fix for THIS gate and is now offered as an equally
    # valid option.
    return (f"GATE G3 (anti-repetition): near-verbatim phrase(s) repeated across different body "
            f"sections: {detail}. Fix by EITHER rewording one occurrence in genuinely DIFFERENT "
            "wording, OR removing/merging the duplicate entirely if it adds no new information -- "
            "a shorter section that no longer repeats itself is a valid, preferred fix, not a "
            "regression.")


def gate_a(report_path):
    d = _load(report_path)
    s = d.get("summary", d)
    return (f"GATE A (fact-check): broken_official_hard={s.get('broken_official_hard', 0)} "
            f"unsourced_stat_count={s.get('unsourced_stat_count', 0)} "
            f"unbacked_attribution_count={s.get('unbacked_attribution_count', 0)}. Every hard "
            "statistic must be backed by one of the official links ON THE SAME SENTENCE, and "
            "every official link cited must be a real, live URL.")


def gate_b(report_path):
    d = _load(report_path)
    dims = d.get("dimension_scores", {})
    return (f"GATE B (EEAT): score={d.get('total_eeat_score', '?')} below required "
            f"minimum={d.get('minimum_required', '?')}. Dimension scores: "
            f"experience={dims.get('experience', '?')} expertise={dims.get('expertise', '?')} "
            f"authority={dims.get('authority', '?')} trust={dims.get('trust', '?')}. Strengthen "
            "the weakest dimension(s) with concrete first-person examples, regulatory "
            "terminology, and official citations.")


AGENT_04_OWN_VALIDATION_FALLBACK = (
    "Agent 04's own writing/validation failed on the previous attempt -- ensure the article "
    "meets minimum words/FAQs/distinct official sources/case studies/comparison table/expert "
    "recommendation/disclaimer/author bio requirements."
)

_BUILDERS = {"g_substance": g_substance, "g3": g3, "gate_a": gate_a, "gate_b": gate_b}


def build_feedback(gate, report_path):
    return _BUILDERS[gate](report_path)


def main():
    ap = argparse.ArgumentParser(description="Build gate-specific retry feedback for agent_04")
    ap.add_argument("--gate", required=True, choices=sorted(_BUILDERS))
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    print(build_feedback(args.gate, args.report))


if __name__ == "__main__":
    main()
