"""Embedding-model bakeoff for the compliance corpus.

Runs the same 22-question search eval across multiple embedding models so
we can choose a sensible default for the no-OpenAI-key fallback path.
Each candidate gets its own scratch ChromaDB so we don't mix vector
spaces.

Candidates (override with --candidates):

  - openai:text-embedding-3-small   1536d, cloud — baseline, needs OPENAI_API_KEY
  - local:BAAI/bge-small-en-v1.5    384d, ~130 MB on disk after first download
  - local:BAAI/bge-base-en-v1.5     768d, ~440 MB
  - local:sentence-transformers/all-MiniLM-L6-v2  384d, ~80 MB
  - local:intfloat/e5-small-v2      384d, ~130 MB

We score smart_search() because that's what users actually hit in
production. Latency is reported per question (median ms) so the bakeoff
captures both quality and cost.

Run from project root:
    /Users/lichenyu/miniconda3/envs/compliance-os/bin/python \
        tests/eval/embedding_bakeoff.py
"""

from __future__ import annotations

import os
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from compliance_os.indexer.index import DocumentIndexer  # noqa: E402
from compliance_os.query.engine import ComplianceQueryEngine  # noqa: E402
from compliance_os.settings import settings as default_settings  # noqa: E402
from tests.eval.fixtures import write_fixtures  # noqa: E402
from tests.eval.search_eval import QUESTIONS, _dedup_by_stem, score  # noqa: E402


CANDIDATES: list[tuple[str, str]] = [
    # (label, "provider:model")
    ("openai_3small", "openai:text-embedding-3-small"),
    ("bge_small",     "local:BAAI/bge-small-en-v1.5"),
    ("bge_base",      "local:BAAI/bge-base-en-v1.5"),
    ("minilm_l6",     "local:sentence-transformers/all-MiniLM-L6-v2"),
    ("e5_small",      "local:intfloat/e5-small-v2"),
]


def _configure(provider_spec: str) -> None:
    """Mutate default_settings so resolve_embed_model() picks this candidate."""
    provider, _, model_name = provider_spec.partition(":")
    if provider == "openai":
        default_settings.embedding_provider = "openai"
        default_settings.embedding_model = model_name
        default_settings.embedding_dimensions = 1536
    elif provider == "local":
        default_settings.embedding_provider = "local"
        default_settings.local_embedding_model = model_name
    else:
        raise ValueError(f"unknown provider: {provider}")


def _run_smart(engine: ComplianceQueryEngine, q: dict) -> tuple[list[str], int]:
    res = engine.smart_search(
        query=q["query"],
        doc_type=q.get("doc_type"),
        top_k=10,
        min_tier1_results=3,
        prefer_recent=True,
    )
    return _dedup_by_stem(res["results"]), res["latency_ms"]


def run_one(label: str, provider_spec: str, fixtures_dir: Path) -> dict:
    """Build a fresh index for this embedding, then score the full bank."""
    tmp = Path(tempfile.mkdtemp(prefix=f"bakeoff_{label}_"))
    chroma_dir = tmp / "chroma_db"
    chroma_dir.mkdir()
    try:
        default_settings.chroma_dir = chroma_dir
        _configure(provider_spec)

        t0 = time.time()
        indexer = DocumentIndexer(data_dir=fixtures_dir, chroma_dir=chroma_dir)
        indexer.build_index(force=True, verbose=False)
        index_ms = (time.time() - t0) * 1000

        engine = ComplianceQueryEngine(chroma_dir=chroma_dir)

        top1s, recalls, precs, lats = [], [], [], []
        for q in QUESTIONS:
            try:
                returned, lat = _run_smart(engine, q)
            except Exception as exc:
                print(f"  [{label}] {q['id']} ERROR: {exc}")
                returned, lat = [], 0
            t1, rec, prec = score(returned, q["gt"])
            if t1 is not None:
                top1s.append(t1)
            if rec is not None:
                recalls.append(rec)
            if prec is not None:
                precs.append(prec)
            lats.append(lat)

        return {
            "label": label,
            "spec": provider_spec,
            "top1": sum(top1s) / len(top1s) if top1s else 0.0,
            "recall": sum(recalls) / len(recalls) if recalls else 0.0,
            "precision": sum(precs) / len(precs) if precs else 0.0,
            "latency_p50_ms": statistics.median(lats) if lats else 0,
            "latency_p90_ms": (
                statistics.quantiles(lats, n=10)[8] if len(lats) >= 10 else max(lats or [0])
            ),
            "index_build_ms": int(index_ms),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    # Only the openai_3small candidate needs a key — skip it gracefully if
    # not available so the bakeoff still runs end-to-end.
    have_key = bool(os.environ.get("OPENAI_API_KEY"))

    fixtures_root = Path(tempfile.mkdtemp(prefix="bakeoff_fixtures_"))
    try:
        write_fixtures(fixtures_root)
        results = []
        for label, spec in CANDIDATES:
            if spec.startswith("openai:") and not have_key:
                print(f"SKIP {label} ({spec}) — no OPENAI_API_KEY in env")
                continue
            print(f"\n=== {label} ({spec}) ===")
            r = run_one(label, spec, fixtures_root)
            print(f"  top1={r['top1']:.2f}  recall={r['recall']:.2f}  "
                  f"prec={r['precision']:.2f}  p50={r['latency_p50_ms']}ms  "
                  f"p90={r['latency_p90_ms']:.0f}ms  index={r['index_build_ms']}ms")
            results.append(r)

        print()
        print("=" * 90)
        print("EMBEDDING BAKEOFF — RANKED BY TOP-1 (then recall as tiebreak)")
        print("=" * 90)
        print(f"{'Label':<16} {'Top-1':<7} {'Recall':<8} {'Prec':<7} {'p50 ms':<8} {'p90 ms':<8} {'Index ms':<10}")
        print("-" * 90)
        results.sort(key=lambda r: (r["top1"], r["recall"]), reverse=True)
        for r in results:
            print(
                f"{r['label']:<16} "
                f"{r['top1']:<7.2f} "
                f"{r['recall']:<8.2f} "
                f"{r['precision']:<7.2f} "
                f"{r['latency_p50_ms']:<8.0f} "
                f"{r['latency_p90_ms']:<8.0f} "
                f"{r['index_build_ms']:<10}"
            )
        if results:
            winner = results[0]
            print(f"\nRECOMMENDED LOCAL DEFAULT: {winner['spec']}  "
                  f"(top1={winner['top1']:.2f}, recall={winner['recall']:.2f})")
        return 0
    finally:
        shutil.rmtree(fixtures_root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
