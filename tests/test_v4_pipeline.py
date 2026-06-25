"""
NEXUS-14 V4 - tests/test_v4_pipeline.py (M10 - Regression Tests)

Real, runnable pytest regression suite for the V4 components implemented on the
feature/nexus14-v4-enterprise branch. Tests are deterministic (the default
"hashing" embeddings backend needs no network) and assert the safety-critical
invariants of the redesign.

RUN
    pip install pytest pyyaml
    pytest tests/test_v4_pipeline.py -v

NOTE: These tests have been WRITTEN but NOT executed in this environment.
Do not treat them as passing until pytest has actually been run in CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.schema_fields import (
    build_schema_fields, assert_no_forbidden_meta, contains_jsonld,
    FORBIDDEN_META_KEYS,
)
from services.content_similarity import (
    title_similarity, intent_overlap,
)
from services.embeddings_service import EmbeddingsService
from agents.agent_17_cannibalization import decide, BAND_ALLOW, BAND_MERGE
from agents.agent_19_originality import (
    run_originality_check, detect_ai_patterns, ngram_jaccard,
)
from agents.agent_20_ymyl_validator import run_ymyl_validation, validate_named_values


class TestSchema:
    def test_yoast_meta_has_no_rank_math_keys(self):
        fields = build_schema_fields({"keyword": "tfsa", "title": "TFSA Guide",
                                      "meta_description": "x"})
        meta = fields.to_yoast_meta()
        for k in FORBIDDEN_META_KEYS:
            assert k not in meta
        assert_no_forbidden_meta(meta)

    def test_assert_no_forbidden_meta_raises_on_rank_math(self):
        with pytest.raises(ValueError):
            assert_no_forbidden_meta({"_rank_math_description": "x"})

    def test_body_jsonld_guard_detects_script(self):
        assert contains_jsonld('<script type="application/ld+json">{}</script>')
        assert not contains_jsonld("<p>clean body, no schema</p>")


class TestOriginality:
    def test_detect_banned_opener(self):
        md = "In today's world, banking is hard. ## Section\nbody"
        violations = detect_ai_patterns(md)
        assert any(v["type"] == "banned_opener" for v in violations)

    def test_detect_emoji_heading(self):
        md = "## \U0001F680 Getting Started\nbody text here"
        violations = detect_ai_patterns(md)
        assert any(v["type"] == "emoji_heading" for v in violations)

    def test_identical_intro_flagged_for_regeneration(self, tmp_path):
        intro = ("This guide explains how newcomers open a bank account in Canada "
                 "step by step with all the required documents and tips. ")
        article = intro + "\n\n## Details\nUnique body content about banking.\n"
        corpus = [{"markdown": intro + "\n\n## Other\nDifferent body entirely.\n"}]
        rep = run_originality_check(article, corpus, str(tmp_path / "orig.json"))
        assert "introduction" in rep["regenerate_sections"]
        assert rep["passed"] is False

    def test_ngram_jaccard_identical_is_high(self):
        a = "the quick brown fox jumps over the lazy dog today"
        assert ngram_jaccard(a, a) == pytest.approx(1.0)


class TestCannibalization:
    def test_decision_bands(self):
        assert decide(BAND_ALLOW - 0.01) == "ALLOW"
        assert decide(BAND_MERGE + 0.01) == "BLOCK"

    def test_embedding_similarity_self_is_one(self):
        emb = EmbeddingsService(provider="hashing")
        v = emb.embed_text("tax free savings account newcomers")
        assert emb.cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_title_similarity_detects_near_duplicate(self):
        s = title_similarity("Best Bank Accounts for Newcomers in Canada",
                             "Best Bank Account for Newcomers to Canada")
        assert s > 0.7

    def test_intent_overlap(self):
        assert intent_overlap("best credit cards review", "top credit cards compared") == 1.0


class TestYMYL:
    def test_named_value_extraction(self):
        registry = {"registry": {"tfsa_contribution_limit_2025":
                    {"value": 7000, "tolerance": 0, "label": "TFSA",
                     "authority": "CRA", "source_url": "https://canada.ca"}}}
        res = validate_named_values("TFSA limit is $7,000", registry)
        assert res and res[0]["status"] == "VERIFIED"

    def test_contradicted_value_detected(self):
        registry = {"registry": {"tfsa_contribution_limit_2025":
                    {"value": 7000, "tolerance": 0, "label": "TFSA",
                     "authority": "CRA", "source_url": "https://canada.ca"}}}
        res = validate_named_values("TFSA limit is $99,999", registry)
        assert res and res[0]["status"] == "CONTRADICTED"


class TestQualityGate:
    def test_schema_check_blocks_body_jsonld(self):
        from scripts.quality_gate_v4 import check_schema
        res = check_schema('body <script type="application/ld+json">{}</script>')
        assert res["passed"] is False

    def test_formatting_check_blocks_emoji_heading(self):
        from scripts.quality_gate_v4 import check_formatting
        res = check_formatting("## \U0001F680 Intro\nbody")
        assert res["passed"] is False

    def test_internal_links_minimum_enforced(self):
        from scripts.quality_gate_v4 import check_internal_links
        few = "[a](https://moneyabroadguide.com/a)"
        assert check_internal_links(few)["passed"] is False

    def test_accessibility_requires_alt(self):
        from scripts.quality_gate_v4 import check_accessibility
        assert check_accessibility('<img src="x.png">')["passed"] is False
        assert check_accessibility('<img src="x.png" alt="desc">')["passed"] is True


class TestMigration:
    def test_strip_jsonld_from_content(self):
        from scripts.migrate_schema import transform_content
        html = 'Body.<script type="application/ld+json">{"@type":"FAQPage"}</script>'
        new, changes = transform_content(html)
        assert "application/ld+json" not in new
        assert changes["jsonld_removed"] == 1

    def test_clean_content_unchanged(self):
        from scripts.migrate_schema import transform_content
        html = "<p>Clean body, nothing to strip.</p>"
        new, changes = transform_content(html)
        assert new == html
        assert changes["jsonld_removed"] == 0


# --------------------------------------------------------------------------- #
# V4 pre-merge additions: Writer variation layer, Performance + Competitor
# agents, and EEAT enrichment. Deterministic + offline.
# --------------------------------------------------------------------------- #
from services.writer_variation import (
    build_variation_directives, strip_banned_patterns, verify_variation,
    plan_regeneration, pick_opener, APPROVED_OPENERS,
)
from agents.agent_19_originality import BANNED_OPENERS, BANNED_PHRASES


class TestWriterVariation:
    def test_directives_reference_banned_patterns(self):
        d = build_variation_directives(["introduction"], {"introduction": "x"}, seed="slug")
        assert "introduction" in d
        assert BANNED_OPENERS[0] in d["introduction"]

    def test_directives_only_for_requested_sections(self):
        d = build_variation_directives(["faq"], {}, seed="s")
        assert set(d.keys()) == {"faq"}

    def test_pick_opener_is_deterministic(self):
        assert pick_opener("abc") == pick_opener("abc")
        assert pick_opener("abc") in APPROVED_OPENERS

    def test_strip_banned_opener_replaced(self):
        text = BANNED_OPENERS[0] + " banking is hard for newcomers."
        cleaned, changes = strip_banned_patterns(text, seed="s")
        assert not cleaned.lower().startswith(BANNED_OPENERS[0])
        assert any(c["type"] == "opener_replaced" for c in changes)

    def test_strip_banned_phrase_removed(self):
        phrase = BANNED_PHRASES[0]
        text = "Some content. " + phrase + " more content."
        cleaned, changes = strip_banned_patterns(text, seed="s")
        assert phrase not in cleaned.lower()
        assert any(c["type"] == "phrase_removed" for c in changes)

    def test_verify_variation_flags_identical(self):
        prior = "the quick brown fox jumps over the lazy dog every single day"
        check = verify_variation(prior, prior)
        assert check["sufficiently_different"] is False
        assert check["passed"] is False

    def test_plan_regeneration_returns_prior_text(self):
        article = "Intro text here.\n\n## FAQ\n### Q?\nA.\n"
        plan = plan_regeneration(article, ["introduction"], seed="slug")
        assert "introduction" in plan["directives"]
        assert "introduction" in plan["prior_sections"]


class TestWriterV4Loop:
    def test_loop_regenerates_then_progresses(self, tmp_path, monkeypatch):
        import agents.agent_04_writer_v4 as w4
        dup_intro = ("This guide explains how newcomers open a bank account in "
                     "Canada step by step with all the documents and tips needed. ")
        article = dup_intro + "\n\n## Details\nUnique body content here.\n"
        corpus = [{"markdown": dup_intro + "\n\n## Other\nDifferent body.\n"}]

        def fake_generator(section, directive):
            return ("Start with the numbers: opening an account takes about an "
                    "hour once your study permit and proof of address are ready.")

        monkeypatch.chdir(tmp_path)
        Path("output/agent_04").mkdir(parents=True, exist_ok=True)
        result = w4.run_writer_v4_loop(article, corpus, fake_generator, seed="slug")
        assert result["rounds"] >= 1
        assert dup_intro.strip() not in result["markdown"]

    def test_replace_section_targeted(self):
        import agents.agent_04_writer_v4 as w4
        md = "Intro.\n\n## FAQ\n### Old?\nOld answer.\n\n## Conclusion\nDone.\n"
        out = w4.replace_section(md, "## FAQ", "### New?\nNew answer.")
        assert "New answer." in out
        assert "## Conclusion" in out
        assert "Old answer." not in out


class TestPerformanceAgent:
    def test_pending_blocks_when_no_measurement(self, tmp_path):
        from agents.agent_22_performance import run_performance_check
        rep = run_performance_check(None, None, str(tmp_path / "perf.json"))
        assert rep["status"] == "PENDING"
        assert rep["passed"] is False

    def test_evaluate_passes_on_good_metrics(self):
        from agents.agent_22_performance import evaluate
        metrics = {"seo": 98, "performance": 92, "accessibility": 97,
                   "best_practices": 96, "cls": 0.03}
        assert evaluate(metrics) is True

    def test_evaluate_fails_on_high_cls(self):
        from agents.agent_22_performance import evaluate
        metrics = {"seo": 98, "performance": 92, "accessibility": 97,
                   "best_practices": 96, "cls": 0.5}
        assert evaluate(metrics) is False


class TestCompetitorAgent:
    def test_pending_blocks_without_competitors(self, tmp_path):
        from agents.agent_23_competitor import run_competitor_check
        rep = run_competitor_check("article text", None, "kw", str(tmp_path / "c.json"))
        assert rep["status"] == "PENDING"
        assert rep["passed"] is False

    def test_information_gain_rewards_new_entities(self):
        from agents.agent_23_competitor import information_gain
        article = "newcomer banking osfi fintrac provincial healthcare premiums"
        competitors = ["generic banking information only"]
        assert information_gain(article, competitors) > 0.2

    def test_missing_faq_detected(self):
        from agents.agent_23_competitor import missing_components
        article = "Body without questions."
        competitors = [{"text": "## Frequently Asked Questions\nQ and A here"}]
        missing = missing_components(article, competitors)
        assert missing["faq"] is True


class TestEEATEnrichment:
    def test_build_eeat_fields_populates_required_keys(self):
        from services.eeat_enrichment import build_eeat_fields, REQUIRED_ELEMENTS
        body = ("Intro with an official source https://www.irs.gov/limits and an "
                "internal link https://moneyabroadguide.com/guide . Affiliate "
                "disclosure: we may earn a commission.")
        fields = build_eeat_fields({"author": "Talal Eddaouahiri"}, body)
        for key in REQUIRED_ELEMENTS:
            assert key in fields
        assert fields["official_references"]
        assert fields["disclosure"] is True

    def test_validate_eeat_blocks_on_missing(self):
        from services.eeat_enrichment import validate_eeat
        result = validate_eeat({"author": "x"})  # almost everything missing
        assert result["passed"] is False
        assert "review_date" in result["missing_elements"]

    def test_validate_eeat_passes_when_complete(self):
        from services.eeat_enrichment import build_eeat_fields, validate_eeat
        body = ("https://www.irs.gov/x https://moneyabroadguide.com/y "
                "Affiliate disclosure included.")
        fields = build_eeat_fields({"author": "Talal"}, body)
        result = validate_eeat(fields)
        assert result["passed"] is True
        assert result["eeat_score"] == 100.0
