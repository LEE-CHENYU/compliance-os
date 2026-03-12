"""Document classifier — infers document type and metadata from file paths and names.

The classifier uses a rule-based approach to categorize documents into compliance-relevant
types. Rules are loaded from config/document_types.yaml if available, with built-in
defaults as fallback.
"""

from pathlib import Path

import yaml

from compliance_os.settings import settings


# Default classification rules (overridable via config/document_types.yaml)
DEFAULT_RULES: list[dict] = [
    {
        "doc_type": "tax_form",
        "keywords": [
            "w2", "w-2", "1099", "1098", "1040", "1040-nr", "3520", "3520-a",
            "8843", "8938", "5472", "fbar", "fatca", "schedule-c", "540nr",
        ],
    },
    {
        "doc_type": "payroll",
        "keywords": ["paystub", "payroll", "paycheck", "pay_stub", "earnings"],
    },
    {
        "doc_type": "immigration",
        "keywords": [
            "h1b", "h-1b", "i-20", "i20", "i-765", "i765", "visa", "immigration",
            "uscis", "sevis", "opt", "stem-opt", "cpt", "ead", "i-94", "i94",
            "g-28", "h1br", "petition", "beneficiary",
        ],
    },
    {
        "doc_type": "deadline",
        "keywords": ["deadline", "timeline", "schedule", "due_date", "calendar"],
    },
    {
        "doc_type": "financial",
        "keywords": [
            "bank", "statement", "transaction", "transfer", "wire",
            "brokerage", "balance", "deposit", "withdrawal",
        ],
    },
    {
        "doc_type": "legal",
        "keywords": [
            "lawyer", "attorney", "legal", "consultation", "retainer",
            "engagement", "malpractice", "bar",
        ],
    },
    {
        "doc_type": "correspondence",
        "keywords": ["draft", "reply", "email", "request", "inquiry", "followup"],
    },
    {
        "doc_type": "corporate",
        "keywords": [
            "llc", "corp", "formation", "ein", "articles", "operating_agreement",
            "annual_report", "registered_agent", "bylaws",
        ],
    },
]


def _load_rules() -> list[dict]:
    """Load classification rules from config file or use defaults."""
    config_path = settings.project_root / "config" / "document_types.yaml"
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        if data and "rules" in data:
            return data["rules"]
    return DEFAULT_RULES


def classify_document(filepath: Path, base_dir: Path | None = None) -> dict:
    """Classify a document by its path and filename.

    Returns metadata dict with: file_path, category, subcategory, doc_type,
    file_ext, file_name.
    """
    base = base_dir or settings.data_dir
    try:
        rel_path = filepath.relative_to(base)
    except ValueError:
        rel_path = filepath

    parts = rel_path.parts
    category = parts[0] if parts else "unknown"
    subcategory = parts[1] if len(parts) > 2 else ""

    # Match against rules
    fname = filepath.name.lower()
    doc_type = "general"
    rules = _load_rules()

    for rule in rules:
        if any(kw in fname for kw in rule["keywords"]):
            doc_type = rule["doc_type"]
            break

    return {
        "file_path": str(rel_path),
        "category": category,
        "subcategory": subcategory,
        "doc_type": doc_type,
        "file_ext": filepath.suffix.lower(),
        "file_name": filepath.name,
    }
