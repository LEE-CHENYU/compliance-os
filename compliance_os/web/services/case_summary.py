"""Case summary synthesis for share pages.

Parses an optional `00_CASE_BRIEF_*.txt` in the folder root to extract
structured key facts (parties, timeline, issues) and combines it with
the template match report. Falls back gracefully when no brief exists.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from compliance_os.case_templates.matcher import Report
from compliance_os.case_templates.schema import Template


@dataclass
class KeyFact:
    label: str
    value: str


@dataclass
class TimelinePhase:
    name: str
    period: str
    detail: str = ""


@dataclass
class KnownIssue:
    id: str
    title: str
    severity: str = "info"  # info, warning, critical
    summary: str = ""


@dataclass
class CaseSummary:
    title: str
    prepared_for: str = ""
    prepared_by: str = ""
    date: str = ""
    overview: str = ""
    key_facts: list[KeyFact] = field(default_factory=list)
    timeline: list[TimelinePhase] = field(default_factory=list)
    issues: list[KnownIssue] = field(default_factory=list)
    pending_items: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "prepared_for": self.prepared_for,
            "prepared_by": self.prepared_by,
            "date": self.date,
            "overview": self.overview,
            "key_facts": [asdict(f) for f in self.key_facts],
            "timeline": [asdict(p) for p in self.timeline],
            "issues": [asdict(i) for i in self.issues],
            "pending_items": self.pending_items,
            "open_questions": self.open_questions,
        }


def _find_brief(folder: Path) -> Path | None:
    for name in (
        "00_CASE_BRIEF", "CASE_BRIEF", "case_brief",
        "00_CASE_SUMMARY", "CASE_SUMMARY", "case_summary",
    ):
        matches = list(folder.glob(f"{name}*.txt"))
        if matches:
            return matches[0]
    return None


_GENERIC_SECTION_RE = re.compile(
    r"\n={10,}\n([A-Z][^\n]{1,80})\n={10,}\n", re.M
)
# Looser: header (UPPERCASE line) followed by a single === bar.
# Catches CPA-style briefs where the bar only appears under the
# header, not above. Also subsumes H-1B style since we only look
# below the header.
_LOOSE_HEADER_RE = re.compile(
    r"(?:^|\n)([A-Z][A-Z0-9 /()\-&:\u2014]{3,80})\n={10,}\n"
)
_LABEL_VALUE_RE = re.compile(r"^([A-Z][A-Za-z0-9 /()-]{2,40}):\s{2,}(\S[^\n]*)$", re.M)


_HEADER_RE = re.compile(r"^(Prepared for|Prepared by|Date|Re):\s*(.+)$", re.I)


def _parse_brief(path: Path) -> dict:
    """Extract structured sections from the case brief text.

    Supports both the H-1B brief format ("SECTION N: TITLE" between ===
    barriers) and looser formats that just use === barriers around
    UPPERCASE headers (CPA gold-standard).
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    data: dict = {"headers": {}, "sections": {}, "raw": text}

    for line in text.splitlines()[:20]:
        m = _HEADER_RE.match(line.strip())
        if m:
            data["headers"][m.group(1).lower()] = m.group(2).strip()

    # Primary: "HEADER\n===" pattern — catches both H-1B
    # ("SECTION N: TITLE" sandwiched by ===) and CPA
    # ("UPPERCASE HEADER" followed by === only) formats.
    matches = list(_LOOSE_HEADER_RE.finditer(text))
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # Skip the trailing "END OF ..." sentinel — no body worth
        # extracting, and it would otherwise hold trailing trivia.
        if header.startswith("END OF"):
            continue
        data["sections"][header] = text[start:end].strip()

    return data


def _generic_key_facts(brief: dict) -> list[KeyFact]:
    """Scan all sections for `Label:<space>Value` pairs — generic extractor."""
    facts: list[KeyFact] = []
    seen: set[str] = set()
    # Preserve document order: scan sections in insertion order
    for _header, body in brief["sections"].items():
        for m in _LABEL_VALUE_RE.finditer(body):
            label = m.group(1).strip()
            value = m.group(2).strip()
            if label.lower() in seen:
                continue
            # Filter out verbose values
            if len(value) > 80:
                value = value[:77].rstrip() + "..."
            seen.add(label.lower())
            facts.append(KeyFact(label, value))
            if len(facts) >= 14:
                return facts
    return facts


_PHASE_RE = re.compile(
    r"^PHASE \d+\s+(.+?)\s{2,}(.+)$", re.M
)
_ISSUE_RE = re.compile(r"^ISSUE (\d+):\s+(.+)$", re.M)
_PENDING_RE = re.compile(r"^\[!\]\s+\S+\s+(.+?)\s*(?:—|$)", re.M)
_QUESTION_RE = re.compile(r"^\s*Q(\d+)\.\s+(.+?)(?=^\s*Q\d+\.|\Z)", re.M | re.S)


def _key_facts_from_brief(brief: dict) -> list[KeyFact]:
    facts: list[KeyFact] = []
    parties = brief["sections"].get("SECTION 1: THE PARTIES", "")
    # Petitioner name
    m = re.search(r"Entity:\s*(\S+(?:\s+\S+)*?)(?:\n|\s{2,})", parties)
    if m:
        facts.append(KeyFact("Petitioner", m.group(1).strip()))
    m = re.search(r"EIN:\s*(\S+)", parties)
    if m:
        facts.append(KeyFact("EIN", m.group(1).strip()))
    m = re.search(r"Incorporated:\s*(.+)", parties)
    if m:
        facts.append(KeyFact("Incorporated", m.group(1).strip().split("\n")[0]))
    m = re.search(r"Address:\s*(.+?)(?:\n\s+(?:Frontier|Commercial))", parties, re.S)
    if m:
        facts.append(KeyFact("Address", " ".join(m.group(1).split())))
    # Beneficiary
    m = re.search(r"Name:\s+(\S[^\n]+)", parties)
    if m:
        facts.append(KeyFact("Beneficiary", m.group(1).strip()))
    m = re.search(r"SEVIS ID:\s+(\S+)", parties)
    if m:
        facts.append(KeyFact("SEVIS ID", m.group(1).strip()))
    m = re.search(r"Current Status:\s+(.+)", parties)
    if m:
        facts.append(KeyFact("Current Status", m.group(1).strip().split("\n")[0]))
    # Position
    position = brief["sections"].get("SECTION 1: THE PARTIES", "")
    m = re.search(r"Title:\s+(.+)", position)
    if m:
        facts.append(KeyFact("Position", m.group(1).strip().split("\n")[0]))
    m = re.search(r"SOC Code:\s+(.+)", position)
    if m:
        facts.append(KeyFact("SOC", m.group(1).strip().split("\n")[0]))
    m = re.search(r"Prevailing Wage:\s+(.+)", position)
    if m:
        facts.append(KeyFact("Prevailing Wage", m.group(1).strip().split("\n")[0]))
    m = re.search(r"Salary Filed:\s+(.+)", position)
    if m:
        facts.append(KeyFact("Salary Filed", m.group(1).strip().split("\n")[0]))
    return facts


def _timeline_from_brief(brief: dict) -> list[TimelinePhase]:
    body = brief["sections"].get(
        "SECTION 2: COMPLETE F-1 STATUS AND EMPLOYMENT LINEAGE", ""
    )
    phases: list[TimelinePhase] = []
    for m in _PHASE_RE.finditer(body):
        name = m.group(1).strip()
        period = m.group(2).strip()
        phases.append(TimelinePhase(name=name, period=period))
    return phases


def _issues_from_brief(brief: dict) -> list[KnownIssue]:
    body = brief["sections"].get("SECTION 3: KNOWN ISSUES — PROACTIVE DISCLOSURE", "")
    issues: list[KnownIssue] = []
    for m in _ISSUE_RE.finditer(body):
        num, title = m.group(1), m.group(2).strip()
        severity = "warning"
        tl = title.lower()
        if any(k in tl for k in ("unauthorized", "open sevis", "break lawful")):
            severity = "critical"
        elif any(k in tl for k in ("in progress", "pending")):
            severity = "info"
        issues.append(KnownIssue(id=f"issue-{num}", title=title, severity=severity))
    return issues


def _pending_from_brief(brief: dict) -> list[str]:
    body = brief["sections"].get("SECTION 4: COMPLETE DOCUMENT INVENTORY", "")
    items: list[str] = []
    for m in _PENDING_RE.finditer(body):
        items.append(m.group(1).strip())
    return items


def _questions_from_brief(brief: dict) -> list[str]:
    body = brief["sections"].get("SECTION 6: OPEN QUESTIONS FOR ELISE", "")
    qs: list[str] = []
    for m in _QUESTION_RE.finditer(body):
        q_text = " ".join(m.group(2).split())
        qs.append(f"Q{m.group(1)}. {q_text}")
    return qs


def build_summary(
    folder: Path,
    template: Template,
    report: Report,
) -> CaseSummary:
    """Build a CaseSummary from folder + matched report, enriched by brief if present."""
    brief_path = _find_brief(folder)
    summary = CaseSummary(title=template.name)

    if brief_path is None:
        summary.overview = (
            f"Automated summary of {report.files_scanned} files against "
            f"the {template.name} template."
        )
        return summary

    brief = _parse_brief(brief_path)
    h = brief["headers"]
    summary.prepared_for = h.get("prepared for", "")
    summary.prepared_by = h.get("prepared by", "")
    summary.date = h.get("date", "")
    if h.get("re"):
        summary.title = h["re"].strip() or template.name

    # H-1B-specific extractors first; if they produce nothing (e.g. CPA
    # brief has no "SECTION 1: THE PARTIES"), fall back to the generic
    # Label: Value scanner that works for any structured brief.
    summary.key_facts = _key_facts_from_brief(brief)
    if not summary.key_facts:
        summary.key_facts = _generic_key_facts(brief)
    summary.timeline = _timeline_from_brief(brief)
    summary.issues = _issues_from_brief(brief)
    summary.pending_items = _pending_from_brief(brief)
    summary.open_questions = _questions_from_brief(brief)

    # First paragraph after cover block
    lead_match = re.search(
        r"This document is the master briefing[^\n]*(?:\n[^\n]+){0,6}",
        brief_path.read_text(encoding="utf-8", errors="replace"),
    )
    if lead_match:
        summary.overview = " ".join(lead_match.group(0).split())

    return summary
