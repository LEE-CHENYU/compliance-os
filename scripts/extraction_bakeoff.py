#!/usr/bin/env python3
"""
LLM Extraction Bake-off Harness
================================
Compares extraction accuracy, latency, and cost across multiple LLM providers
using production ground-truth data from the database.

Models tested:
  - Claude Haiku 4.5  (claude-haiku-4-5-20251001)
  - GPT-5.4 nano      (gpt-5.4-nano)
  - GPT-5.4 mini      (gpt-5.4-mini)
  - Gemini 2.5 Flash   (gemini-2.5-flash)

Usage:
  conda activate compliance-os
  python scripts/extraction_bakeoff.py [--limit N] [--doc-type TYPE]

Output: scripts/bakeoff_results/YYYY-MM-DD_bakeoff_report.json
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from sqlalchemy.orm import Session, sessionmaker

from compliance_os.web.models.database import get_engine
from compliance_os.web.models.tables_v2 import CheckRow, DocumentRow, ExtractedFieldRow
from compliance_os.web.services.extractor import SCHEMAS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configs: (provider, model_id, cost_per_1M_input, cost_per_1M_output)
# ---------------------------------------------------------------------------

MODELS = {
    "haiku-4.5": {
        "provider": "anthropic",
        "model": "claude-haiku-4-5-20251001",
        "cost_input": 0.80,
        "cost_output": 4.00,
    },
    "gpt-5.4-nano": {
        "provider": "openai",
        "model": "gpt-5.4-nano",
        "cost_input": 0.20,
        "cost_output": 1.25,
    },
    "gpt-5.4-mini": {
        "provider": "openai",
        "model": "gpt-5.4-mini",
        "cost_input": 0.75,
        "cost_output": 4.50,
    },
    "gemini-2.5-flash": {
        "provider": "google",
        "model": "gemini-2.5-flash",
        "cost_input": 0.15,
        "cost_output": 0.60,
    },
}

# ---------------------------------------------------------------------------
# Prompt (identical to production extractor.py _call_llm)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = "You are a document field extractor. Return only valid JSON, no explanation or markdown."


def build_user_prompt(doc_type: str, text: str, schema: dict[str, str]) -> str:
    field_descriptions = "\n".join(f"- {name}: {desc}" for name, desc in schema.items())
    return f"""Extract the following fields from this {doc_type} document.
Return a JSON object with these fields. Use null for any field you cannot find.

Fields to extract:
{field_descriptions}

Document text:
{text}

Return ONLY valid JSON, no explanation."""


# ---------------------------------------------------------------------------
# LLM callers per provider
# ---------------------------------------------------------------------------


def _call_anthropic(model: str, system: str, user: str) -> tuple[dict, dict]:
    """Call Anthropic and return (parsed_json, usage_info)."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    t0 = perf_counter()
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0,
    )
    latency_ms = int((perf_counter() - t0) * 1000)
    content = response.content[0].text
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    usage = response.usage
    return json.loads(content), {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "latency_ms": latency_ms,
    }


def _call_openai(model: str, system: str, user: str) -> tuple[dict, dict]:
    """Call OpenAI and return (parsed_json, usage_info)."""
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    t0 = perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_completion_tokens=4096,
    )
    latency_ms = int((perf_counter() - t0) * 1000)
    content = response.choices[0].message.content
    usage = response.usage
    return json.loads(content), {
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "latency_ms": latency_ms,
    }


def _call_google(model: str, system: str, user: str) -> tuple[dict, dict]:
    """Call Google Gemini and return (parsed_json, usage_info)."""
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    gen_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0,
            max_output_tokens=4096,
        ),
    )
    t0 = perf_counter()
    response = gen_model.generate_content(user)
    latency_ms = int((perf_counter() - t0) * 1000)
    content = response.text
    usage_meta = response.usage_metadata
    return json.loads(content), {
        "input_tokens": getattr(usage_meta, "prompt_token_count", 0),
        "output_tokens": getattr(usage_meta, "candidates_token_count", 0),
        "latency_ms": latency_ms,
    }


CALLERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "google": _call_google,
}


def call_model(model_key: str, system: str, user: str) -> tuple[dict | None, dict]:
    """Call a model and return (result_json, usage_info). Returns None on error."""
    cfg = MODELS[model_key]
    caller = CALLERS[cfg["provider"]]
    try:
        result, usage = caller(cfg["model"], system, user)
        usage["cost"] = (
            usage["input_tokens"] * cfg["cost_input"] / 1_000_000
            + usage["output_tokens"] * cfg["cost_output"] / 1_000_000
        )
        usage["error"] = None
        return result, usage
    except Exception as exc:
        logger.error("  %s FAILED: %s", model_key, exc)
        return None, {
            "input_tokens": 0,
            "output_tokens": 0,
            "latency_ms": 0,
            "cost": 0,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_extraction(ground_truth: dict[str, str | None], predicted: dict[str, Any] | None) -> dict:
    """Compare predicted extraction against ground truth.

    Returns dict with field-level matches and overall accuracy.
    """
    if predicted is None:
        return {
            "accuracy": 0.0,
            "total_fields": len(ground_truth),
            "correct": 0,
            "wrong": len(ground_truth),
            "missing": len(ground_truth),
            "field_results": {k: "error" for k in ground_truth},
        }

    correct = 0
    wrong = 0
    missing = 0
    field_results = {}

    for field_name, gt_value in ground_truth.items():
        pred_value = predicted.get(field_name)

        # Normalize for comparison
        gt_norm = _normalize_for_compare(gt_value)
        pred_norm = _normalize_for_compare(pred_value)

        if gt_norm is None and pred_norm is None:
            # Both null — correct
            correct += 1
            field_results[field_name] = "correct_null"
        elif gt_norm is None and pred_norm is not None:
            # GT is null but model extracted something — mild penalty
            wrong += 1
            field_results[field_name] = f"extra:{pred_norm}"
        elif gt_norm is not None and pred_norm is None:
            # GT has value but model missed it
            missing += 1
            field_results[field_name] = f"missing:{gt_norm}"
        elif gt_norm == pred_norm:
            correct += 1
            field_results[field_name] = "correct"
        else:
            wrong += 1
            field_results[field_name] = f"wrong:gt={gt_norm}|pred={pred_norm}"

    total = len(ground_truth)
    return {
        "accuracy": correct / total if total > 0 else 1.0,
        "total_fields": total,
        "correct": correct,
        "wrong": wrong,
        "missing": missing,
        "field_results": field_results,
    }


def _normalize_for_compare(value: Any) -> str | None:
    """Normalize a field value for comparison."""
    if value is None:
        return None
    s = str(value).strip().lower()
    if s in ("", "null", "none", "n/a"):
        return None
    # Remove trailing .0 from numbers
    if s.endswith(".0"):
        try:
            float(s)
            s = s[:-2]
        except ValueError:
            pass
    # Remove commas from numbers
    s = s.replace(",", "")
    return s


# ---------------------------------------------------------------------------
# Ground truth loader
# ---------------------------------------------------------------------------


def load_ground_truth(db: Session, *, limit: int = 20, doc_type: str | None = None) -> list[dict]:
    """Load documents with existing extracted fields as ground truth.

    Returns list of dicts: {document_id, doc_type, ocr_text, fields: {name: value}}
    """
    query = (
        db.query(DocumentRow)
        .filter(DocumentRow.is_active.is_(True))
        .filter(DocumentRow.ocr_text.isnot(None))
        .filter(DocumentRow.ocr_text != "")
    )
    if doc_type:
        query = query.filter(DocumentRow.doc_type == doc_type)

    docs = query.order_by(DocumentRow.uploaded_at.desc()).limit(limit * 3).all()

    results = []
    for doc in docs:
        if doc.doc_type not in SCHEMAS:
            continue
        fields = {f.field_name: f.field_value for f in doc.extracted_fields}
        if not fields:
            continue
        # Only include fields that are in the schema
        schema = SCHEMAS[doc.doc_type]
        gt_fields = {k: fields.get(k) for k in schema}
        results.append({
            "document_id": doc.id,
            "doc_type": doc.doc_type,
            "filename": doc.filename,
            "ocr_text": doc.ocr_text[:8000],  # Truncate for cost control
            "ground_truth": gt_fields,
        })
        if len(results) >= limit:
            break

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def check_api_keys() -> list[str]:
    """Check which models have API keys configured. Return list of available model keys."""
    available = []
    for key, cfg in MODELS.items():
        provider = cfg["provider"]
        if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
            available.append(key)
        elif provider == "openai" and os.environ.get("OPENAI_API_KEY"):
            available.append(key)
        elif provider == "google" and os.environ.get("GOOGLE_API_KEY"):
            available.append(key)
        else:
            logger.warning("Skipping %s — no API key for %s", key, provider)
    return available


def run_bakeoff(*, limit: int = 20, doc_type: str | None = None) -> dict:
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Load ground truth
        samples = load_ground_truth(db, limit=limit, doc_type=doc_type)
        logger.info("Loaded %d ground truth samples", len(samples))
        if not samples:
            logger.error("No ground truth samples found! Upload and extract documents first.")
            return {}

        available_models = check_api_keys()
        if not available_models:
            logger.error("No API keys configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, and/or GOOGLE_API_KEY.")
            return {}

        logger.info("Testing models: %s", ", ".join(available_models))

        # Run extraction for each sample x model
        results = {mk: [] for mk in available_models}
        totals = {mk: {"accuracy": 0, "latency_ms": 0, "cost": 0, "errors": 0, "count": 0}
                  for mk in available_models}

        for i, sample in enumerate(samples):
            doc_type_s = sample["doc_type"]
            schema = SCHEMAS[doc_type_s]
            prompt = build_user_prompt(doc_type_s, sample["ocr_text"], schema)

            logger.info("[%d/%d] %s (%s)", i + 1, len(samples), sample["filename"], doc_type_s)

            for model_key in available_models:
                predicted, usage = call_model(model_key, SYSTEM_PROMPT, prompt)
                score = score_extraction(sample["ground_truth"], predicted)

                result_entry = {
                    "document_id": sample["document_id"],
                    "doc_type": doc_type_s,
                    "filename": sample["filename"],
                    "accuracy": score["accuracy"],
                    "correct": score["correct"],
                    "wrong": score["wrong"],
                    "missing": score["missing"],
                    "total_fields": score["total_fields"],
                    "latency_ms": usage["latency_ms"],
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": usage["output_tokens"],
                    "cost": usage["cost"],
                    "error": usage["error"],
                    "field_results": score["field_results"],
                }
                results[model_key].append(result_entry)

                t = totals[model_key]
                t["accuracy"] += score["accuracy"]
                t["latency_ms"] += usage["latency_ms"]
                t["cost"] += usage["cost"]
                t["count"] += 1
                if usage["error"]:
                    t["errors"] += 1

                logger.info(
                    "  %-16s acc=%.0f%% lat=%dms cost=$%.4f %s",
                    model_key,
                    score["accuracy"] * 100,
                    usage["latency_ms"],
                    usage["cost"],
                    f"ERR: {usage['error']}" if usage["error"] else "",
                )

        # Aggregate
        summary = {}
        for mk in available_models:
            t = totals[mk]
            n = t["count"] or 1
            summary[mk] = {
                "model_id": MODELS[mk]["model"],
                "provider": MODELS[mk]["provider"],
                "samples": t["count"],
                "errors": t["errors"],
                "avg_accuracy": round(t["accuracy"] / n, 4),
                "avg_latency_ms": round(t["latency_ms"] / n),
                "total_cost": round(t["cost"], 4),
                "avg_cost_per_doc": round(t["cost"] / n, 6),
            }

        # Per doc_type breakdown
        doc_type_summary = {}
        for mk in available_models:
            for entry in results[mk]:
                dt = entry["doc_type"]
                if dt not in doc_type_summary:
                    doc_type_summary[dt] = {m: {"acc_sum": 0, "count": 0} for m in available_models}
                doc_type_summary[dt][mk]["acc_sum"] += entry["accuracy"]
                doc_type_summary[dt][mk]["count"] += 1

        doc_type_report = {}
        for dt, models_data in doc_type_summary.items():
            doc_type_report[dt] = {}
            for mk, data in models_data.items():
                if data["count"] > 0:
                    doc_type_report[dt][mk] = round(data["acc_sum"] / data["count"], 4)

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": {
                "limit": limit,
                "doc_type_filter": doc_type,
                "models": {k: MODELS[k] for k in available_models},
            },
            "summary": summary,
            "accuracy_by_doc_type": doc_type_report,
            "detailed_results": results,
        }

        return report

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="LLM extraction bake-off")
    parser.add_argument("--limit", type=int, default=20, help="Max documents to test (default: 20)")
    parser.add_argument("--doc-type", type=str, default=None, help="Filter to specific doc type")
    args = parser.parse_args()

    report = run_bakeoff(limit=args.limit, doc_type=args.doc_type)
    if not report:
        sys.exit(1)

    # Save report
    output_dir = Path(__file__).parent / "bakeoff_results"
    output_dir.mkdir(exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M")
    output_path = output_dir / f"{date_str}_bakeoff_report.json"
    output_path.write_text(json.dumps(report, indent=2))
    logger.info("Report saved to %s", output_path)

    # Print summary table
    print("\n" + "=" * 80)
    print("EXTRACTION BAKE-OFF RESULTS")
    print("=" * 80)
    print(f"{'Model':<20} {'Accuracy':>10} {'Avg Latency':>12} {'Total Cost':>12} {'$/Doc':>10} {'Errors':>8}")
    print("-" * 80)
    for mk, s in report["summary"].items():
        print(
            f"{mk:<20} {s['avg_accuracy']*100:>9.1f}% {s['avg_latency_ms']:>10}ms ${s['total_cost']:>10.4f} ${s['avg_cost_per_doc']:>8.6f} {s['errors']:>8}"
        )
    print("-" * 80)

    # Print per doc_type accuracy
    if report.get("accuracy_by_doc_type"):
        print("\nAccuracy by Document Type:")
        print(f"{'Doc Type':<25}", end="")
        models = list(report["summary"].keys())
        for mk in models:
            print(f"{mk:>18}", end="")
        print()
        print("-" * (25 + 18 * len(models)))
        for dt, accs in sorted(report["accuracy_by_doc_type"].items()):
            print(f"{dt:<25}", end="")
            for mk in models:
                v = accs.get(mk)
                if v is not None:
                    print(f"{v*100:>17.1f}%", end="")
                else:
                    print(f"{'—':>18}", end="")
            print()

    print(f"\nFull report: {output_path}")


if __name__ == "__main__":
    main()
