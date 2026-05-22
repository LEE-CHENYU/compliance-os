"""Document smart-search endpoint — Tier 1 filtered RAG → Tier 2 open RAG.

Exposes ComplianceQueryEngine.smart_search() over HTTP so the web dashboard
and external integrations get the same retrieval behavior as the MCP
query_documents tool. The endpoint returns ranked chunks (no LLM
synthesis) so the caller decides how to present them.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    doc_type: str | None = None
    category: str | None = None
    subcategory: str | None = None
    file_name_contains: str | None = None
    top_k: int = Field(10, ge=1, le=50)
    min_tier1_results: int = Field(3, ge=1, le=20)
    prefer_recent: bool = True


class SearchSource(BaseModel):
    file_path: str
    file_name: str | None
    doc_type: str | None
    category: str | None
    score: float | None
    snippet: str
    tier2_match: bool = False


class SearchResponse(BaseModel):
    tier_used: int
    tier1_count: int
    note: str
    latency_ms: int
    sources: list[SearchSource]


@router.post("", response_model=SearchResponse)
def search_documents(req: SearchRequest) -> SearchResponse:
    # Import locally so the route only pulls llama-index when actually called
    # — keeps the cold-start cost off endpoints that don't need it.
    from compliance_os.query.engine import ComplianceQueryEngine

    engine = ComplianceQueryEngine()
    try:
        res = engine.smart_search(
            query=req.query,
            doc_type=req.doc_type,
            category=req.category,
            subcategory=req.subcategory,
            file_name_contains=req.file_name_contains,
            top_k=req.top_k,
            min_tier1_results=req.min_tier1_results,
            prefer_recent=req.prefer_recent,
        )
    except Exception as exc:
        msg = str(exc)
        if "does not exist" in msg or "Collection" in msg:
            raise HTTPException(
                status_code=409,
                detail=(
                    "no_index: no documents indexed yet. Upload documents "
                    "and run index_documents first."
                ),
            )
        raise HTTPException(status_code=500, detail=msg)

    sources: list[SearchSource] = []
    seen: set[str] = set()
    for c in res["results"]:
        fp = c["metadata"].get("file_path", "unknown")
        if fp in seen:
            continue
        seen.add(fp)
        sources.append(SearchSource(
            file_path=fp,
            file_name=c["metadata"].get("file_name"),
            doc_type=c["metadata"].get("doc_type"),
            category=c["metadata"].get("category"),
            score=c.get("final_score") or c.get("score"),
            snippet=(c.get("text") or "")[:280],
            tier2_match=bool(c.get("tier2_match", False)),
        ))

    return SearchResponse(
        tier_used=res["tier_used"],
        tier1_count=res["tier1_count"],
        note=res["note"],
        latency_ms=res["latency_ms"],
        sources=sources,
    )
