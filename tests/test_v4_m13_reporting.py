"""Offline tests for the M13 regeneration-plan reporter.

M13 turns the dict returned by the M12 planner (plan_regeneration) into small,
human/log-friendly counters. These tests are deterministic and offline (no
network, no LLM, no IO). They verify:
* a disabled / empty / missing plan reports zero work (no-op);
* when enabled, articles, sections and quality/consistency flags are counted;
* section_counts and total_sections aggregate correctly;
* top_section is the most frequent section with a deterministic tie-break;
* the optional 'enabled' override wins over the plan's own flag;
* malformed / None input never raises and the input is never mutated.
"""
import importlib

import pytest


def _import_orchestrator():
    try:
        return importlib.import_module('orchestrator.orchestrator')
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f'orchestrator import unavailable: {exc}')


def _plan(articles, enabled=True):
    return {'enabled': enabled, 'articles': list(articles),
            'total_sections': sum(len(a.get('regenerate_sections') or []) for a in articles),
            'blocking': False}


def test_disabled_plan_is_noop():
    mod = _import_orchestrator()
    plan = _plan([
        {'keyword': 'a', 'quality_passed': False, 'consistency_passed': False,
         'regenerate_sections': ['body']},
    ], enabled=False)
    s = mod.summarize_regeneration_plan(plan)
    assert s['enabled'] is False
    assert s['articles_to_regenerate'] == 0
    assert s['total_sections'] == 0
    assert s['section_counts'] == {}
    assert s['top_section'] is None


def test_enabled_counts_articles_and_sections():
    mod = _import_orchestrator()
    plan = _plan([
        {'keyword': 'a', 'quality_passed': False, 'consistency_passed': True,
         'regenerate_sections': ['body', 'faq']},
        {'keyword': 'b', 'quality_passed': True, 'consistency_passed': False,
         'regenerate_sections': ['body']},
    ])
    s = mod.summarize_regeneration_plan(plan)
    assert s['enabled'] is True
    assert s['articles_to_regenerate'] == 2
    assert s['total_sections'] == 3
    assert s['section_counts'] == {'body': 2, 'faq': 1}
    assert s['quality_flagged'] == 1
    assert s['consistency_flagged'] == 1
    assert s['both_flagged'] == 0


def test_both_flagged_counted():
    mod = _import_orchestrator()
    plan = _plan([
        {'keyword': 'a', 'quality_passed': False, 'consistency_passed': False,
         'regenerate_sections': ['intro']},
    ])
    s = mod.summarize_regeneration_plan(plan)
    assert s['quality_flagged'] == 1
    assert s['consistency_flagged'] == 1
    assert s['both_flagged'] == 1


def test_top_section_is_most_frequent():
    mod = _import_orchestrator()
    plan = _plan([
        {'keyword': 'a', 'quality_passed': False, 'consistency_passed': True,
         'regenerate_sections': ['body', 'faq']},
        {'keyword': 'b', 'quality_passed': False, 'consistency_passed': True,
         'regenerate_sections': ['body']},
    ])
    s = mod.summarize_regeneration_plan(plan)
    assert s['top_section'] == 'body'


def test_top_section_tie_break_is_deterministic():
    mod = _import_orchestrator()
    # 'body' and 'aaa' both appear once: tie-break picks the lexicographically
    # smallest name -> 'aaa'.
    plan = _plan([
        {'keyword': 'a', 'quality_passed': False, 'consistency_passed': True,
         'regenerate_sections': ['body']},
        {'keyword': 'b', 'quality_passed': False, 'consistency_passed': True,
         'regenerate_sections': ['aaa']},
    ])
    s = mod.summarize_regeneration_plan(plan)
    assert s['top_section'] == 'aaa'


def test_enabled_override_wins():
    mod = _import_orchestrator()
    plan = _plan([
        {'keyword': 'a', 'quality_passed': False, 'consistency_passed': True,
         'regenerate_sections': ['body']},
    ], enabled=False)
    # override forces the summary on even though the plan says disabled
    s = mod.summarize_regeneration_plan(plan, enabled=True)
    assert s['enabled'] is True
    assert s['articles_to_regenerate'] == 1
    assert s['total_sections'] == 1


def test_empty_missing_and_none_safe():
    mod = _import_orchestrator()
    assert mod.summarize_regeneration_plan({}, enabled=True)['articles_to_regenerate'] == 0
    assert mod.summarize_regeneration_plan(None, enabled=True)['total_sections'] == 0
    empty = mod.summarize_regeneration_plan({'enabled': True, 'articles': []})
    assert empty['enabled'] is True
    assert empty['top_section'] is None


def test_malformed_input_never_raises():
    mod = _import_orchestrator()
    plan = {'enabled': True, 'articles': [None, {}, {'regenerate_sections': None},
                                          {'regenerate_sections': ['', 'body']}]}
    s = mod.summarize_regeneration_plan(plan)
    # only the real 'body' section is counted; empty string is ignored
    assert s['section_counts'] == {'body': 1}
    assert s['total_sections'] == 1


def test_summary_does_not_mutate_input():
    mod = _import_orchestrator()
    plan = _plan([
        {'keyword': 'a', 'quality_passed': False, 'consistency_passed': False,
         'regenerate_sections': ['body']},
    ])
    import copy
    before = copy.deepcopy(plan)
    mod.summarize_regeneration_plan(plan)
    assert plan == before


def test_orchestrator_exposes_reporter():
    mod = _import_orchestrator()
    assert hasattr(mod, 'summarize_regeneration_plan')
    import inspect
    src = inspect.getsource(mod.summarize_regeneration_plan)
    assert 'No network, no LLM' in src
    assert 'NEVER raises' in src


def test_end_to_end_with_real_planner():
    mod = _import_orchestrator()
    state = {'m10_advisories': [
        {'keyword': 'weak', 'decision': 'NEEDS_CORRECTION',
         'advisory': {'quality_passed': False, 'consistency_passed': False,
                      'regenerate_sections': ['body', 'faq']}},
        {'keyword': 'one', 'decision': 'NEEDS_CORRECTION',
         'advisory': {'quality_passed': False, 'consistency_passed': True,
                      'regenerate_sections': ['body']}},
    ]}
    plan = mod.plan_regeneration(state, enabled=True)
    s = mod.summarize_regeneration_plan(plan)
    assert s['enabled'] is True
    assert s['articles_to_regenerate'] == 2
    assert s['total_sections'] == 3
    assert s['top_section'] == 'body'
    assert s['both_flagged'] == 1

# end of M13 regeneration-plan reporter tests
