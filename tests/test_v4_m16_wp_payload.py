import json

from orchestrator.orchestrator import (
    build_wordpress_payload,
    validate_wordpress_payload,
)


def _article(title="Best Banks for Newcomers in Canada", chars=6000, words=4500):
    """Build an article dict whose content meets the live gate thresholds."""
    # word that is 1 char + 1 space = 2 chars; build enough words and pad chars.
    body = ("alpha " * words)
    if len(body) < chars:
        body = body + ("x" * (chars - len(body)))
    return {
        "title": title,
        "content": body,
        "seo_title": "SEO " + title,
        "meta_description": "A complete guide.",
        "keyword": "newcomer banking",
    }


# ---------------- build_wordpress_payload ----------------

def test_build_disabled_by_default_is_noop():
    out = build_wordpress_payload(_article())
    assert out["enabled"] is False
    assert out["payload"] is None
    assert out["schema"] == "nexus14.wp_publish_payload.v1"


def test_build_payload_shape_matches_agent():
    out = build_wordpress_payload(_article(), enabled=True, featured_media=42, category_ids=[7])
    p = out["payload"]
    assert set(p.keys()) == {
        "title", "content", "status", "slug", "categories",
        "featured_media", "author", "meta",
    }
    assert p["status"] == "draft"
    assert p["featured_media"] == 42
    assert p["categories"] == [7]
    assert p["author"] == 1
    assert set(p["meta"].keys()) == {
        "_yoast_wpseo_title", "_yoast_wpseo_metadesc", "_yoast_wpseo_focuskw",
    }


def test_build_slug_is_deterministic():
    out = build_wordpress_payload(
        {"title": "Best Banks: For Newcomers! (2025)", "content": "x"}, enabled=True
    )
    assert out["payload"]["slug"] == "best-banks-for-newcomers-2025"


def test_build_slug_capped_at_100_chars():
    out = build_wordpress_payload({"title": "a" * 250, "content": "x"}, enabled=True)
    assert len(out["payload"]["slug"]) <= 100


def test_build_custom_status_publish():
    out = build_wordpress_payload(_article(), enabled=True, status="publish")
    assert out["payload"]["status"] == "publish"


def test_build_seo_title_falls_back_to_title():
    art = {"title": "My Title", "content": "x"}
    out = build_wordpress_payload(art, enabled=True)
    assert out["payload"]["meta"]["_yoast_wpseo_title"] == "My Title"


def test_build_yoast_meta_values():
    out = build_wordpress_payload(_article(), enabled=True)
    meta = out["payload"]["meta"]
    assert meta["_yoast_wpseo_title"] == "SEO Best Banks for Newcomers in Canada"
    assert meta["_yoast_wpseo_metadesc"] == "A complete guide."
    assert meta["_yoast_wpseo_focuskw"] == "newcomer banking"


def test_build_does_not_mutate_input():
    art = _article()
    before = json.dumps(art, sort_keys=True)
    build_wordpress_payload(art, enabled=True, featured_media=1, category_ids=[2, 3])
    assert json.dumps(art, sort_keys=True) == before


def test_build_never_raises_on_garbage():
    for bad in (None, 42, "str", [], {"title": 123}):
        out = build_wordpress_payload(bad, enabled=True)
        assert out["schema"] == "nexus14.wp_publish_payload.v1"


def test_build_bad_category_ids_become_empty():
    out = build_wordpress_payload(_article(), enabled=True, category_ids=["notint"])
    assert out["payload"]["categories"] == []


# ---------------- validate_wordpress_payload ----------------

def test_validate_passes_for_good_payload():
    out = build_wordpress_payload(_article(), enabled=True)
    v = validate_wordpress_payload(out)
    assert v["passed"] is True
    assert v["errors"] == []
    assert v["schema"] == "nexus14.wp_publish_validation.v1"


def test_validate_accepts_raw_payload_dict():
    out = build_wordpress_payload(_article(), enabled=True)
    v = validate_wordpress_payload(out["payload"])
    assert v["passed"] is True


def test_validate_flags_empty_title():
    art = _article(title="")
    out = build_wordpress_payload(art, enabled=True)
    v = validate_wordpress_payload(out)
    assert "TITLE_EMPTY_OR_DEFAULT" in v["errors"]
    assert v["passed"] is False


def test_validate_flags_default_title():
    art = _article(title="Untitled Article")
    v = validate_wordpress_payload(build_wordpress_payload(art, enabled=True))
    assert "TITLE_EMPTY_OR_DEFAULT" in v["errors"]


def test_validate_flags_short_content():
    art = {"title": "Real Title", "content": "too short"}
    v = validate_wordpress_payload(build_wordpress_payload(art, enabled=True))
    assert any(e.startswith("CONTENT_TOO_SHORT") for e in v["errors"])
    assert any(e.startswith("WORD_COUNT_TOO_LOW") for e in v["errors"])
    assert v["passed"] is False


def test_validate_flags_jsonld():
    art = {
        "title": "Real Title",
        "content": "x" * 6000 + " " + "word " * 4500 + ' application/ld+json ',
    }
    v = validate_wordpress_payload(build_wordpress_payload(art, enabled=True))
    assert "BODY_JSONLD_FORBIDDEN" in v["errors"]


def test_validate_errors_are_sorted():
    art = {"title": "", "content": "short"}
    v = validate_wordpress_payload(build_wordpress_payload(art, enabled=True))
    assert v["errors"] == sorted(v["errors"])


def test_validate_never_raises_on_garbage():
    for bad in (None, 42, "str", []):
        v = validate_wordpress_payload(bad)
        assert v["schema"] == "nexus14.wp_publish_validation.v1"
        assert v["passed"] is False


def test_validate_custom_thresholds():
    art = {"title": "Real Title", "content": "word " * 50}
    v = validate_wordpress_payload(
        build_wordpress_payload(art, enabled=True), min_chars=10, min_words=10
    )
    assert v["passed"] is True
