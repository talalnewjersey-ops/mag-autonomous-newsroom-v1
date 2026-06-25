"""
NEXUS-14 V4 - tests/test_v4_pipeline.py  (M10 - Regression Tests)

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
