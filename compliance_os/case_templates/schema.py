"""Template schema: Slot + Template dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Slot:
    id: str
    section: str
    section_name: str
    title: str
    description: str = ""
    required: bool = True
    doc_types: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    filename_patterns: list[str] = field(default_factory=list)
    # Chronological order within section (for lineage verification).
    # Slots with order < 0 are not lineage-tracked.
    order: int = -1
    # Optional phase label for employment/status timelines.
    phase: str = ""


@dataclass
class Template:
    id: str
    name: str
    description: str
    sections: dict[str, str]  # section_code -> section_name
    slots: list[Slot]

    def required_slots(self) -> list[Slot]:
        return [s for s in self.slots if s.required]

    def slot_by_id(self, slot_id: str) -> Slot | None:
        for s in self.slots:
            if s.id == slot_id:
                return s
        return None

    def slots_by_section(self, section: str) -> list[Slot]:
        return [s for s in self.slots if s.section == section]
