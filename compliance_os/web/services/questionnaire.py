"""Config-backed questionnaire loading and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


QUESTIONNAIRE_DIR = Path(__file__).resolve().parents[3] / "config" / "questionnaires"
QUESTIONNAIRE_ALIASES = {
    "opt_execution": "opt_execution",
    "opt_advisory": "opt_execution",
}


@dataclass(slots=True)
class QuestionnaireEvaluation:
    recommendation: str
    advisory_reason: str | None
    execution_reason: str | None
    missing_required_items: list[str]
    complexity_flags: list[str]


def _normalize_service(service_sku: str) -> str:
    return QUESTIONNAIRE_ALIASES.get(service_sku, service_sku)


@lru_cache(maxsize=8)
def load_questionnaire_config(service_sku: str) -> dict[str, Any]:
    normalized = _normalize_service(service_sku)
    path = QUESTIONNAIRE_DIR / f"{normalized}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Questionnaire config not found for {service_sku}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid questionnaire config for {service_sku}")
    return data


def serialize_questionnaire_config(service_sku: str) -> dict[str, Any]:
    config = load_questionnaire_config(service_sku)
    return {
        "service": config.get("service", _normalize_service(service_sku)),
        "title": config.get("title"),
        "description": config.get("description"),
        "sections": list(config.get("sections") or []),
        "routing": dict(config.get("routing") or {}),
    }


def normalize_questionnaire_responses(
    responses: list[dict[str, Any]] | dict[str, Any],
) -> dict[str, bool]:
    if isinstance(responses, dict):
        return {str(key): bool(value) for key, value in responses.items()}

    normalized: dict[str, bool] = {}
    for item in responses:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id") or "").strip()
        if not item_id:
            continue
        normalized[item_id] = bool(item.get("checked"))
    return normalized


def evaluate(
    service_sku: str,
    responses: list[dict[str, Any]] | dict[str, Any],
) -> QuestionnaireEvaluation:
    config = load_questionnaire_config(service_sku)
    response_map = normalize_questionnaire_responses(responses)

    missing_required_items: list[str] = []
    complexity_flags: list[str] = []

    for section in list(config.get("sections") or []):
        if not isinstance(section, dict):
            continue
        rule = str(section.get("required_for_execution") or "").strip()
        items = [item for item in list(section.get("items") or []) if isinstance(item, dict)]
        if rule == "all":
            for item in items:
                item_id = str(item.get("id") or "").strip()
                if item_id and not response_map.get(item_id, False):
                    missing_required_items.append(str(item.get("label") or item_id))
        elif rule == "all_unchecked":
            for item in items:
                item_id = str(item.get("id") or "").strip()
                if item_id and response_map.get(item_id, False):
                    complexity_flags.append(str(item.get("label") or item_id))

    if missing_required_items or complexity_flags:
        advisory_parts = missing_required_items + complexity_flags
        advisory_reason = "Guardian recommends Advisory Mode because of: " + "; ".join(advisory_parts)
        return QuestionnaireEvaluation(
            recommendation="advisory",
            advisory_reason=advisory_reason,
            execution_reason=None,
            missing_required_items=missing_required_items,
            complexity_flags=complexity_flags,
        )

    return QuestionnaireEvaluation(
        recommendation="execution",
        advisory_reason=None,
        execution_reason="Guardian recommends Execution Mode because the required OPT readiness items are covered and no complexity flags were selected.",
        missing_required_items=[],
        complexity_flags=[],
    )
