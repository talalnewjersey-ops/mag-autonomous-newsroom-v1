"""PriorityScore -- Task 4(a) of the 2026-07-19 editorial-strategy proposal.

Deterministic, logged, auditable ranking model for candidate topics. This is
a MODEL INDEX (0-100), not a measured-truth score -- Revenue and Winnability
in particular depend on search-volume/CPC/difficulty data that is not wired
into this repo (no GSC or keyword-tool integration exists here). Every score
this module produces should be logged with its per-factor breakdown so a
human can see exactly which inputs are estimates and audit the ranking, not
just trust a single opaque number.

Formula (spec, Task 4a):
  PriorityScore = 0.25*Revenue + 0.25*Winnability + 0.15*IntentFit
                + 0.10*AuthorityContribution + 0.15*CannibalizationSafety
                + 0.10*Freshness
  each factor scored 0-5 by the caller, this module applies weights and
  scales to 0-100.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional

WEIGHTS = {
    "revenue": 0.25,
    "winnability": 0.25,
    "intent_fit": 0.15,
    "authority_contribution": 0.10,
    "cannibalization_safety": 0.15,
    "freshness": 0.10,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "PriorityScore weights must sum to 1.0"

FACTOR_MIN, FACTOR_MAX = 0, 5
SCALE = 20  # (0-5 weighted sum) * 20 -> 0-100


@dataclass
class PriorityFactors:
    revenue: float
    winnability: float
    intent_fit: float
    authority_contribution: float
    cannibalization_safety: float
    freshness: float
    # per-factor basis strings for the audit log -- e.g. "monetization_score
    # from topic_registry.json (measured)" vs "[estimation: no keyword-tool
    # feed wired in, defaulted to 3/5 pending GSC integration]"
    basis: Dict[str, str] = field(default_factory=dict)

    def validate(self):
        for name in ("revenue", "winnability", "intent_fit",
                     "authority_contribution", "cannibalization_safety", "freshness"):
            v = getattr(self, name)
            if not (FACTOR_MIN <= v <= FACTOR_MAX):
                raise ValueError(f"{name}={v} out of range [{FACTOR_MIN}, {FACTOR_MAX}]")


def compute_priority_score(factors: PriorityFactors) -> Dict:
    """Returns the score plus a full audit trail -- never just a bare number.
    Callers (e.g. agent_01's selection loop) should log the whole dict, not
    just `score`, so a human reviewing topic_registry.json history can see
    why a topic ranked where it did."""
    factors.validate()
    weighted_sum = sum(getattr(factors, k) * w for k, w in WEIGHTS.items())
    score = round(weighted_sum * SCALE, 1)
    breakdown = {
        k: {
            "value": getattr(factors, k),
            "weight": WEIGHTS[k],
            "contribution": round(getattr(factors, k) * WEIGHTS[k] * SCALE, 2),
            "basis": factors.basis.get(k, "[unspecified -- caller should always supply a basis string]"),
        }
        for k in WEIGHTS
    }
    return {"score": score, "breakdown": breakdown}


def factors_from_registry_entry(entry: Dict, cannibalization_max_similarity: Optional[float] = None) -> PriorityFactors:
    """Best-effort mapping from an existing data/topic_registry.json entry's
    fields to the 6 PriorityFactors. Registry entries only carry
    monetization_score/traffic_score (0-5 already) -- everything else here
    is a documented default pending real data sources, NOT a measured value.
    This function exists to make the dry-run demo runnable against the real
    registry; a production integration should replace the defaulted factors
    with real inputs (GSC for winnability/intent_fit, an internal-links graph
    for authority_contribution, publish-date recency for freshness) rather
    than trusting these defaults long-term."""
    revenue = min(FACTOR_MAX, float(entry.get("monetization_score", 3)))
    winnability = 3.0  # [estimation: no keyword-difficulty source wired in -- neutral default]
    intent_fit = min(FACTOR_MAX, float(entry.get("traffic_score", 3)))  # proxy only, traffic_score != intent match
    authority_contribution = 3.0  # [estimation: no internal-links graph consulted here -- neutral default]
    if cannibalization_max_similarity is None:
        cannibalization_safety = 3.0
        cann_basis = "[estimation: no similarity check run for this factor computation]"
    else:
        # invert similarity into a safety score: high similarity to existing content = low safety
        cannibalization_safety = round(FACTOR_MAX * (1 - min(1.0, cannibalization_max_similarity)), 2)
        cann_basis = f"derived from max cannibalization similarity={cannibalization_max_similarity:.3f} (see agents._embedding_similarity)"
    freshness = 3.0  # [estimation: no content-age/SERP-freshness signal wired in -- neutral default]

    return PriorityFactors(
        revenue=revenue, winnability=winnability, intent_fit=intent_fit,
        authority_contribution=authority_contribution,
        cannibalization_safety=cannibalization_safety, freshness=freshness,
        basis={
            "revenue": f"monetization_score={entry.get('monetization_score')} from topic_registry.json (measured, repo-native)",
            "winnability": "[estimation: no GSC/keyword-tool feed wired in -- neutral default 3/5, TODO fill from GSC]",
            "intent_fit": f"traffic_score={entry.get('traffic_score')} used as a rough proxy (measured field, but traffic_score != intent-match, TODO replace)",
            "authority_contribution": "[estimation: no internal-links graph consulted -- neutral default 3/5]",
            "cannibalization_safety": cann_basis,
            "freshness": "[estimation: no content-age/SERP-freshness signal wired in -- neutral default 3/5]",
        },
    )
