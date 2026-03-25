"""LLM extraction service — PDF text → OpenAI structured output → extracted fields."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import os

import fitz  # PyMuPDF


SCHEMAS: dict[str, dict[str, str]] = {
    "i983": {
        "student_name": "Full name of the student",
        "sevis_number": "SEVIS number (format: N followed by 10 digits)",
        "school_name": "Name of the school or university",
        "degree_level": "Degree level (Bachelor's, Master's, Doctoral)",
        "major": "Major field of study",
        "employer_name": "Name of the employer",
        "employer_ein": "Employer EIN (format: XX-XXXXXXX)",
        "employer_address": "Employer mailing address",
        "work_site_address": "Physical work site address",
        "job_title": "Job title / position",
        "start_date": "Employment start date (YYYY-MM-DD)",
        "end_date": "Employment end date (YYYY-MM-DD)",
        "compensation": "Annual compensation (number only)",
        "compensation_type": "Compensation type (Salary, hourly, stipend)",
        "duties_description": "Description of job duties and responsibilities",
        "training_goals": "Training goals and objectives",
        "supervisor_name": "Supervisor / mentor name",
        "supervisor_title": "Supervisor title",
        "supervisor_phone": "Supervisor phone number",
        "full_time": "Full-time employment (true/false)",
    },
    "employment_letter": {
        "employee_name": "Employee full name",
        "employer_name": "Employer / company name",
        "employer_address": "Employer address",
        "job_title": "Job title / position",
        "start_date": "Employment start date (YYYY-MM-DD)",
        "end_date": "Employment end date (YYYY-MM-DD) or null if ongoing",
        "compensation": "Annual compensation (number only)",
        "compensation_type": "Compensation type (Salary, hourly)",
        "duties_description": "Description of job duties and responsibilities",
        "manager_name": "Manager / supervisor name",
        "full_time": "Full-time or part-time (true for full-time)",
        "work_location": "Work location / office address",
    },
    "tax_return": {
        "form_type": "Tax form type (1040, 1040-NR, 1120, 1120-S, 1065)",
        "tax_year": "Tax year (number)",
        "entity_name": "Entity name (for business returns) or null",
        "ein": "EIN (format: XX-XXXXXXX) or null",
        "filing_status": "Filing status (Single, MFJ, etc.) or null",
        "total_income": "Total income amount (number)",
        "schedules_present": "List of schedules present (e.g., schedule_c, schedule_d, schedule_nec)",
        "form_5472_present": "Whether Form 5472 is attached (true/false)",
        "form_3520_present": "Whether Form 3520 is attached (true/false)",
        "form_8938_present": "Whether Form 8938 is attached (true/false)",
        "state_returns_filed": "List of state abbreviations for state returns filed",
    },
}


def extract_pdf_text(file_path: str | Path) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    doc = fitz.open(str(file_path))
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def extract_document(
    doc_type: str,
    text: str,
) -> dict[str, dict[str, Any]]:
    """Extract structured fields from document text using LLM.

    Returns dict of {field_name: {"value": ..., "confidence": ...}}
    """
    schema = SCHEMAS.get(doc_type, {})
    if not schema:
        return {}

    result = _call_llm(text, doc_type, schema)

    # Map to {field_name: {"value": ..., "confidence": ...}}
    fields: dict[str, dict[str, Any]] = {}
    for field_name in schema:
        value = result.get(field_name)
        confidence = 0.85 if value is not None else 0.0
        fields[field_name] = {"value": value, "confidence": confidence}

    return fields


def _call_llm(
    text: str,
    doc_type: str,
    schema: dict[str, str],
) -> dict[str, Any]:
    """Call LLM to extract structured fields from document text.
    Uses Claude (Anthropic) if ANTHROPIC_API_KEY is set, otherwise falls back to OpenAI.
    """
    field_descriptions = "\n".join(f"- {name}: {desc}" for name, desc in schema.items())

    prompt = f"""Extract the following fields from this {doc_type} document.
Return a JSON object with these fields. Use null for any field you cannot find.

Fields to extract:
{field_descriptions}

Document text:
{text}

Return ONLY valid JSON, no explanation."""

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if anthropic_key:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
            system="You are a document field extractor. Return only valid JSON, no explanation or markdown.",
            temperature=0,
        )
        content = response.content[0].text
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(content)
    else:
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a document field extractor. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content
        return json.loads(content)
