"""Offline tests for the M12 opt-in regeneration planner.

M12 turns the M10/M11 advisories collected during a run into an ORDERED
regeneration plan. These tests are deterministic and offline (no network, no
LLM, no IO). They verify:
* the planner is DISABLED by default (enabled=False) -> empty, no-op plan;
* when enabled, only flagged drafts that carry regenerate_sections are planned;
* weakest drafts (quality AND consistency failing) are ordered first;
* max_articles caps the plan; total_sections is computed;
* it is defensive: empty / missing / malformed state never raises.
"""
import importlib

import pytest


def _import_orchestrator():
    try:
        return importlib.import_module('orchestrator.orchestrator')
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f'orchestrator import unavailable: {exc}')


def _state(records):
    return {'m10_advisories': records}


def test_disabled_by_default_is_noop():
    mod = _import_orchestrator()
    state = _state([
        {'keyword': 'a', 'decision': 'NEEDS_CORRECTION',
         'advisory': {'quality_passed': False, 'consistency_passed': True,
                      'regenerate_sections': ['body']}},
    ])
    plan = mod.plan_regeneration(state)
    assert plan['enabled'] is False
    assert plan['articles'] == []
    assert plan['total_sections'] == 0
    assert plan['blocking'] is False


def test_enabled_plans_only_flagged_with_sections():
    mod = _import_orchestrator()
    state = _state([
        # flagged + has sections -> planned
        {'keyword': 'flagged', 'decision': 'NEEDS_CORRECTION',
         'advisory': {'quality_passed': False, 'consistency_passed': True,
                      'regenerate_sections': ['body', 'faq']}},
        # passes both -> skipped
        {'keyword': 'clean', 'decision': 'READY_TO_PUBLISH',
         'advisory': {'quality_passed': True, 'consistency_passed': True,
                      'regenerate_sections': []}},
        # flagged but no sections -> skipped
        {'keyword': 'no_sections', 'decision': 'NEEDS_CORRECTION',
         'advisory': {'quality_passed': False, 'consistency_passed': True,
                      'regenerate_sections': []}},
    ])
    plan = mod.plan_regeneration(state, enabled=True)
    assert plan['enabled'] is True
    keywords = [a['keyword'] for a in plan['articles']]
    assert keywords == ['flagged']
    assert plan['articles'][0]['regenerate_sections'] == ['body', 'faq']
    assert plan['total_sections'] == 2


def test_weakest_drafts_ordered_first():
    mod = _import_orchestrator()
    state = _state([
        # only quality fails (weakness = 1)
        {'keyword': 'one_fail', 'decision': 'NEEDS_CORRECTION',
         'advisory': {'quality_passed': False, 'consistency_passed': True,
                      'regenerate_sections': ['body']}},
        # both fail (weakness = 0 -> first)
        {'keyword': 'both_fail', 'decision': 'NEEDS_CORRECTION',
         'advisory': {'quality_passed': False, 'consistency_passed': False,
                      'regenerate_sections': ['body']}},
    ])
    plan = mod.plan_regeneration(state, enabled=True)
    assert [a['keyword'] for a in plan['articles']] == ['both_fail', 'one_fail']


def test_max_articles_caps_plan():
    mod = _import_orchestrator()
    records = []
    for i in range(5):
        records.append({
            'keyword': f'k{i}', 'decision': 'NEEDS_CORRECTION',
            'advisory': {'quality_passed': False, 'consistency_passed': False,
                         'regenerate_sections': ['body']},
        })
    plan = mod.plan_regeneration(_state(records), enabled=True, max_articles=2)
    assert len(plan['articles']) == 2
    assert plan['total_sections'] == 2


def test_empty_and_missing_state_safe():
    mod = _import_orchestrator()
    assert mod.plan_regeneration({}, enabled=True)['articles'] == []
    assert mod.plan_regeneration(None, enabled=True)['articles'] == []
    assert mod.plan_regeneration({'m10_advisories': []}, enabled=True)['total_sections'] == 0


def test_malformed_records_never_raise():
    mod = _import_orchestrator()
    state = _state([None, {}, {'advisory': None}, {'advisory': {}},
                    {'advisory': {'regenerate_sections': ['body']}}])
    plan = mod.plan_regeneration(state, enabled=True)
    # none of the malformed records are flagged -> nothing planned, no raise
    assert plan['articles'] == []
    assert plan['total_sections'] == 0


def test_planner_is_non_blocking_and_pure():
    mod = _import_orchestrator()
    state = _state([
        {'keyword': 'a', 'decision': 'NEEDS_CORRECTION',
         'advisory': {'quality_passed': False, 'consistency_passed': False,
                      'regenerate_sections': ['body']}},
    ])
    before = list(state['m10_advisories'])
    plan = mod.plan_regeneration(state, enabled=True)
    assert plan['blocking'] is False
    # input is not mutated
    assert state['m10_advisories'] == before


def test_orchestrator_exposes_planner():
    mod = _import_orchestrator()
    assert hasattr(mod, 'plan_regeneration')
    import inspect
    src = inspect.getsource(mod.plan_regeneration)
    assert 'enabled=False' in src
    assert 'No network, no LLM' in src

# end of M12 opt-in regeneration-planner tests
