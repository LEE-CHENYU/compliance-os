"""Paths, JSON I/O, and hashing helpers for the rubric loop."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# All paths are relative to the repo root, discovered by walking up from this file.
# scripts/rubric/io.py -> scripts/rubric -> scripts -> <repo root>
PROJECT_ROOT = Path(__file__).resolve().parents[2]

FIXTURE_DIR = PROJECT_ROOT / "scripts" / "rubric_fixtures"
GOLDENS_DIR = FIXTURE_DIR / "goldens"
CACHE_ROOT = PROJECT_ROOT / "scripts" / "rubric_cache"
EVAL_CACHE_DIR = CACHE_ROOT / "evaluate"
JUDGE_CACHE_DIR = CACHE_ROOT / "judge"
OUT_DIR = PROJECT_ROOT / "out"

CONFIG_RULES_DIR = PROJECT_ROOT / "config" / "rules"
CONFIG_RUBRIC_DIR = PROJECT_ROOT / "config" / "rubric"


def ensure_dirs(*paths: Path) -> None:
    """Create each directory if missing. Idempotent."""
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def sha256_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_of_obj(obj: Any) -> str:
    """Stable hash of a JSON-serializable object (key order ignored)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return sha256_of_text(canonical)


def sha256_of_file(path: Path) -> str:
    return sha256_of_text(path.read_text())


def save_json(path: Path, obj: Any) -> None:
    """Write obj as pretty-printed JSON to path, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())
