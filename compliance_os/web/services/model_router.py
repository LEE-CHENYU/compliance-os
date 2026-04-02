"""Doc-type-aware model routing for extraction.

Reads config/model_routing.yaml to determine which provider+model to use
for a given document type. Falls back to the global LLM_PROVIDER config
if the routing file is missing or the provider's API key is not set.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "model_routing.yaml"


class ModelChoice(NamedTuple):
    provider: str  # "anthropic", "openai", "google"
    model: str     # e.g. "gpt-5.4-mini", "gemini-2.5-flash"


def _api_key_available(provider: str) -> bool:
    """Check whether the API key for a provider is configured."""
    keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    return bool(os.environ.get(keys.get(provider, "")))


@lru_cache(maxsize=1)
def _load_config() -> dict:
    """Load and cache the routing config. Returns empty dict on failure."""
    if not _CONFIG_PATH.exists():
        logger.warning("Model routing config not found at %s", _CONFIG_PATH)
        return {}
    try:
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        logger.warning("Failed to load model routing config: %s", exc)
        return {}


def reload_config() -> None:
    """Clear the cached config so the next call to resolve() re-reads the file."""
    _load_config.cache_clear()


def resolve(doc_type: str) -> ModelChoice | None:
    """Return the best (provider, model) for a document type.

    Returns None if routing config is missing or the required API key
    is not available — caller should fall back to default LLM_PROVIDER.
    """
    config = _load_config()
    if not config:
        return None

    # Check doc_type override first
    overrides = config.get("overrides") or {}
    entry = overrides.get(doc_type)
    if entry and _api_key_available(entry.get("provider", "")):
        return ModelChoice(provider=entry["provider"], model=entry["model"])

    # Fall back to default
    default = config.get("default")
    if default and _api_key_available(default.get("provider", "")):
        return ModelChoice(provider=default["provider"], model=default["model"])

    return None
