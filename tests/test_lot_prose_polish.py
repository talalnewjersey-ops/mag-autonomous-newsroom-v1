"""Prose-polish pass -- DELETION-ONLY. Offline: no network, no API key.

Proves the four scar classes are handled (clean a fragment, or drop the whole
sentence when it is broken beyond repair), the HARD invariant (no digit absent
from the input can appear in the output -> repair never reinvents), that legit
short sentences and structure (headings/tables) are preserved, and that a broken
sentence is DELETED whole, not left as a stump.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.polish_prose import polish


# ---------- the four scar classes (before/after) ----------

def test_paren_scar_is_cleaned():
    out, _ = polish("payments build payment history (of your FICO score) while funding a certificate.")
    assert "(of your FICO score)" not in out
    assert "payment history while funding a certificate" in out


def test_emdash_appositive_scar_is_cleaned_with_a_space():
    out, _ = polish("This diversifies your **credit mix** —the factor accounting for of your FICO calculation —without requiring a score.")
    assert "for of" not in out and "**credit mix** without requiring a score" in out


def test_broken_clause_deletes_whole_sentence():
    out, rep = polish("Every ITIN-linked account that), length of credit history, credit mix, and new inquiries.")
    assert out.strip() == "" and rep["sentences_deleted"] == 1   # no stump left


def test_orphaned_unit_deletes_its_sentence_not_a_stump():
    out, _ = polish("**Monthly cost:** Self plans start at /month. Frame this as infrastructure, not an expense.")
    assert "Self plans start" not in out                          # stump not kept
    assert "Frame this as infrastructure, not an expense." in out # the good sentence survives


# ---------- HARD invariant: no reinvention ----------

def test_no_digit_absent_from_input_appears_in_output():
    scarred = ("account age contributes of your FICO score. Rates rose by. "
               "The largest factor at ** of your score**. Deposits of range.")
    out, _ = polish(scarred)
    assert set(re.findall(r"\d", out)) <= set(re.findall(r"\d", scarred))


def test_deletion_only_every_output_word_came_from_input():
    text = "This diversifies your **credit mix** —the factor accounting for of your FICO calculation —without a score."
    out, _ = polish(text)
    in_words = set(re.findall(r"[A-Za-z']+", text.lower()))
    assert set(re.findall(r"[A-Za-z']+", out.lower())) <= in_words   # only deletions


# ---------- preservation ----------

def test_legit_short_sentences_are_preserved():
    text = "It isn't. Start today. Let's begin the process now."
    out, _ = polish(text)
    assert "It isn't." in out and "Start today." in out


def test_headings_and_tables_pass_through():
    text = "## 1. Overview\n| Product | Cost |\n|---|---|\n> A quote line."
    out, _ = polish(text)
    assert out == text


def test_clean_prose_is_untouched():
    text = "You are entitled to one free credit report from each bureau every week."
    assert polish(text)[0] == text
