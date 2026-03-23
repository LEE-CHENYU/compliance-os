"""FastAPI app for the Compliance OS MVP workbench."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compliance_os.web.models.database import get_engine
from compliance_os.web.routers import cases, discovery, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    get_engine()
    yield


app = FastAPI(
    title="Compliance OS API",
    description="Compliance copilot backend — discovery, document management, and review.",
    lifespan=lifespan,
)

# CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(cases.router)
app.include_router(discovery.router)
app.include_router(documents.router)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
