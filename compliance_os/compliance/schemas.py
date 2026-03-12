"""Data models for the compliance engine.

These schemas define the core domain objects: deadlines, events, document
requirements, and their statuses. All compliance logic operates on these
types — no raw strings or dicts in the engine layer.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class DeadlineStatus(str, Enum):
    OVERDUE = "overdue"
    URGENT = "urgent"        # Due within 30 days
    UPCOMING = "upcoming"    # Due within 90 days
    LATER = "later"          # Due 90+ days out
    DONE = "done"


class DocumentRequirement(BaseModel):
    """A document needed for a compliance obligation."""
    name: str                           # e.g., "2024 FBAR (FinCEN Form 114)"
    form_number: str | None = None      # e.g., "FinCEN 114"
    description: str = ""
    obtained: bool = False
    file_path: str | None = None        # Path in document vault if obtained
    depends_on: list[str] = Field(default_factory=list)  # Other doc names


class Deadline(BaseModel):
    """A compliance deadline with status tracking."""
    id: str                             # Unique identifier
    title: str
    due_date: date
    category: str                       # tax, immigration, corporate, legal
    status: DeadlineStatus = DeadlineStatus.UPCOMING
    action: str = ""                    # What needs to be done
    documents: list[DocumentRequirement] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)  # File paths for context
    auto_extend_to: date | None = None  # e.g., FBAR auto-extends to Oct 15
    completed_date: date | None = None
    notes: str = ""

    def compute_status(self, as_of: date | None = None) -> DeadlineStatus:
        """Compute status based on current date."""
        if self.completed_date:
            return DeadlineStatus.DONE
        ref_date = as_of or date.today()
        effective_due = self.auto_extend_to or self.due_date
        days_until = (effective_due - ref_date).days
        if days_until < 0:
            return DeadlineStatus.OVERDUE
        elif days_until <= 30:
            return DeadlineStatus.URGENT
        elif days_until <= 90:
            return DeadlineStatus.UPCOMING
        return DeadlineStatus.LATER


class ComplianceEvent(BaseModel):
    """An event that may trigger compliance obligations.

    Examples: visa status change, receiving a wire transfer, starting
    employment, forming an LLC, crossing an account balance threshold.
    """
    id: str
    event_type: str                     # wire_received, status_change, employment_start, etc.
    date: date
    description: str = ""
    amount: float | None = None         # For financial events
    metadata: dict = Field(default_factory=dict)
    triggered_deadlines: list[str] = Field(default_factory=list)  # Deadline IDs


class ComplianceProfile(BaseModel):
    """A user's compliance profile — the core state model.

    This is the 'regulatory state model' that forms the product moat:
    visa status, tax residency, document inventory, and active obligations.
    """
    # Identity
    user_id: str
    name: str = ""

    # Immigration state
    visa_type: str | None = None        # F-1, H-1B, OPT, etc.
    visa_expiry: date | None = None
    i94_expiry: date | None = None
    sevis_number: str | None = None
    program_end_date: date | None = None

    # Tax state
    tax_residency: str | None = None    # nonresident, resident, dual-status
    first_us_entry: date | None = None
    exempt_years_remaining: int | None = None  # For F/J/M visa SPT exemption

    # Corporate
    entities: list[dict] = Field(default_factory=list)  # LLCs, corps, etc.

    # Tracking
    deadlines: list[Deadline] = Field(default_factory=list)
    events: list[ComplianceEvent] = Field(default_factory=list)
    documents: list[DocumentRequirement] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
