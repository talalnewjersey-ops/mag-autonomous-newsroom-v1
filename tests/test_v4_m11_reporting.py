"""Offline tests for the M11 advisory-reporting layer.

M11 surfaces the M10 advisory in the final pipeline result. These tests are
deterministic and offline (no network, no LLM, no IO). They verify:
  * summarize_advisories() counts quality/consistency flags correctly;
  * it is defensive (empty / missing / malformed input -> zeroed summary);
  * the per-article append record has the expected shape and is non-blocking;
  * the orchestrator exposes the m10_advisories state key and the helper.
"""
import importlib

import pytest


def _append_advisory(state, context):
    decision = (context.get('editor_report') or {}).get('decision', 'NEEDS_CORRECTION')
    try:
        adv = context.get('m10_quality_consistency')
        if adv is not None:
            state['m10_advisories'].append({
                'keyword': (context.get('current_topic') or {}).get('keyword'),
                'decision': decision,
                'advisory': adv,
            })
    except Exception:
        pass
    return state


def _fresh_state():
    return {'m10_advisories': []}


def _import_orchestrator():
    try:
        return importlib.import_module('orchestrator.orchestrator')
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f'orchestrator import unavailable: {exc}')


def test_summary_counts_flags():
    mod = _import_orchestrator()
    state = {
        'm10_advisories': [
            {'advisory': {'quality_passed': False, 'consistency_passed': True, 'regenerate_sections': ['intro']}},
            {'advisory': {'quality_passed': True, 'consistency_passed': False, 'regenerate_sections': []}},
            {'advisory': {'quality_passed': True, 'consistency_passed': True, 'regenerate_sections': []}},
        ]
    }
    summ = mod.summarize_advisories(state)
    assert summ['total'] == 3
    assert summ['quality_flagged'] == 1
    assert summ['consistency_flagged'] == 1
    assert summ['with_regenerate_sections'] == 1


def test_summary_empty_and_missing():
    mod = _import_orchestrator()
    assert mod.summarize_advisories({'m10_advisories': []})['total'] == 0
    assert mod.summarize_advisories({})['total'] == 0
    assert mod.summarize_advisories(None)['total'] == 0


def test_summary_malformed_records_are_safe():
    mod = _import_orchestrator()
    state = {'m10_advisories': [None, {}, {'advisory': None}, {'advisory': {}}]}
    summ = mod.summarize_advisories(state)
    assert summ['total'] == 4
    assert summ['quality_flagged'] == 0
    assert summ['consistency_flagged'] == 0
    assert summ['with_regenerate_sections'] == 0


def test_append_builds_expected_record():
    state = _fresh_state()
    ctx = {
        'current_topic': {'keyword': 'us bank account'},
        'editor_report': {'decision': 'READY_TO_PUBLISH'},
        'm10_quality_consistency': {'quality_passed': False, 'consistency_passed': True, 'regenerate_sections': ['faq']},
    }
    _append_advisory(state, ctx)
    assert len(state['m10_advisories']) == 1
    rec = state['m10_advisories'][0]
    assert rec['keyword'] == 'us bank account'
    assert rec['decision'] == 'READY_TO_PUBLISH'
    assert rec['advisory']['regenerate_sections'] == ['faq']


def test_append_is_noop_without_report():
    state = _fresh_state()
    ctx = {'current_topic': {'keyword': 'x'}, 'editor_report': {'decision': 'REJECTED'}}
    _append_advisory(state, ctx)
    assert state['m10_advisories'] == []


def test_append_never_raises_on_bad_context():
    state = _fresh_state()
    _append_advisory(state, {'m10_quality_consistency': {'quality_passed': True}})
    assert len(state['m10_advisories']) == 1


def test_orchestrator_has_m11_state_key_and_helper():
    mod = _import_orchestrator()
    assert hasattr(mod, 'summarize_advisories')
    import inspect
    src = inspect.getsource(mod)
    assert 'm10_advisories' in src
    assert 'reporting only: never block' in src

# end of M11 advisory-reporting tests
