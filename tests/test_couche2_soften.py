"""Couche 2 -- deterministic soften pass. Offline: no network, no API key.

Proves the soften rules (prose strip keeps the clause; sourced numbers and Couche 1
facts untouched; attribution cue+number removed; table cell -> 'varies'; residue
< K -> sentence deleted, with K configurable), plus idempotence, no-op on clean
text, correct report, and that the pass is NON-BLOCKING (CLI exits 0).
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.soften_claims import soften

GOV = "https://www.insurance.ca.gov/01-consumers/105-type/95-guides/01-auto/"


# ---------------- prose ----------------

def test_prose_strip_keeps_directional_clause():
    out, rep = soften("Foreign drivers pay by 20-40% above the national average today.")
    assert "20" not in out and "40%" not in out
    assert "above the national average" in out
    assert rep["stripped"] == 1 and rep["unsourced_found"] == 1


def test_sourced_number_is_left_untouched():
    text = f"Premiums run about $1,800 per year for new drivers, per {GOV} today."
    out, rep = soften(text)
    assert "$1,800" in out and rep["unsourced_found"] == 0 and rep["stripped"] == 0


def test_couche1_style_inline_citation_is_untouched():
    text = (f"Texas requires $30,000 of bodily-injury coverage per person "
            f"({GOV}) for every driver.")
    out, rep = soften(text)
    assert "$30,000" in out and rep["stripped"] == 0


def test_attribution_cue_and_number_removed_clause_kept():
    out, _ = soften("According to J.D. Power, 40% of drivers never compare quotes before renewing.")
    assert "40%" not in out and "According to" not in out
    assert "never compare quotes before renewing" in out


# ---------------- residue deletion (K configurable) ----------------

def test_short_residue_sentence_is_deleted_at_default_k():
    out, rep = soften("Drivers overpay. They pay 25%. Shop around first.")
    assert "25%" not in out
    assert "They pay" not in out                 # 2-word residue < 4 -> deleted
    assert "Shop around first." in out
    assert rep["sentences_deleted"] == 1


def test_k_is_configurable_same_input_different_outcome():
    text = "They pay 25%."                        # residue "They pay" = 2 words
    deleted_out, deleted_rep = soften(text, min_residue_words=4)
    kept_out, kept_rep = soften(text, min_residue_words=2)
    assert deleted_rep["sentences_deleted"] == 1 and "They pay" not in deleted_out
    assert kept_rep["sentences_deleted"] == 0 and "They pay" in kept_out


# ---------------- tables ----------------

def test_table_cell_with_unsourced_number_becomes_varies():
    row = "| **State Farm** | Yes | up to 25% | $180-$260 |"
    out, rep = soften(row)
    assert "25%" not in out and "$180" not in out
    assert out.count("varies") >= 2               # both numeric cells softened
    assert out.startswith("| **State Farm** |")    # structure preserved
    assert rep["table_cells_softened"] >= 2


# ---------------- safety / idempotence / no-op ----------------

def test_noop_on_clean_all_sourced_text():
    text = f"Coverage varies by state. See {GOV} for the current minimums."
    out, rep = soften(text)
    assert out == text and rep["unsourced_found"] == 0


def test_idempotent():
    text = "Rates rose by 15% last year and premiums climbed 30% for newcomers."
    once, _ = soften(text)
    twice, rep2 = soften(once)
    assert once == twice and rep2["stripped"] == 0


def test_report_counts_total_and_unsourced():
    # The two invented figures are pushed well past the +-100 char proximity window
    # so the sourced sentence's URL cannot shelter them (same window as detection).
    filler = "This filler sentence exists only to push the invented figures far beyond " \
             "the hundred character proximity window that the shared detector applies. "
    text = f"Texas requires $30,000 of coverage ({GOV}). {filler}Newcomers overpay 25% and deposits reach $500 with no citation."
    _, rep = soften(text)
    assert rep["numeric_claims_total"] == 3 and rep["unsourced_found"] == 2


# ---------------- prose repair (Piece 1) + extended detection (Piece 2) ----------------

def test_range_strip_does_not_eat_adjacent_letters():
    out, _ = soften("Providers require deposits of $200-$500 from applicants with no history.")
    assert "deposits from applicants" in out     # clean: no eaten 'f' (was "of rom"), no dangling "$"
    assert "$" not in out and "200" not in out


def test_stripped_bold_percent_leaves_no_empty_bold():
    out, _ = soften("Utilization accounts for **30%** of your score and should stay below **10%**.")
    assert "****" not in out and "30%" not in out and "10%" not in out


def test_bare_million_is_detected_and_stripped():
    out, rep = soften("The CFPB says approximately 45 million Americans are credit invisible.")
    assert rep["unsourced_found"] == 1 and "45 million" not in out


def test_score_threshold_is_detected_and_stripped():
    out, rep = soften("A 650+ score is achievable within a year for most newcomers.")
    assert rep["unsourced_found"] == 1 and "650+" not in out


# ---------------- link safety (Piece 3): a .gov source is NEVER touched ----------------

GOVURL = "https://www.consumerfinance.gov/consumer-tools/credit-reports-and-scores/"


def test_link_at_end_of_sentence_is_intact():
    out, _ = soften(f"Premiums are higher for newcomers, see [CFPB]({GOVURL}).")
    assert GOVURL in out


def test_link_glued_to_a_number_keeps_the_link():
    # non-.gov link glued to an unsourced number: number softened, link byte-intact.
    out, _ = soften("Rates rose [source](https://example.com/x)25% last year for thin files.")
    assert "https://example.com/x" in out and "25%" not in out


def test_multiple_links_same_paragraph_all_intact():
    urls = (GOVURL, "https://www.irs.gov/individuals", "https://consumer.ftc.gov/articles/free-credit-reports")
    out, _ = soften(f"See [A]({urls[0]}) and [B]({urls[1]}) and [C]({urls[2]}) for details.")
    assert all(u in out for u in urls)


def test_number_immediately_before_a_url_never_corrupts_it():
    # figure just BEFORE a URL whose path even contains a cue word ("report") -> the
    # figure is softened and the URL stays byte-identical.
    out, _ = soften("Rates jumped 30% [ref](https://example.com/report-and-scores/) overall.")
    assert "https://example.com/report-and-scores/" in out and "30%" not in out


def test_url_never_corrupted_even_when_a_distant_number_is_stripped():
    # The real L39 bug: an attribution cue ("reports") sat INSIDE the URL path and the
    # strip ate the URL tail. With masking the URL is atomic and can never be touched.
    long = ("and payment history matters a great deal for thin files over many months of "
            "steady activity, so drivers overpay by 30% typically without a domestic record.")
    out, _ = soften(f"Diverse accounts matter because [CFPB report]({GOVURL}) {long}")
    assert GOVURL in out          # byte-identical
    assert "30%" not in out       # the distant unsourced figure was still softened


# ---------------- extended detection (Piece 2): "N points" no longer survives ----------------

def test_points_is_detected_and_stripped():
    out, rep = soften("Adding a loan can accelerate growth by 20-40 points faster than one card.")
    assert rep["unsourced_found"] >= 1 and "20-40 points" not in out


def test_percentage_points_is_detected_and_stripped():
    out, rep = soften("This increased the likelihood by 24 percentage points overall for thin files.")
    assert rep["unsourced_found"] >= 1 and "24 percentage points" not in out


# ---------------- non-blocking CLI ----------------

def test_cli_is_non_blocking_and_rewrites(tmp_path):
    draft = tmp_path / "article_draft.md"
    draft.write_text("Drivers pay by 20-40% more than locals in most cities.", encoding="utf-8")
    report = tmp_path / "soften_report.json"
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "soften_claims.py"),
         "--input", str(draft), "--report", str(report)],
        capture_output=True, text=True)
    assert r.returncode == 0                        # NON-BLOCKING: always succeeds
    assert "20-40%" not in draft.read_text(encoding="utf-8")
    assert json.loads(report.read_text())["stripped"] == 1
