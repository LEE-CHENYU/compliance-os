"""Query engine — retrieves and synthesizes answers from indexed documents."""

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

        LlamaSettings.embed_model = OpenAIEmbedding(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

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
