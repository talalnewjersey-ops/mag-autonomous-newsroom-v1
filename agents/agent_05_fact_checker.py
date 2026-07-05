"""
NEXUS-14 - Agent 05: Fact Checker Agent
MoneyAbroadGuide Autonomous Newsroom
Verifies facts, statistics, numbers, sources, government links, financial data.
Output: fact_check_report.json
"""

import asyncio
import json
import re
import logging
from datetime import datetime
from typing import Any
from pathlib import Path
import aiohttp

from agents.base_agent import BaseAgent
from agents._sources import _classify_url  # shared official-source allow-list (single source of truth)
from agents._claims import _NUM_RE, _ATTR_RE, _URL_IN  # shared claim regexes (also used by Couche 2 soften)
from agents._fact_coverage import classify_claims  # LEVIER C: value-matched fact coverage
from agents._source_pool import resolve_gate_vertical

logger = logging.getLogger(__name__)

# Some official sites (state DOI/DMV, FTC) return 403 to non-browser User-Agents.
# The live-source gate must NOT false-positive those real, live pages, so it
# presents a real browser UA (verified: with this UA dmv.ny.gov / consumer.ftc.gov
# / studentaid.gov return 200; the default aiohttp UA gets 403).
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

TRUSTED_DOMAINS = [
    "canada.ca", "gc.ca", "cic.gc.ca", "cra-arc.gc.ca",
    "usa.gov", "irs.gov", "state.gov", "dol.gov", "federalreserve.gov",
    "imf.org", "worldbank.org", "oecd.org", "bis.org",
    "bankofcanada.ca", "ecb.europa.eu",
    "transferwise.com", "wise.com", "xe.com",
    "forbes.com", "wsj.com", "ft.com", "reuters.com", "bloomberg.com",
    "investopedia.com", "nerdwallet.com",
    "moneyabroadguide.com"
]

CLAIM_PATTERNS = [
    r"\b(\d+(?:\.\d+)?%)",
    r"\b\$(\d[\d,]*(?:\.\d+)?)\b",
    r"\bCAD\s*(\d[\d,]*(?:\.\d+)?)\b",
    r"\b(\d{4})\b(?=.*(?:law|act|regulation|rule))",
    r"\b(\d+)\s+(?:days?|weeks?|months?|years?)\b",
    r"(?i)\b(?:according to|study shows?|research (?:shows?|found)|data (?:shows?|indicates?))\b",
    r"(?i)\b(?:government|official|federal|provincial|state)\s+(?:data|statistics?|figures?|report)\b",
    r"(?i)\b(?:average|median|typical|standard)\s+(?:rate|fee|cost|salary|income)\b",
    r"(?i)\b(?:maximum|minimum|limit|cap|threshold)\s+(?:of\s+)?\$?\d",
]

# Sprint 10 anti-hallucination: numeric-claim <-> citation detection.
# _NUM_RE / _ATTR_RE / _URL_IN now live in agents/_claims.py (single source of
# truth) so this detection and the Couche 2 soften pass can never diverge.


def detect_unsourced_claims(text, vertical):
    """Flag numeric/statistical claims not COVERED by an engraved Couche 1 STABLE
    fact of `vertical` (LEVIER C, agents/_fact_coverage.py). An allow-listed link
    sitting nearby is no longer sufficient by itself -- the number must match
    that fact's exact engraved value, or it is treated as unsourced even though a
    real .gov link is right there (the "proximity-false-sourced" blind spot). A
    stat attributed to a named source ("according to ...", "(2023)") but with no
    covering fact is the higher-severity 'unbacked_attribution'. Sentences with
    NO number are never flagged (precision -> no false positive on legitimate
    prose like "the IRS requires filing")."""
    text = text or ""
    unsourced, attributions = [], []
    for c in classify_claims(text, vertical):
        if c["fact"] is not None:
            continue  # value-matched to an engraved fact -> genuinely sourced
        lo, hi = max(0, c["start"] - 100), min(len(text), c["end"] + 100)
        snippet = text[lo:hi].strip()[:200]
        (attributions if c["is_attr"] else unsourced).append(snippet)
    return {"unsourced_stats": unsourced, "unbacked_attributions": attributions}


class FactCheckerAgent(BaseAgent):
    """Agent 05: Automated fact-checking for NEXUS-14 articles."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(name="FactCheckerAgent", config=config)
        self.search_service = None
        self.llm_service = None
        self.session: aiohttp.ClientSession | None = None
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def run(self, article_draft_path: str, output_dir: str = "outputs",
                  market: str = "", category: str = "") -> dict[str, Any]:
        """Read article draft, extract all checkable claims, verify them."""
        self.logger.info("Agent 05 - Fact Checker starting...")
        start_time = datetime.now()
        vertical = resolve_gate_vertical(market, category)

        draft_path = Path(article_draft_path)
        if not draft_path.exists():
            raise FileNotFoundError(f"Article draft not found: {article_draft_path}")
        article_text = draft_path.read_text(encoding="utf-8")
        self.logger.info(f"Loaded article: {len(article_text)} chars")

        async with aiohttp.ClientSession(timeout=self.timeout,
                                         headers={"User-Agent": _BROWSER_UA}) as session:
            self.session = session
            claims = await self._extract_claims(article_text)
            self.logger.info(f"Extracted {len(claims)} claims to verify")

            verified = []
            for claim in claims:
                result = await self._verify_claim(claim)
                verified.append(result)
                await asyncio.sleep(0.3)

            urls = self._extract_urls(article_text)
            url_results = await self._check_urls(urls)
            stats_report = await self._validate_statistics(article_text)
            hallucinations = detect_unsourced_claims(article_text, vertical)

        report = self._build_report(verified, url_results, stats_report, start_time, hallucinations)

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        report_file = output_path / "fact_check_report.json"
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        self.logger.info(
            f"Fact check complete - {report['summary']['verified_count']} verified, "
            f"{report['summary']['issues_count']} issues"
        )
        return report

    async def _extract_claims(self, text: str) -> list[dict]:
        claims: list[dict] = []
        seen: set[str] = set()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        for idx, sentence in enumerate(sentences):
            has_claim = any(re.search(p, sentence) for p in CLAIM_PATTERNS)
            if has_claim and sentence not in seen:
                seen.add(sentence)
                claims.append({
                    "id": f"claim_{idx:04d}",
                    "text": sentence.strip(),
                    "type": self._classify_claim(sentence),
                    "source_position": idx,
                })
        if self.llm_service and len(claims) < 50:
            try:
                llm_claims = await self._llm_extract_claims(text)
                for c in llm_claims:
                    if c["text"] not in seen:
                        seen.add(c["text"])
                        claims.append(c)
            except Exception as e:
                self.logger.warning(f"LLM claim extraction failed: {e}")
        return claims[:100]

    def _classify_claim(self, sentence: str) -> str:
        s = sentence.lower()
        if re.search(r"\$|\bcad\b|\busd\b|fee|cost|rate|salary|income", s):
            return "financial"
        if re.search(r"\d+%|percent", s):
            return "statistical"
        if re.search(r"law|act|regulation|rule|policy|government|official", s):
            return "legal_regulatory"
        if re.search(r"day|week|month|year|processing|timeline|deadline", s):
            return "timeline"
        if re.search(r"study|research|according to|survey|report", s):
            return "sourced_claim"
        return "general"

    async def _llm_extract_claims(self, text: str) -> list[dict]:
        prompt = (
            "From the following article excerpt, identify up to 20 specific factual claims "
            "that can be verified (statistics, fees, rates, timelines, regulatory facts).\n"
            "Return JSON array: [{\"id\":\"c001\",\"text\":\"claim text\","
            "\"type\":\"financial|statistical|legal|timeline|sourced\"}]\n\n"
            f"ARTICLE (first 3000 chars):\n{text[:3000]}\n\nJSON only:"
        )
        response = await self.llm_service.complete(prompt, max_tokens=1500)
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            return json.loads(response[start:end])
        except Exception:
            return []

    async def _verify_claim(self, claim: dict) -> dict:
        result = {
            **claim,
            "status": "UNVERIFIED",
            "confidence": 0.0,
            "supporting_sources": [],
            "contradicting_sources": [],
            "notes": "",
            "verified_at": datetime.now().isoformat(),
        }
        try:
            if self.search_service:
                query = self._build_verification_query(claim)
                search_results = await self.search_service.search(query, num_results=5)
                support, contradict, confidence = self._evaluate_search_results(
                    claim["text"], search_results
                )
                result["supporting_sources"] = support
                result["contradicting_sources"] = contradict
                result["confidence"] = confidence
                result["status"] = self._determine_status(confidence, support, contradict)
            else:
                result.update(self._heuristic_verify(claim))
        except Exception as e:
            self.logger.warning(f"Claim verification error ({claim['id']}): {e}")
            result["status"] = "VERIFICATION_ERROR"
            result["notes"] = str(e)
        return result

    def _build_verification_query(self, claim: dict) -> str:
        text = claim["text"]
        numbers = re.findall(r"\$?[\d,]+(?:\.\d+)?%?", text)
        keywords = " ".join(numbers[:3]) if numbers else ""
        short = re.sub(r"[^a-zA-Z0-9\s%$.,]", " ", text[:100]).strip()
        trusted = " OR site:".join(TRUSTED_DOMAINS[:8])
        return f"{short} {keywords} site:({trusted})"

    def _evaluate_search_results(self, claim_text: str, results: list[dict]) -> tuple:
        supporting = []
        contradicting = []
        trusted_hits = 0
        total_hits = len(results)
        for r in results:
            url = r.get("url", "").lower()
            snippet = r.get("snippet", "").lower()
            is_trusted = any(d in url for d in TRUSTED_DOMAINS)
            claim_nums = set(re.findall(r"[\d.]+", claim_text))
            snippet_nums = set(re.findall(r"[\d.]+", snippet))
            overlap = claim_nums & snippet_nums
            if is_trusted and overlap:
                trusted_hits += 1
                supporting.append({"url": r.get("url"), "snippet": snippet[:200]})
            elif not overlap and len(snippet) > 50:
                contradicting.append({"url": r.get("url"), "snippet": snippet[:200]})
        confidence = min(1.0, (trusted_hits / max(total_hits, 1)) + (len(supporting) * 0.1))
        return supporting, contradicting, round(confidence, 2)

    def _determine_status(self, confidence: float, support: list, contradict: list) -> str:
        if confidence >= 0.7 and len(support) >= 1:
            return "VERIFIED"
        if len(contradict) > len(support):
            return "DISPUTED"
        if confidence >= 0.4:
            return "PARTIALLY_VERIFIED"
        return "UNVERIFIED"

    def _heuristic_verify(self, claim: dict) -> dict:
        text = claim["text"]
        notes = []
        issues = []
        pcts = [float(p.replace("%", "")) for p in re.findall(r"([\d.]+)%", text)]
        for p in pcts:
            if p > 100:
                issues.append(f"Percentage {p}% exceeds 100")
            elif p > 50 and claim["type"] == "financial":
                notes.append(f"High percentage {p}% - manual review recommended")
        amounts = re.findall(r"\$(\d[\d,]*)", text)
        for a in amounts:
            val = int(a.replace(",", ""))
            if val > 1_000_000:
                notes.append(f"Large amount ${val:,} - verify accuracy")
        status = "FLAGGED" if issues else "HEURISTIC_PASS"
        return {
            "status": status,
            "confidence": 0.5 if not issues else 0.2,
            "notes": "; ".join(notes + issues) if (notes or issues) else "Passed heuristic checks",
        }

    def _extract_urls(self, text: str) -> list[str]:
        pattern = r"https?://[^\s\)\]>|,;]+"
        return list(set(re.findall(pattern, text)))[:50]

    async def _check_urls(self, urls: list[str]) -> dict:
        results = {"live": [], "broken": [], "redirected": [], "untrusted": []}

        async def check_one(url: str):
            # Sprint 4 fact-live-sources: classify each official source as live or
            # broken. A definite 4xx/5xx (reason="http") is a hard failure (likely an
            # invented/erroneous URL); a transport error/timeout after retries
            # (reason="transport") is soft (the page may exist; never blocks prod).
            last_err = None
            for attempt in range(3):  # 1 try + 2 retries for transient transport errors
                try:
                    async with self.session.head(url, allow_redirects=True,
                                                 timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        status = resp.status
                        # Some servers reject HEAD (405/501) or bot-block it (403)
                        # but serve GET: fall back before treating it as broken.
                        if status in (403, 405, 501):
                            async with self.session.get(url, allow_redirects=True,
                                                         timeout=aiohttp.ClientTimeout(total=10)) as gresp:
                                status = gresp.status
                                resp = gresp
                        domain = re.sub(r"https?://(www\.)?", "", url).split("/")[0]
                        is_trusted = any(d in domain for d in TRUSTED_DOMAINS)
                        entry = {"url": url, "status_code": status, "trusted": is_trusted}
                        if status == 200:
                            results["live"].append(entry)
                        elif status in (301, 302, 307, 308):
                            results["redirected"].append({**entry, "final_url": str(resp.url)})
                        else:
                            results["broken"].append({**entry, "reason": "http"})
                        if not is_trusted:
                            results["untrusted"].append(entry)
                    last_err = None
                    break  # success (got an HTTP response) -> no more retries
                except Exception as e:
                    last_err = e
                    if attempt < 2:
                        await asyncio.sleep(0.5 * (attempt + 1))  # light backoff
            if last_err is not None:
                # Transport error/timeout persisted across retries: soft failure.
                results["broken"].append({"url": url, "error": str(last_err)[:100],
                                          "trusted": False, "reason": "transport"})

        await asyncio.gather(*[check_one(u) for u in urls])
        return results

    async def _validate_statistics(self, text: str) -> dict:
        stats = {"validated": [], "flagged": [], "info": []}
        usd_cad = re.findall(r"(?i)1\s*(?:usd|us\$)\s*[=\u2248]\s*([\d.]+)\s*(?:cad|can)", text)
        for rate in usd_cad:
            r = float(rate)
            if 1.0 <= r <= 2.0:
                stats["validated"].append({"type": "exchange_rate", "value": r, "note": "USD/CAD in range"})
            else:
                stats["flagged"].append({"type": "exchange_rate", "value": r, "note": f"USD/CAD={r} unusual"})
        interest_rates = re.findall(r"([\d.]+)%\s+(?:interest|APR|APY|annual)", text, re.I)
        for rate in interest_rates:
            r = float(rate)
            if r > 30:
                stats["flagged"].append({"type": "interest_rate", "value": r, "note": f"{r}% seems high"})
            else:
                stats["validated"].append({"type": "interest_rate", "value": r, "note": "Normal range"})
        processing_times = re.findall(r"(\d+)\s+(?:business\s+)?days?\s+(?:processing|approval)", text, re.I)
        for t in processing_times:
            days = int(t)
            if days > 365:
                stats["flagged"].append({"type": "processing_time", "value": days, "note": f"{days} days excessive"})
            else:
                stats["info"].append({"type": "processing_time", "value": days, "note": "Noted"})
        return stats

    def _build_report(self, verified: list, url_results: dict, stats: dict, start_time: datetime,
                      hallucinations: dict = None) -> dict:
        elapsed = (datetime.now() - start_time).total_seconds()
        verified_count = sum(1 for c in verified if c["status"] == "VERIFIED")
        disputed_count = sum(1 for c in verified if c["status"] == "DISPUTED")
        unverified_count = sum(1 for c in verified if c["status"] in ("UNVERIFIED", "VERIFICATION_ERROR"))
        flagged_count = sum(1 for c in verified if c["status"] == "FLAGGED")
        broken_urls = len(url_results.get("broken", []))
        stats_flagged = len(stats.get("flagged", []))
        issues_count = disputed_count + unverified_count + flagged_count + broken_urls + stats_flagged
        # Sprint 4 fact-live-sources: a broken URL that is an OFFICIAL source
        # (allow-list .gov/.gc.ca/canada.ca) must block, but only on a definite
        # HTTP failure (reason="http": 404/410/4xx/5xx -> likely invented). A
        # transport error/timeout (reason="transport") stays a non-blocking
        # warning, surfaced loudly for human review (residual: a permanently
        # unreachable official URL could still be invented -> see WARNING below).
        _broken = url_results.get("broken", [])
        broken_official_hard = sum(
            1 for b in _broken
            if b.get("reason") == "http" and _classify_url(b.get("url", "")) == "official"
        )
        broken_official_soft = [
            b for b in _broken
            if b.get("reason") == "transport" and _classify_url(b.get("url", "")) == "official"
        ]
        for b in broken_official_soft:
            logger.warning(
                "official source unreachable after retries: %s - human review needed "
                "(possibly invented)", b.get("url", "")
            )
        # Sprint 10 anti-hallucination: unsourced numeric claims + named attributions
        # with no backing link. An unbacked attribution is unambiguous + high YMYL
        # risk -> hard-block here (GATE A). Bare unsourced stats are reported and
        # recalibrated by the QA score (agent_12) so the article still yields an
        # inspectable [QA-FAILED] draft instead of being killed pre-draft.
        _hal = hallucinations or {}
        unsourced_stats = list(_hal.get("unsourced_stats", []))
        unbacked_attributions = list(_hal.get("unbacked_attributions", []))
        if broken_official_hard > 0 or len(unbacked_attributions) > 0:
            # Invented official URL (4xx) OR a stat falsely attributed to a named
            # source with no link -> block publication.
            verdict = "FAIL"
        elif issues_count == 0:
            verdict = "PASS"
        elif disputed_count > 0:
            verdict = "FAIL"
        elif issues_count <= 3:
            verdict = "PASS_WITH_WARNINGS"
        else:
            verdict = "NEEDS_REVIEW"
        return {
            "agent": "agent_05_fact_checker",
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "verdict": verdict,
            "summary": {
                "total_claims": len(verified),
                "verified_count": verified_count,
                "disputed_count": disputed_count,
                "unverified_count": unverified_count,
                "flagged_count": flagged_count,
                "issues_count": issues_count,
                "urls_checked": sum(len(v) for v in url_results.values()),
                "broken_urls": broken_urls,
                "broken_official_hard": broken_official_hard,
                "broken_official_soft": len(broken_official_soft),
                "redirected_urls": len(url_results.get("redirected", [])),
                "stats_validated": len(stats.get("validated", [])),
                "stats_flagged": stats_flagged,
                # Sprint 10 anti-hallucination counts (read by agent_12 for the QA penalty)
                "unsourced_stat_count": len(unsourced_stats),
                "unbacked_attribution_count": len(unbacked_attributions),
            },
            "claims": verified,
            "url_check": url_results,
            "statistics_validation": stats,
            "hallucination_check": {
                "unsourced_stats": unsourced_stats,
                "unbacked_attributions": unbacked_attributions,
            },
            "recommendations": self._generate_recommendations(verified, url_results, stats),
        }

    def _generate_recommendations(self, verified: list, url_results: dict, stats: dict) -> list[str]:
        recs = []
        broken = url_results.get("broken", [])
        if broken:
            recs.append(f"Fix {len(broken)} broken URL(s): {[b['url'][:60] for b in broken[:3]]}")
        disputed = [c for c in verified if c["status"] == "DISPUTED"]
        if disputed:
            recs.append(f"Review {len(disputed)} disputed claim(s)")
        unverified = [c for c in verified if c["status"] == "UNVERIFIED"]
        if unverified:
            recs.append(f"Add sources for {len(unverified)} unverified claim(s)")
        stat_flags = stats.get("flagged", [])
        if stat_flags:
            recs.append(f"Verify {len(stat_flags)} flagged statistic(s)")
        if not recs:
            recs.append("All checks passed - article is factually sound")
        return recs


# ============================================================
# CLI ENTRY POINT - Added V3.2 for workflow execution
# Workflow call: python -m agents.agent_05_fact_checker
#   --input output/agent_04/article_draft.md
#   --output output/agent_05/fact_check_report.json
#   --min-sources 10
# ============================================================

def main():
    """CLI entry point for workflow execution."""
    import argparse, sys, logging
    from pathlib import Path
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [AGENT-05] %(levelname)s %(message)s"
    )
    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(description="Agent 05 - Fact Checker")
    parser.add_argument("--input", required=True, help="Path to article_draft.md")
    parser.add_argument("--output", required=True, help="Output path for fact_check_report.json")
    parser.add_argument("--min-sources", type=int, default=10)
    parser.add_argument("--market", default="", help="LEVIER C: routes vertical for fact coverage")
    parser.add_argument("--category", default="", help="LEVIER C: routes vertical for fact coverage")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        log.error(f"Article draft not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    agent = FactCheckerAgent(config)

    try:
        import asyncio
        report = asyncio.run(agent.run(
            article_draft_path=str(input_path),
            output_dir=str(output_path.parent),
            market=args.market,
            category=args.category,
        ))
        verdict = report.get('verdict', 'UNKNOWN')
        log.info(f"Fact check complete: verdict={verdict}")
        log.info(f"Report written: {output_path}")

        # P4 FIX: Fact checker is now a BLOCKING GATE
        # FAIL or DISPUTED verdict blocks publication (exit code 1)
        if verdict in ("FAIL", "DISPUTED"):
            broken_urls = report.get('summary', {}).get('broken_urls', 0)
            disputed = report.get('summary', {}).get('disputed_count', 0)
            broken_off = report.get('summary', {}).get('broken_official_hard', 0)
            log.error(f"FACT CHECK GATE FAIL: verdict={verdict} | broken_urls={broken_urls} | broken_official_hard={broken_off} | disputed={disputed}")
            log.error("Publication BLOCKED: Fix all disputed claims and broken URLs before publishing.")
            sys.exit(1)

        # PASS or PASS_WITH_WARNINGS: continue pipeline
        if verdict == "PASS_WITH_WARNINGS":
            log.warning(f"Fact check passed with warnings — review recommendations before publishing")
        sys.exit(0)

    except Exception as e:
        log.error(f"Fact checking failed with exception: {e}")
        # P4 FIX: Exception in fact checker also blocks publication
        import json
        fallback = {
            "agent": "agent_05_fact_checker",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "verdict": "EXCEPTION",
            "summary": {"total_claims": 0, "verified_count": 0, "issues_count": 1},
            "claims": [], "url_check": {}, "statistics_validation": {},
            "recommendations": [f"Fact check exception: {str(e)[:200]}"],
            "error": str(e)
        }
        output_path.write_text(json.dumps(fallback, indent=2), encoding="utf-8")
        log.error(f"Fact check exception — publication blocked. Report: {output_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
