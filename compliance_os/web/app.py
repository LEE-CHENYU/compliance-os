"""FastAPI app for the Compliance OS MVP workbench."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from compliance_os.web.models.database import get_engine
from compliance_os.web.routers import cases, discovery, documents
from compliance_os.web.routers import checks as checks_v2, extraction, review
from compliance_os.web.routers import auth as auth_router
from compliance_os.web.routers import dashboard


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
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://*.fly.dev"],
    allow_origin_regex=r"https://.*\.fly\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Catch unhandled exceptions and return JSON with CORS headers
from fastapi.responses import JSONResponse
from starlette.requests import Request


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

# Mount routers
app.include_router(cases.router)
app.include_router(discovery.router)
app.include_router(documents.router)

# Guardian check flow (v2)
app.include_router(checks_v2.router)
app.include_router(extraction.router)
app.include_router(review.router)
app.include_router(auth_router.router)
app.include_router(dashboard.router)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}
