# RAG & Memory Layer Research for Document Repository
**Date:** 2026-03-11
**Purpose:** Evaluate open-source frameworks for building a retrieval/memory layer over this accounting repo (PDFs, text files, CSVs — tax forms, legal docs, immigration records, financial statements).

---

## Full RAG Frameworks

| Framework | Stars | Best For | Local Embeddings | PDF/CSV/TXT |
|-----------|-------|----------|-----------------|-------------|
| **LangChain** | ~125K | Largest ecosystem, complex multi-step pipelines | Yes (HuggingFace, Ollama) | Yes |
| **Dify** | ~114K | Visual no-code RAG builder with web UI | Yes (Ollama) | Yes |
| **RAGFlow** | ~70K | Best PDF parsing (OCR, tables, layouts) — Docker-based | Yes | Yes (best-in-class PDF) |
| **LlamaIndex** | ~46.5K | Purpose-built for document indexing/retrieval | Yes (HuggingFace, Ollama) | Yes |
| **LightRAG** | ~27K | Graph-based retrieval, runs on CPU/laptop | Yes | Yes |
| **Haystack** | ~24K | Production-grade, modular pipelines | Yes (HuggingFace) | Yes |
| **txtai** | ~10K | All-in-one, fully local, zero API keys needed | Yes (default) | Yes |
| **LLMWare** | ~10K | Runs on CPU with small specialized models, zero-config | Yes (ships own models) | Yes |

## Vector Databases

| DB | Stars | Notes |
|----|-------|-------|
| **Milvus** | ~42.5K | Enterprise-scale, billions of vectors |
| **FAISS** (Meta) | ~37K | Raw speed, library not DB, no persistence |
| **Qdrant** | ~29K | Rust-based, great filtering, good for personal use |
| **ChromaDB** | ~26.5K | Simplest setup — `pip install` and go, built-in embeddings |
| **Weaviate** | ~15.8K | Built-in vectorization, hybrid search |

## Memory / Knowledge Graph

| Tool | Stars | Notes |
|------|-------|-------|
| **Mem0** | ~37K | Hybrid vector + graph memory, 26% accuracy boost over standard RAG |
| **Graphiti** (Zep) | ~20K | Temporal knowledge graph — tracks when facts become true/false |

## Document Processing

| Tool | Stars | Notes |
|------|-------|-------|
| **Docling** (IBM) | ~20K | 97.9% accuracy on table extraction, best PDF parser |
| **Unstructured** | ~10K | Broad format support, ETL for documents |

## Personal Knowledge Management

- **Khoj** (~25K stars) — self-hostable "AI second brain", reads PDFs/Markdown/repos, built-in RAG + chat UI, connects to Ollama for fully local operation

---

## Recommendations for This Repo

**Quickest to get running:**
- **txtai** — single `pip install`, fully local, no API keys, handles all formats

**Best document quality (PDFs with tables/forms):**
- **RAGFlow** — deep document understanding with OCR, best at extracting structured data from tax forms and financial PDFs

**Best personal knowledge base:**
- **Khoj** — designed exactly for this: index a personal document folder, query via chat

**Most flexible for building custom tools:**
- **LlamaIndex + ChromaDB + Docling** — LlamaIndex for RAG pipeline, ChromaDB for vector storage, Docling for parsing complex PDFs

**For evolving knowledge (deadlines, status changes):**
- **Graphiti** — temporal awareness tracks when facts change over time, uniquely suited for deadlines, statuses, and action items that evolve
