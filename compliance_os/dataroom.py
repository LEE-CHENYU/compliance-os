"""Canonical on-disk data room: a category/doc-type folder tree + a
file↔data manifest.

The flat upload store (``~/.guardian/uploads/<check_id>/<uuid>_<name>``) stays
the physical source of truth. This module derives a human-browsable mirror —
``~/.guardian/data-room/<category>/<doc_type>/<filename>`` — by **copying**
(never moving) each active document into a canonical taxonomy, and writes the
mapping between files and their data:

  * ``manifest.json`` — machine-readable: every file → doc id, type, category,
    chains, content hash, the fields extracted from it, and the canonical
    source-of-truth facts it asserted.
  * ``INDEX.md``     — the same mapping as a human-readable index.

``sync_data_room`` is idempotent and cheap (hash-compare before copy), so the
write tools call it after every upload / fact-recording — the tree is actively
maintained, not built on demand. ``build_data_room`` (the MCP tool) just runs
the same sync explicitly.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

# Categories mirror the canonical fact vocabulary (immigration / tax /
# corporate / personal / employment / education) + "other" as the fallback.
# Doc types with mapped extraction fields are categorized by majority vote
# over their mapped facts' categories; these overrides cover common types
# whose extraction mapping is absent or unrepresentative.
CATEGORY_OVERRIDES: dict[str, str] = {
    "w2": "tax", "1040_nr": "tax", "form_8843": "tax", "fbar": "tax",
    "bank_statement": "tax", "brokerage_statement": "tax",
    "annual_account_summary": "tax",
    "paystub": "employment", "employment_letter": "employment",
    "offer_letter": "employment",
    "degree_certificate": "education", "transcript": "education",
    "admission_letter": "education", "enrollment_verification": "education",
    "language_test_certificate": "education",
    "articles_of_organization": "corporate", "ein_letter": "corporate",
    "certificate_of_good_standing": "corporate", "business_license": "corporate",
    "company_filing": "corporate", "operating_agreement": "corporate",
    "passport": "personal", "drivers_license": "personal",
    "identity_document": "personal", "insurance_card": "personal",
    "insurance_record": "personal",
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ ()\[\]-]+")


def dataroom_root() -> Path:
    """The canonical tree root: GUARDIAN_DATAROOM_DIR, else
    <GUARDIAN_HOME or ~/.guardian>/data-room. Resolved from env LIVE."""
    explicit = os.environ.get("GUARDIAN_DATAROOM_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    home = Path(os.environ.get("GUARDIAN_HOME") or (Path.home() / ".guardian"))
    return (home / "data-room").resolve()


def category_for_doc_type(doc_type: str) -> str:
    """Canonical category for a doc type: explicit override, else majority
    vote over the categories of the facts its fields map to, else 'other'."""
    doc_type = (doc_type or "").lower()
    if doc_type in CATEGORY_OVERRIDES:
        return CATEGORY_OVERRIDES[doc_type]
    from compliance_os.facts.extraction_map import schema_for_doc_type
    from compliance_os.facts.vocabulary import resolve_fact_def

    votes: Counter[str] = Counter()
    for field in schema_for_doc_type(doc_type):
        fd = resolve_fact_def(field.get("fact_key", ""))
        if fd is not None and getattr(fd, "category", None):
            votes[fd.category] += 1
    if votes:
        return votes.most_common(1)[0][0]
    return "other"


_CHAINS_CACHE: dict[str, list[str]] | None = None


def chains_for_doc_type(doc_type: str) -> list[str]:
    """Which document chains (stem_opt / h1b / tax / corporate) include this
    doc type, per document_chains.yaml."""
    global _CHAINS_CACHE
    if _CHAINS_CACHE is None:
        import yaml
        spec_path = Path(__file__).parent / "compliance" / "document_chains.yaml"
        try:
            spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
        except Exception:
            spec = {}
        mapping: dict[str, list[str]] = {}
        for chain_id, chain in (spec.get("chains") or {}).items():
            for d in chain.get("documents") or []:
                mapping.setdefault(str(d.get("doc_type", "")).lower(), []).append(chain_id)
        _CHAINS_CACHE = mapping
    return _CHAINS_CACHE.get((doc_type or "").lower(), [])


def _safe_filename(name: str) -> str:
    base = Path(name or "document").name  # strip any path components
    base = _SAFE_NAME.sub("_", base).strip(" .") or "document"
    return base


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _unwrap(value):
    return value["v"] if isinstance(value, dict) and "v" in value else value


def sync_data_room(db: Session, user_id: str) -> dict:
    """Mirror every active document into the canonical tree (COPY, never move)
    and rewrite manifest.json + INDEX.md. Idempotent; returns a summary."""
    from compliance_os.web.models.tables_v2 import DocumentRow
    from compliance_os.web.services.user_facts import get_active_facts

    root = dataroom_root()
    root.mkdir(parents=True, exist_ok=True)

    # Facts grouped by originating document (source_ref.document_id).
    fact_rows = get_active_facts(db, user_id=user_id)
    facts_by_doc: dict[str, dict] = {}
    for r in fact_rows:
        doc_id = (r.source_ref or {}).get("document_id")
        if doc_id:
            facts_by_doc.setdefault(doc_id, {})[r.fact_key] = _unwrap(r.value)

    docs = (
        db.query(DocumentRow)
        .filter(DocumentRow.is_active.is_(True))
        .order_by(DocumentRow.uploaded_at)
        .all()
    )

    entries: list[dict] = []
    claimed: dict[str, str] = {}  # relative target path -> doc_id
    copied = updated = unchanged = missing = 0
    categories: Counter[str] = Counter()

    for doc in docs:
        category = category_for_doc_type(doc.doc_type)
        categories[category] += 1
        filename = _safe_filename(doc.filename or "")
        rel = Path(category) / (doc.doc_type or "unknown") / filename
        if claimed.get(str(rel)) not in (None, doc.id):
            rel = rel.with_name(f"{doc.id[:8]}_{rel.name}")
        claimed[str(rel)] = doc.id

        entry: dict = {
            "path": str(rel),
            "doc_id": doc.id,
            "doc_type": doc.doc_type,
            "category": category,
            "chains": chains_for_doc_type(doc.doc_type),
            "original_filename": doc.filename,
            "stored_at": doc.file_path,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "version": doc.document_version,
            "extracted_fields": {
                ef.field_name: ef.field_value for ef in (doc.extracted_fields or [])
            },
            "facts": facts_by_doc.get(doc.id, {}),
        }

        source = Path(doc.file_path) if doc.file_path else None
        target = root / rel
        if source is None or not source.exists():
            missing += 1
            entry["file_missing"] = True
        else:
            src_hash = doc.content_hash if (doc.content_hash and len(doc.content_hash) == 64) else _sha256(source)
            entry["sha256"] = src_hash
            entry["size"] = source.stat().st_size
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)  # COPY — the upload store keeps the original
                copied += 1
            elif _sha256(target) != src_hash:
                shutil.copy2(source, target)
                updated += 1
            else:
                unchanged += 1
        entries.append(entry)

    manifest = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "note": "Canonical mirror of the Guardian data room. Files are COPIES; "
                "originals remain in the upload store.",
        "files": entries,
        "facts_snapshot": {r.fact_key: _unwrap(r.value) for r in fact_rows},
    }
    manifest_path = root / "manifest.json"
    tmp = manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    tmp.replace(manifest_path)

    (root / "INDEX.md").write_text(_render_index(manifest), encoding="utf-8")

    return {
        "root": str(root),
        "manifest": str(manifest_path),
        "total": len(entries),
        "copied": copied,
        "updated": updated,
        "unchanged": unchanged,
        "missing_source": missing,
        "categories": dict(categories),
    }


def _render_index(manifest: dict) -> str:
    """Human-readable index: the file→data mapping as Markdown."""
    lines = [
        "# Guardian Data Room",
        "",
        f"_Generated {manifest['generated_at']} — files are copies; originals stay in the upload store._",
        "",
    ]
    by_cat: dict[str, list[dict]] = {}
    for e in manifest["files"]:
        by_cat.setdefault(e["category"], []).append(e)
    for cat in sorted(by_cat):
        lines += [f"## {cat.title()}", ""]
        lines += ["| File | Type | Chains | Extracted | Facts asserted |", "|---|---|---|---|---|"]
        for e in sorted(by_cat[cat], key=lambda x: x["path"]):
            extracted = ", ".join(f"{k}={v}" for k, v in list(e["extracted_fields"].items())[:4]) or "—"
            facts = ", ".join(f"{k}={v}" for k, v in list(e["facts"].items())[:4]) or "—"
            chains = ", ".join(e["chains"]) or "—"
            cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
            lines.append(
                f"| `{cell(e['path'])}` | {cell(e['doc_type'])} | {cell(chains)} "
                f"| {cell(extracted)} | {cell(facts)} |"
            )
        lines.append("")
    if not manifest["files"]:
        lines.append("_No documents yet — upload one and it will be filed here._")
    return "\n".join(lines)
