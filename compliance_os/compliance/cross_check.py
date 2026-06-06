"""Chain-aware local compliance cross-check.

Reads the on-device facts SoT + each document's extracted fields and reports
cross-document fact mismatches, missing-from-chain documents, and deadline
risks. Deterministic and local — no model call, no network. Chain knowledge
lives in config/document_chains.yaml; this module is chain-agnostic.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG = Path(__file__).resolve().parents[2] / "config" / "document_chains.yaml"


@lru_cache(maxsize=1)
def load_chains() -> dict:
    """Load the chain spec. Cached; call load_chains.cache_clear() in tests
    that write a custom config."""
    with open(_CONFIG) as f:
        return (yaml.safe_load(f) or {}).get("chains", {})
