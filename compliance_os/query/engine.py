"""Query engine — retrieves and synthesizes answers from indexed documents."""

import math
import os
import time
from datetime import datetime, timezone

import chromadb
from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore

from compliance_os.settings import settings


def resolve_embed_model():
    """Pick the embedding model based on settings + env.

    Decision tree:
      - GUARDIAN_EMBEDDING_PROVIDER=openai → OpenAI (errors out without a key)
      - GUARDIAN_EMBEDDING_PROVIDER=local  → HuggingFace local model
      - auto (default): OpenAI if OPENAI_API_KEY is set, else local

    Local model defaults to BAAI/bge-small-en-v1.5 (winner of the bakeoff;
    overridable via GUARDIAN_LOCAL_EMBEDDING_MODEL).
    """
    provider = (settings.embedding_provider or "auto").lower()
    has_key = bool(os.environ.get("OPENAI_API_KEY") or settings.openai_api_key)

    if provider == "openai" or (provider == "auto" and has_key):
        return OpenAIEmbedding(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    # Local fallback. Import lazily so users on the openai path don't have to
    # install huggingface deps.
    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    except ImportError as exc:  # pragma: no cover — surfaced at runtime
        raise RuntimeError(
            "Local embedding requested but llama-index-embeddings-huggingface "
            "is not installed. Install with: pip install "
            "'compliance-os[local-embed]' — or set OPENAI_API_KEY and use the "
            "openai provider."
        ) from exc
    return HuggingFaceEmbedding(model_name=settings.local_embedding_model)


SYSTEM_PROMPT = """You are a compliance assistant helping an individual manage tax,
immigration, corporate, and financial documents. Answer questions based ONLY on the
retrieved document context. Always cite the source file path.

If the context doesn't contain enough information, say so clearly and suggest what
documents might help.

Rules:
- When discussing deadlines, be explicit about dates and whether they are past due.
- When discussing amounts, be precise with numbers.
- When discussing legal/tax matters, note this is informational only — not legal or tax advice.
- Never fabricate information not present in the source documents."""

VALID_FILTER_KEYS = {"doc_type", "category", "subcategory", "file_ext", "file_name"}


class ComplianceQueryEngine:
    """Query interface for the compliance document store."""

    def __init__(self, chroma_dir=None):
        self.chroma_dir = chroma_dir or settings.chroma_dir
        self._index = None

    def _get_index(self) -> VectorStoreIndex:
        """Lazy-load the vector store index."""
        if self._index is not None:
            return self._index

        LlamaSettings.embed_model = resolve_embed_model()

        chroma_client = chromadb.PersistentClient(path=str(self.chroma_dir))
        chroma_collection = chroma_client.get_collection(name=settings.collection_name)
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        self._index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        return self._index

    @staticmethod
    def parse_filters(filter_strs: list[str]) -> MetadataFilters | None:
        """Parse KEY=VAL filter strings into LlamaIndex metadata filters."""
        if not filter_strs:
            return None
        filters = []
        for f in filter_strs:
            if "=" not in f:
                continue
            key, val = f.split("=", 1)
            if key not in VALID_FILTER_KEYS:
                continue
            filters.append(MetadataFilter(key=key, value=val, operator=FilterOperator.EQ))
        return MetadataFilters(filters=filters) if filters else None

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filters: MetadataFilters | None = None,
    ) -> list[dict]:
        """Retrieve matching document chunks without LLM synthesis.

        Returns list of dicts with: text, score, metadata.
        """
        index = self._get_index()
        retriever = index.as_retriever(
            similarity_top_k=top_k or settings.default_top_k,
            filters=filters,
        )
        nodes = retriever.retrieve(query)
        return [
            {
                "text": node.text,
                "score": node.score,
                "metadata": node.metadata,
            }
            for node in nodes
        ]

    def query(
        self,
        query: str,
        top_k: int | None = None,
        filters: MetadataFilters | None = None,
    ) -> dict:
        """Query with LLM synthesis — retrieves context and generates an answer.

        Returns dict with: answer, sources.
        """
        LlamaSettings.llm = OpenAI(
            model=settings.llm_model,
            temperature=0,
            system_prompt=SYSTEM_PROMPT,
        )

        index = self._get_index()
        query_engine = index.as_query_engine(
            similarity_top_k=top_k or settings.default_top_k,
            filters=filters,
            response_mode="tree_summarize",
        )
        response = query_engine.query(query)

        sources = []
        seen = set()
        for node in (response.source_nodes or []):
            fp = node.metadata.get("file_path", "unknown")
            if fp not in seen:
                sources.append({
                    "file_path": fp,
                    "score": node.score,
                    "doc_type": node.metadata.get("doc_type", "unknown"),
                })
                seen.add(fp)

        return {
            "answer": response.response,
            "sources": sources,
        }

    # ────────────────────────────────────────────────────────
    #  Smart search — Tier 1 metadata-filter RAG → Tier 2 open
    #  RAG with recency rerank. Mirrors stock_journal's
    #  smart_search escalation: cheap filtered retrieval first,
    #  fall back to broader semantic search only if Tier 1 is
    #  thin. Returns raw chunks (no LLM synthesis) so the caller
    #  can decide whether to feed them to an LLM.
    # ────────────────────────────────────────────────────────

    def smart_search(
        self,
        query: str,
        doc_type: str | None = None,
        category: str | None = None,
        subcategory: str | None = None,
        file_name_contains: str | None = None,
        top_k: int = 10,
        min_tier1_results: int = 3,
        prefer_recent: bool = True,
        recency_half_life_days: float = 180.0,
    ) -> dict:
        """Auto-escalating retrieval: filtered RAG → open RAG with recency rerank.

        Tier 1: semantic search restricted to chunks whose metadata matches
                the user's filters (doc_type, category, etc.). Cheap because
                the vector store narrows the candidate pool before scoring.
        Tier 2: semantic search across the whole index, then a soft recency
                rerank (file mtime) so freshly uploaded docs beat older ones
                of equal similarity. Only runs when Tier 1 is thin.

        Returns:
            {
              tier_used: 1 | 2,
              tier1_count: int,
              results: [{ text, score, metadata, recency_score?, final_score? }, ...],
              note: str,
              latency_ms: int,
            }
        """
        t0 = time.time()

        filters = _build_filters(
            doc_type=doc_type,
            category=category,
            subcategory=subcategory,
            file_name_contains=file_name_contains,
        )

        tier1 = self.retrieve(query, top_k=top_k, filters=filters)
        n1 = len(tier1)
        if n1 >= min_tier1_results or not filters:
            # Either Tier 1 was sufficient, or there were no filters to relax
            # (an open query that hit Tier 1 thin would just rerun the same
            # search in Tier 2, so short-circuit).
            results = _recency_rerank(tier1, half_life_days=recency_half_life_days) if prefer_recent else tier1
            return {
                "tier_used": 1,
                "tier1_count": n1,
                "results": results,
                "note": f"Tier 1 returned {n1} results.",
                "latency_ms": int((time.time() - t0) * 1000),
            }

        # Tier 2: drop the filters, broaden the candidate pool, then rerank
        # by similarity * recency-decay.
        tier2 = self.retrieve(query, top_k=max(top_k * 2, 20), filters=None)
        if prefer_recent:
            tier2 = _recency_rerank(tier2, half_life_days=recency_half_life_days)

        # Merge: Tier 1 first (filtered, high precision), then unique Tier 2
        # additions. Dedup on file_path because the same file can chunk
        # multiple times.
        seen_paths = {r["metadata"].get("file_path") for r in tier1}
        combined = list(tier1)
        for r in tier2:
            fp = r["metadata"].get("file_path")
            if fp in seen_paths:
                continue
            r["tier2_match"] = True
            combined.append(r)
            seen_paths.add(fp)
            if len(combined) >= top_k:
                break

        return {
            "tier_used": 2,
            "tier1_count": n1,
            "results": combined[:top_k],
            "note": f"Tier 1 sparse ({n1}); broadened to Tier 2.",
            "latency_ms": int((time.time() - t0) * 1000),
        }


# ─── Helpers ────────────────────────────────────────────────


def _build_filters(
    doc_type: str | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    file_name_contains: str | None = None,
) -> MetadataFilters | None:
    """Build a LlamaIndex MetadataFilters from user-facing arguments.

    file_name_contains is rendered as an EQ filter on file_name; LlamaIndex
    doesn't expose a substring operator across all vector stores, and Chroma's
    `where_document` is content-only. Callers that need substring matching
    should filter the results post-hoc.
    """
    parts = []
    if doc_type:
        parts.append(MetadataFilter(key="doc_type", value=doc_type, operator=FilterOperator.EQ))
    if category:
        parts.append(MetadataFilter(key="category", value=category, operator=FilterOperator.EQ))
    if subcategory:
        parts.append(MetadataFilter(key="subcategory", value=subcategory, operator=FilterOperator.EQ))
    if file_name_contains:
        parts.append(MetadataFilter(key="file_name", value=file_name_contains, operator=FilterOperator.EQ))
    return MetadataFilters(filters=parts) if parts else None


def _recency_rerank(
    results: list[dict],
    half_life_days: float = 180.0,
    sim_weight: float = 0.7,
    rec_weight: float = 0.3,
) -> list[dict]:
    """Rerank chunks by similarity blended with file-mtime recency decay.

    Docs without a resolvable mtime keep their raw similarity; the rerank
    only nudges ties. Half-life of 180 days matches the typical refresh
    cadence of compliance docs (annual tax forms, multi-year visa stamps).
    """
    now = datetime.now(timezone.utc).timestamp()
    rescored = []
    for r in results:
        sim = float(r.get("score") or 0.0)
        mtime = _resolve_mtime(r["metadata"].get("file_path"))
        if mtime is None:
            r["recency_score"] = None
            r["final_score"] = sim
            rescored.append(r)
            continue
        age_days = max(0.0, (now - mtime) / 86400.0)
        decay = math.exp(-age_days / half_life_days)
        r["recency_score"] = decay
        r["final_score"] = sim_weight * sim + rec_weight * sim * decay
        rescored.append(r)
    rescored.sort(key=lambda r: r["final_score"], reverse=True)
    return rescored


def _resolve_mtime(file_path: str | None) -> float | None:
    if not file_path:
        return None
    try:
        return os.path.getmtime(file_path)
    except OSError:
        return None
