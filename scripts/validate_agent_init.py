#!/usr/bin/env python3
"""
NEXUS-14 Agent Init Validation
Lightweight smoke test for the fix/nexus14-agent-compatibility repair.
Init-only: no network, no secrets, no publishing.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

results = []


def record(name, ok, err=""):
    status = "PASS" if ok else "FAIL"
    results.append((name, status, err))
    line = "[%s] %s" % (status, name)
    if err:
        line += " :: " + err
    print(line, flush=True)


config = {
    "llm_provider": "anthropic",
    "anthropic_api_key": "test-dummy",
    "openai_api_key": "test-dummy",
    "gemini_api_key": "test-dummy",
    "output_dir": "output",
    "eeat_threshold": 90,
}

orch_mod = None
try:
    import orchestrator.orchestrator as orch_mod
    record("import orchestrator.orchestrator", True)
except Exception as e:
    record("import orchestrator.orchestrator", False, repr(e))
    traceback.print_exc()

try:
    from agents.agent_06_eeat_validator import EEATValidatorAgent  # noqa: F401
    record("import EEATValidatorAgent", True)
except Exception as e:
    record("import EEATValidatorAgent", False, repr(e))
    traceback.print_exc()

if orch_mod is not None:
    try:
        orch_mod.Orchestrator(config)
        record("Orchestrator initializes", True)
    except Exception as e:
        record("Orchestrator initializes", False, repr(e))
        traceback.print_exc()

services = {}
try:
    from services.llm_service import LLMService
    from services.storage_service import StorageService
    from services.search_service import SearchService
    from services.image_service import ImageService
    services["llm"] = LLMService(config)
    services["storage"] = StorageService(config)
    services["search"] = SearchService(config)
    services["image"] = ImageService(config)
except Exception as e:
    print("[WARN] Could not pre-build services: %r" % (e,), flush=True)

agent_targets = [
    ("Agent 01", "agents.agent_01_seo_research", "SEOResearchAgent"),
    ("Agent 02", "agents.agent_02_keyword_validation", "KeywordValidationAgent"),
    ("Agent 05", "agents.agent_05_fact_checker", "FactCheckerAgent"),
    ("Agent 06", "agents.agent_06_eeat_validator", "EEATValidatorAgent"),
    ("Agent 07", "agents.agent_07_internal_linking", "InternalLinkingAgent"),
    ("Agent 08", "agents.agent_08_affiliate_optimizer", "AffiliateOptimizerAgent"),
    ("Agent 09", "agents.agent_09_image_prompt_generator", "ImagePromptGeneratorAgent"),
    ("Agent 10", "agents.agent_10_image_production", "ImageProductionAgent"),
]

for label, modpath, clsname in agent_targets:
    try:
        mod = __import__(modpath, fromlist=[clsname])
        cls = getattr(mod, clsname)
        kwargs = {
            "config": config,
            "llm_service": services.get("llm"),
            "storage_service": services.get("storage"),
        }
        if clsname == "SEOResearchAgent":
            kwargs["search_service"] = services.get("search")
        if clsname == "ImageProductionAgent":
            kwargs["image_service"] = services.get("image")
        cls(**kwargs)
        record(label + " initializes", True)
    except Exception as e:
        record(label + " initializes", False, repr(e))
        traceback.print_exc()

print("", flush=True)
print("================ SUMMARY ================", flush=True)
for name, status, err in results:
    print("%-4s  %s" % (status, name), flush=True)
print("=========================================", flush=True)

failed = [r for r in results if r[1] == "FAIL"]
if failed:
    print("%d check(s) FAILED" % len(failed), flush=True)
    sys.exit(1)
print("ALL CHECKS PASSED", flush=True)
sys.exit(0)
