"""Compliance document search retrieval eval.

Ports stock_journal/tests/eval/journal_search_eval.py to the compliance
document corpus. Builds a synthetic 20-doc fixture set, indexes it, then
compares retrieval strategies side-by-side on a 22-question bank.

Strategies under test:
  S1 NAIVE_GLOB         — filename glob over base_dir (pre-RAG baseline)
  S2 METADATA_FILTER    — Chroma metadata filter only (doc_type / category) —
                          no semantic search
  S3 OPEN_RAG           — pure semantic RAG (current ComplianceQueryEngine)
  S4 FILTERED_RAG       — RAG with doc_type/category filter
  S5 RAG_RECENT         — RAG + recency rerank (file mtime)
  S6 SMART_SEARCH       — production path: Tier 1 filtered RAG → Tier 2
                          open RAG with recency rerank (auto-escalating)

Each question carries ground-truth doc stems (the filename without the
extension, defined in fixtures.py) plus an optional doc_type/category
hint that a smart caller would pass through.

Run from project root with the conda env that has compliance-os + openai
+ llama-index installed:

    /Users/lichenyu/miniconda3/envs/compliance-os/bin/python tests/eval/search_eval.py

Requires OPENAI_API_KEY in env. The eval reuses a temp chroma_db (rebuilt
on each run) so it does not stomp on the user's real index.
"""

from __future__ import annotations

import math
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from compliance_os.indexer.index import DocumentIndexer  # noqa: E402
from compliance_os.query.engine import ComplianceQueryEngine, _recency_rerank  # noqa: E402
from compliance_os.settings import settings as default_settings  # noqa: E402
from tests.eval.fixtures import write_fixtures  # noqa: E402

# ─── Question bank ─────────────────────────────────────────────────────
# Each question: (id, query, ground-truth doc stems, optional filters, note).
# Ground truth uses the fixture's filename stem (e.g. "i797_h1b_approval_2026").
QUESTIONS: list[dict] = [
    {
        "id": "Q1_H1B_LATEST",
        "query": "What's the latest status of my H-1B petition?",
        "gt": ["i797_h1b_amendment_2027", "i797_h1b_approval_2026"],
        "doc_type": "immigration",
        "note": "Recency-sensitive — amendment supersedes the original",
    },
    {
        "id": "Q2_STEM_OPT_EXPIRY",
        "query": "When does my STEM OPT expire?",
        "gt": ["i20_stem_opt_extension_2025"],
        "doc_type": "immigration",
        "note": "Single specific doc",
    },
    {
        "id": "Q3_FORM_8843",
        "query": "Did I file Form 8843 for tax year 2024?",
        "gt": ["form_8843_2025"],
        "doc_type": "tax",
        "note": "Form-number exact lookup",
    },
    {
        "id": "Q4_TAX_RETURN_2024",
        "query": "Show me my 1040-NR tax return",
        "gt": ["form_1040nr_2025"],
        "doc_type": "tax",
        "note": "Form-number lookup",
    },
    {
        "id": "Q5_W2_WAGES",
        "query": "How much did Acme pay me in 2024?",
        "gt": ["w2_acme_2025", "form_1040nr_2025"],
        "doc_type": "tax",
        "note": "Concept lookup spanning W-2 and 1040-NR",
    },
    {
        "id": "Q6_FBAR_FILED",
        "query": "Did I file FBAR for my Chinese bank account?",
        "gt": ["fbar_fincen114_2025"],
        "doc_type": "tax",
        "note": "FBAR specific",
    },
    {
        "id": "Q7_FORM_5472",
        "query": "Form 5472 foreign-owned LLC reporting status",
        "gt": ["form_5472_2025", "articles_of_incorp_acme_2024"],
        "doc_type": "tax",
        "note": "Form + entity context",
    },
    {
        "id": "Q8_EAD_RENEWAL",
        "query": "When was my EAD renewed?",
        "gt": ["ead_card_renewal_2026"],
        "doc_type": "immigration",
        "note": "EAD-specific",
    },
    {
        "id": "Q9_I9_VERIFIED",
        "query": "I-9 employment eligibility verification record",
        "gt": ["i9_employment_eligibility_2025"],
        "doc_type": "immigration",
        "note": "Cross-domain (employment + immigration)",
    },
    {
        "id": "Q10_OFFER_LETTER",
        "query": "What was the salary in my Acme offer letter?",
        "gt": ["offer_letter_acme_2025"],
        "doc_type": "payroll",
        "note": "Employment doc",
    },
    {
        "id": "Q11_RECENT_PAYSTUB",
        "query": "Show me my most recent pay stub",
        "gt": ["paystub_acme_2026_03"],
        "doc_type": "payroll",
        "note": "Recency-sensitive — only one paystub in fixtures",
    },
    {
        "id": "Q12_LLC_FORMATION",
        "query": "When was Acme Holdings LLC formed?",
        "gt": ["articles_of_incorp_acme_2024", "ein_letter_acme_2024"],
        "doc_type": "corporate",
        "note": "Corporate filing + EIN",
    },
    {
        "id": "Q13_EIN",
        "query": "Acme Holdings EIN number",
        "gt": ["ein_letter_acme_2024"],
        "doc_type": "corporate",
        "note": "EIN-specific",
    },
    {
        "id": "Q14_2026_DEADLINES",
        "query": "What compliance deadlines do I have in 2026?",
        "gt": ["deadline_calendar_2026"],
        "doc_type": "deadline",
        "note": "Calendar lookup",
    },
    {
        "id": "Q15_VISA_RENEWAL",
        "query": "When should I start visa renewal?",
        "gt": ["deadline_visa_renewal"],
        "doc_type": "deadline",
        "note": "Concept query",
    },
    {
        "id": "Q16_RFE_DUE",
        "query": "When is the USCIS RFE response due?",
        "gt": ["uscis_rfe_2026"],
        "doc_type": "immigration",
        "note": "Critical deadline",
    },
    {
        "id": "Q17_ATTORNEY",
        "query": "Who is my immigration attorney?",
        "gt": ["attorney_engagement_2025"],
        "doc_type": "legal",
        "note": "Correspondence-style lookup",
    },
    {
        "id": "Q18_TESLA_DECOY",
        "query": "Tesla stock thesis valuation",
        "gt": [],
        "doc_type": None,
        "note": "Negative test — no relevant docs in corpus",
    },
    {
        "id": "Q19_METHODOLOGY",
        "query": "How does Guardian cross-check filings?",
        "gt": ["methodology_compliance_principles"],
        "doc_type": None,
        "note": "Concept / methodology lookup with no metadata hint",
    },
    {
        "id": "Q20_AMENDMENT_AWARENESS",
        "query": "Has my H-1B been amended?",
        "gt": ["i797_h1b_amendment_2027"],
        "doc_type": "immigration",
        "note": "Specifically wants the amendment, not the original",
    },
    {
        "id": "Q21_TRAINING_PLAN",
        "query": "Where is my I-983 STEM OPT training plan?",
        "gt": ["i983_training_plan_2025"],
        "doc_type": "immigration",
        "note": "Form-number lookup",
    },
    {
        "id": "Q22_COMPENSATION",
        "query": "What's my current annual compensation at Acme?",
        "gt": ["offer_letter_acme_2025", "paystub_acme_2026_03", "w2_acme_2025"],
        "doc_type": None,
        "note": "Concept query spanning offer + paystub + W-2",
    },
]


# ─── Eval engine setup ────────────────────────────────────────────────


def _stem_of(metadata: dict) -> str | None:
    """Return the fixture's stem from a chunk's metadata.

    Indexer attaches file_name like 'i797_h1b_approval_2026.txt'; we strip
    the extension so ground truth lines up with what callers see.
    """
    fn = metadata.get("file_name", "")
    if not fn:
        return None
    return fn.rsplit(".", 1)[0]


def _dedup_by_stem(chunks: list[dict]) -> list[str]:
    """Reduce chunk list to ordered unique stems (preserves rank)."""
    out, seen = [], set()
    for c in chunks:
        s = _stem_of(c["metadata"])
        if s and s not in seen:
            out.append(s)
            seen.add(s)
    return out


def s1_naive_glob(engine: ComplianceQueryEngine, q: dict, fixtures_dir: Path) -> list[str]:
    """Filename-substring scan — the pre-RAG baseline anyone might write."""
    needle_terms = [t.lower() for t in q["query"].split() if len(t) > 2]
    hits = []
    for p in fixtures_dir.rglob("*.txt"):
        stem = p.stem
        score = sum(1 for t in needle_terms if t in stem.lower())
        if score:
            hits.append((score, stem))
    hits.sort(key=lambda x: -x[0])
    return [s for _, s in hits[:10]]


def s2_metadata_filter(engine: ComplianceQueryEngine, q: dict, _fixtures_dir: Path) -> list[str]:
    """Pure metadata filter — no semantic search. Returns docs of the
    requested doc_type, in chroma's natural order."""
    if not q.get("doc_type"):
        return []
    # Reach into the chroma collection directly to fetch all matching docs
    # without an embedding call.
    import chromadb
    client = chromadb.PersistentClient(path=str(engine.chroma_dir))
    coll = client.get_collection(name=default_settings.collection_name)
    res = coll.get(where={"doc_type": q["doc_type"]}, limit=20)
    metas = res.get("metadatas", []) or []
    stems = []
    for m in metas:
        s = _stem_of(m)
        if s and s not in stems:
            stems.append(s)
    return stems[:10]


def s3_open_rag(engine: ComplianceQueryEngine, q: dict, _fixtures_dir: Path) -> list[str]:
    chunks = engine.retrieve(q["query"], top_k=10, filters=None)
    return _dedup_by_stem(chunks)


def s4_filtered_rag(engine: ComplianceQueryEngine, q: dict, _fixtures_dir: Path) -> list[str]:
    from compliance_os.query.engine import _build_filters
    filters = _build_filters(doc_type=q.get("doc_type"))
    chunks = engine.retrieve(q["query"], top_k=10, filters=filters)
    return _dedup_by_stem(chunks)


def s5_rag_recent(engine: ComplianceQueryEngine, q: dict, _fixtures_dir: Path) -> list[str]:
    chunks = engine.retrieve(q["query"], top_k=20, filters=None)
    reranked = _recency_rerank(chunks, half_life_days=180.0)
    return _dedup_by_stem(reranked)[:10]


def s6_smart_search(engine: ComplianceQueryEngine, q: dict, _fixtures_dir: Path) -> list[str]:
    res = engine.smart_search(
        query=q["query"],
        doc_type=q.get("doc_type"),
        top_k=10,
        min_tier1_results=3,
        prefer_recent=True,
    )
    return _dedup_by_stem(res["results"])


# ─── Scoring ───────────────────────────────────────────────────────────


def score(returned: list[str], gt: list[str]) -> tuple[int | None, float | None, float | None]:
    if not gt:
        # Negative test: returning empty is the right answer. Score top1 as 1
        # if and only if returned is empty (i.e. no false positives). recall
        # and precision are NA.
        return (1 if not returned else 0, None, None)
    top1 = 1 if returned and returned[0] in gt else 0
    recall = sum(1 for g in gt if g in returned[:5]) / len(gt)
    precision = sum(1 for s in returned[:5] if s in gt) / max(1, min(5, len(returned)))
    return (top1, recall, precision)


# ─── Run ───────────────────────────────────────────────────────────────


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set — required for embedding model.")
        return 2

    # Use a scratch chroma + fixture dir so we never touch the real index.
    tmp = Path(tempfile.mkdtemp(prefix="guardian_search_eval_"))
    fixtures_dir = tmp / "fixtures"
    chroma_dir = tmp / "chroma_db"
    fixtures_dir.mkdir()
    chroma_dir.mkdir()

    try:
        print(f"Materializing fixtures at {fixtures_dir}")
        write_fixtures(fixtures_dir)

        # Indexer reads settings.chroma_dir — point it at our scratch dir.
        default_settings.chroma_dir = chroma_dir
        print(f"Indexing fixtures into {chroma_dir}")
        indexer = DocumentIndexer(data_dir=fixtures_dir, chroma_dir=chroma_dir)
        stats = indexer.build_index(force=True, verbose=False)
        print(f"Indexed: {stats}")

        engine = ComplianceQueryEngine(chroma_dir=chroma_dir)

        strategies = [
            ("S1_NAIVE_GLOB",     s1_naive_glob),
            ("S2_METADATA_FLT",   s2_metadata_filter),
            ("S3_OPEN_RAG",       s3_open_rag),
            ("S4_FILTERED_RAG",   s4_filtered_rag),
            ("S5_RAG_RECENT",     s5_rag_recent),
            ("S6_SMART_SEARCH",   s6_smart_search),
        ]

        print()
        print("=" * 96)
        print(f"{'Q':<28} {'Strategy':<18} {'Top1':<6} {'Rec@5':<7} {'Prec@5':<8} {'ms':<6}")
        print("=" * 96)

        agg: dict[str, dict[str, list]] = {
            name: {"top1": [], "recall": [], "precision": [], "ms": []}
            for name, _ in strategies
        }
        detailed: list[str] = []

        for q in QUESTIONS:
            qid = q["id"]
            detailed.append(f"\n### {qid}: {q['query']}")
            detailed.append(f"  GT: {q['gt']} ({q['note']})")
            for sname, fn in strategies:
                t0 = time.time()
                try:
                    returned = fn(engine, q, fixtures_dir)
                except Exception as exc:
                    returned = []
                    detailed.append(f"  {sname}: ERROR {exc}")
                elapsed_ms = (time.time() - t0) * 1000
                t1, rec, prec = score(returned, q["gt"])
                rec_s = "NA" if rec is None else f"{rec:.2f}"
                prec_s = "NA" if prec is None else f"{prec:.2f}"
                print(f"{qid:<28} {sname:<18} {str(t1):<6} {rec_s:<7} {prec_s:<8} {elapsed_ms:<6.0f}")
                detailed.append(f"  {sname}: {returned[:5]}")
                if t1 is not None:
                    agg[sname]["top1"].append(t1)
                if rec is not None:
                    agg[sname]["recall"].append(rec)
                if prec is not None:
                    agg[sname]["precision"].append(prec)
                agg[sname]["ms"].append(elapsed_ms)

        # Aggregate scoreboard
        print()
        print("=" * 96)
        print("AGGREGATE SCOREBOARD")
        print("=" * 96)
        print(f"{'Strategy':<18} {'Top-1':<8} {'Recall@5':<10} {'Precision@5':<13} {'Avg latency':<12}")
        print("-" * 96)
        for sname, _ in strategies:
            a = agg[sname]
            t1 = sum(a["top1"]) / len(a["top1"]) if a["top1"] else 0
            rec = sum(a["recall"]) / len(a["recall"]) if a["recall"] else 0
            prec = sum(a["precision"]) / len(a["precision"]) if a["precision"] else 0
            ms = sum(a["ms"]) / len(a["ms"]) if a["ms"] else 0
            print(f"{sname:<18} {t1:<8.2f} {rec:<10.2f} {prec:<13.2f} {ms:<12.0f}ms")

        print("\n" + "=" * 96)
        print("PER-QUESTION DETAIL")
        print("=" * 96)
        for line in detailed:
            print(line)

        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
