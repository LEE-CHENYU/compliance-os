"""Validation helpers for real-source data-room batch slices."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from compliance_os.batch_loop import BatchSpec, load_manifest
from compliance_os.web.services.document_intake import (
    UploadValidationError,
    resolve_document_type,
    validate_upload,
)


@dataclass(slots=True)
class BatchManifestEntry:
    label: str
    file_path: str
    expected_doc_type: str


@dataclass(slots=True)
class BatchSourceCheck:
    label: str
    file_path: str
    absolute_path: str
    expected_doc_type: str
    exists: bool
    mime_type: str | None
    size_bytes: int | None
    resolved_doc_type: str | None
    classification_source: str | None
    ok: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "file_path": self.file_path,
            "absolute_path": self.absolute_path,
            "expected_doc_type": self.expected_doc_type,
            "exists": self.exists,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "resolved_doc_type": self.resolved_doc_type,
            "classification_source": self.classification_source,
            "ok": self.ok,
            "error": self.error,
        }


@dataclass(slots=True)
class BatchValidationSummary:
    batch_id: str
    batch_number: int
    focus: str
    record: str
    source_root: str
    target_size: int | None
    manifest_rows: int
    checks: list[BatchSourceCheck]

    @property
    def ok(self) -> bool:
        if self.target_size is not None and self.manifest_rows != self.target_size:
            return False
        return all(check.ok for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "batch_number": self.batch_number,
            "focus": self.focus,
            "record": self.record,
            "source_root": self.source_root,
            "target_size": self.target_size,
            "manifest_rows": self.manifest_rows,
            "ok": self.ok,
            "checks": [check.to_dict() for check in self.checks],
        }


@dataclass(slots=True)
class BatchCollectionValidationSummary:
    source_root: str
    selected_batches: list[BatchValidationSummary]

    @property
    def ok(self) -> bool:
        return all(summary.ok for summary in self.selected_batches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_root": self.source_root,
            "selected_batches": [summary.to_dict() for summary in self.selected_batches],
            "ok": self.ok,
            "total_batches": len(self.selected_batches),
            "passed_batches": sum(1 for summary in self.selected_batches if summary.ok),
        }


def _strip_cell(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("`") and stripped.endswith("`") and len(stripped) >= 2:
        return stripped[1:-1]
    return stripped.strip("`").strip()


def _parse_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        raise ValueError(f"Not a markdown table row: {line}")
    return [_strip_cell(cell) for cell in stripped.strip("|").split("|")]


def parse_manifest_entries(record_path: str | Path) -> list[BatchManifestEntry]:
    lines = Path(record_path).read_text().splitlines()
    file_key = "File"
    expected_candidates = (
        "Current classification result",
        "Data room classification result",
        "Intended doc type",
        "Expected doc type",
    )

    for index, line in enumerate(lines):
        if not (line.strip().startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|")):
            continue

        header = _parse_markdown_row(lines[index])
        expected_key = next((candidate for candidate in expected_candidates if candidate in header), None)
        if file_key not in header or expected_key is None:
            continue

        data_lines: list[str] = []
        for data_line in lines[index + 2:]:
            if not data_line.strip().startswith("|"):
                break
            data_lines.append(data_line)

        label_index = header.index("Label") if "Label" in header else None
        file_index = header.index(file_key)
        expected_index = header.index(expected_key)

        entries: list[BatchManifestEntry] = []
        for data_line in data_lines:
            cells = _parse_markdown_row(data_line)
            if len(cells) < len(header):
                cells.extend([""] * (len(header) - len(cells)))
            entries.append(
                BatchManifestEntry(
                    label=cells[label_index] if label_index is not None else cells[file_index],
                    file_path=cells[file_index],
                    expected_doc_type=cells[expected_index],
                )
            )
        return entries

    raise ValueError(f"Manifest table in {record_path} must include `File` and expected doc type columns")


def _guess_mime_type(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".csv":
        return "text/csv"
    if suffix == ".txt":
        return "text/plain"
    return None


def _select_batch(
    batches: list[BatchSpec],
    *,
    batch_number: int | None = None,
    batch_id: str | None = None,
) -> BatchSpec:
    for spec in batches:
        if batch_number is not None and spec.batch_number == batch_number:
            return spec
        if batch_id is not None and spec.batch_id == batch_id:
            return spec
    wanted = f"batch_number={batch_number}" if batch_number is not None else f"batch_id={batch_id}"
    raise ValueError(f"Batch not found for {wanted}")


def validate_batch_source_slice(
    *,
    project_root: str | Path,
    manifest_path: str | Path,
    batch_number: int | None = None,
    batch_id: str | None = None,
    source_root_override: str | Path | None = None,
) -> BatchValidationSummary:
    source_root, batches = load_manifest(manifest_path)
    spec = _select_batch(batches, batch_number=batch_number, batch_id=batch_id)
    if not spec.record:
        raise ValueError(f"Batch {spec.batch_id} has no record")

    project_root_path = Path(project_root)
    record_path = project_root_path / spec.record
    entries = parse_manifest_entries(record_path)

    source_root_path = Path(source_root_override or source_root or "")
    if not source_root_path:
        raise ValueError("No source_root configured for batch manifest")

    checks: list[BatchSourceCheck] = []
    for entry in entries:
        absolute_path = source_root_path / entry.file_path
        mime_type = _guess_mime_type(absolute_path)
        if not absolute_path.exists():
            checks.append(
                BatchSourceCheck(
                    label=entry.label,
                    file_path=entry.file_path,
                    absolute_path=str(absolute_path),
                    expected_doc_type=entry.expected_doc_type,
                    exists=False,
                    mime_type=mime_type,
                    size_bytes=None,
                    resolved_doc_type=None,
                    classification_source=None,
                    ok=False,
                    error="File missing from source_root",
                )
            )
            continue

        size_bytes = absolute_path.stat().st_size
        try:
            validate_upload(mime_type, size_bytes)
            resolved = resolve_document_type(
                str(absolute_path),
                mime_type,
                allow_ocr=False,
            )
            ok = resolved.doc_type == entry.expected_doc_type
            error = None if ok else f"Resolved as {resolved.doc_type!r}, expected {entry.expected_doc_type!r}"
            checks.append(
                BatchSourceCheck(
                    label=entry.label,
                    file_path=entry.file_path,
                    absolute_path=str(absolute_path),
                    expected_doc_type=entry.expected_doc_type,
                    exists=True,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    resolved_doc_type=resolved.doc_type,
                    classification_source=resolved.source,
                    ok=ok,
                    error=error,
                )
            )
        except UploadValidationError as exc:
            checks.append(
                BatchSourceCheck(
                    label=entry.label,
                    file_path=entry.file_path,
                    absolute_path=str(absolute_path),
                    expected_doc_type=entry.expected_doc_type,
                    exists=True,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    resolved_doc_type=None,
                    classification_source=None,
                    ok=False,
                    error=str(exc),
                )
            )

    return BatchValidationSummary(
        batch_id=spec.batch_id,
        batch_number=spec.batch_number,
        focus=spec.focus,
        record=spec.record,
        source_root=str(source_root_path),
        target_size=spec.target_size,
        manifest_rows=len(entries),
        checks=checks,
    )


def validate_batch_collection(
    *,
    project_root: str | Path,
    manifest_path: str | Path,
    statuses: set[str] | None = None,
    min_batch_number: int | None = None,
    max_batch_number: int | None = None,
    batch_numbers: set[int] | None = None,
    source_root_override: str | Path | None = None,
) -> BatchCollectionValidationSummary:
    source_root, batches = load_manifest(manifest_path)
    selected: list[BatchSpec] = []
    for spec in batches:
        if statuses is not None and spec.status not in statuses:
            continue
        if min_batch_number is not None and spec.batch_number < min_batch_number:
            continue
        if max_batch_number is not None and spec.batch_number > max_batch_number:
            continue
        if batch_numbers is not None and spec.batch_number not in batch_numbers:
            continue
        selected.append(spec)

    results = [
        validate_batch_source_slice(
            project_root=project_root,
            manifest_path=manifest_path,
            batch_number=spec.batch_number,
            source_root_override=source_root_override,
        )
        for spec in selected
    ]
    return BatchCollectionValidationSummary(
        source_root=str(source_root_override or source_root or ""),
        selected_batches=results,
    )
