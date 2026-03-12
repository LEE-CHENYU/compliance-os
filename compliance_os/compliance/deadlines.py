"""Deadline engine — deterministic deadline tracking and alerting.

This is part of the compliance engine's critical path. All logic here is
rule-based (no LLM) to ensure correctness for legal/tax deadlines.
"""

from datetime import date

from compliance_os.compliance.schemas import (
    Deadline,
    DeadlineStatus,
    ComplianceEvent,
)


class DeadlineEngine:
    """Manages deadlines: creation, status computation, event-triggered updates."""

    def __init__(self):
        self.deadlines: list[Deadline] = []

    def add(self, deadline: Deadline) -> None:
        self.deadlines.append(deadline)

    def remove(self, deadline_id: str) -> None:
        self.deadlines = [d for d in self.deadlines if d.id != deadline_id]

    def complete(self, deadline_id: str, completed_date: date | None = None) -> None:
        for d in self.deadlines:
            if d.id == deadline_id:
                d.completed_date = completed_date or date.today()
                d.status = DeadlineStatus.DONE
                return

    def refresh_statuses(self, as_of: date | None = None) -> None:
        """Recompute all deadline statuses based on current date."""
        for d in self.deadlines:
            d.status = d.compute_status(as_of)

    def get_overdue(self, as_of: date | None = None) -> list[Deadline]:
        self.refresh_statuses(as_of)
        return [d for d in self.deadlines if d.status == DeadlineStatus.OVERDUE]

    def get_urgent(self, as_of: date | None = None) -> list[Deadline]:
        self.refresh_statuses(as_of)
        return [d for d in self.deadlines if d.status == DeadlineStatus.URGENT]

    def get_upcoming(self, as_of: date | None = None) -> list[Deadline]:
        self.refresh_statuses(as_of)
        return [
            d for d in self.deadlines
            if d.status in (DeadlineStatus.URGENT, DeadlineStatus.UPCOMING)
        ]

    def get_by_category(self, category: str) -> list[Deadline]:
        return [d for d in self.deadlines if d.category == category]

    def process_event(self, event: ComplianceEvent) -> list[Deadline]:
        """Process a compliance event and return any newly triggered deadlines.

        This is the core of the deterministic compliance engine — events
        (wire transfers, status changes, etc.) trigger new deadlines based
        on rules.
        """
        new_deadlines = []

        if event.event_type == "wire_received_foreign":
            # Foreign gift tracking: if cumulative gifts from foreign persons
            # exceed $100K in a calendar year, Form 3520 is required
            new_deadlines.extend(
                self._check_foreign_gift_threshold(event)
            )

        elif event.event_type == "account_balance_exceeded":
            # FBAR threshold: if aggregate foreign account balance > $10K
            # at any point during the year, FBAR is required
            new_deadlines.extend(
                self._check_fbar_threshold(event)
            )

        elif event.event_type == "employment_start":
            # New employment may trigger CPT/OPT reporting, I-9, etc.
            new_deadlines.extend(
                self._check_employment_triggers(event)
            )

        elif event.event_type == "visa_status_change":
            # Status change may affect tax residency, work authorization, etc.
            new_deadlines.extend(
                self._check_status_change_triggers(event)
            )

        for d in new_deadlines:
            event.triggered_deadlines.append(d.id)
            self.add(d)

        return new_deadlines

    def _check_foreign_gift_threshold(self, event: ComplianceEvent) -> list[Deadline]:
        """Check if foreign gifts exceed $100K threshold for Form 3520."""
        # Placeholder — in production, this aggregates all wire_received_foreign
        # events for the calendar year and checks against $100,000
        year = event.date.year
        threshold = 100_000
        cumulative = event.metadata.get("cumulative_year_total", 0)

        if cumulative >= threshold:
            return [Deadline(
                id=f"form_3520_{year}",
                title=f"Form 3520 — {year} Foreign Gifts (>${threshold:,.0f})",
                due_date=date(year + 1, 4, 15),
                auto_extend_to=date(year + 1, 10, 15),
                category="tax",
                action=f"File Form 3520 reporting foreign gifts totaling ${cumulative:,.0f}",
            )]
        return []

    def _check_fbar_threshold(self, event: ComplianceEvent) -> list[Deadline]:
        """Check if foreign account balances exceed $10K for FBAR."""
        year = event.date.year
        return [Deadline(
            id=f"fbar_{year}",
            title=f"{year} FBAR (FinCEN Form 114)",
            due_date=date(year + 1, 4, 15),
            auto_extend_to=date(year + 1, 10, 15),
            category="tax",
            action="File via BSA E-Filing (bsaefiling.fincen.gov)",
        )]

    def _check_employment_triggers(self, event: ComplianceEvent) -> list[Deadline]:
        """Check employment-related compliance triggers."""
        # Placeholder for CPT/OPT reporting, I-9 verification, etc.
        return []

    def _check_status_change_triggers(self, event: ComplianceEvent) -> list[Deadline]:
        """Check visa status change triggers."""
        # Placeholder for status-change-driven obligations
        return []

    def summary(self, as_of: date | None = None) -> dict:
        """Return a summary of all deadline statuses."""
        self.refresh_statuses(as_of)
        counts = {}
        for status in DeadlineStatus:
            items = [d for d in self.deadlines if d.status == status]
            counts[status.value] = len(items)
        return {
            "total": len(self.deadlines),
            "by_status": counts,
            "overdue": [
                {"id": d.id, "title": d.title, "due": str(d.due_date)}
                for d in self.deadlines if d.status == DeadlineStatus.OVERDUE
            ],
        }
