"""
NEXUS-14: Main Orchestrator
Coordinates all 14 agents in the production pipeline.
"""

import asyncio
import inspect
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from agents.agent_01_seo_research import SEOResearchAgent
from agents.agent_02_keyword_validation import KeywordValidationAgent
from agents.agent_03_content_planner import ContentPlannerAgent
from agents.agent_04_article_writer import ArticleWriterAgent
from agents.agent_05_fact_checker import FactCheckerAgent
from agents.agent_06_eeat_validator import EEATValidatorAgent
from agents.agent_07_internal_linking import InternalLinkingAgent
from agents.agent_08_affiliate_optimizer import AffiliateOptimizerAgent
from agents.agent_09_image_prompt_generator import ImagePromptGeneratorAgent
from agents.agent_10_image_production import ImageProductionAgent
from agents.agent_11_wordpress_integration import WordPressIntegrationAgent
from agents.agent_12_quality_assurance import QualityAssuranceAgent
from agents.agent_13_chief_editor import ChiefEditorAgent
from agents.agent_14_production_director import ProductionDirectorAgent

from services.llm_service import LLMService
from services.search_service import SearchService
from services.wordpress_service import WordPressService
from services.image_service import ImageService
from services.email_service import EmailService
from services.storage_service import StorageService

logger = logging.getLogger("NEXUS14.Orchestrator")

def _agent_display_name(agent, agent_id: str) -> str:
    """Return a human-readable agent name, tolerating legacy agents without AGENT_NAME."""
    return getattr(agent, "AGENT_NAME", None) or getattr(agent, "AGENT_ID", None) or type(agent).__name__ or agent_id

def _construct_agent(agent_cls, **candidate_kwargs):
    """Instantiate an agent passing only the kwargs its __init__ accepts.

    Supports, transparently:
    * BaseAgent constructors: __init__(self, config, llm_service, storage_service, ...)
    * Legacy constructors: __init__(self, config=None)
    * Constructors that accept **kwargs (everything is forwarded)

    Uses inspect.signature() to filter the candidate kwargs down to the
    names the target constructor actually declares, so passing a superset
    of services never raises TypeError for agents that ignore them.
    """
    try:
        sig = inspect.signature(agent_cls.__init__)
    except (ValueError, TypeError):
        # No introspectable signature: best-effort no-arg construction.
        return agent_cls()

    params = sig.parameters
    accepts_var_kw = any(p.kind == p.VAR_KEYWORD for p in params.values())
    if accepts_var_kw:
        return agent_cls(**candidate_kwargs)

    accepted = {k: v for k, v in candidate_kwargs.items() if k in params}
    return agent_cls(**accepted)

async def _invoke_agent(agent, context: Dict) -> Any:
    """Compatibility dispatch supporting BaseAgent and legacy agents.

    Handles, in order of preference:
    * BaseAgent-style: async def run(self, context=None)
    * No-arg run: def run(self) / async def run(self)
    * Legacy callable agent: agent(context) or agent()
    Uses inspect.signature() to decide whether to pass the context argument,
    and awaits the result only when it is awaitable.
    """
    runner = getattr(agent, "run", None)
    if runner is None:
        if callable(agent):
            runner = agent
        else:
            raise AttributeError(
                f"Agent {type(agent).__name__} exposes no run() method and is not callable"
            )

    try:
        sig = inspect.signature(runner)
        # Count positional params the runner can accept (excluding bound self).
        accepts_context = any(
            p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.VAR_POSITIONAL)
            for name, p in sig.parameters.items()
        )
    except (ValueError, TypeError):
        # Builtins / C-callables without introspectable signatures: assume context-accepting.
        accepts_context = True

    result = runner(context) if accepts_context else runner()

    if inspect.isawaitable(result):
        result = await result
    return result

class Orchestrator:
    """
    Main NEXUS-14 Orchestrator

    Coordinates all 14 specialized agents through the complete
    content production pipeline from SEO research to WordPress publication.

    Pipeline:
    01 SEO Research -> 02 Validation -> 03 Planning -> 04 Writing
    -> 05 Fact Check -> 06 EEAT -> 07 Linking -> 08 Affiliate
    -> 09 Image Prompts -> 10 Images -> 11 WordPress -> 12 QA
    -> 13 Chief Editor -> 14 Production Director
    """

    def __init__(self, config: Dict):
        self.config = config
        self.run_id = f"nexus14_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Initializing NEXUS-14 Orchestrator (Run ID: {self.run_id})")

        # Initialize services
        self.llm = LLMService(config)
        self.search = SearchService(config)
        self.wordpress = WordPressService(config)
        self.image_service = ImageService(config)
        self.email = EmailService(config)
        self.storage = StorageService(config)

        # Initialize agents
        self._init_agents()

        # Pipeline state
        self.pipeline_state = {
            "run_id": self.run_id,
            "start_time": None,
            "current_agent": None,
            "completed_agents": [],
            "failed_agents": [],
            "articles_produced": [],
            "articles_validated": [],
            "articles_rejected": []
        }

    def _init_agents(self):
        """Initialize all 14 agents.

        Each agent is built via _construct_agent(), which filters the full
        superset of available services down to the kwargs each constructor
        actually accepts. This lets BaseAgent agents (config + services) and
        legacy agents (config only) coexist without TypeError.
        """
        services = {
            "config": self.config,
            "llm_service": self.llm,
            "storage_service": self.storage,
            "search_service": self.search,
            "wordpress_service": self.wordpress,
            "image_service": self.image_service,
            "email_service": self.email,
        }

        agent_classes = {
            "01": SEOResearchAgent,
            "02": KeywordValidationAgent,
            "03": ContentPlannerAgent,
            "04": ArticleWriterAgent,
            "05": FactCheckerAgent,
            "06": EEATValidatorAgent,
            "07": InternalLinkingAgent,
            "08": AffiliateOptimizerAgent,
            "09": ImagePromptGeneratorAgent,
            "10": ImageProductionAgent,
            "11": WordPressIntegrationAgent,
            "12": QualityAssuranceAgent,
            "13": ChiefEditorAgent,
            "14": ProductionDirectorAgent,
        }

        self.agents = {}
        for agent_id, agent_cls in agent_classes.items():
            try:
                self.agents[agent_id] = _construct_agent(agent_cls, **services)
            except Exception as e:
                logger.error(f"Failed to construct Agent {agent_id} ({agent_cls.__name__}): {e}")
                raise

        logger.info(f"Initialized {len(self.agents)} agents")

    async def run_full_pipeline(self) -> Dict:
        """Run the complete production pipeline."""
        self.pipeline_state["start_time"] = datetime.utcnow().isoformat()

        logger.info("=" * 60)
        logger.info(" NEXUS-14 FULL PIPELINE STARTING")
        logger.info(f" Run ID: {self.run_id}")
        logger.info("=" * 60)

        try:
            # Stage 1: Research Phase
            context = {}
            context = await self._run_agent("01", context)
            context = await self._run_agent("02", context)
            context = await self._run_agent("03", context)

            # Stage 2: Production Phase (for each validated topic)
            validated_topics = context.get("validated_topics", {}).get("topics", [])

            for topic in validated_topics[:self.config.get("articles_per_batch", 5)]:
                try:
                    article_context = {**context, "current_topic": topic}
                    article_context = await self._run_article_pipeline(article_context)
                    self.pipeline_state["articles_produced"].append(topic.get("keyword"))
                except Exception as e:
                    logger.error(f"Failed to produce article for '{topic.get('keyword')}': {e}")
                    self.pipeline_state["articles_rejected"].append(topic.get("keyword"))

            # Stage 3: Quality & Publishing Phase
            context = await self._run_agent("14", context)

            logger.info("=" * 60)
            logger.info(" NEXUS-14 PIPELINE COMPLETE")
            logger.info(f" Articles produced: {len(self.pipeline_state['articles_produced'])}")
            logger.info(f" Articles rejected: {len(self.pipeline_state['articles_rejected'])}")
            logger.info("=" * 60)

            return self.pipeline_state

        except Exception as e:
            logger.critical(f"Pipeline failed: {e}", exc_info=True)
            self.pipeline_state["error"] = str(e)
            raise

    async def _run_article_pipeline(self, context: Dict) -> Dict:
        """Run the article production pipeline for a single topic."""
        # Writing pipeline
        context = await self._run_agent("04", context)
        context = await self._run_agent("05", context)
        context = await self._run_agent("06", context)
        context = await self._run_agent("07", context)
        context = await self._run_agent("08", context)

        # Media pipeline (parallel with article)
        context = await self._run_agent("09", context)
        context = await self._run_agent("10", context)

        # Integration & QA
        context = await self._run_agent("11", context)
        context = await self._run_agent("12", context)

        # Editorial decision
        context = await self._run_agent("13", context)

        # Check editor decision
        editor_report = context.get("editor_report", {})
        decision = editor_report.get("decision", "NEEDS_CORRECTION")

        if decision == "READY_TO_PUBLISH":
            self.pipeline_state["articles_validated"].append(
                context.get("current_topic", {}).get("keyword")
            )
        elif decision == "REJECTED":
            self.pipeline_state["articles_rejected"].append(
                context.get("current_topic", {}).get("keyword")
            )

        return context

    async def _run_agent(self, agent_id: str, context: Dict) -> Dict:
        """Run a specific agent and update context.

        Uses the _invoke_agent compatibility dispatcher so both BaseAgent
        agents (async run(context)) and legacy agents are supported.
        """
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        logger.info(f"Running Agent {agent_id}: {_agent_display_name(agent, agent_id)}")
        self.pipeline_state["current_agent"] = agent_id

        try:
            result = await _invoke_agent(agent, context)
            context[f"agent_{agent_id}_result"] = result
            self.pipeline_state["completed_agents"].append(agent_id)
            logger.info(f"Agent {agent_id} completed successfully")
            return context

        except Exception as e:
            logger.error(f"Agent {agent_id} failed: {e}", exc_info=True)
            self.pipeline_state["failed_agents"].append({
                "agent_id": agent_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            raise

    async def run_batch(self, batch_id: int) -> Dict:
        """Run a specific production batch."""
        logger.info(f"Running Batch #{batch_id}")
        return await self.run_full_pipeline()

    def get_pipeline_state(self) -> Dict:
        """Get current pipeline state."""
        return self.pipeline_state
