"""Query engine — retrieves and synthesizes answers from indexed documents."""

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

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


def resolved_embedding_config() -> dict[str, str | int | None]:
    """Return the embedding provider/model settings for the current process."""
    provider = (settings.embedding_provider or "auto").lower()
    has_key = bool(os.environ.get("OPENAI_API_KEY") or settings.openai_api_key)

    if provider == "openai" or (provider == "auto" and has_key):
        return {
            "provider": "openai",
            "model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
        }

    if provider == "huggingface":
        return {
            "provider": "huggingface",
            "model": settings.local_embedding_model,
            "dimensions": None,
        }

    return {
        "provider": "fastembed",
        "model": settings.local_embedding_model,
        "dimensions": None,
    }


def resolve_embed_model():
    """Pick the embedding model based on settings + env.

    Decision tree:
      - GUARDIAN_EMBEDDING_PROVIDER=openai     → OpenAI cloud
      - GUARDIAN_EMBEDDING_PROVIDER=fastembed  → fastembed (ONNX, local)
      - GUARDIAN_EMBEDDING_PROVIDER=huggingface→ HuggingFace (torch, local)
      - GUARDIAN_EMBEDDING_PROVIDER=local      → fastembed (legacy alias)
      - auto (default): OpenAI if a key is set, else fastembed

    fastembed is the default local runtime — runs ONNX models via a ~50 MB
    onnxruntime install instead of pulling ~1.5 GB of torch + transformers.
    Override the model name via GUARDIAN_LOCAL_EMBEDDING_MODEL.
    """
    config = resolved_embedding_config()

    if config["provider"] == "openai":
        return OpenAIEmbedding(
            model=str(config["model"]),
            dimensions=int(config["dimensions"] or settings.embedding_dimensions),
        )

    # huggingface path is kept as a fallback for users who explicitly opt
    # into it (e.g. they already have torch installed and want to use a
    # model fastembed doesn't ship).
    if config["provider"] == "huggingface":
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "HuggingFace provider requested but "
                "llama-index-embeddings-huggingface is not installed."
            ) from exc
        return HuggingFaceEmbedding(model_name=str(config["model"]))

    # Default local path: fastembed.
    try:
        from compliance_os.query.fastembed_adapter import FastEmbedEmbedding
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "fastembed is not installed. Install with: pip install fastembed — "
            "or set OPENAI_API_KEY and use the openai provider."
        ) from exc
    return FastEmbedEmbedding(model_name=str(config["model"]))


def validate_index_embedding_config(chroma_dir: Path | str | None = None) -> None:
    """Refuse to query an index built with a different embedding model."""
    path = Path(chroma_dir or settings.chroma_dir) / "index_manifest.json"
    if not path.exists():
        return

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Unable to read index manifest at {path}. Rebuild the index with "
            "index_documents(force=True)."
        ) from exc

    if not manifest.get("indexed_files"):
        return

    expected = resolved_embedding_config()
    actual = manifest.get("embedding")
    if actual == expected:
        return

    if actual is None:
        detail = "the index was built before embedding metadata was recorded"
    else:
        detail = f"index uses {actual}, current runtime uses {expected}"
    raise RuntimeError(
        "Embedding configuration mismatch: "
        f"{detail}. Rebuild with index_documents(force=True), or restore the "
        "same OPENAI_API_KEY/GUARDIAN_EMBEDDING_PROVIDER settings used when "
        "the index was built."
    )


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

        # Chroma's persistent client needs the parent directory to exist
        # before it can open the SQLite file. uv-installed extensions land
        # compliance_os in a read-only cache dir, so the chroma_dir default
        # must be under the user's home; mkdir here guards against partial
        # state where the dir was deleted between runs.
        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)

        validate_index_embedding_config(self.chroma_dir)
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
        allowed_file_paths: set[str] | None = None,
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

        semantic_filters = _build_filters(
            doc_type=doc_type,
            category=category,
            subcategory=subcategory,
        )
        scope_filters = _build_allowed_path_filter(allowed_file_paths)
        if allowed_file_paths is not None and scope_filters is None:
            return {
                "tier_used": 1,
                "tier1_count": 0,
                "results": [],
                "note": "No active documents are available for this search scope.",
                "latency_ms": int((time.time() - t0) * 1000),
            }

        filters = _combine_metadata_filters(semantic_filters, scope_filters)
        candidate_k = max(top_k, 50) if (file_name_contains or allowed_file_paths) else top_k

        tier1 = self.retrieve(query, top_k=candidate_k, filters=filters)
        tier1 = _apply_result_guards(
            tier1,
            file_name_contains=file_name_contains,
            allowed_file_paths=allowed_file_paths,
        )[:top_k]
        n1 = len(tier1)
        if n1 >= min_tier1_results or semantic_filters is None:
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

        # Tier 2: drop the semantic filters, keep the caller's visibility
        # scope, broaden the candidate pool, then rerank by recency.
        tier2 = self.retrieve(query, top_k=max(top_k * 5, 50), filters=scope_filters)
        tier2 = _apply_result_guards(
            tier2,
            file_name_contains=file_name_contains,
            allowed_file_paths=allowed_file_paths,
        )
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
) -> MetadataFilters | None:
    """Build a LlamaIndex MetadataFilters from user-facing arguments.

    Filename substring matching is applied after retrieval because LlamaIndex
    does not expose a portable metadata-substring operator for Chroma.
    """
    parts = []
    if doc_type:
        parts.append(MetadataFilter(key="doc_type", value=doc_type, operator=FilterOperator.EQ))
    if category:
        parts.append(MetadataFilter(key="category", value=category, operator=FilterOperator.EQ))
    if subcategory:
        parts.append(MetadataFilter(key="subcategory", value=subcategory, operator=FilterOperator.EQ))
    return MetadataFilters(filters=parts) if parts else None


def _build_allowed_path_filter(allowed_file_paths: set[str] | None) -> MetadataFilters | None:
    """Build a vector-store filter for the caller's visible document paths."""
    if allowed_file_paths is None:
        return None
    values = sorted({str(path) for path in allowed_file_paths if path})
    if not values:
        return None
    return MetadataFilters(
        filters=[
            MetadataFilter(
                key="file_path",
                value=values,
                operator=FilterOperator.IN,
            )
        ]
    )


def _combine_metadata_filters(
    *filter_sets: MetadataFilters | None,
) -> MetadataFilters | None:
    parts = []
    for filter_set in filter_sets:
        if filter_set is None:
            continue
        parts.extend(filter_set.filters)
    return MetadataFilters(filters=parts) if parts else None


def _apply_result_guards(
    results: list[dict],
    *,
    file_name_contains: str | None = None,
    allowed_file_paths: set[str] | None = None,
) -> list[dict]:
    """Apply caller-side filters that Chroma cannot express safely."""
    needle = (file_name_contains or "").strip().lower()
    guarded = []
    for result in results:
        metadata = result.get("metadata") or {}
        file_path = str(metadata.get("file_path") or "")
        file_name = str(metadata.get("file_name") or "")
        if allowed_file_paths is not None and file_path not in allowed_file_paths:
            continue
        if needle and needle not in file_name.lower() and needle not in file_path.lower():
            continue
        guarded.append(result)
    return guarded


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
