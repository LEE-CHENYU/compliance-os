"""Public share endpoints for data-room collaborators.

Auth via share token in URL path (no user session required). Read-only,
scoped to a single folder + template.
"""

from __future__ import annotations

import io
import mimetypes
import zipfile
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from compliance_os.case_templates import H1B_TEMPLATE, match_folder
from compliance_os.case_templates.schema import Template
from compliance_os.web.services.case_summary import build_summary
from compliance_os.web.services.share_tokens import decode_share_token

router = APIRouter(prefix="/api/share", tags=["share"])


_TEMPLATES: dict[str, Template] = {
    "h1b_petition": H1B_TEMPLATE,
}


def _resolve(token: str) -> tuple[dict, Path, Template]:
    payload = decode_share_token(token)
    folder = Path(payload["folder"]).expanduser().resolve()
    if not folder.is_dir():
        raise HTTPException(404, "Shared folder no longer exists")
    template = _TEMPLATES.get(payload["template_id"])
    if template is None:
        raise HTTPException(400, f"Unknown template '{payload['template_id']}'")
    return payload, folder, template


@router.get("/{token}")
def get_share(token: str) -> dict:
    """Render the data room JSON for a share token."""
    payload, folder, template = _resolve(token)
    report = match_folder(folder, template)
    summary = build_summary(folder, template, report)

    # Serialize sections + slot details for the frontend
    sections = []
    for code, name in template.sections.items():
        slots = []
        for slot in template.slots_by_section(code):
            match = report.matched.get(slot.id)
            top = match[0] if match else None
            slots.append({
                "id": slot.id,
                "title": slot.title,
                "description": slot.description,
                "required": slot.required,
                "order": slot.order,
                "phase": slot.phase,
                "status": "matched" if top else ("missing" if slot.required else "optional_missing"),
                "file": top.file_path if top else None,
                "score": top.score if top else 0,
            })
        slots.sort(key=lambda s: (s["order"] if s["order"] > 0 else 9999, s["id"]))
        sections.append({"code": code, "name": name, "slots": slots})

    return {
        "template_id": template.id,
        "template_name": template.name,
        "recipient": payload.get("recipient", ""),
        "issuer": payload.get("issuer", ""),
        "expires_at": payload.get("exp"),
        "files_scanned": report.files_scanned,
        "coverage": report.coverage,
        "missing_required": [
            {"id": s.id, "title": s.title, "section": s.section}
            for s in report.missing_required
        ],
        "missing_optional": [
            {"id": s.id, "title": s.title, "section": s.section}
            for s in report.missing_optional
        ],
        "unmatched_files": report.unmatched_files,
        "lineage_issues": report.lineage_issues,
        "misplaced": [
            {"file": f, "current": c, "expected": e}
            for f, c, e in report.misplaced
        ],
        "sections": sections,
        "summary": summary.to_dict(),
    }


@router.get("/{token}/file/{slot_id}")
def get_file(token: str, slot_id: str):
    """Serve the file for a slot inline (PDF/image preview)."""
    _payload, folder, template = _resolve(token)
    report = match_folder(folder, template)
    match = report.matched.get(slot_id)
    if not match:
        raise HTTPException(404, f"No file matched for slot {slot_id}")

    rel = match[0].file_path
    abs_path = folder / rel
    # Defensive — ensure we don't serve outside the shared folder
    try:
        abs_path.resolve().relative_to(folder)
    except ValueError:
        raise HTTPException(403, "Path escape blocked")
    if not abs_path.is_file():
        raise HTTPException(404, "File no longer exists")

    media, _ = mimetypes.guess_type(str(abs_path))
    return FileResponse(
        abs_path,
        media_type=media or "application/octet-stream",
        filename=abs_path.name,
        headers={"Content-Disposition": f'inline; filename="{abs_path.name}"'},
    )


@router.get("/{token}/download")
def download_all(token: str):
    """Stream a zip of the entire case folder — for a one-click download."""
    _payload, folder, _template = _resolve(token)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in folder.rglob("*"):
            if not p.is_file():
                continue
            if p.name.startswith("._") or p.name.startswith("."):
                continue
            arc = p.relative_to(folder)
            zf.write(p, arcname=str(arc))
    buf.seek(0)
    fname = f"{folder.name}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
