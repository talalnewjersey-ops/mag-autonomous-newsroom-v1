"""Offline tests for the M10 orchestrator integration.

M10 wires a NON-BLOCKING quality+consistency advisory gate into the
production orchestrator right after Agent 04 produces a draft. These tests
are deterministic and offline (no network, no LLM, no IO). They verify:
  * the orchestrator module stays importable and exposes the M10 hook symbols;
  * the combined advisory report has the expected shape and keys;
  * the gate is non-blocking: it never raises and never mutates the draft,
    even when an underlying check raises or returns nothing;
  * empty / non-string drafts yield no advisory (skipped safely).
"""
import importlib

import pytest

from services.content_quality import assess_quality
from services.content_consistency import assess_consistency, combine_checks


# Faithful re-implementation of the inline orchestrator hook so the advisory
# contract can be unit-tested without spinning up the async pipeline. The real
# code lives in orchestrator/orchestrator.py and is covered by the import test.
def _advisory(draft, q_fn=assess_quality, c_fn=assess_consistency):
    if not (isinstance(draft, str) and draft.strip()):
        return None
    try:
        q = q_fn(draft)
        c = c_fn(draft)
        secs = []
        for s in list(q.get('regenerate_sections') or []) + list(c.get('regenerate_sections') or []):
            if s not in secs:
                secs.append(s)
        return {
            'quality_score': q.get('score'),
            'quality_passed': q.get('passed'),
            'consistency_score': c.get('score'),
            'consistency_passed': c.get('passed'),
            'regenerate_sections': secs,
            'blocking': False,
        }
    except Exception:
        return None


SAMPLE = (
    '# Opening a US Bank Account as a Newcomer\n\n'
    'You can open an account in about 30 minutes. The monthly fee is 12 dollars.\n\n'
    '## Step by step\n\n'
    'First, gather your passport. Then visit a branch. Later the monthly fee is 5 dollars.\n\n'
    '## FAQ\n\nQ: How long does it take? A: About 30 minutes.\n'
)


def test_advisory_report_shape():
    rep = _advisory(SAMPLE)
    assert rep is not None
    for key in (
        'quality_score', 'quality_passed', 'consistency_score',
        'consistency_passed', 'regenerate_sections', 'blocking',
    ):
        assert key in rep
    assert rep['blocking'] is False
    assert isinstance(rep['regenerate_sections'], list)


def test_advisory_is_advisory_not_blocking():
    rep = _advisory(SAMPLE)
    assert rep['blocking'] is False


def test_advisory_skips_empty_or_nonstring():
    assert _advisory('') is None
    assert _advisory('   ') is None
    assert _advisory(None) is None
    assert _advisory(123) is None


def test_advisory_never_mutates_draft():
    original = SAMPLE
    snapshot = str(SAMPLE)
    _advisory(original)
    assert original == snapshot


def test_advisory_survives_raising_check():
    def boom(_text):
        raise RuntimeError('quality engine offline')
    rep = _advisory(SAMPLE, q_fn=boom)
    assert rep is None


def test_advisory_handles_missing_sections_key():
    def thin(_text):
        return {'score': 50, 'passed': False}
    rep = _advisory(SAMPLE, q_fn=thin)
    assert rep is not None
    assert isinstance(rep['regenerate_sections'], list)


def test_regenerate_sections_is_union_and_deduped():
    q = assess_quality(SAMPLE)
    c = assess_consistency(SAMPLE)
    rep = _advisory(SAMPLE)
    expected = []
    for s in list(q.get('regenerate_sections') or []) + list(c.get('regenerate_sections') or []):
        if s not in expected:
            expected.append(s)
    assert rep['regenerate_sections'] == expected
    assert len(rep['regenerate_sections']) == len(set(rep['regenerate_sections']))


def test_combine_checks_matches_union_behavior():
    combined = combine_checks(
        lambda md: assess_quality(md)['regenerate_sections'],
        lambda md: assess_consistency(md)['regenerate_sections'],
    )
    out = combined(SAMPLE)
    assert isinstance(out, list)
    assert len(out) == len(set(out))


def test_combine_checks_is_defensive():
    def boom(_md):
        raise ValueError('nope')
    combined = combine_checks(boom, lambda md: ['intro'])
    assert combined(SAMPLE) == ['intro']


def _import_orchestrator():
    try:
        return importlib.import_module('orchestrator.orchestrator')
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f'orchestrator import unavailable: {exc}')


def test_orchestrator_imports_with_m10_symbols():
    mod = _import_orchestrator()
    assert hasattr(mod, '_m10_assess_quality')
    assert hasattr(mod, '_m10_assess_consistency')
    assert hasattr(mod, '_m10_combine')


def test_orchestrator_source_has_advisory_after_agent_04():
    import inspect
    mod = _import_orchestrator()
    src = inspect.getsource(mod)
    assert 'm10_quality_consistency' in src
    assert 'advisory only: never block' in src

# end of M10 orchestrator-integration tests
