"""NEXUS-14 V3 — Configuration Loader
MoneyAbroadGuide.com Autonomous Newsroom

Provides ConfigLoader class for loading YAML configuration files.
Required by all agents for consistent config access.

Created: 2026-06-12
Fix for: ModuleNotFoundError: No module named 'config.config_loader'
Fix v2:  Supports both ConfigLoader.load() (class method) and
         ConfigLoader().load() (instance method) usage patterns.
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

# Module-level cache for class-method usage pattern
_cached_config: Optional[Dict[str, Any]] = None


def _load_yaml_file(config_path: Path) -> Dict[str, Any]:
    """Internal helper to load a YAML file."""
    global _cached_config

    if not YAML_AVAILABLE:
        logger.error("PyYAML not installed. Run: pip install pyyaml")
        return _get_env_defaults()

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        logger.info("Config loaded from: {}".format(config_path))
        return config
    except FileNotFoundError:
        logger.error("Config file not found: {}".format(config_path))
        return _get_env_defaults()
    except Exception as e:
        logger.error("Error loading config {}: {}".format(config_path, e))
        return _get_env_defaults()


def _get_env_defaults() -> Dict[str, Any]:
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


class ConfigLoader:
    """Loads and provides access to NEXUS-14 configuration.

    Supports BOTH usage patterns found in agents:

    Pattern 1 - Class method (used by some agents):
        config = ConfigLoader.load()
        value = config.get('max_articles_per_batch', 3)

    Pattern 2 - Instance method (standard OOP):
        loader = ConfigLoader()
        value = loader.get('max_articles_per_batch', 3)

    Supports dot-notation for nested keys:
        value = loader.get('agents.agent_01.timeout', 60)
    """

    # Class-level config cache (shared across all instances)
    _class_config: Optional[Dict[str, Any]] = None
    _config_file_path: Optional[Path] = None

    def __init__(self, config_path: Optional[str] = None):
        self._instance_config: Optional[Dict[str, Any]] = None

        if config_path:
            self._instance_config_path = Path(config_path)
        elif DEFAULT_CONFIG_PATH.exists():
            self._instance_config_path = DEFAULT_CONFIG_PATH
        elif FALLBACK_CONFIG_PATH.exists():
            self._instance_config_path = FALLBACK_CONFIG_PATH
        else:
            self._instance_config_path = DEFAULT_CONFIG_PATH

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "ConfigLoader":
        """Load configuration. Works as classmethod OR instance method.

        Can be called as:
          config = ConfigLoader.load()          # class method -> returns instance
          config = ConfigLoader.load(path)      # class method with path
          config = ConfigLoader().load()        # instance method -> returns self

        Returns:
            ConfigLoader instance with config loaded (supports .get() calls)
        """
        if config_path:
            path = Path(config_path)
        elif DEFAULT_CONFIG_PATH.exists():
            path = DEFAULT_CONFIG_PATH
        elif FALLBACK_CONFIG_PATH.exists():
            path = FALLBACK_CONFIG_PATH
        else:
            path = DEFAULT_CONFIG_PATH

        instance = cls(str(path))
        if instance._instance_config is None:
            instance._instance_config = _load_yaml_file(path)
        return instance

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key. Supports dot-notation for nested keys.

        Args:
            key: Simple key ('max_articles') or dot-notation ('agents.agent_01.timeout')
            default: Value to return if key not found

        Returns:
            Config value or default
        """
        if self._instance_config is None:
            self._instance_config = _load_yaml_file(self._instance_config_path)

        config = self._instance_config

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
        if self._instance_config is None:
            self._instance_config = _load_yaml_file(self._instance_config_path)
        return self._instance_config.get("system", self._instance_config.get("nexus14", {}))

    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """Get config for a specific agent."""
        if self._instance_config is None:
            self._instance_config = _load_yaml_file(self._instance_config_path)
        agents = self._instance_config.get("agents", {})
        return agents.get(agent_id, {})

    def get_quality_gates(self) -> Dict[str, Any]:
        """Get quality gates configuration."""
        if self._instance_config is None:
            self._instance_config = _load_yaml_file(self._instance_config_path)
        return self._instance_config.get("quality_gates", {})

    def get_content_strategy(self) -> Dict[str, Any]:
        """Get content strategy (STANDARD/PILLAR thresholds)."""
        if self._instance_config is None:
            self._instance_config = _load_yaml_file(self._instance_config_path)
        return self._instance_config.get("content_strategy", {})

    def get_wordpress_config(self) -> Dict[str, Any]:
        """Get WordPress integration config."""
        if self._instance_config is None:
            self._instance_config = _load_yaml_file(self._instance_config_path)
        return self._instance_config.get("wordpress", {})

    def reload(self) -> "ConfigLoader":
        """Force reload of config from disk."""
        self._instance_config = None
        return self

    def __repr__(self):
        return "ConfigLoader(path={}, loaded={})".format(
            self._instance_config_path, self._instance_config is not None)


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
