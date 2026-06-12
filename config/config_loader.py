"""NEXUS-14 V3 — Configuration Loader
MoneyAbroadGuide.com Autonomous Newsroom

Provides ConfigLoader class for loading YAML configuration files.
Required by all agents for consistent config access.

Created: 2026-06-12
Fix for: ModuleNotFoundError: No module named 'config.config_loader'
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not available — config loading will use defaults")


# Default config path relative to this file
DEFAULT_CONFIG_PATH = Path(__file__).parent / "nexus14_v2_config.yaml"
FALLBACK_CONFIG_PATH = Path(__file__).parent / "config.yaml"


class ConfigLoader:
    """Loads and provides access to NEXUS-14 configuration.

    Supports:
    - nexus14_v2_config.yaml (primary — V3 config)
    - config.yaml (fallback)
    - Environment variable overrides
    - Dot-notation key access (e.g. 'agents.agent_01.timeout')

    Usage:
        from config.config_loader import ConfigLoader
        config = ConfigLoader()
        value = config.get('max_articles_per_batch', default=3)
        nested = config.get('agents.agent_01.timeout', default=60)
    """

    def __init__(self, config_path: Optional[str] = None):
        self._config: Optional[Dict[str, Any]] = None
        self._config_path = None

        if config_path:
            self._config_path = Path(config_path)
        elif DEFAULT_CONFIG_PATH.exists():
            self._config_path = DEFAULT_CONFIG_PATH
        elif FALLBACK_CONFIG_PATH.exists():
            self._config_path = FALLBACK_CONFIG_PATH
            logger.warning("Using fallback config: {}".format(FALLBACK_CONFIG_PATH))
        else:
            logger.error("No config file found. Expected: {}".format(DEFAULT_CONFIG_PATH))
            self._config_path = DEFAULT_CONFIG_PATH  # Will fail gracefully on load

    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file. Cached after first load."""
        if self._config is not None:
            return self._config

        if not YAML_AVAILABLE:
            logger.error("PyYAML not installed. Run: pip install pyyaml")
            self._config = self._get_env_defaults()
            return self._config

        try:
            with open(self._config_path, encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            logger.info("Config loaded from: {}".format(self._config_path))
        except FileNotFoundError:
            logger.error("Config file not found: {}".format(self._config_path))
            self._config = self._get_env_defaults()
        except yaml.YAMLError as e:
            logger.error("YAML parse error in {}: {}".format(self._config_path, e))
            self._config = self._get_env_defaults()

        # Apply environment variable overrides
        self._apply_env_overrides()
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key. Supports dot-notation for nested keys.

        Args:
            key: Simple key ('max_articles') or dot-notation ('agents.agent_01.timeout')
            default: Value to return if key not found

        Returns:
            Config value or default
        """
        config = self.load()

        if "." not in key:
            return config.get(key, default)

        # Traverse nested dict with dot notation
        parts = key.split(".")
        current = config
        for part in parts:
            if not isinstance(current, dict):
                return default
            current = current.get(part)
            if current is None:
                return default
        return current if current is not None else default

    def get_system_config(self) -> Dict[str, Any]:
        """Get the system-level config section."""
        config = self.load()
        return config.get("system", config.get("nexus14", {}))

    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """Get config for a specific agent.

        Args:
            agent_id: Agent identifier (e.g. 'agent_01', 'agent_17')

        Returns:
            Dict with agent config, or empty dict if not found
        """
        config = self.load()
        agents = config.get("agents", {})
        return agents.get(agent_id, {})

    def get_quality_gates(self) -> Dict[str, Any]:
        """Get quality gates configuration."""
        config = self.load()
        return config.get("quality_gates", {})

    def get_content_strategy(self) -> Dict[str, Any]:
        """Get content strategy (STANDARD/PILLAR thresholds)."""
        config = self.load()
        return config.get("content_strategy", {})

    def get_wordpress_config(self) -> Dict[str, Any]:
        """Get WordPress integration config."""
        config = self.load()
        return config.get("wordpress", {})

    def reload(self) -> Dict[str, Any]:
        """Force reload of config from disk."""
        self._config = None
        return self.load()

    def _get_env_defaults(self) -> Dict[str, Any]:
        """Build minimal config from environment variables as fallback."""
        return {
            "system": {
                "version": "V3",
                "max_articles_per_batch": int(os.getenv("MAX_ARTICLES_PER_BATCH", "3")),
                "max_articles_per_day": int(os.getenv("MAX_ARTICLES_PER_DAY", "6")),
                "quality_first": True,
            },
            "content_strategy": {
                "standard": {
                    "min_word_count": 3500,
                    "target_word_count": 5500,
                    "min_faq": 8,
                    "min_sources": 5,
                },
                "pillar": {
                    "min_word_count": 7000,
                    "target_word_count": 8500,
                    "min_faq": 15,
                    "min_sources": 10,
                },
            },
            "quality_gates": {
                "seo_score_min": 90,
                "eeat_score_min": 90,
                "revenue_score_min": 60,
            },
            "wordpress": {
                "url": os.getenv("WORDPRESS_URL", ""),
                "username": os.getenv("WORDPRESS_USERNAME", ""),
            },
            "apis": {
                "anthropic_key": os.getenv("ANTHROPIC_API_KEY", ""),
                "gemini_key": os.getenv("GEMINI_API_KEY", ""),
                "serpapi_key": os.getenv("SERPAPI_KEY", ""),
                "semrush_key": os.getenv("SEMRUSH_API_KEY", ""),
            },
        }

    def _apply_env_overrides(self):
        """Apply environment variable overrides to loaded config."""
        if self._config is None:
            return

        env_overrides = {
            "WORDPRESS_URL": ("wordpress", "url"),
            "WORDPRESS_USERNAME": ("wordpress", "username"),
            "MAX_ARTICLES_PER_BATCH": ("system", "max_articles_per_batch"),
        }

        for env_key, config_path in env_overrides.items():
            value = os.getenv(env_key)
            if value:
                section, key = config_path
                if section not in self._config:
                    self._config[section] = {}
                if key in ("max_articles_per_batch",):
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                self._config[section][key] = value

    def __repr__(self):
        return "ConfigLoader(path={}, loaded={})".format(
            self._config_path, self._config is not None)


# Module-level singleton for convenience
_default_loader: Optional[ConfigLoader] = None


def get_config(config_path: Optional[str] = None) -> ConfigLoader:
    """Get or create the default ConfigLoader singleton.

    Args:
        config_path: Optional path to config file. Uses default if None.

    Returns:
        ConfigLoader instance
    """
    global _default_loader
    if _default_loader is None or config_path is not None:
        _default_loader = ConfigLoader(config_path)
    return _default_loader
