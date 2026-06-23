#!/usr/bin/env python3
"""
NEXUS-14 - Search Intent Heuristic (Etape 1 - Agent 17 Observation Mode)

Pure local heuristic. No external API, no cost, no external dependency.
Source of truth for search-intent and financial-category classification used
by Agent 17 in OBSERVATION mode. The optional LLM analysis in Agent 17 stays
purely informational; THIS module is the source of truth.

Public API:
    classify_intent(title, keywords=None) -> str
        one of: informational | transactional | comparative | navigational
    classify_category(title, keywords=None) -> str
        one of: bank_account | credit_card | taxes | insurance | transfer |
                credit_score | housing | phone_plan | newcomer_banking | other
    detect_country_signals(text) -> dict
        {"usa": bool, "canada": bool, "signals": [...]}
    intent_similarity(a, b) -> float  in [0.0, 1.0]
    analyze(title, keywords=None) -> dict  (convenience aggregate)
"""

import re

INTENTS = ("informational", "transactional", "comparative", "navigational")

CATEGORIES = (
    "bank_account", "credit_card", "taxes", "insurance", "transfer",
    "credit_score", "housing", "phone_plan", "newcomer_banking", "other",
)

# --- Lexical signatures (lowercase tokens / substrings) ---

COMPARATIVE_MARKERS = (
    "vs", "versus", "compare", "comparison", "best", "top", "vs.",
    "alternatives", "alternative", "which", "better", "cheapest",
)

TRANSACTIONAL_MARKERS = (
    "open", "apply", "sign up", "signup", "get", "send", "transfer",
    "buy", "order", "register", "switch", "activate", "download",
    "how to open", "how to apply", "how to send", "how to get",
)

NAVIGATIONAL_BRANDS = (
    "wise", "remitly", "western union", "moneygram", "ofx", "transfergo",
    "worldremit", "xe", "paypal", "revolut", "tangerine", "rbc", "td bank",
    "scotiabank", "bmo", "cibc", "chase", "wells fargo", "bank of america",
    "simplii", "koho", "neo financial", "eq bank",
)

# Category term dictionaries
CATEGORY_TERMS = {
    "credit_card": ("credit card", "creditcard", "cashback", "rewards card", "secured card"),
    "credit_score": ("credit score", "credit history", "credit bureau", "fico", "equifax", "transunion", "build credit"),
    "taxes": ("tax", "taxes", "irs", "cra", "tax return", "tax filing", "income tax", "tax id", "itin", "sin number"),
    "insurance": ("insurance", "insured", "coverage", "policy", "premium", "life insurance", "health insurance", "auto insurance"),
    "transfer": ("send money", "money transfer", "wire transfer", "remittance", "remit", "international transfer", "transfer money"),
    "housing": ("rent", "rental", "mortgage", "apartment", "lease", "housing", "landlord", "tenant", "first home"),
    "phone_plan": ("phone plan", "sim card", "mobile plan", "carrier", "prepaid", "cell phone plan", "wireless plan"),
    "newcomer_banking": ("newcomer", "immigrant", "new to canada", "new to the usa", "new to us", "first bank account", "newcomer banking", "newcomer account"),
    "bank_account": ("bank account", "checking account", "savings account", "chequing", "open an account", "no fee account", "debit"),
}


def _norm(text):
    return re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).strip()


def _haystack(title, keywords=None):
    parts = [title or ""]
    if keywords:
        if isinstance(keywords, (list, tuple, set)):
            parts.extend(str(k) for k in keywords)
        else:
            parts.append(str(keywords))
    return _norm(" ".join(parts))


def _contains_any(hay, terms):
    return [t for t in terms if t in hay]


def classify_intent(title, keywords=None):
    """Return one of INTENTS. Heuristic precedence:
    comparative > transactional > navigational > informational.
    """
    hay = _haystack(title, keywords)
    padded = " " + hay + " "

    if _contains_any(hay, COMPARATIVE_MARKERS) or " vs " in padded:
        return "comparative"

    if _contains_any(hay, TRANSACTIONAL_MARKERS):
        return "transactional"

    # Navigational only when a brand is present AND no info-question marker
    info_markers = ("what", "why", "how", "guide", "explained", "meaning", "understand")
    brands = _contains_any(hay, NAVIGATIONAL_BRANDS)
    if brands and not _contains_any(hay, info_markers):
        return "navigational"

    return "informational"


def classify_category(title, keywords=None):
    """Return one of CATEGORIES. First matching dictionary wins by priority order."""
    hay = _haystack(title, keywords)
    # Priority order: most specific first
    priority = (
        "credit_score", "credit_card", "taxes", "insurance", "transfer",
        "housing", "phone_plan", "newcomer_banking", "bank_account",
    )
    for cat in priority:
        if _contains_any(hay, CATEGORY_TERMS[cat]):
            return cat
    return "other"


USA_SIGNALS = ("irs", "fdic", "ssn", "social security", "itin", "usa", "united states", "u s ", "american")
CANADA_SIGNALS = ("cra", "fintrac", "cdic", "sin number", "canada", "canadian", "newcomer to canada")


def detect_country_signals(text):
    hay = _haystack(text)
    usa_hits = _contains_any(hay, USA_SIGNALS)
    can_hits = _contains_any(hay, CANADA_SIGNALS)
    return {
        "usa": bool(usa_hits),
        "canada": bool(can_hits),
        "signals": {"usa": usa_hits, "canada": can_hits},
    }


def intent_similarity(a, b):
    """Similarity in [0,1] between two topics (each a dict with title/keywords,
    or a plain string). Combines intent equality, category equality and
    lexical token overlap.
    """
    def unpack(x):
        if isinstance(x, dict):
            return x.get("title") or x.get("keyword") or "", x.get("keywords")
        return str(x), None

    ta, ka = unpack(a)
    tb, kb = unpack(b)

    intent_a = classify_intent(ta, ka)
    intent_b = classify_intent(tb, kb)
    cat_a = classify_category(ta, ka)
    cat_b = classify_category(tb, kb)

    intent_eq = 1.0 if intent_a == intent_b else 0.0
    cat_eq = 1.0 if cat_a == cat_b else 0.0

    set_a = set(_haystack(ta, ka).split())
    set_b = set(_haystack(tb, kb).split())
    overlap = (len(set_a & set_b) / len(set_a | set_b)) if (set_a | set_b) else 0.0

    # Weighted blend: intent 0.4, category 0.3, lexical overlap 0.3
    return round(0.4 * intent_eq + 0.3 * cat_eq + 0.3 * overlap, 3)


def analyze(title, keywords=None):
    """Convenience aggregate used by Agent 17 observation block."""
    return {
        "intent": classify_intent(title, keywords),
        "category": classify_category(title, keywords),
        "country_signals": detect_country_signals(
            " ".join([title or ""] + ([str(k) for k in keywords] if isinstance(keywords, (list, tuple, set)) else ([str(keywords)] if keywords else [])))
        ),
    }


if __name__ == "__main__":
    # Lightweight self-check (no external deps)
    samples = [
        ("Best way to send money internationally 2026", ["send money"]),
        ("How to open a bank account as a newcomer to Canada", ["newcomer banking"]),
        ("Wise vs Remitly: which is cheaper", ["wise vs remitly"]),
        ("Wise transfer fees", ["wise"]),
        ("What is a credit score", ["credit score"]),
    ]
    for t, k in samples:
        print(t, "->", classify_intent(t, k), "|", classify_category(t, k))
