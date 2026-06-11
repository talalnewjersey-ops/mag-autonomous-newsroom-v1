"""
NEXUS-14 - Agent 06: EEAT Validator Agent
MoneyAbroadGuide Autonomous Newsroom

Validates Experience, Expertise, Authority, Trust (E-E-A-T)
for SEO 2026 compliance. Target score: >= 95.
Output: eeat_report.json
"""

import json
import re
import logging
from datetime import datetime
from typing import Any
from pathlib import Path

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# E-E-A-T dimension weights (must sum to 100)
EEAT_WEIGHTS = {
    "experience": 25,
    "expertise": 30,
    "authority": 25,
    "trust": 20,
}

# Signals for each dimension
EEAT_SIGNALS = {
    "experience": {
        "first_person_narrative": {
            "weight": 20,
            "patterns": [
                r"(?i)\b(?:I|we|our|my)\s+(?:have|had|used|tried|experienced|found|discovered)",
                r"(?i)\b(?:in my experience|personally|firsthand|I can confirm)",
                r"(?i)\b(?:when I|after I|before I|once I)",
            ],
            "min_count": 3,
        },
        "specific_examples": {
            "weight": 30,
            "patterns": [
                r"(?i)\b(?:for example|for instance|such as|specifically|case study)",
                r"(?i)\b(?:real-world|real world|in practice|in reality|actual)",
            ],
            "min_count": 2,
        },
        "detailed_process": {
            "weight": 25,
            "patterns": [
                r"(?i)\bstep\s+\d+|step-by-step|step by step",
                r"(?i)\b(?:process|procedure|instructions?|how to|tutorial)",
                r"(?i)\b(?:first|second|third|then|next|finally)\s+(?:you|we|the)",
            ],
            "min_count": 3,
        },
        "recent_date": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:2024|2025|2026)\b",
                r"(?i)\b(?:last updated|updated|as of|current|latest|recent)\b",
            ],
            "min_count": 2,
        },
    },
    "expertise": {
        "technical_terminology": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:SWIFT|SEPA|IBAN|BIC|KYC|AML|FINTRAC|CRA|IRS|FATCA)",
                r"(?i)\b(?:remittance|forex|wire transfer|ACH|interbank|correspondent banking)",
                r"(?i)\b(?:TFSA|RRSP|401k|RESP|GIC|T4|W-2|1099)",
                r"(?i)\b(?:exchange rate|spread|mid-market|conversion fee|FX|hedging)",
            ],
            "min_count": 5,
        },
        "regulatory_references": {
            "weight": 30,
            "patterns": [
                r"(?i)\b(?:FINTRAC|OSFI|FCAC|CFPB|FinCEN|FDIC|OCC|NCUA)",
                r"(?i)\b(?:Bank Act|PCMLTFA|Money Services Business|MSB|MTL)",
                r"(?i)\b(?:regulation|regulatory|compliance|licensed|regulated|registered)",
            ],
            "min_count": 3,
        },
        "data_and_statistics": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:according to|research|study|survey|statistics|data|report|analysis)",
                r"(?i)\b(?:\d+(?:\.\d+)?\s*(?:percent|%|million|billion|thousand))",
            ],
            "min_count": 3,
        },
        "external_links_gov": {
            "weight": 20,
            "patterns": [
                r"https?://(?:www\.)?(?:canada\.ca|gc\.ca|irs\.gov|usa\.gov|federalreserve\.gov)",
                r"https?://(?:www\.)?(?:bankofcanada\.ca|imf\.org|worldbank\.org|oecd\.org)",
            ],
            "min_count": 2,
        },
    },
    "authority": {
        "author_credentials": {
            "weight": 35,
            "patterns": [
                r"(?i)\b(?:by|author|written by|published by|expert|specialist|advisor|consultant)",
                r"(?i)\b(?:CFA|CPA|CFP|MBA|PhD|CMA|CGA|CA|CGA)",
                r"(?i)\b(?:years of experience|licensed|certified|qualified|accredited)",
            ],
            "min_count": 1,
        },
        "brand_mentions": {
            "weight": 20,
            "patterns": [
                r"(?i)\b(?:moneyabroadguide|MoneyAbroadGuide)",
            ],
            "min_count": 2,
        },
        "publication_standards": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:editorial|reviewed by|fact-checked|editorial policy|editorial standards)",
                r"(?i)\b(?:methodology|disclosure|affiliate disclosure|sponsored)",
            ],
            "min_count": 1,
        },
        "internal_links": {
            "weight": 20,
            "patterns": [
                r"https?://(?:www\.)?moneyabroadguide\.com",
                r"\[.+?\]\((?:/[^)]+|https?://moneyabroadguide)[^)]*\)",
            ],
            "min_count": 3,
        },
    },
    "trust": {
        "disclaimer_present": {
            "weight": 30,
            "patterns": [
                r"(?i)\b(?:not financial advice|not a financial advisor|consult a professional)",
                r"(?i)\b(?:disclaimer|disclosure|this is not|general information only)",
                r"(?i)\b(?:seek professional advice|independent financial advice)",
            ],
            "min_count": 1,
        },
        "last_updated": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:last updated|updated on|published on|reviewed on)",
                r"(?i)\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
            ],
            "min_count": 1,
        },
        "author_bio": {
            "weight": 25,
            "patterns": [
                r"(?i)\b(?:about the author|author bio|about us|meet the team|written by)",
                r"(?i)\b(?:author's note|contributor|editor|journalist)",
            ],
            "min_count": 1,
        },
        "fact_checked": {
            "weight": 20,
            "patterns": [
                r"(?i)\b(?:fact[- ]?checked|fact checking|verified|accuracy|sources cited)",
                r"(?i)\b(?:references|bibliography|sources|citations|footnotes)",
            ],
            "min_count": 1,
        },
    },
}


class EEATValidatorAgent(BaseAgent):
    """Agent 06 - E-E-A-T Validation: Experience, Expertise, Authority, Trust."""

    MINIMUM_EEAT_SCORE = 95.0

    def __init__(self, config: dict):
        super().__init__(agent_id="agent_06", name="EEATValidatorAgent", config=config)

    async def run(self, article_draft_path: str, output_dir: str = "outputs") -> dict:
        """
        Validate the article for E-E-A-T compliance.
        Returns eeat_report dict and saves eeat_report.json.
        """
        self.logger.info("Agent 06 - EEAT Validator starting...")
        start_time = datetime.now()

        draft_path = Path(article_draft_path)
        if not draft_path.exists():
            raise FileNotFoundError(f"Article draft not found: {article_draft_path}")
        article_text = draft_path.read_text(encoding="utf-8")
        word_count = len(article_text.split())
        self.logger.info(f"Loaded article: {word_count} words")

        # Run all four dimension evaluations
        scores = {}
        details = {}
        for dimension in ["experience", "expertise", "authority", "trust"]:
            score, found, missing = self._evaluate_dimension(dimension, article_text)
            scores[dimension] = score
            details[dimension] = {"score": score, "found_signals": found, "missing_signals": missing}

        total_score = self._calculate_total(scores)
        report = self._build_report(scores, details, total_score, word_count, start_time)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        report_file = output_path / "eeat_report.json"
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))

        status = "PASS" if total_score >= self.MINIMUM_EEAT_SCORE else "FAIL"
        self.logger.info(f"EEAT validation complete: {total_score:.1f}/100 - {status}")
        return report

    # ------------------------------------------------------------------ #
    #  Dimension Evaluation                                                #
    # ------------------------------------------------------------------ #

    def _evaluate_dimension(self, dimension: str, text: str) -> tuple:
        """Evaluate one EEAT dimension against its signals."""
        signals = EEAT_SIGNALS[dimension]
        dimension_weight = EEAT_WEIGHTS[dimension]
        total_signal_weight = sum(s["weight"] for s in signals.values())
        earned_weight = 0
        found_signals = []
        missing_signals = []

        for signal_name, signal_def in signals.items():
            matches = 0
            for pattern in signal_def["patterns"]:
                found = re.findall(pattern, text)
                matches += len(found)
            min_count = signal_def["min_count"]
            weight = signal_def["weight"]

            if matches >= min_count:
                # Full points if >= min_count, partial if some found
                earned_weight += weight
                found_signals.append({
                    "signal": signal_name,
                    "weight": weight,
                    "matches": matches,
                    "status": "FOUND",
                })
            elif matches > 0:
                # Partial credit
                partial = weight * (matches / min_count)
                earned_weight += partial
                found_signals.append({
                    "signal": signal_name,
                    "weight": partial,
                    "matches": matches,
                    "status": "PARTIAL",
                })
            else:
                missing_signals.append({
                    "signal": signal_name,
                    "weight": weight,
                    "matches": 0,
                    "status": "MISSING",
                    "recommendation": self._get_signal_recommendation(signal_name, dimension),
                })

        raw_score = (earned_weight / total_signal_weight) * 100 if total_signal_weight > 0 else 0
        return round(raw_score, 2), found_signals, missing_signals

    def _get_signal_recommendation(self, signal_name: str, dimension: str) -> str:
        recs = {
            "first_person_narrative": "Add personal experience statements",
            "specific_examples": "Add concrete real-world examples",
            "technical_terminology": "Use financial terms: APR, IBAN, KYC, RRSP, TFSA",
            "regulatory_references": "Reference regulations: FINTRAC, CRA, IRS",
            "external_links_gov": "Link to government sites: canada.ca, irs.gov",
            "disclaimer_present": "Add disclaimer: Not financial advice. Consult a professional.",
            "last_updated": "Add update date: Last updated: [Month Year]",
            "author_bio": "Add author bio section",
            "fact_checked": "Add fact-checked notation",
            "author_credentials": "Add author credentials and qualifications",
            "brand_mentions": "Mention MoneyAbroadGuide brand at least twice",
            "publication_standards": "Add editorial policy or reviewed-by section",
            "internal_links": "Add internal links to related MoneyAbroadGuide articles",
            "detailed_process": "Add step-by-step process sections",
            "recent_date": "Add or verify publication/update date is recent",
            "data_and_statistics": "Add current statistics with percentage/number data",
        }
        return recs.get(signal_name, f"Improve {signal_name} in {dimension}")

    def _calculate_total(self, scores: dict) -> float:
        total = 0
        for dimension, weight in EEAT_WEIGHTS.items():
            total += (scores.get(dimension, 0) / 100) * weight
        return round(total, 2)

    # ------------------------------------------------------------------ #
    #  Report Builder                                                      #
    # ------------------------------------------------------------------ #

    def _build_report(self, scores: dict, details: dict, total_score: float, word_count: int, start_time: datetime) -> dict:
        elapsed = (datetime.now() - start_time).total_seconds()
        passes = total_score >= self.MINIMUM_EEAT_SCORE
        recommendations = self._generate_recommendations(scores, details)
        critical_issues = self._get_critical_issues(scores, details)

        return {
            "agent": "agent_06_eeat_validator",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "verdict": "PASS" if passes else "FAIL",
            "total_eeat_score": total_score,
            "minimum_required": self.MINIMUM_EEAT_SCORE,
            "passes_threshold": passes,
            "word_count": word_count,
            "dimension_scores": {
                "experience": scores.get("experience", 0),
                "expertise": scores.get("expertise", 0),
                "authority": scores.get("authority", 0),
                "trust": scores.get("trust", 0),
            },
            "eeat_weights": EEAT_WEIGHTS,
            "dimension_details": details,
            "recommendations": recommendations,
            "critical_issues": critical_issues,
            "improvement_actions": self._generate_improvement_actions(scores, details),
        }

    def _generate_recommendations(self, scores: dict, details: dict) -> list:
        recs = []
        for dimension, detail in details.items():
            score = detail["score"]
            missing = detail.get("missing_signals", [])
            if score < 70:
NEXUS-14 - Agent 06: EEAT Validator Agent
MoneyAbroadGuide Autonomous Newsroom
Validates Experience, Expertise, Authority, Trust scores.
Target: EEAT >= 95. Output: eeat_report.json
"""

import json
import re
import logging
from datetime import datetime
from typing import Any
from pathlib import Path

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

EEAT_WEIGHTS = {
    "experience": 25,
    "expertise": 25,
    "authority": 25,
    "trust": 25,
}

EXPERIENCE_SIGNALS = {
    "first_person_narrative": (r"(?i)\b(i have|my experience|in my|i found|i tried)", 8),
    "specific_examples": (r"(?i)\bfor example|for instance|such as|case study", 6),
    "dates_mentioned": (r"\b(20[0-9]{2}|january|february|march|april|may|june|july)", 4),
    "personal_testimony": (r"(?i)\b(based on|from my|in our|we found|we tested)", 4),
    "process_description": (r"(?i)\b(step by step|process|procedure|how to|workflow)", 3),
}

EXPERTISE_SIGNALS = {
    "technical_terminology": (r"(?i)\b(apr|apy|remittance|swift|iban|kyc|aml|forex|sepa|rrsp|tfsa)", 8),
    "regulatory_references": (r"(?i)\b(regulation|act|law|policy|compliance|fintrac|osfi|fdic|cfpb|irs)", 7),
    "data_citations": (r"(?i)\b(according to|source:|cited by|study by|research by|report by)", 5),
    "expert_quotes": (r"(?i)\b(said|stated|according to|expert|analyst|advisor)", 4),
    "comparison_analysis": (r"(?i)\b(compared to|versus|vs\.|better than|worse than)", 3),
}

AUTHORITY_SIGNALS = {
    "external_links_gov": (r"https?://[^\s]*(?:canada\.ca|gc\.ca|usa\.gov|irs\.gov|federalreserve\.gov)", 10),
    "external_links_finance": (r"https?://[^\s]*(?:imf\.org|worldbank\.org|bankofcanada\.ca|reuters\.com)", 7),
    "statistics_with_sources": (r"(?i)\d+(?:\.\d+)?%.*(?:according to|source|from|per)", 5),
    "publication_references": (r"(?i)\b(published|journal|report|study|whitepaper)", 4),
    "brand_mentions": (r"(?i)\b(moneyabroadguide|our site|our platform|our team)", 3),
}

TRUST_SIGNALS = {
    "disclaimer_present": (r"(?i)\b(not financial advice|consult a|professional advice|disclaimer)", 8),
    "last_updated": (r"(?i)\b(last updated|updated on|as of|reviewed on)", 7),
    "author_bio": (r"(?i)\b(about the author|author bio|written by|by [A-Z])", 6),
    "fact_checked": (r"(?i)\b(fact.check|verified by|reviewed by|edited by)", 5),
    "privacy_security": (r"(?i)\b(secure|encrypted|privacy|confidential|ssl|https)", 3),
}

ALL_SIGNALS = {
    "experience": EXPERIENCE_SIGNALS,
    "expertise": EXPERTISE_SIGNALS,
    "authority": AUTHORITY_SIGNALS,
    "trust": TRUST_SIGNALS,
}


class EEATValidatorAgent(BaseAgent):
    """Agent 06: EEAT validation scoring for NEXUS-14."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(agent_id="agent_06", name="EEATValidatorAgent", config=config)
        self.llm_service = None
        self.target_score = config.get("eeat_target_score", 95)

    async def run(self, article_draft_path: str, output_dir: str = "outputs") -> dict[str, Any]:
        """Score EEAT dimensions and produce detailed report."""
        self.logger.info("Agent 06 - EEAT Validator starting...")
        start_time = datetime.now()

        draft_path = Path(article_draft_path)
        if not draft_path.exists():
            raise FileNotFoundError(f"Article draft not found: {article_draft_path}")
        article_text = draft_path.read_text(encoding="utf-8")
        word_count = len(article_text.split())
        self.logger.info(f"Analyzing article: {word_count} words")

        scores = {}
        details = {}
        for dimension, signals in ALL_SIGNALS.items():
            score, found, missing = self._score_dimension(article_text, dimension, signals)
            scores[dimension] = score
            details[dimension] = {
                "found_signals": found,
                "missing_signals": missing,
                "raw_score": score
            }

        total_score = self._calculate_total(scores)

        llm_analysis = None
        if self.llm_service:
            try:
                llm_analysis = await self._llm_eeat_analysis(article_text, scores)
            except Exception as e:
                self.logger.warning(f"LLM EEAT analysis failed: {e}")

        recommendations = self._generate_recommendations(scores, details, total_score)
        elapsed = (datetime.now() - start_time).total_seconds()
        verdict = "PASS" if total_score >= self.target_score else "FAIL"

        report = {
            "agent": "agent_06_eeat_validator",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "article_stats": {
                "word_count": word_count,
                "char_count": len(article_text),
            },
            "scores": {
                "experience": round(scores["experience"], 1),
                "expertise": round(scores["expertise"], 1),
                "authority": round(scores["authority"], 1),
                "trust": round(scores["trust"], 1),
                "total_eeat": round(total_score, 1),
                "target": self.target_score,
                "passes_threshold": total_score >= self.target_score,
            },
            "verdict": verdict,
            "details": details,
            "llm_analysis": llm_analysis,
            "recommendations": recommendations,
            "critical_issues": self._get_critical_issues(scores, details),
        }

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "eeat_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self.logger.info(f"EEAT validation complete - Total: {total_score:.1f} ({verdict})")
        return report

    def _score_dimension(self, text: str, dimension: str, signals: dict) -> tuple:
        found_signals = []
        missing_signals = []
        total_weight = sum(w for _, w in signals.values())
        earned_weight = 0
        for signal_name, (pattern, weight) in signals.items():
            matches = re.findall(pattern, text)
            if matches:
                count = len(matches)
                multiplier = min(1.5, 1.0 + (count - 1) * 0.1)
                earned = min(weight, weight * multiplier)
                earned_weight += earned
                found_signals.append({
                    "signal": signal_name,
                    "weight": weight,
                    "earned": round(earned, 2),
                    "occurrences": count,
                })
            else:
                missing_signals.append({
                    "signal": signal_name,
                    "weight": weight,
                    "recommendation": self._get_signal_rec(signal_name),
                })
        raw_score = (earned_weight / total_weight) * 100 if total_weight > 0 else 0
        return round(raw_score, 2), found_signals, missing_signals

    def _get_signal_rec(self, signal_name: str) -> str:
        recs = {
            "first_person_narrative": "Add: I have helped clients... or From my experience...",
            "specific_examples": "Add concrete real-world examples",
            "technical_terminology": "Use: APR, IBAN, KYC, RRSP, TFSA, AML, SWIFT",
            "regulatory_references": "Reference: FINTRAC, CRA, IRS, OSFI regulations",
            "external_links_gov": "Link to: canada.ca, irs.gov, federalreserve.gov",
            "disclaimer_present": "Add: This is not financial advice. Consult a professional.",
            "last_updated": "Add: Last updated: January 2026",
            "author_bio": "Add author bio section",
            "fact_checked": "Add: Fact-checked by editorial team",
        }
        return recs.get(signal_name, f"Improve {signal_name} signal")

    def _calculate_total(self, scores: dict) -> float:
        total = 0
        for dimension, weight in EEAT_WEIGHTS.items():
            total += (scores.get(dimension, 0) / 100) * weight
        return min(100, total)

    async def _llm_eeat_analysis(self, text: str, scores: dict) -> dict:
        score_summary = json.dumps(scores, indent=2)
        prompt = (
            "EEAT specialist review for MoneyAbroadGuide.com financial article.\n"
            f"Current scores:\n{score_summary}\n\n"
            "Analyze article (first 2000 chars).\n"
            "Return JSON: {\"assessment\":\"...\",\"strengths\":[],\"improvements\":[],\"adjusted_score\":90}\n\n"
            f"ARTICLE:\n{text[:2000]}"
        )
        response = await self.llm_service.complete(prompt, max_tokens=800)
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            return json.loads(response[start:end])
        except Exception:
            return {"assessment": response[:500]}

    def _generate_recommendations(self, scores: dict, details: dict, total_score: float) -> list:
        recs = []
        for dimension in ["experience", "expertise", "authority", "trust"]:
            score = scores.get(dimension, 0)
            missing = details[dimension]["missing_signals"]
            top_missing = sorted(missing, key=lambda x: x["weight"], reverse=True)[:2]
            priority = "HIGH" if score < 50 else ("MEDIUM" if score < 70 else "LOW")
            for m in top_missing:
                recs.append({
                    "priority": priority,
                    "dimension": dimension.upper(),
                    "score": round(score, 1),
                    "action": m["recommendation"],
                })
        return recs

    def _get_critical_issues(self, scores: dict, details: dict) -> list:
        critical = []
        trust_missing = [m["signal"] for m in details.get("trust", {}).get("missing_signals", [])]
        if "author_bio" in trust_missing:
            critical.append("CRITICAL: No author bio detected")
        if "disclaimer_present" in trust_missing:
            critical.append("CRITICAL: No disclaimer found")
        if "last_updated" in trust_missing:
            critical.append("HIGH: No last-updated date")
        auth_missing = [m["signal"] for m in details.get("authority", {}).get("missing_signals", [])]
        if "external_links_gov" in auth_missing:
            critical.append("HIGH: No government source links")
        if scores.get("expertise", 0) < 30:
            critical.append("CRITICAL: Very low expertise score")
        return critical
