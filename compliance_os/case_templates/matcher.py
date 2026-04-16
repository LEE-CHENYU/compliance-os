"""Template matcher: scan a folder, score files against slots, emit gap report."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from compliance_os.case_templates.schema import Slot, Template


# Ignored files/dirs
_IGNORE_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
_IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv"}

_DOC_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".heic", ".txt", ".docx", ".doc"}


@dataclass
class Match:
    slot_id: str
    file_path: str
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class Report:
    template_id: str
    folder: str
    files_scanned: int
    matched: dict[str, list[Match]]   # slot_id -> matches (best first)
    missing_required: list[Slot]
    missing_optional: list[Slot]
    unmatched_files: list[str]
    misplaced: list[tuple[str, str, str]]  # (file, current_section, expected_section)
    lineage_issues: list[str]
    coverage: dict[str, float]  # section -> fraction of required slots covered


def _iter_files(folder: Path) -> list[Path]:
    files = []
    for p in folder.rglob("*"):
        if p.is_dir():
            if p.name in _IGNORE_DIRS:
                # rglob doesn't prune; just skip children via filter below
                continue
            continue
        if any(part in _IGNORE_DIRS for part in p.parts):
            continue
        if p.name in _IGNORE_NAMES:
            continue
        # macOS AppleDouble resource-fork files and other dotfiles
        if p.name.startswith("._") or p.name.startswith("."):
            continue
        if p.suffix.lower() not in _DOC_EXTS:
            continue
        files.append(p)
    return files


def _score_slot(slot: Slot, path: Path) -> tuple[float, list[str]]:
    """Score a file against a slot. Returns (score, reasons).

    Scoring guards against false positives: a bare slot-id prefix
    (e.g. `D14_`) alone is not enough to claim a slot — there must
    also be a keyword, pattern, or folder-section corroboration.
    """
    name = path.name.lower()
    stem = path.stem.lower()
    parent = path.parent.name.lower()

    score = 0.0
    reasons: list[str] = []

    # Ignore patterns that just re-encode the slot-id prefix — those
    # are handled by the prefix logic below and would otherwise act
    # as self-corroboration (e.g. slot D14's pattern ^D14[_-] shouldn't
    # vouch for D14_yangtze_employment_letter.pdf on its own).
    slot_id_lower = slot.id.lower()
    pattern_hit = False
    for pat in slot.filename_patterns:
        pat_stripped = pat.lstrip("^").lower()
        if pat_stripped.startswith(slot_id_lower):
            continue
        if re.search(pat, name, re.IGNORECASE):
            score += 3.0
            reasons.append(f"filename matches /{pat}/")
            pattern_hit = True
            break

    prefix_hit = bool(re.match(rf"^{re.escape(slot.id.lower())}[_\-.]", stem))

    kw_hits = [kw for kw in slot.keywords if kw.lower() in name]
    if kw_hits:
        score += 1.0 * len(kw_hits)
        reasons.append(f"keyword(s) in filename: {', '.join(kw_hits)}")

    # Folder hint: parent folder looks like a section directory
    # (e.g. "A_Beneficiary", "D_Corporate"). Don't accept a bare
    # letter-in-name match — a pytest tmp dir like "test_foo_a_bar"
    # should not count as section A.
    section_lc = slot.section.lower()
    section_name_lc = slot.section_name.lower().replace(" ", "_")
    folder_hit = (
        re.match(rf"^{re.escape(section_lc)}[_\-]", parent) is not None
        or section_name_lc in parent
    )
    if folder_hit:
        score += 0.5
        reasons.append(f"parent folder '{parent}' hints section {slot.section}")

    # Slot-id prefix is a strong signal only when corroborated by
    # content (pattern or keyword). A folder hint alone isn't enough,
    # because prefix conventions are usually per-section, so the
    # section folder is a near-tautology for a prefix match.
    # Example: D14_yangtze_employment_letter.pdf has the D14 prefix
    # and sits in D_Corporate/, but its content is an employment
    # letter, not the bank statement D14 represents.
    if prefix_hit:
        if pattern_hit or kw_hits:
            score += 5.0
            reasons.append(f"filename starts with slot id '{slot.id}'")
        else:
            score += 1.0
            reasons.append(f"slot-id prefix '{slot.id}' present but no content corroboration")

    return score, reasons


def match_folder(
    folder: str | Path,
    template: Template,
    min_score: float = 2.0,
) -> Report:
    """Scan `folder`, score each file against template slots, return a Report."""
    folder = Path(folder).expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory")

    files = _iter_files(folder)

    # For each file, find best-matching slot(s)
    matches_per_slot: dict[str, list[Match]] = {}
    file_best_slot: dict[str, tuple[str, float]] = {}

    for f in files:
        rel = str(f.relative_to(folder))
        best_score = 0.0
        slot_scores: list[tuple[Slot, float, list[str]]] = []
        for slot in template.slots:
            s, reasons = _score_slot(slot, f)
            if s > 0:
                slot_scores.append((slot, s, reasons))
                if s > best_score:
                    best_score = s

        if best_score >= min_score:
            # A file belongs to its top-scoring slot(s) only — ties
            # are kept so genuinely ambiguous matches surface, but we
            # don't spray a file across every slot whose keywords it
            # happens to overlap with.
            top = [t for t in slot_scores if t[1] == best_score]
            file_best_slot[rel] = (top[0][0].id, best_score)
            for slot, s, reasons in top:
                matches_per_slot.setdefault(slot.id, []).append(
                    Match(slot_id=slot.id, file_path=rel, score=s, reasons=reasons)
                )
        # Else: file stays unmatched

    # Sort each slot's matches by score (desc)
    for slot_id in matches_per_slot:
        matches_per_slot[slot_id].sort(key=lambda m: -m.score)

    matched_file_paths = set(file_best_slot.keys())
    unmatched = [str(f.relative_to(folder)) for f in files if str(f.relative_to(folder)) not in matched_file_paths]

    # Missing slots
    missing_required = [s for s in template.slots if s.required and s.id not in matches_per_slot]
    missing_optional = [s for s in template.slots if not s.required and s.id not in matches_per_slot]

    # Misplaced: file's best slot is in a different section than its parent folder suggests
    misplaced: list[tuple[str, str, str]] = []
    for rel, (slot_id, _) in file_best_slot.items():
        slot = template.slot_by_id(slot_id)
        if slot is None:
            continue
        # Parent folder naming convention: "A_Beneficiary", "B_I20_History", etc.
        top = Path(rel).parts[0] if len(Path(rel).parts) > 1 else ""
        if top and re.match(r"^[A-Z](?:_|$)", top):
            current_section = top[0]
            if current_section != slot.section:
                misplaced.append((rel, current_section, slot.section))

    # Lineage check: order-tracked slots (e.g. B01→B13) should appear in chronological order
    lineage_issues: list[str] = []
    for section_code in template.sections:
        ordered = [s for s in template.slots_by_section(section_code) if s.order > 0]
        if not ordered:
            continue
        ordered.sort(key=lambda s: s.order)
        # Only required slots contribute to lineage gap detection
        seen_ids = [s.id for s in ordered if s.id in matches_per_slot]
        # Detect gaps in required slots
        for s in ordered:
            if s.required and s.id not in matches_per_slot:
                lineage_issues.append(f"{section_code}: missing {s.id} ({s.title}) — breaks lineage")

    # Coverage per section (required slots only)
    coverage: dict[str, float] = {}
    for section_code in template.sections:
        req = [s for s in template.slots_by_section(section_code) if s.required]
        if not req:
            coverage[section_code] = 1.0
            continue
        hit = sum(1 for s in req if s.id in matches_per_slot)
        coverage[section_code] = hit / len(req)

    return Report(
        template_id=template.id,
        folder=str(folder),
        files_scanned=len(files),
        matched=matches_per_slot,
        missing_required=missing_required,
        missing_optional=missing_optional,
        unmatched_files=unmatched,
        misplaced=misplaced,
        lineage_issues=lineage_issues,
        coverage=coverage,
    )


def format_report(report: Report, template: Template, verbose: bool = False) -> str:
    """Render a report as human-readable text."""
    lines = []
    lines.append(f"# {template.name} — Active Search Report")
    lines.append(f"Folder: {report.folder}")
    lines.append(f"Files scanned: {report.files_scanned}")
    lines.append("")

    # Coverage summary
    lines.append("## Coverage by section (required slots)")
    total_req = sum(1 for s in template.slots if s.required)
    hit_req = sum(1 for s in template.slots if s.required and s.id in report.matched)
    lines.append(f"Overall: {hit_req}/{total_req} required slots filled ({100*hit_req/total_req:.0f}%)")
    for code, name in template.sections.items():
        frac = report.coverage.get(code, 0.0)
        req = [s for s in template.slots_by_section(code) if s.required]
        hit = sum(1 for s in req if s.id in report.matched)
        lines.append(f"  {code} {name:<28s}  {hit}/{len(req)}  ({100*frac:.0f}%)")
    lines.append("")

    # Missing required
    if report.missing_required:
        lines.append("## Missing required slots")
        for s in report.missing_required:
            lines.append(f"  [ ] {s.id}  {s.title}")
            if s.description:
                lines.append(f"       {s.description}")
        lines.append("")
    else:
        lines.append("## Missing required slots: NONE ✓\n")

    # Missing optional (brief)
    if report.missing_optional:
        lines.append("## Missing optional slots")
        for s in report.missing_optional:
            lines.append(f"  [ ] {s.id}  {s.title}")
        lines.append("")

    # Lineage issues
    if report.lineage_issues:
        lines.append("## Lineage issues")
        for issue in report.lineage_issues:
            lines.append(f"  ! {issue}")
        lines.append("")

    # Misplaced
    if report.misplaced:
        lines.append("## Misplaced files")
        for f, cur, exp in report.misplaced:
            lines.append(f"  {f}  (in section {cur}, template expects {exp})")
        lines.append("")

    # Matched
    lines.append("## Matched slots")
    for slot in template.slots:
        ms = report.matched.get(slot.id, [])
        if not ms:
            continue
        best = ms[0]
        flag = "✓" if slot.required else "·"
        lines.append(f"  [{flag}] {slot.id}  {slot.title}")
        lines.append(f"       {best.file_path}  (score {best.score:.1f})")
        if verbose:
            for r in best.reasons:
                lines.append(f"         · {r}")
            for extra in ms[1:]:
                lines.append(f"       + also: {extra.file_path} (score {extra.score:.1f})")
    lines.append("")

    # Unmatched
    if report.unmatched_files:
        lines.append(f"## Unmatched files ({len(report.unmatched_files)})")
        for f in report.unmatched_files[:30]:
            lines.append(f"  ? {f}")
        if len(report.unmatched_files) > 30:
            lines.append(f"  ... and {len(report.unmatched_files) - 30} more")
        lines.append("")

    return "\n".join(lines)
