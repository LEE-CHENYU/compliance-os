"""Tests for the deadline engine — the deterministic compliance core."""

from datetime import date

from compliance_os.compliance.schemas import Deadline, DeadlineStatus, ComplianceEvent
from compliance_os.compliance.deadlines import DeadlineEngine


def test_compute_status_overdue():
    d = Deadline(
        id="test_1", title="Test", due_date=date(2025, 10, 15), category="tax",
    )
    assert d.compute_status(as_of=date(2026, 3, 11)) == DeadlineStatus.OVERDUE


def test_compute_status_urgent():
    d = Deadline(
        id="test_2", title="Test", due_date=date(2026, 4, 1), category="tax",
    )
    assert d.compute_status(as_of=date(2026, 3, 11)) == DeadlineStatus.URGENT


def test_compute_status_upcoming():
    d = Deadline(
        id="test_3", title="Test", due_date=date(2026, 5, 15), category="tax",
    )
    assert d.compute_status(as_of=date(2026, 3, 11)) == DeadlineStatus.UPCOMING


def test_compute_status_later():
    d = Deadline(
        id="test_4", title="Test", due_date=date(2027, 1, 1), category="tax",
    )
    assert d.compute_status(as_of=date(2026, 3, 11)) == DeadlineStatus.LATER


def test_compute_status_done():
    d = Deadline(
        id="test_5", title="Test", due_date=date(2026, 4, 15), category="tax",
        completed_date=date(2026, 3, 1),
    )
    assert d.compute_status(as_of=date(2026, 3, 11)) == DeadlineStatus.DONE


def test_auto_extend():
    """FBAR auto-extends from Apr 15 to Oct 15."""
    d = Deadline(
        id="fbar", title="FBAR", due_date=date(2026, 4, 15),
        auto_extend_to=date(2026, 10, 15), category="tax",
    )
    # After original due but before extension — should NOT be overdue
    assert d.compute_status(as_of=date(2026, 7, 1)) != DeadlineStatus.OVERDUE
    # Within 90 days of extension deadline — should be upcoming
    assert d.compute_status(as_of=date(2026, 8, 1)) == DeadlineStatus.UPCOMING


def test_engine_get_overdue():
    engine = DeadlineEngine()
    engine.add(Deadline(id="d1", title="Past", due_date=date(2025, 1, 1), category="tax"))
    engine.add(Deadline(id="d2", title="Future", due_date=date(2027, 1, 1), category="tax"))
    overdue = engine.get_overdue(as_of=date(2026, 3, 11))
    assert len(overdue) == 1
    assert overdue[0].id == "d1"


def test_engine_complete():
    engine = DeadlineEngine()
    engine.add(Deadline(id="d1", title="Test", due_date=date(2025, 1, 1), category="tax"))
    engine.complete("d1", completed_date=date(2026, 3, 1))
    assert engine.deadlines[0].status == DeadlineStatus.DONE
    assert len(engine.get_overdue(as_of=date(2026, 3, 11))) == 0


def test_foreign_gift_threshold():
    engine = DeadlineEngine()
    event = ComplianceEvent(
        id="wire_1",
        event_type="wire_received_foreign",
        date=date(2025, 8, 1),
        amount=150000,
        metadata={"cumulative_year_total": 150000},
    )
    new_deadlines = engine.process_event(event)
    assert len(new_deadlines) == 1
    assert new_deadlines[0].id == "form_3520_2025"
    assert new_deadlines[0].due_date == date(2026, 4, 15)


def test_foreign_gift_below_threshold():
    engine = DeadlineEngine()
    event = ComplianceEvent(
        id="wire_2",
        event_type="wire_received_foreign",
        date=date(2025, 3, 1),
        amount=50000,
        metadata={"cumulative_year_total": 50000},
    )
    new_deadlines = engine.process_event(event)
    assert len(new_deadlines) == 0
