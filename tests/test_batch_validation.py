from compliance_os.batch_validation import parse_manifest_entries, validate_batch_source_slice
from compliance_os.web.services.document_intake import ResolvedDocumentType


def test_parse_manifest_entries_reads_expected_doc_type_column(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text(
        "\n".join(
            [
                "# Batch",
                "",
                "## Batch manifest",
                "",
                "| Label | File | Intended use | Current classification result |",
                "| --- | --- | --- | --- |",
                "| `passport_identity` | `passport.jpeg` | identity page | `passport` |",
                "| `i94_recent` | `I94.pdf` | travel record | `i94` |",
            ]
        )
    )

    entries = parse_manifest_entries(record)

    assert [(entry.label, entry.file_path, entry.expected_doc_type) for entry in entries] == [
        ("passport_identity", "passport.jpeg", "passport"),
        ("i94_recent", "I94.pdf", "i94"),
    ]


def test_parse_manifest_entries_skips_unrelated_tables(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text(
        "\n".join(
            [
                "# Batch",
                "",
                "| Status | Value |",
                "| --- | --- |",
                "| Completed | yes |",
                "",
                "| Label | File | Current classification result |",
                "| --- | --- | --- |",
                "| `passport_identity` | `passport.jpeg` | `passport` |",
            ]
        )
    )

    entries = parse_manifest_entries(record)

    assert len(entries) == 1
    assert entries[0].file_path == "passport.jpeg"
    assert entries[0].expected_doc_type == "passport"


def test_parse_manifest_entries_accepts_legacy_data_room_result_header(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text(
        "\n".join(
            [
                "# Batch",
                "",
                "| Label | File | Intended use | Data room classification result |",
                "| --- | --- | --- | --- |",
                "| `ead_opt` | `Personal Info Archive/EAD (OPT).jpeg` | EAD card | `ead` |",
            ]
        )
    )

    entries = parse_manifest_entries(record)

    assert len(entries) == 1
    assert entries[0].file_path == "Personal Info Archive/EAD (OPT).jpeg"
    assert entries[0].expected_doc_type == "ead"


def test_parse_manifest_entries_preserves_leading_spaces_inside_backticks(tmp_path):
    record = tmp_path / "batch.md"
    record.write_text(
        "\n".join(
            [
                "# Batch",
                "",
                "| Label | File | Intended use | Intended doc type |",
                "| --- | --- | --- | --- |",
                "| `spaced_transcript` | ` Transcript(WES).pdf` | transcript with leading-space filename | `transcript` |",
            ]
        )
    )

    entries = parse_manifest_entries(record)

    assert len(entries) == 1
    assert entries[0].file_path == " Transcript(WES).pdf"


def test_validate_batch_source_slice_checks_real_source_files(tmp_path, monkeypatch):
    source_root = tmp_path / "Important Docs "
    source_root.mkdir()
    (source_root / "passport.jpeg").write_bytes(b"passport-bytes")
    (source_root / "I94.pdf").write_bytes(b"%PDF-1.4 fake")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    record = docs_dir / "batch-06.md"
    record.write_text(
        "\n".join(
            [
                "# Batch 06",
                "",
                "| Label | File | Intended use | Current classification result |",
                "| --- | --- | --- | --- |",
                "| `passport_identity` | `passport.jpeg` | identity page | `passport` |",
                "| `i94_recent` | `I94.pdf` | travel record | `i94` |",
            ]
        )
    )

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "\n".join(
            [
                f'source_root: "{source_root}"',
                "batches:",
                "  - id: batch_06",
                "    number: 6",
                "    focus: identity and travel",
                "    status: planned",
                "    record: docs/batch-06.md",
                "    target_size: 2",
            ]
        )
    )

    def fake_resolve_document_type(file_path: str, mime_type: str, *, provided_doc_type=None, allow_ocr=False):
        if file_path.endswith("passport.jpeg"):
            return ResolvedDocumentType(doc_type="passport", confidence="high", source="filename")
        if file_path.endswith("I94.pdf"):
            return ResolvedDocumentType(doc_type="i94", confidence="high", source="filename")
        raise AssertionError(file_path)

    monkeypatch.setattr("compliance_os.batch_validation.resolve_document_type", fake_resolve_document_type)

    summary = validate_batch_source_slice(
        project_root=tmp_path,
        manifest_path=manifest,
        batch_number=6,
    )

    assert summary.ok is True
    assert summary.manifest_rows == 2
    assert [check.resolved_doc_type for check in summary.checks] == ["passport", "i94"]
    assert all(check.ok for check in summary.checks)


def test_validate_batch_source_slice_reports_missing_file(tmp_path, monkeypatch):
    source_root = tmp_path / "Important Docs "
    source_root.mkdir()
    (source_root / "passport.jpeg").write_bytes(b"passport-bytes")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    record = docs_dir / "batch-06.md"
    record.write_text(
        "\n".join(
            [
                "# Batch 06",
                "",
                "| Label | File | Intended use | Current classification result |",
                "| --- | --- | --- | --- |",
                "| `passport_identity` | `passport.jpeg` | identity page | `passport` |",
                "| `i94_recent` | `I94.pdf` | travel record | `i94` |",
            ]
        )
    )

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        "\n".join(
            [
                f'source_root: "{source_root}"',
                "batches:",
                "  - id: batch_06",
                "    number: 6",
                "    focus: identity and travel",
                "    status: planned",
                "    record: docs/batch-06.md",
                "    target_size: 2",
            ]
        )
    )

    def fake_resolve_document_type(file_path: str, mime_type: str, *, provided_doc_type=None, allow_ocr=False):
        return ResolvedDocumentType(doc_type="passport", confidence="high", source="filename")

    monkeypatch.setattr("compliance_os.batch_validation.resolve_document_type", fake_resolve_document_type)

    summary = validate_batch_source_slice(
        project_root=tmp_path,
        manifest_path=manifest,
        batch_number=6,
    )

    assert summary.ok is False
    missing = next(check for check in summary.checks if check.file_path == "I94.pdf")
    assert missing.exists is False
    assert missing.error == "File missing from source_root"
