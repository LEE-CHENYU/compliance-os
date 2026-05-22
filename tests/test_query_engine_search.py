import json

import pytest

from compliance_os.query.engine import (
    ComplianceQueryEngine,
    validate_index_embedding_config,
)
from compliance_os.settings import settings


class DummySearchEngine(ComplianceQueryEngine):
    def __init__(self, results: list[dict]):
        self.results = results

    def retrieve(self, query: str, top_k: int | None = None, filters=None) -> list[dict]:
        return self.results[:top_k]


def _result(file_path: str, file_name: str) -> dict:
    return {
        "text": f"text for {file_name}",
        "score": 0.8,
        "metadata": {
            "file_path": file_path,
            "file_name": file_name,
            "doc_type": "immigration",
        },
    }


def test_smart_search_filters_file_name_by_substring():
    engine = DummySearchEngine([
        _result("uploads/i20.pdf", "i20.pdf"),
        _result("uploads/passport_scan.pdf", "passport_scan.pdf"),
    ])

    result = engine.smart_search(
        "passport",
        file_name_contains="passport",
        prefer_recent=False,
    )

    assert [r["metadata"]["file_name"] for r in result["results"]] == ["passport_scan.pdf"]


def test_smart_search_filters_to_allowed_file_paths():
    engine = DummySearchEngine([
        _result("uploads/a.pdf", "a.pdf"),
        _result("uploads/b.pdf", "b.pdf"),
    ])

    result = engine.smart_search(
        "document",
        allowed_file_paths={"uploads/b.pdf"},
        prefer_recent=False,
    )

    assert [r["metadata"]["file_path"] for r in result["results"]] == ["uploads/b.pdf"]


def test_embedding_manifest_mismatch_requires_reindex(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(settings, "embedding_provider", "auto")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "local_embedding_model", "BAAI/bge-small-en-v1.5")
    (tmp_path / "index_manifest.json").write_text(json.dumps({
        "indexed_files": {"uploads/a.pdf": "hash"},
        "embedding": {
            "provider": "openai",
            "model": "text-embedding-3-small",
            "dimensions": 1536,
        },
    }))

    with pytest.raises(RuntimeError, match="Embedding configuration mismatch"):
        validate_index_embedding_config(tmp_path)


def test_legacy_embedding_manifest_requires_reindex(tmp_path):
    (tmp_path / "index_manifest.json").write_text(json.dumps({
        "indexed_files": {"uploads/a.pdf": "hash"},
    }))

    with pytest.raises(RuntimeError, match="before embedding metadata"):
        validate_index_embedding_config(tmp_path)
