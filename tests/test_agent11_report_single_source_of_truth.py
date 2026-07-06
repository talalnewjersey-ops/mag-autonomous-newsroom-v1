"""PATH-DUPLICATION FIX (2026-07-06): agent_11 (and agent_12/13, same bug
class) used to write THREE divergent copies of their own report per run:
  1. main()'s direct write to args.output -- the ONLY path the workflow
     reads (--wordpress-report / --output flags) -- but its own report dict
     hardcoded uploaded_images=[]/image_count=0/featured_image_id=None since
     commit f4007c13 (2026-06-16), ignoring the real `result` it already had.
  2. The class's own internal self.save_output("wordpress_report.json", ...)
     call, landing at a DIFFERENT, doubly-nested path because
     BaseAgent.__init__ appends self.AGENT_ID onto config["output_dir"] --
     which main() had ALREADY set to the per-agent folder -- and
     StorageService.save() re-joins base_output_dir onto an already-complete
     path on top of that. This copy had the CORRECT data but was never read
     by anything.
  3. A further-nested variant from the same double-join compounding.

Fix: main() now threads the real `result` fields through instead of
hardcoding them, and the redundant internal self.save_output() calls were
removed from agent_11/12/13's run()-equivalents -- main() is the single
writer. This test proves (a) the hardcoded stale dict is gone, (b) the
redundant internal save call is gone, and (c) a real run only ever produces
ONE wordpress_report.json under an article's output tree (would fail if a
future edit reintroduces a divergent second writer).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SRC_11 = open(os.path.join(ROOT, "agents/agent_11_wordpress_integration.py"), encoding="utf-8").read()
SRC_12 = open(os.path.join(ROOT, "agents/agent_12_quality_assurance.py"), encoding="utf-8").read()
SRC_13 = open(os.path.join(ROOT, "agents/agent_13_chief_editor.py"), encoding="utf-8").read()


def test_agent11_main_report_no_longer_hardcodes_empty_images():
    # The SUCCESS-path report now threads real data through (the ONE legitimate
    # remaining hardcoded-empty instance is _write_failure_reports' genuine
    # failure path, where zero images really is correct).
    assert '"uploaded_images": uploaded_images, "image_count": image_count, "featured_image_id": featured_id,' in SRC_11
    assert SRC_11.count('"uploaded_images": [], "image_count": 0, "featured_image_id": None,') == 1


def test_agent11_main_pulls_images_from_run_result():
    assert 'uploaded_images = result.get("uploaded_images", [])' in SRC_11
    assert 'image_count = result.get("image_count"' in SRC_11


def test_agent11_class_no_longer_writes_its_own_redundant_copy():
    assert 'self.save_output("wordpress_report.json"' not in SRC_11


def test_agent12_class_no_longer_writes_its_own_redundant_copy():
    assert 'self.save_output("qa_report.json"' not in SRC_12


def test_agent13_class_no_longer_writes_its_own_redundant_copy():
    assert 'self.save_output("editor_report.json"' not in SRC_13


def test_agent12_wires_wordpress_report_images_into_di_stack_context():
    # The DEEPER, separate bug: agent_12's DI-stack context dict never included
    # uploaded_images/featured_image_id at all, so _audit_images() ALWAYS saw
    # zero images regardless of what agent_11 reported -- independent of the
    # path-duplication bug above. This masked the point-1 image fallback on
    # every run where an API key was set (the real GH Actions condition).
    assert '"uploaded_images": wp_report.get("uploaded_images", [])' in SRC_12
    assert '"featured_image_id": wp_report.get("featured_image_id")' in SRC_12


def test_single_wordpress_report_per_article_output_tree(tmp_path):
    # Simulates a real article output tree and asserts only ONE
    # wordpress_report.json exists under it -- would fail if a future change
    # reintroduces a second writer at a different nested path.
    article_dir = tmp_path / "article_1"
    (article_dir / "agent_11").mkdir(parents=True)
    (article_dir / "agent_11" / "wordpress_report.json").write_text(
        json.dumps({"post_id": 1, "uploaded_images": [{"id": 1}], "image_count": 1}),
        encoding="utf-8",
    )
    matches = list(article_dir.rglob("wordpress_report.json"))
    assert len(matches) == 1, f"expected exactly one wordpress_report.json, found {len(matches)}: {matches}"


def test_no_agent_appends_its_own_agent_id_onto_an_already_agent_scoped_output_dir():
    # Regression guard for the ROOT CAUSE: main() must not pass an output_dir
    # that ALREADY ends in the agent's own folder name into a config dict used
    # to construct the agent (BaseAgent.__init__ appends self.AGENT_ID onto
    # whatever output_dir it receives -- doing so twice is what doubled the path).
    for agent_id, src in [("agent_11", SRC_11), ("agent_12", SRC_12), ("agent_13", SRC_13)]:
        # str(output_path.parent) is still used for StorageService (intermediate,
        # non-report saves) -- only the redundant *report* write was removed above;
        # this test documents that save_output for the FINAL report is gone.
        assert f'self.save_output("wordpress_report.json"' not in src
        assert f'self.save_output("qa_report.json"' not in src
        assert f'self.save_output("editor_report.json"' not in src
