#!/usr/bin/env python3
"""Compliance OS — CLI entry point.

Usage:
    cos index [--force] [--dir DIR ...]
    cos query "your question here" [--top-k N] [--filter KEY=VAL] [--sources-only]
    cos deadlines [--category CAT]
    cos status
"""

import argparse
import sys

from compliance_os.settings import settings


def cmd_index(args):
    """Index documents into the vector store."""
    from compliance_os.indexer import DocumentIndexer

    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)

    indexer = DocumentIndexer()

    if not indexer.data_dir.exists():
        print(f"ERROR: Data directory not found: {indexer.data_dir}")
        print("Create it and add your documents, or set COS_DATA_DIR in .env")
        sys.exit(1)

    dirs = args.dirs if args.dirs else None
    indexer.build_index(force=args.force, directories=dirs, verbose=True)


def cmd_query(args):
    """Query the document store."""
    from compliance_os.query import ComplianceQueryEngine

    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)

    engine = ComplianceQueryEngine()
    filters = engine.parse_filters(args.filters) if args.filters else None

    if args.sources_only:
        results = engine.retrieve(args.query, top_k=args.top_k, filters=filters)
        if not results:
            print("No matching documents found.")
            return

        print(f"\n{'='*60}")
        print(f"Query: {args.query}")
        print(f"Results: {len(results)} chunks")
        print(f"{'='*60}")

        for i, r in enumerate(results):
            score = f"{r['score']:.4f}" if r['score'] else "N/A"
            meta = r["metadata"]
            print(f"\n--- [{i+1}] Score: {score} ---")
            print(f"File: {meta.get('file_path', 'unknown')}")
            print(f"Type: {meta.get('doc_type', 'unknown')} | Category: {meta.get('category', 'unknown')}")
            print(f"{'─'*40}")
            text = r["text"].strip()
            if len(text) > 800:
                text = text[:800] + "\n... [truncated]"
            print(text)
        print(f"\n{'='*60}")
    else:
        result = engine.query(args.query, top_k=args.top_k, filters=filters)
        print(f"\n{'='*60}")
        print(f"Query: {args.query}")
        print(f"{'='*60}")
        print(f"\n{result['answer']}")
        if result["sources"]:
            print(f"\n{'─'*40}")
            print("Sources:")
            for s in result["sources"]:
                score = f"{s['score']:.4f}" if s['score'] else "N/A"
                print(f"  [{score}] {s['file_path']}")
        print(f"\n{'='*60}")


def cmd_deadlines(args):
    """Show deadline status summary."""
    from compliance_os.compliance import DeadlineEngine

    engine = DeadlineEngine()
    # TODO: Load deadlines from persistent store
    summary = engine.summary()
    print(f"Total deadlines: {summary['total']}")
    print(f"Status breakdown: {summary['by_status']}")
    if summary["overdue"]:
        print("\nOVERDUE:")
        for d in summary["overdue"]:
            print(f"  [{d['due']}] {d['title']}")


def cmd_status(args):
    """Show overall compliance status."""
    import json

    manifest_path = settings.chroma_dir / "index_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        print(f"Last indexed: {manifest.get('last_run', 'never')}")
        print(f"Documents:    {manifest.get('total_documents', 0)}")
        print(f"Chunks:       {manifest.get('total_chunks', 0)}")
        print(f"DB path:      {settings.chroma_dir}")
    else:
        print("No index found. Run `cos index` first.")


def main():
    parser = argparse.ArgumentParser(
        prog="cos",
        description="Compliance OS — document vault, deadline engine, and compliance tracking",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # index
    p_index = subparsers.add_parser("index", help="Index documents into vector store")
    p_index.add_argument("--force", action="store_true", help="Re-index all documents")
    p_index.add_argument("--dir", action="append", dest="dirs", help="Specific directories to index")

    # query
    p_query = subparsers.add_parser("query", help="Query the document store")
    p_query.add_argument("query", help="Natural language query")
    p_query.add_argument("--top-k", type=int, default=settings.default_top_k)
    p_query.add_argument("--filter", action="append", dest="filters", default=[])
    p_query.add_argument("--sources-only", "--no-llm", action="store_true")

    # deadlines
    p_deadlines = subparsers.add_parser("deadlines", help="Show deadline status")
    p_deadlines.add_argument("--category", help="Filter by category")

    # status
    subparsers.add_parser("status", help="Show system status")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "index": cmd_index,
        "query": cmd_query,
        "deadlines": cmd_deadlines,
        "status": cmd_status,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
