#!/usr/bin/env python3
"""
Generate model_routing.yaml from accumulated bake-off results.

Aggregates ALL bake-off reports in scripts/bakeoff_results/ — not just the
latest. Each doc_type × model accuracy is weighted by sample count, so
larger bake-off runs have more influence. Recent runs can optionally be
weighted more heavily with --recency-weight.

Usage:
  python scripts/generate_model_routing.py                   # aggregate all
  python scripts/generate_model_routing.py --latest-only     # single latest report
  python scripts/generate_model_routing.py --recency-weight 2.0  # 2x weight for newest
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml

RESULTS_DIR = Path(__file__).parent / "bakeoff_results"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "config" / "model_routing.yaml"

MODEL_REGISTRY = {
    "haiku-4.5": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
    "gpt-5.4-nano": {"provider": "openai", "model": "gpt-5.4-nano"},
    "gpt-5.4-mini": {"provider": "openai", "model": "gpt-5.4-mini"},
    "gemini-2.5-flash": {"provider": "google", "model": "gemini-2.5-flash"},
}

DEFAULT_MODEL_KEY = "gpt-5.4-mini"


def load_all_reports() -> list[tuple[str, dict]]:
    """Load all bake-off reports sorted oldest → newest. Returns (filename, data) pairs."""
    reports = sorted(RESULTS_DIR.glob("*_bakeoff_report.json"))
    if not reports:
        print("No bake-off reports found in", RESULTS_DIR)
        sys.exit(1)
    result = []
    for p in reports:
        try:
            data = json.loads(p.read_text())
            result.append((p.name, data))
        except Exception as exc:
            print(f"Warning: skipping {p.name}: {exc}")
    return result


def aggregate_accuracy(
    reports: list[tuple[str, dict]],
    recency_weight: float = 1.0,
) -> dict[str, dict[str, dict]]:
    """Aggregate accuracy across all reports, weighted by sample count.

    Returns: {doc_type: {model_key: {"weighted_correct": float, "weighted_total": float}}}
    """
    agg: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"weighted_correct": 0.0, "weighted_total": 0.0}))

    num_reports = len(reports)
    for idx, (filename, report) in enumerate(reports):
        # Recency multiplier: newest report gets recency_weight, oldest gets 1.0
        if num_reports > 1 and recency_weight > 1.0:
            t = idx / (num_reports - 1)  # 0.0 for oldest, 1.0 for newest
            weight = 1.0 + t * (recency_weight - 1.0)
        else:
            weight = 1.0

        detailed = report.get("detailed_results", {})
        for model_key, entries in detailed.items():
            if model_key not in MODEL_REGISTRY:
                continue
            for entry in entries:
                if entry.get("error"):
                    continue
                dt = entry["doc_type"]
                total = entry["total_fields"]
                correct = entry["correct"]
                agg[dt][model_key]["weighted_correct"] += correct * weight
                agg[dt][model_key]["weighted_total"] += total * weight

    return dict(agg)


def compute_accuracies(agg: dict) -> dict[str, dict[str, float]]:
    """Convert aggregated counts to accuracy percentages."""
    result = {}
    for dt, models in agg.items():
        result[dt] = {}
        for mk, data in models.items():
            total = data["weighted_total"]
            if total > 0:
                result[dt][mk] = data["weighted_correct"] / total
    return result


def compute_cost_summary(reports: list[tuple[str, dict]]) -> dict[str, float]:
    """Aggregate avg cost per doc across all reports."""
    totals: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "count": 0})
    for _, report in reports:
        for mk, entries in report.get("detailed_results", {}).items():
            for entry in entries:
                if not entry.get("error"):
                    totals[mk]["cost"] += entry.get("cost", 0)
                    totals[mk]["count"] += 1
    return {mk: d["cost"] / d["count"] if d["count"] > 0 else 999 for mk, d in totals.items()}


def sample_counts(agg: dict) -> dict[str, dict[str, int]]:
    """Count raw samples per doc_type per model (for reporting)."""
    result = {}
    for dt, models in agg.items():
        result[dt] = {}
        for mk, data in models.items():
            # weighted_total / 1.0 ≈ sample count (approximate when recency > 1)
            result[dt][mk] = int(data["weighted_total"])
    return result


def pick_best_model(accuracies: dict[str, float], cost_by_model: dict[str, float]) -> str:
    if not accuracies:
        return DEFAULT_MODEL_KEY

    best_acc = max(accuracies.values())
    tied = [mk for mk, acc in accuracies.items() if acc >= best_acc - 0.005]

    if len(tied) == 1:
        return tied[0]

    # Break tie by lowest cost
    tied.sort(key=lambda mk: cost_by_model.get(mk, 999))

    if DEFAULT_MODEL_KEY in tied:
        return DEFAULT_MODEL_KEY

    return tied[0]


def generate_routing(
    accuracies: dict[str, dict[str, float]],
    cost_by_model: dict[str, float],
) -> tuple[dict, dict]:
    overrides = {}
    reasons = {}

    for doc_type, model_accs in sorted(accuracies.items()):
        best = pick_best_model(model_accs, cost_by_model)
        if best != DEFAULT_MODEL_KEY:
            reg = MODEL_REGISTRY[best]
            overrides[doc_type] = {
                "provider": reg["provider"],
                "model": reg["model"],
            }
            reasons[doc_type] = {
                "winner": best,
                "accuracy": model_accs.get(best, 0),
                "default_accuracy": model_accs.get(DEFAULT_MODEL_KEY, 0),
            }

    return overrides, reasons


def write_yaml(overrides: dict, num_reports: int, total_samples: int) -> None:
    default_reg = MODEL_REGISTRY[DEFAULT_MODEL_KEY]
    now = datetime.now().strftime("%Y-%m-%d")

    config = {
        "default": {
            "provider": default_reg["provider"],
            "model": default_reg["model"],
        },
        "overrides": overrides if overrides else None,
    }

    header = f"""# Model routing for document extraction.
# Auto-generated on {now} from {num_reports} bake-off runs ({total_samples} total evaluations).
#
# Default: {DEFAULT_MODEL_KEY} ({default_reg['provider']}/{default_reg['model']})
# Re-run bake-off: python scripts/extraction_bakeoff.py --limit 50
# Regenerate routing: python scripts/generate_model_routing.py
"""

    with open(OUTPUT_PATH, "w") as f:
        f.write(header + "\n")
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def main():
    parser = argparse.ArgumentParser(description="Generate model routing from bake-off results")
    parser.add_argument("--latest-only", action="store_true", help="Use only the latest report")
    parser.add_argument("--recency-weight", type=float, default=1.5,
                        help="Weight multiplier for newest report (default: 1.5)")
    args = parser.parse_args()

    all_reports = load_all_reports()
    if args.latest_only:
        all_reports = [all_reports[-1]]

    print(f"Aggregating {len(all_reports)} bake-off reports:")
    for name, report in all_reports:
        n_samples = sum(
            len(entries) for entries in report.get("detailed_results", {}).values()
        )
        print(f"  {name} ({n_samples} evaluations)")

    agg = aggregate_accuracy(all_reports, recency_weight=args.recency_weight)
    accuracies = compute_accuracies(agg)
    cost_by_model = compute_cost_summary(all_reports)
    samples = sample_counts(agg)

    overrides, reasons = generate_routing(accuracies, cost_by_model)

    total_evals = sum(
        sum(entries for entries in dt_counts.values())
        for dt_counts in samples.values()
    )
    write_yaml(overrides, len(all_reports), total_evals)

    print(f"\nGenerated {OUTPUT_PATH}")
    print(f"Default: {DEFAULT_MODEL_KEY}")
    print(f"Data: {len(all_reports)} reports, {total_evals} total evaluations")

    # Print accuracy table
    all_models = sorted(set(mk for dt_accs in accuracies.values() for mk in dt_accs))
    print(f"\n{'Doc Type':<30}", end="")
    for mk in all_models:
        print(f"{mk:>18}", end="")
    print(f"{'  Winner':>12}")
    print("-" * (30 + 18 * len(all_models) + 12))

    for dt in sorted(accuracies):
        best = pick_best_model(accuracies[dt], cost_by_model)
        marker = " *" if best != DEFAULT_MODEL_KEY else ""
        print(f"{dt:<30}", end="")
        for mk in all_models:
            v = accuracies[dt].get(mk)
            if v is not None:
                print(f"{v*100:>17.1f}%", end="")
            else:
                print(f"{'—':>18}", end="")
        print(f"  {best}{marker}")

    if overrides:
        print(f"\n{len(overrides)} overrides applied (marked with *).")
    else:
        print("\nNo overrides — default model wins everywhere.")


if __name__ == "__main__":
    main()
