#!/usr/bin/env python3
"""Post-batch priority report -- one markdown file summarizing every article
in a completed production run, for human triage before publishing any of
them (2026-07-25, user decision after CASE 5 validation: auto-publish is
off, every article lands as a WordPress draft, and this report is what
tells the human which draft to review and publish first).

Reads a LOCAL directory holding the already-downloaded/extracted GitHub
Actions artifact for a run (the `article_N/agent_XX/*.json` layout
`gh run download` produces) -- this script does not call the GitHub API
itself, it only reads files already on disk.

HONESTY CONTRACT (the whole reason this script exists as written): every
column is labeled either a REAL pipeline measurement or an ESTIMATION, and
the two are never allowed to look alike in the output. Concretely:
  - No search-volume, keyword-difficulty, or AdSense-revenue number is ever
    printed. agents/agent_01_seo_research.py's search_volume/keyword_
    difficulty fields are HARDCODED PLACEHOLDERS (1000/35) for every
    registry-selected AND --topic-override topic, regardless of anything
    about the real topic -- confirmed by reading _normalize_topic and the
    SERPAPI parsing path, 2026-07-25. Printing them, even labeled, invites
    exactly the mistake this script exists to prevent. If Ahrefs/Similarweb
    are ever wired in (tracked as a separate, later piece of work), this is
    the one place that would need a real column added.
  - Monetization potential and "pillar" potential are self-contained
    heuristics with NO claim to predictive accuracy -- documented inline at
    the functions that compute them, and every report this script writes
    repeats that disclaimer next to the columns themselves, not just in a
    footnote a reader can miss.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def _load(path):
    """None if the file doesn't exist or can't be parsed -- both are
    ordinary "this article never reached that stage" outcomes here, not
    errors to raise on."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _gate_chain(a04, g3, wp, gate_d, qa):
    """(publishable: bool, reason: str) -- walks the REAL blocking-gate
    order observed in scripts/production_batch_loop.sh's own log output
    (length -> G-Substance -> G3 -> WordPress draft [Gate C] -> placeholder
    [Gate D] -> agent_12 QA), returning the FIRST stage that actually
    blocked the article, not a later one it never reached. Every branch
    reflects a real field this session verified against downloaded
    artifacts (agent_04/g_substance_report.json, agent_04/g3_report.json,
    agent_11/wordpress_report.json, agent_11/placeholder_gate_report.json,
    agent_12/qa_report.json) -- not guessed field names."""
    length = a04.get("_length")
    if length and length.get("over_ceiling"):
        return False, (f"GATE LENGTH FAIL: {length.get('word_count')} mots "
                        f"> plafond {length.get('ceiling_words')}")
    g_sub = a04.get("_g_substance")
    if g_sub is None:
        return False, "jamais atteint G-Substance (échec en amont : recherche/planification)"
    if g_sub.get("verdict") != "PASS":
        return False, f"G-SUBSTANCE FAIL: {'; '.join(g_sub.get('reasons', [])) or 'raison non précisée'}"
    if g3 is not None and not (g3.get("passed") or g3.get("decision") == "PASS"):
        dup = g3.get("blocking_dup_count", "?")
        return False, f"G3 FAIL: répétition détectée ({dup} paire(s) bloquante(s))"
    if wp is None:
        return False, ("brouillon WordPress jamais créé -- bloqué avant agent_11 (G-Substance/G3 "
                        "OK d'après les rapports disponibles). La raison exacte -- ex. GATE C, ou "
                        "RETRY-COMPLETENESS, qui n'écrit pas de rapport JSON -- n'est pas "
                        "reconstructible depuis ces fichiers seuls : voir le log du run.")
    if gate_d is None:
        return False, "GATE D: rapport manquant (incohérent, brouillon WP existe -- à vérifier manuellement)"
    if gate_d.get("status") != "PASS":
        findings = (gate_d.get("body_findings", []) + gate_d.get("title_findings", [])
                    + gate_d.get("alt_text_findings", []))
        first = findings[0]["type"] if findings else "?"
        return False, f"GATE D FAIL: {len(findings)} trouvaille(s) -- {first}"
    if qa is None:
        return False, "jamais noté par agent_12 (QA) -- incohérent, GATE D a pourtant réussi, à vérifier"
    if qa.get("status") != "PASS":
        return False, f"QA {qa.get('status')} (score {qa.get('overall_score')})"
    return True, f"tous les gates OK -- score QA {qa.get('overall_score')}"


_SIMILARITY_BUCKET = {
    "CREATE_NEW_ARTICLE": "neuf",
    "UPDATE_EXISTING_ARTICLE": "proche d'un existant",
    "MERGE_WITH_EXISTING": "proche d'un existant",
    "REJECT_DUPLICATE": "doublon",
}


def _similarity(canib):
    if canib is None:
        return "n/d", None
    decision = canib.get("decision", "")
    score = canib.get("observation", {}).get("max_combined_score")
    return _SIMILARITY_BUCKET.get(decision, decision or "n/d"), score


_MONETIZATION_DISCLAIMER = (
    "ESTIMATION -- score 0-100 d'agent_18 (correspondance de mots-clés sur "
    "des tables statiques + un ajustement IA non fondé sur des données "
    "réelles), rescalé sur 1-5. Aucun appel AdSense/affiliation réel.")


def _monetization_1_5(revenue):
    """1-5 rescale of agent_18's 0-100 revenue_score. See
    _MONETIZATION_DISCLAIMER -- this is agent_18's own heuristic, not a new
    one, just rescaled for a compact table column."""
    if revenue is None:
        return None
    score = revenue.get("revenue_score")
    if not isinstance(score, (int, float)):
        return None
    return max(1, min(5, round(score / 20)))


_PILLAR_DISCLAIMER = (
    "ESTIMATION -- heuristique maison (aucun signal pipeline n'existe pour "
    "ceci) : mots-clés courts et génériques notés plus \"pilier\" que des "
    "mots-clés longs avec un qualificatif précis (visa, montant, "
    "institution nommée). Subjectif, à valider par un humain, pas un calcul "
    "de trafic ou de maillage réel.")

_SPECIFIC_QUALIFIER_RE = re.compile(
    r"\d|\bssn\b|\bitin\b|\bf-?1\b|\bh-?1b\b|\bj-?1\b|\bl-?1\b|\bo-?1\b|"
    r"\bdaca\b|\bein\b|\bein\b|matricula|\bfico\b|\bfdic\b|\bncua\b",
    re.IGNORECASE,
)


def _pillar_1_5(keyword):
    if not keyword:
        return None
    words = keyword.split()
    specific = bool(_SPECIFIC_QUALIFIER_RE.search(keyword))
    if specific:
        return 2 if len(words) <= 8 else 1
    if len(words) <= 5:
        return 5
    if len(words) <= 7:
        return 4
    return 3


def analyze_article(article_dir):
    a01 = _load(article_dir / "agent_01" / "topics.json")
    a04 = {
        "_g_substance": _load(article_dir / "agent_04" / "g_substance_report.json"),
        "_length": _load(article_dir / "agent_04" / "length_report.json"),
    }
    g3 = _load(article_dir / "agent_04" / "g3_report.json")
    wp = _load(article_dir / "agent_11" / "wordpress_report.json")
    gate_d = _load(article_dir / "agent_11" / "placeholder_gate_report.json")
    qa = _load(article_dir / "agent_12" / "qa_report.json")
    canib = _load(article_dir / "agent_17" / "cannibalization_report.json")
    revenue = _load(article_dir / "agent_18" / "revenue_score.json")

    g_sub = a04["_g_substance"] or {}
    topic = (a01 or {}).get("topics", [{}])
    topic = topic[0] if topic else {}
    keyword = (wp or {}).get("keyword") or topic.get("keyword", "")
    title = (wp or {}).get("title") or topic.get("title", "") or keyword or "(titre inconnu)"

    publishable, reason = _gate_chain(a04, g3, wp, gate_d, qa)
    similarity_bucket, similarity_score = _similarity(canib)

    return {
        "dir": article_dir.name,
        "title": title,
        "keyword": keyword,
        "post_id": (wp or {}).get("post_id"),
        "score": (qa or {}).get("overall_score"),
        "publishable": publishable,
        "reason": reason,
        "vertical": g_sub.get("vertical", "n/d"),
        "similarity_bucket": similarity_bucket,
        "similarity_score": similarity_score,
        "cited_stable_facts": g_sub.get("cited_stable_facts"),
        "monetization_1_5": _monetization_1_5(revenue),
        "pillar_1_5": _pillar_1_5(keyword),
    }


def _fmt(v, suffix=""):
    return "n/d" if v is None else f"{v}{suffix}"


def _priority_key(row):
    # publishable articles first; within each bucket, higher QA score, then
    # higher monetization estimate, then higher pillar estimate -- ties
    # broken by title for determinism. NOT a claim of true business value:
    # this is a display ordering only, built from what's in the row.
    return (
        0 if row["publishable"] else 1,
        -(row["score"] or 0),
        -(row["monetization_1_5"] or 0),
        -(row["pillar_1_5"] or 0),
        row["title"],
    )


def build_report(rows, run_label):
    rows = sorted(rows, key=_priority_key)
    lines = []
    lines.append(f"# Rapport de priorisation -- run {run_label}")
    lines.append("")
    lines.append(
        "Colonnes MESURÉES (calculées directement par le pipeline, "
        "déterministes) : Score, Publiable, Vertical, Similarité, Faits gravés."
    )
    lines.append(
        "Colonnes ESTIMATION (heuristiques, jamais une donnée de marché "
        "réelle) : Monétisation, Pilier -- voir le détail de chaque "
        "heuristique en bas de fichier."
    )
    lines.append(
        "Aucune colonne volume de recherche / difficulté SEO / revenu "
        "AdSense n'est incluse : la pipeline n'a accès à aucune donnée "
        "réelle pour ces mesures tant qu'Ahrefs/Similarweb ne sont pas "
        "branchés (chantier séparé, non fait)."
    )
    lines.append("")

    if rows:
        top = rows[0]
        if top["publishable"]:
            justification = (
                f"**#1 : {top['title']}** -- seul/meilleur candidat publiable "
                f"(score QA {_fmt(top['score'])}), vertical {top['vertical']}, "
                f"sujet {top['similarity_bucket']}, "
                f"{_fmt(top['cited_stable_facts'])} fait(s) gravé(s) cité(s)."
            )
        else:
            justification = (
                f"**Aucun article publiable dans ce batch.** Le mieux classé, "
                f"« {top['title']} », est bloqué : {top['reason']}."
            )
        lines.append(justification)
        lines.append("")

    lines.append(
        "| # | Titre | Publiable | Raison si non | Score | Vertical | "
        "Similarité | Faits gravés | Monétisation (EST.) | Pilier (EST.) | Post ID |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        pub = "OUI" if r["publishable"] else "NON"
        sim = r["similarity_bucket"]
        if r["similarity_score"] is not None:
            sim += f" ({r['similarity_score']:.2f})"
        lines.append(
            f"| {i} | {r['title']} | {pub} | {r['reason'] if not r['publishable'] else '--'} "
            f"| {_fmt(r['score'])} | {r['vertical']} | {sim} "
            f"| {_fmt(r['cited_stable_facts'])} | {_fmt(r['monetization_1_5'])}/5 "
            f"| {_fmt(r['pillar_1_5'])}/5 | {_fmt(r['post_id'])} |"
        )

    lines.append("")
    lines.append("## Détail des heuristiques (ESTIMATION, pas une mesure)")
    lines.append("")
    lines.append(f"**Monétisation (1-5)** -- {_MONETIZATION_DISCLAIMER}")
    lines.append("")
    lines.append(f"**Pilier (1-5)** -- {_PILLAR_DISCLAIMER}")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Generate a human-review priority report for a batch of articles")
    ap.add_argument("--batch-dir", required=True,
                     help="Directory containing article_N/agent_XX/*.json (extracted artifact)")
    ap.add_argument("--run-id", required=True, help="Run label for the report header/filename")
    ap.add_argument("--output", required=True, help="Output markdown path")
    args = ap.parse_args()

    batch_dir = Path(args.batch_dir)
    article_dirs = sorted(
        p for p in batch_dir.glob("article_*") if p.is_dir()
    )
    if not article_dirs:
        print(f"generate_priority_report: no article_* directories found under {batch_dir}", file=sys.stderr)
        sys.exit(1)

    rows = [analyze_article(d) for d in article_dirs]
    report = build_report(rows, args.run_id)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"generate_priority_report: wrote {out_path} ({len(rows)} article(s))")


if __name__ == "__main__":
    main()
