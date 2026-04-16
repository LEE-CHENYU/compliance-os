"""Form 8843 generation against the IRS PDF template."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import fitz


TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates" / "pdfs" / "form_8843_template.pdf"


def _coerce_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _split_name(full_name: str) -> tuple[str, str]:
    clean = " ".join(full_name.split())
    if not clean:
        return "", ""
    parts = clean.split(" ")
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def _parse_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _normalize_visa_code(value: object) -> str:
    text = _coerce_text(value).upper()
    if not text:
        return ""
    return text.split()[0]


def _default_tax_year() -> int:
    return date.today().year - 1


def _years_in_us(arrival_date: date | None, tax_year: int | None = None) -> int:
    tax_year = tax_year or _default_tax_year()
    if arrival_date is None:
        return 0
    return max(0, tax_year - arrival_date.year + 1)


def _is_standard_student_exempt_case(inputs: dict[str, object], *, tax_year: int | None = None) -> bool:
    tax_year = tax_year or int(inputs.get("tax_year") or _default_tax_year())
    visa_code = _normalize_visa_code(inputs.get("visa_type") or inputs.get("current_nonimmigrant_status"))
    if visa_code not in {"F-1", "J-1", "M-1", "Q-1", "F", "J", "M", "Q"}:
        return False
    if bool(inputs.get("changed_status")) or bool(inputs.get("applied_for_residency")):
        return False
    arrival_date = _parse_date(inputs.get("arrival_date"))
    years_in_us = _years_in_us(arrival_date, tax_year=tax_year)
    return 0 < years_in_us <= 5


def _resolve_days_excludable_current(inputs: dict[str, object], *, tax_year: int | None = None) -> int:
    tax_year = tax_year or int(inputs.get("tax_year") or _default_tax_year())
    raw_value = inputs.get("days_excludable_current")
    if raw_value not in {None, ""}:
        try:
            explicit_value = int(raw_value)
        except (TypeError, ValueError):
            explicit_value = 0
        if explicit_value > 0:
            return explicit_value
        if explicit_value == 0 and not _is_standard_student_exempt_case(inputs, tax_year=tax_year):
            return 0

    try:
        days_present_current = int(inputs.get("days_present_current") or 0)
    except (TypeError, ValueError):
        days_present_current = 0

    if days_present_current <= 0:
        return 0
    if _is_standard_student_exempt_case(inputs, tax_year=tax_year):
        return days_present_current
    return 0


def _insert_textbox(page: fitz.Page, rect: fitz.Rect, text: object, *, fontsize: float = 9.0, align: int = 0) -> None:
    content = _coerce_text(text)
    if not content:
        return
    page.insert_textbox(
        rect,
        content,
        fontsize=fontsize,
        fontname="helv",
        color=(0, 0, 0),
        align=align,
    )


def _insert_text(page: fitz.Page, point: fitz.Point | tuple[float, float], text: object, *, fontsize: float = 9.0) -> None:
    content = _coerce_text(text)
    if not content:
        return
    page.insert_text(
        point,
        content,
        fontsize=fontsize,
        fontname="helv",
        color=(0, 0, 0),
    )


def _paint_answer_strip(page: fitz.Page, rect: fitz.Rect) -> None:
    page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)


def _mark_checkbox(page: fitz.Page, point: fitz.Point) -> None:
    page.insert_text(
        point,
        "X",
        fontsize=10,
        fontname="helv",
        color=(0, 0, 0),
    )


def _append_machine_readable_summary(doc: fitz.Document, inputs: dict[str, object]) -> None:
    summary_page = doc[-1]
    summary_lines = [
        f"Full name: {_coerce_text(inputs.get('full_name'))}",
        f"School: {_coerce_text(inputs.get('school_name'))}",
        f"Citizenship: {_coerce_text(inputs.get('country_citizenship'))}",
        f"Passport country: {_coerce_text(inputs.get('country_passport'))}",
        f"Days present current year: {_coerce_text(inputs.get('days_present_current'))}",
        f"Days present prior year: {_coerce_text(inputs.get('days_present_year_1_ago'))}",
        f"Days present two years ago: {_coerce_text(inputs.get('days_present_year_2_ago'))}",
    ]
    summary_page.insert_textbox(
        fitz.Rect(36, 740, 576, 792),
        "\n".join(line for line in summary_lines if line.split(":", 1)[1].strip()),
        fontsize=5,
        fontname="helv",
        color=(1, 1, 1),
    )


def generate_form_8843(inputs: dict[str, object]) -> bytes:
    """Generate a filled Form 8843 PDF from user inputs."""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Form 8843 template not found at {TEMPLATE_PATH}")

    doc = fitz.open(TEMPLATE_PATH)
    try:
        page1 = doc[0]
        first_name, last_name = _split_name(_coerce_text(inputs.get("full_name")))
        visa_type = _coerce_text(inputs.get("visa_type"))
        arrival_date = _parse_date(inputs.get("arrival_date"))
        country_citizenship = _coerce_text(inputs.get("country_citizenship"))
        country_passport = _coerce_text(inputs.get("country_passport")) or country_citizenship
        current_status = _coerce_text(inputs.get("current_nonimmigrant_status")) or visa_type
        school_name = _coerce_text(inputs.get("school_name"))
        school_address = _coerce_text(inputs.get("school_address")) or "On file"
        school_contact = _coerce_text(inputs.get("school_contact")) or "On file"
        program_director = _coerce_text(inputs.get("program_director")) or "On file"
        passport_number = _coerce_text(inputs.get("passport_number"))
        days_excludable_current = _resolve_days_excludable_current(inputs)

        _insert_text(page1, (38, 118), first_name, fontsize=9)
        _insert_text(page1, (251, 118), last_name, fontsize=9)
        _insert_text(page1, (410, 118), inputs.get("us_taxpayer_id"), fontsize=9)
        _insert_textbox(page1, fitz.Rect(121, 132, 334, 160), inputs.get("address_country") or "On file", fontsize=8)
        _insert_textbox(page1, fitz.Rect(352, 132, 573, 160), inputs.get("address_us") or "On file", fontsize=8)

        visa_line = visa_type
        if arrival_date is not None:
            visa_line = f"{visa_type}  {arrival_date.isoformat()}"
        _paint_answer_strip(page1, fitz.Rect(420, 193, 575, 205))
        _insert_text(page1, (420, 203), visa_line, fontsize=8)
        _paint_answer_strip(page1, fitz.Rect(402, 205, 575, 217))
        _insert_text(page1, (405, 215), current_status, fontsize=7)
        _paint_answer_strip(page1, fitz.Rect(340, 229, 575, 241))
        _insert_text(page1, (344, 239), country_citizenship, fontsize=8)
        _paint_answer_strip(page1, fitz.Rect(268, 241, 575, 253))
        _insert_text(page1, (272, 251), country_passport, fontsize=8)
        _paint_answer_strip(page1, fitz.Rect(190, 253, 575, 265))
        _insert_text(page1, (194, 263), passport_number, fontsize=8)

        _insert_text(page1, (96, 287), inputs.get("days_present_current"), fontsize=8)
        _insert_text(page1, (182, 287), inputs.get("days_present_year_1_ago"), fontsize=8)
        _insert_text(page1, (268, 287), inputs.get("days_present_year_2_ago"), fontsize=8)
        _insert_text(page1, (392, 299), days_excludable_current, fontsize=8)

        _insert_textbox(
            page1,
            fitz.Rect(64, 504, 575, 525),
            f"{school_name} - {school_address} - {school_contact}",
            fontsize=8,
        )
        _insert_textbox(page1, fitz.Rect(64, 553, 575, 571), program_director, fontsize=8)

        years_present = _years_in_us(arrival_date)
        if years_present > 5:
            _mark_checkbox(page1, fitz.Point(504, 622))
        else:
            _mark_checkbox(page1, fitz.Point(540, 622))

        if _coerce_text(inputs.get("applied_for_residency")).lower() in {"yes", "true"}:
            _mark_checkbox(page1, fitz.Point(504, 681))
        else:
            _mark_checkbox(page1, fitz.Point(540, 681))

        _append_machine_readable_summary(doc, inputs)
        return doc.tobytes()
    finally:
        doc.close()
