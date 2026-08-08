"""agent_04's anti-fabrication prompt: grammar-preserving instruction (2026-08-07).

Companion fix to tests/test_repair_connector_scars.py -- that module adds a
downstream SAFETY NET (repair a scar after the fact). This test locks in the
UPSTREAM half of the same fix: agent_04's own _anti_fab prompt block must
explicitly tell the writer to rewrite the whole clause, not just delete an
unsourced number, so scripts/soften_claims.py's downstream strip has less
raw material to leave a scar from in the first place.

Source guard only (same convention as tests/test_couche1_facts_injection.py
and tests/test_option_c_facts_injection.py for this exact _anti_fab
variable) -- no LLM call, offline. Asserts against the actual CONCATENATED
runtime string value (via `ast`, same as Python's own parser joins adjacent
string literals), not the raw multi-line source text -- a raw-text substring
check is brittle against nothing but where a future edit happens to wrap a
line, which is exactly what caught a false failure while writing this test.
"""
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_PATH = REPO_ROOT / "agents" / "agent_04_article_writer.py"
SRC = _PATH.read_text(encoding="utf-8")


def _anti_fab_value() -> str:
    """Extract _anti_fab's assigned value as the real joined string Python
    would build at runtime -- walks the module AST for the assignment inside
    _write_article_standalone rather than re-implementing string-literal
    concatenation by hand."""
    tree = ast.parse(SRC, filename=str(_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
           and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "_anti_fab":
            return ast.literal_eval(node.value)
    raise AssertionError("could not find `_anti_fab = (...)` assignment in agent_04_article_writer.py")


ANTI_FAB = _anti_fab_value()


def test_anti_fab_instructs_rewriting_the_whole_clause_not_just_deleting_the_number():
    assert "REWRITE THE WHOLE CLAUSE" in ANTI_FAB


def test_anti_fab_names_the_real_recurring_scar_shapes():
    # Locks in that the instruction is grounded in the actual observed bug
    # (49200/49240, 2026-08-07), not a generic reminder that could drift
    # into vagueness on a future edit.
    assert "at of the prior year's earnings" in ANTI_FAB
    assert "within of status confirmation" in ANTI_FAB


def test_anti_fab_still_forbids_a_fabricated_precise_figure():
    # The new instruction must not weaken the pre-existing rule it sits next to.
    assert "never a fabricated precise figure" in ANTI_FAB
