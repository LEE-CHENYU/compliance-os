"""Document indexer — scans a directory, embeds documents, and stores in ChromaDB.

Supports incremental indexing via a manifest that tracks file hashes. Only
changed or new files are re-embedded on subsequent runs.
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime

import chromadb
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings as LlamaSettings,
    Document,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from compliance_os.settings import settings
from compliance_os.indexer.classifier import classify_document


class DocumentIndexer:
    """Indexes documents from a directory into a ChromaDB vector store."""

    def __init__(self, data_dir: Path | None = None, chroma_dir: Path | None = None):
        self.data_dir = data_dir or settings.data_dir
        self.chroma_dir = chroma_dir or settings.chroma_dir
        self.manifest_path = self.chroma_dir / "index_manifest.json"

    def _get_file_hash(self, filepath: Path) -> str:
        h = hashlib.md5()
        h.update(filepath.read_bytes())
        return h.hexdigest()

    def _should_skip(self, path: Path) -> bool:
        for part in path.parts:
            if part in settings.skip_patterns:
                return True
        return False

    def collect_documents(self, directories: list[str] | None = None) -> list[Path]:
        """Collect all indexable documents from the data directory.

        Args:
            directories: Optional list of subdirectories to scan. If None,
                        scans all top-level directories in data_dir.
        """
        documents = []
        if directories:
            scan_dirs = [self.data_dir / d for d in directories]
        else:
            scan_dirs = [
                p for p in self.data_dir.iterdir()
                if p.is_dir() and not self._should_skip(p)
            ]

        for dir_path in scan_dirs:
            if not dir_path.exists():
                continue
            for filepath in dir_path.rglob("*"):
                if not filepath.is_file():
                    continue
                if self._should_skip(filepath):
                    continue
                if filepath.suffix.lower() not in settings.index_extensions:
                    continue
                if filepath.stat().st_size > settings.max_file_size:
                    continue
                documents.append(filepath)
        return sorted(documents)

    def _load_manifest(self) -> dict:
        if self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text())
        return {"indexed_files": {}, "last_run": None}

    def _save_manifest(self, manifest: dict):
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=2))

    def _read_file(self, filepath: Path) -> str | None:
        """Read file content, handling different formats.

        Uses PyMuPDF for PDFs (more robust than pypdf for scanned/complex
        documents) and python-docx for DOCX files.
        """
        ext = filepath.suffix.lower()
        if ext == ".pdf":
            try:
                import pymupdf

                doc = pymupdf.open(str(filepath))
                pages = []
                for page in doc:
                    text = page.get_text()
                    if text and text.strip():
                        pages.append(text)
                doc.close()
                return "\n\n".join(pages) if pages else None
            except Exception:
                return None
        if ext == ".docx":
            try:
                from compliance_os.web.services.docx_reader import extract_text

                return extract_text(str(filepath)) or None
            except Exception:
                return None
        try:
            return filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    def build_index(
        self,
        force: bool = False,
        directories: list[str] | None = None,
        verbose: bool = True,
    ) -> dict:
        """Build or update the vector index.

        Args:
            force: If True, re-index all documents regardless of cache.
            directories: Optional list of subdirectories to index.
            verbose: Print progress to stdout.

        Returns:
            Summary dict with counts and metadata.
        """
        file_paths = self.collect_documents(directories)
        if verbose:
            print(f"Found {len(file_paths)} indexable documents")

        manifest = self._load_manifest()
        indexed = manifest["indexed_files"]

        # Determine what needs indexing
        to_index = []
        for fp in file_paths:
            rel = str(fp.relative_to(self.data_dir))
            file_hash = self._get_file_hash(fp)
            if force or rel not in indexed or indexed[rel] != file_hash:
                to_index.append((fp, file_hash))

        if not to_index and not force:
            if verbose:
                print("All documents are up to date.")
            return {"indexed": 0, "skipped": 0, "chunks": 0, "up_to_date": True}

        if verbose:
            print(f"Indexing {len(to_index)} documents...")

        # Configure LlamaIndex
        LlamaSettings.embed_model = OpenAIEmbedding(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
        LlamaSettings.chunk_size = settings.chunk_size
        LlamaSettings.chunk_overlap = settings.chunk_overlap

        # Set up ChromaDB
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=str(self.chroma_dir))

        if force:
            try:
                chroma_client.delete_collection(settings.collection_name)
            except Exception:
                pass
            indexed = {}

        chroma_collection = chroma_client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Process documents
        all_nodes = []
        splitter = SentenceSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        success_count = 0
        fail_count = 0

        for i, (filepath, file_hash) in enumerate(to_index):
            rel_path = filepath.relative_to(self.data_dir)
            if verbose:
                print(f"  [{i+1}/{len(to_index)}] {rel_path}", end=" ... ")

            content = self._read_file(filepath)
            if not content or len(content.strip()) < 10:
                if verbose:
                    print("SKIP (empty)")
                fail_count += 1
                continue

            metadata = classify_document(filepath, self.data_dir)
            doc = Document(
                text=content,
                metadata=metadata,
                excluded_llm_metadata_keys=["file_path"],
                excluded_embed_metadata_keys=["file_path"],
            )
            nodes = splitter.get_nodes_from_documents([doc])
            all_nodes.extend(nodes)
            indexed[str(rel_path)] = file_hash
            success_count += 1
            if verbose:
                print(f"OK ({len(nodes)} chunks)")

        if all_nodes:
            if verbose:
                print(f"\nEmbedding {len(all_nodes)} chunks...")
            VectorStoreIndex(
                nodes=all_nodes,
                storage_context=storage_context,
                show_progress=verbose,
            )

        # Save manifest
        manifest["indexed_files"] = indexed
        manifest["last_run"] = datetime.now().isoformat()
        manifest["total_documents"] = len(indexed)
        manifest["total_chunks"] = len(all_nodes)
        self._save_manifest(manifest)

        summary = {
            "indexed": success_count,
            "skipped": fail_count,
            "chunks": len(all_nodes),
            "up_to_date": False,
        }
        if verbose:
            print(f"\nIndexed: {success_count} | Skipped: {fail_count} | Chunks: {len(all_nodes)}")
        return summary
