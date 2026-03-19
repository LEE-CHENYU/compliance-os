"""FastAPI app for the Compliance OS MVP workbench."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from compliance_os.web.demo_data import DemoWorkspaceStore


class AssistantRequest(BaseModel):
    prompt: str
    concern_id: str | None = None


class DraftRequest(BaseModel):
    concern_id: str


STATIC_DIR = Path(__file__).parent / "static"
store = DemoWorkspaceStore()

app = FastAPI(
    title="Compliance OS MVP",
    description="Seeded compliance workbench with concerns, Gmail context, and deterministic risks.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/api/workspace")
def get_workspace() -> dict:
    return store.workspace()


@app.post("/api/assistant")
def assistant_reply(request: AssistantRequest) -> dict:
    try:
        return store.assistant_reply(request.prompt, request.concern_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown concern: {exc.args[0]}") from exc


@app.post("/api/drafts")
def create_draft(request: DraftRequest) -> dict:
    try:
        return store.create_draft(request.concern_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown concern: {exc.args[0]}") from exc


@app.post("/api/drafts/{draft_id}/send")
def send_draft(draft_id: str) -> dict:
    try:
        return store.send_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown draft: {exc.args[0]}") from exc

