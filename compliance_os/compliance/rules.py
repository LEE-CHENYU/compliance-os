"""Compliance rule engine — deterministic rules for tax/immigration obligations.

Rules are loaded from config/compliance_rules.yaml. Each rule maps a condition
(event type + threshold) to an action (create deadline, flag risk, etc.).

This is deliberately NOT LLM-powered. Legal and tax obligations must be computed
deterministically from verified rules, not inferred by a language model.
"""

from datetime import date
from pathlib import Path

import yaml

from compliance_os.compliance.schemas import ComplianceEvent, Deadline, ComplianceProfile
from compliance_os.settings import settings


class ComplianceRuleEngine:
    """Evaluates compliance rules against a user's profile and events."""

    def __init__(self):
        self.rules = self._load_rules()

    def _load_rules(self) -> list[dict]:
        """Load rules from YAML config."""
        config_path = settings.project_root / "config" / "compliance_rules.yaml"
        if config_path.exists():
            with open(config_path) as f:
                data = yaml.safe_load(f)
            return data.get("rules", [])
        return []

    def evaluate(
        self,
        profile: ComplianceProfile,
        events: list[ComplianceEvent] | None = None,
        as_of: date | None = None,
    ) -> list[dict]:
        """Evaluate all rules against a profile and return findings.

        Returns list of dicts with: rule_id, severity, message, action, sources.
        """
        ref_date = as_of or date.today()
        findings = []

        for rule in self.rules:
            result = self._evaluate_rule(rule, profile, events or [], ref_date)
            if result:
                findings.append(result)

        return findings

    def _evaluate_rule(
        self,
        rule: dict,
        profile: ComplianceProfile,
        events: list[ComplianceEvent],
        ref_date: date,
    ) -> dict | None:
        """Evaluate a single rule. Returns finding dict or None."""
        rule_type = rule.get("type")

        if rule_type == "threshold":
            return self._eval_threshold(rule, profile, events, ref_date)
        elif rule_type == "date_proximity":
            return self._eval_date_proximity(rule, profile, ref_date)
        elif rule_type == "missing_document":
            return self._eval_missing_document(rule, profile)

        return None

    def _eval_threshold(self, rule, profile, events, ref_date) -> dict | None:
        """Evaluate a threshold-based rule (e.g., foreign gifts > $100K)."""
        field = rule.get("field")
        threshold = rule.get("threshold", 0)
        event_type = rule.get("event_type")

        if event_type:
            year_events = [
                e for e in events
                if e.event_type == event_type and e.date.year == ref_date.year
            ]
            total = sum(e.amount or 0 for e in year_events)
            if total >= threshold:
                return {
                    "rule_id": rule["id"],
                    "severity": rule.get("severity", "high"),
                    "message": rule.get("message", "").format(
                        total=f"${total:,.0f}",
                        threshold=f"${threshold:,.0f}",
                        year=ref_date.year,
                    ),
                    "action": rule.get("action", ""),
                    "sources": rule.get("sources", []),
                }
        return None

    def _eval_date_proximity(self, rule, profile, ref_date) -> dict | None:
        """Evaluate a date-proximity rule (e.g., passport expiring within 90 days)."""
        field = rule.get("field")
        target_date = None

        if field == "visa_expiry":
            target_date = profile.visa_expiry
        elif field == "program_end_date":
            target_date = profile.program_end_date
        elif field == "i94_expiry":
            target_date = profile.i94_expiry

        if target_date:
            days_until = (target_date - ref_date).days
            window = rule.get("window_days", 90)
            if 0 < days_until <= window:
                return {
                    "rule_id": rule["id"],
                    "severity": rule.get("severity", "medium"),
                    "message": rule.get("message", "").format(
                        days=days_until,
                        date=target_date.isoformat(),
                    ),
                    "action": rule.get("action", ""),
                    "sources": rule.get("sources", []),
                }
        return None

    def _eval_missing_document(self, rule, profile) -> dict | None:
        """Check if a required document is missing."""
        required = rule.get("document_name")
        for doc in profile.documents:
            if doc.name == required and doc.obtained:
                return None
        return {
            "rule_id": rule["id"],
            "severity": rule.get("severity", "medium"),
            "message": rule.get("message", f"Missing required document: {required}"),
            "action": rule.get("action", ""),
            "sources": rule.get("sources", []),
        }
