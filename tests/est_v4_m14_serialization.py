"""Offline tests for the M14 regeneration-report serializer.

M14 turns the dict returned by the M13 reporter (summarize_regeneration_plan)
into a stable, JSON-serializable report and a JSON string helper. These tests
are deterministic and offline (no network, no LLM, no IO). They verify:
* a disabled / empty / missing / None summary serializes to a zero-work report;
* the fixed schema key and the caller-injected 'generated_at' are preserved;
* when enabled, counts and the section list are populated and ordered;
* sections are sorted by count desc then name (deterministic);
* the 'enabled' override wins over the summary's own flag;
* the JSON helper round-trips, sorts keys, and never raises;
* the serializer never mutates its input.
"""
import importlib
import json

import pytest


def _import_orchestrator():
    try:
        return importlib.import_module('orchestrator.orchestrator')
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f'orchestrator import unavailable: {exc}')


def _summary(enabled=True, **over):
    base = {
        'enabled': enabled,
        'articles_to_regenerate': 2,
        'total_sections': 3,
        'quality_flagged': 2,
        'consistency_flagged': 1,
        'both_flagged': 1,
        'top_section': 'body',
        'section_counts': {'body': 2, 'faq': 1},
    }
    base.update(over)
    return base


def test_disabled_summary_serializes_to_zero_work():
    mod = _import_orchestrator()
    r = mod.serialize_regeneration_report(_summary(enabled=False))
    assert r['schema'] == 'nexus14.regeneration_report.v1'
    assert r['enabled'] is False
    assert r['articles_to_regenerate'] == 0
    assert r['total_sections'] == 0
    assert r['sections'] == []
    assert r['top_section'] is None


def test_enabled_report_populates_counts_and_sections():
    mod = _import_orchestrator()
    r = mod.serialize_regeneration_report(_summary())
    assert r['enabled'] is True
    assert r['articles_to_regenerate'] == 2
    assert r['total_sections'] == 3
    assert r['quality_flagged'] == 2
    assert r['consistency_flagged'] == 1
    assert r['both_flagged'] == 1
    assert r['top_section'] == 'body'
    assert r['sections'] == [{'name': 'body', 'count': 2},
                             {'name': 'faq', 'count': 1}]


def test_sections_sorted_by_count_then_name():
    mod = _import_orchestrator()
    r = mod.serialize_regeneration_report(
        _summary(section_counts={'zzz': 1, 'aaa': 1, 'body': 3}))
    # body (3) first; then the two ties sorted by name: aaa before zzz
    assert [s['name'] for s in r['sections']] == ['body', 'aaa', 'zzz']


def test_generated_at_is_passed_through():
    mod = _import_orchestrator()
    r = mod.serialize_regeneration_report(_summary(), generated_at='2025-01-01T00:00:00Z')
    assert r['generated_at'] == '2025-01-01T00:00:00Z'
    # default is None (no internal clock call -> deterministic)
    r2 = mod.serialize_regeneration_report(_summary())
    assert r2['generated_at'] is None


def test_enabled_override_wins():
    mod = _import_orchestrator()
    r = mod.serialize_regeneration_report(_summary(enabled=False), enabled=True)
    assert r['enabled'] is True
    assert r['articles_to_regenerate'] == 2


def test_empty_missing_and_none_safe():
    mod = _import_orchestrator()
    assert mod.serialize_regeneration_report({}, enabled=True)['articles_to_regenerate'] == 0
    assert mod.serialize_regeneration_report(None, enabled=True)['total_sections'] == 0
    assert mod.serialize_regeneration_report(None)['enabled'] is False


def test_malformed_input_never_raises():
    mod = _import_orchestrator()
    bad = {'enabled': True, 'articles_to_regenerate': 'x', 'total_sections': None,
           'section_counts': {'body': 'nope', 'faq': 2}}
    r = mod.serialize_regeneration_report(bad)
    # non-int counters coerce to 0; bad section count coerces to 0
    assert r['articles_to_regenerate'] == 0
    assert r['total_sections'] == 0
    assert {'name': 'faq', 'count': 2} in r['sections']
    assert {'name': 'body', 'count': 0} in r['sections']


def test_json_helper_round_trips_and_sorts_keys():
    mod = _import_orchestrator()
    s = mod.regeneration_report_to_json(_summary(), generated_at='2025-01-01T00:00:00Z')
    assert isinstance(s, str)
    parsed = json.loads(s)
    assert parsed['schema'] == 'nexus14.regeneration_report.v1'
    assert parsed['enabled'] is True
    assert parsed['generated_at'] == '2025-01-01T00:00:00Z'
    assert parsed['sections'] == [{'name': 'body', 'count': 2},
                                  {'name': 'faq', 'count': 1}]
    # sort_keys=True -> top-level keys are sorted in the raw string
    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_json_helper_never_raises_on_bad_input():
    mod = _import_orchestrator()
    # a non-mapping summary still yields a valid JSON string
    s = mod.regeneration_report_to_json(12345, enabled=True)
    assert isinstance(s, str)
    json.loads(s)  # must be parseable


def test_serializer_does_not_mutate_input():
    mod = _import_orchestrator()
    summary = _summary()
    import copy
    before = copy.deepcopy(summary)
    mod.serialize_regeneration_report(summary)
    assert summary == before


def test_orchestrator_exposes_serializer():
    mod = _import_orchestrator()
    assert hasattr(mod, 'serialize_regeneration_report')
    assert hasattr(mod, 'regeneration_report_to_json')
    import inspect
    src = inspect.getsource(mod.serialize_regeneration_report)
    assert 'No network, no LLM' in src
    assert 'NEVER raises' in src
    assert "injected by the caller" in src


def test_end_to_end_planner_reporter_serializer():
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
    summary = mod.summarize_regeneration_plan(plan)
    report = mod.serialize_regeneration_report(summary, generated_at='2025-01-01T00:00:00Z')
    assert report['enabled'] is True
    assert report['articles_to_regenerate'] == 2
    assert report['total_sections'] == 3
    assert report['top_section'] == 'body'
    assert report['sections'][0] == {'name': 'body', 'count': 2}
    # and it serializes cleanly to JSON
    json.loads(mod.regeneration_report_to_json(summary, generated_at='2025-01-01T00:00:00Z'))

# end of M14 regeneration-report serializer tests
