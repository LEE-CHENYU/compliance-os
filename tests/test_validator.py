"""Parameterized validation-pipeline tests.

Exercises the reusable `validate()` runner against every registered
template + the canonical local fixture folder. New case templates just
need a tuple in PAIRS — no new test file required.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from compliance_os.case_templates import (
    TEMPLATES,
    resolve_template,
    validate,
    format_validation,
)


PAIRS: list[tuple[str, str]] = [
    ("h1b", "/Users/lichenyu/accounting/outgoing/klasko/upload_041626"),
    ("cpa", "/Users/lichenyu/accounting/outgoing/kaufman_rossin/data_room"),
]


def _available(folder: str) -> bool:
    return Path(folder).is_dir()


@pytest.mark.parametrize("template_id,folder", PAIRS)
def test_validate_passes(template_id: str, folder: str):
    if not _available(folder):
        pytest.skip(f"Fixture folder not available: {folder}")
    result = validate(template_id, folder)
    assert result.passed, (
        f"{template_id} failed: "
        f"{result.required_matched}/{result.required_total} required, "
        f"missing={[m['id'] for m in result.missing_required]}"
    )
    assert result.files_scanned > 0


@pytest.mark.parametrize("template_id,folder", PAIRS)
def test_validate_returns_coverage_per_section(template_id: str, folder: str):
    if not _available(folder):
        pytest.skip(f"Fixture folder not available: {folder}")
    result = validate(template_id, folder)
    tpl = resolve_template(template_id)
    assert set(result.coverage.keys()) == set(tpl.sections.keys())


@pytest.mark.parametrize("template_id,folder", PAIRS)
def test_validate_format_produces_report(template_id: str, folder: str):
    if not _available(folder):
        pytest.skip(f"Fixture folder not available: {folder}")
    result = validate(template_id, folder)
    text = format_validation(result)
    assert "Active Search Report" in text
    assert "Coverage by section" in text
    assert result.template_name in text


def test_validate_rejects_unknown_template():
    with pytest.raises(KeyError):
        validate("nonexistent_template", "/tmp")


def test_validate_rejects_missing_folder():
    # Pick first registered template
    any_template = next(iter(TEMPLATES.keys()))
    with pytest.raises(NotADirectoryError):
        validate(any_template, "/definitely/not/a/folder")


def test_validation_result_serializes_to_json():
    import json
    if not _available(PAIRS[0][1]):
        pytest.skip("Fixture not available")
    result = validate(*PAIRS[0])
    blob = json.dumps(result.to_dict())
    parsed = json.loads(blob)
    assert parsed["template_id"] == result.template_id
    assert parsed["passed"] == result.passed


def test_strict_mode_stricter_than_default():
    if not _available(PAIRS[0][1]):
        pytest.skip("Fixture not available")
    lenient = validate(*PAIRS[0], require_full_required=False)
    strict = validate(*PAIRS[0], require_full_required=True)
    # If anything required is missing, strict must be stricter
    if lenient.missing_required:
        assert strict.passed is False
    # Otherwise both should agree
    else:
        assert lenient.passed == strict.passed
