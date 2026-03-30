"""
SENTINEL2 — Configuration Loader
Loads config.yaml and models.yaml with singleton pattern.
"""

import os
import logging
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

logger = logging.getLogger("sentinel2.config")

# Resolve project root (two levels up from src/utils/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

_config: Optional[dict] = None
_models: Optional[dict] = None


def _find_env_file() -> Optional[Path]:
    """Locate .env file in project root."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        return env_path
    return None


def get_config() -> dict:
    """
    Load and return the main pipeline config (singleton).
    Also loads .env variables into the environment.
    """
    global _config
    if _config is not None:
        return _config

    # Load .env
    env_file = _find_env_file()
    if env_file:
        load_dotenv(env_file, override=True)
        logger.info(f"Loaded environment from {env_file}")

    # Load config.yaml
    config_path = CONFIG_DIR / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)

    logger.info(f"Loaded config from {config_path}")
    return _config


def get_models_config() -> dict:
    """Load and return the model routing config (singleton)."""
    global _models
    if _models is not None:
        return _models

    models_path = CONFIG_DIR / "models.yaml"
    if not models_path.exists():
        raise FileNotFoundError(f"Models config not found: {models_path}")

    with open(models_path, "r", encoding="utf-8") as f:
        _models = yaml.safe_load(f)

    logger.info(f"Loaded models config from {models_path}")
    return _models


def get_model_for_component(component: str) -> dict:
    """
    Get the model config for a specific pipeline component.

    Args:
        component: Key from models.yaml routing section
                   (e.g., 'cma', 'processor', 'analysis_group_1')

    Returns:
        Dict with keys: model, provider, temperature, max_tokens
    """
    models = get_models_config()
    routing = models.get("routing", {})
    if component not in routing:
        raise KeyError(f"No model routing defined for component: {component}")
    return routing[component]


def get_project_root() -> Path:
    """Return the absolute project root path."""
    return PROJECT_ROOT


def get_reports_dir(report_type: str = "daily") -> Path:
    """Get the reports directory for a given type."""
    config = get_config()
    reports_cfg = config.get("reports", {})
    dir_key = f"{report_type}_dir"
    rel_path = reports_cfg.get(dir_key, f"reports/{report_type}")
    abs_path = PROJECT_ROOT / rel_path
    abs_path.mkdir(parents=True, exist_ok=True)
    return abs_path


def get_prompts_dir() -> Path:
    """Get the prompts directory."""
    return PROJECT_ROOT / "prompts"


def get_pirs_dir() -> Path:
    """Get the PIRs directory."""
    return PROJECT_ROOT / "pirs"
