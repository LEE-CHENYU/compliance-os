"""Deterministic YAML-based compliance rule engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from dateutil.relativedelta import relativedelta


@dataclass
class FindingResult:
    rule_id: str
    severity: str
    category: str
    title: str
    action: str
    consequence: str
    immigration_impact: bool


@dataclass
class EvaluationContext:
    answers: dict[str, Any]
    extraction_a: dict[str, Any]
    extraction_b: dict[str, Any]
    comparisons: dict[str, dict[str, Any]]
    today: date = field(default_factory=date.today)


@dataclass
class Condition:
    field: str
    operator: str
    value: Any
    source: str

    def evaluate(self, ctx: EvaluationContext) -> bool:
        actual = self._resolve(ctx)

        if self.operator == "mismatch":
            if actual is None:
                return False
            return actual.get("status") in ("mismatch", "needs_review")

        if self.operator == "missing":
            return actual is None or actual == ""

        if self.operator == "eq":
            return actual == self.value

        if self.operator == "neq":
            return actual != self.value

        if self.operator == "gt":
            return self._compare_gt(actual, ctx.today)

        if self.operator == "lt":
            return self._compare_lt(actual, ctx.today)

        if self.operator == "in":
            return actual in self.value

        if self.operator == "contains":
            return isinstance(actual, list) and self.value in actual

        return False

    def _resolve(self, ctx: EvaluationContext) -> Any:
        if self.source == "answers":
            return ctx.answers.get(self.field)
        if self.source == "extraction_a":
            return ctx.extraction_a.get(self.field)
        if self.source == "extraction_b":
            return ctx.extraction_b.get(self.field)
        if self.source == "comparison":
            return ctx.comparisons.get(self.field)
        return None

    def _resolve_date_value(self, ref_date: date) -> date:
        if self.value == "today":
            return ref_date
        if isinstance(self.value, str) and "_months_ago" in self.value:
            n = int(self.value.split("_")[0])
            return ref_date - relativedelta(months=n)
        if isinstance(self.value, str) and "_days_from_now" in self.value:
            n = int(self.value.split("_")[0])
            return ref_date + relativedelta(days=n)
        return ref_date

    def _parse_date(self, val: Any) -> date | None:
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            try:
                return datetime.strptime(val, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def _compare_gt(self, actual: Any, today: date) -> bool:
        if isinstance(actual, (int, float)) and isinstance(self.value, (int, float)):
            return actual > self.value
        parsed = self._parse_date(actual)
        if parsed:
            return parsed > self._resolve_date_value(today)
        return False

    def _compare_lt(self, actual: Any, today: date) -> bool:
        if isinstance(actual, (int, float)) and isinstance(self.value, (int, float)):
            return actual < self.value
        parsed = self._parse_date(actual)
        if parsed:
            return parsed < self._resolve_date_value(today)
        return False


@dataclass
class Rule:
    id: str
    track: str
    type: str
    conditions: list[Condition]
    severity: str
    finding: dict[str, Any]


class RuleEngine:
    def __init__(self, rules: list[Rule], version: str = "0.0.0"):
        self.rules = rules
        self.version = version

    @classmethod
    def from_yaml(cls, path: str | Path) -> RuleEngine:
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        version = data.get("version", "0.0.0")
        rules = []
        for r in data.get("rules", []):
            conditions = [
                Condition(
                    field=c["field"],
                    operator=c["operator"],
                    value=c.get("value"),
                    source=c["source"],
                )
                for c in r.get("conditions", [])
            ]
            rules.append(
                Rule(
                    id=r["id"],
                    track=r["track"],
                    type=r["type"],
                    conditions=conditions,
                    severity=r["severity"],
                    finding=r["finding"],
                )
            )
        return cls(rules, version)

    def evaluate(self, ctx: EvaluationContext) -> list[FindingResult]:
        findings = []
        for rule in self.rules:
            if all(c.evaluate(ctx) for c in rule.conditions):
                findings.append(
                    FindingResult(
                        rule_id=rule.id,
                        severity=rule.severity,
                        category=rule.type,
                        title=rule.finding["title"],
                        action=rule.finding["action"],
                        consequence=rule.finding["consequence"],
                        immigration_impact=rule.finding.get("immigration_impact", False),
                    )
                )
        order = {"critical": 0, "warning": 1, "info": 2}
        findings.sort(key=lambda f: order.get(f.severity, 9))
        return findings
