#!/usr/bin/env python3
"""
Generate model_routing.yaml from the latest bake-off results.

For each doc type, picks the model with the highest accuracy.
Ties are broken by: lowest cost, then lowest latency.
If the winner matches the default model, no override is emitted.

Usage:
  python scripts/generate_model_routing.py [path/to/bakeoff_report.json]

If no path is given, uses the most recent file in scripts/bakeoff_results/.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

RESULTS_DIR = Path(__file__).parent / "bakeoff_results"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "config" / "model_routing.yaml"

# Model key → provider + model ID
MODEL_REGISTRY = {
    "haiku-4.5": {"provider": "anthropic", "model": "claude-haiku-4-5-20251001"},
    "gpt-5.4-nano": {"provider": "openai", "model": "gpt-5.4-nano"},
    "gpt-5.4-mini": {"provider": "openai", "model": "gpt-5.4-mini"},
    "gemini-2.5-flash": {"provider": "google", "model": "gemini-2.5-flash"},
}

# Default model — used for doc types where it wins or ties
DEFAULT_MODEL_KEY = "gpt-5.4-mini"


def load_report(path: Path | None = None) -> dict:
    if path:
        return json.loads(path.read_text())

    reports = sorted(RESULTS_DIR.glob("*_bakeoff_report.json"))
    if not reports:
        print("No bake-off reports found in", RESULTS_DIR)
        sys.exit(1)

    latest = reports[-1]
    print(f"Using latest report: {latest.name}")
    return json.loads(latest.read_text())


def pick_best_model(accuracies: dict[str, float], summary: dict) -> str:
    """Pick the best model for a doc type. Highest accuracy wins; ties broken by cost."""
    if not accuracies:
        return DEFAULT_MODEL_KEY

    best_acc = max(accuracies.values())
    tied = [mk for mk, acc in accuracies.items() if acc >= best_acc - 0.001]

    if len(tied) == 1:
        return tied[0]

    # Break tie by lowest avg cost
    def cost_key(mk: str) -> float:
        s = summary.get(mk, {})
        return s.get("avg_cost_per_doc", 999)

    tied.sort(key=cost_key)

    # If default model is among the tied, prefer it (no override needed)
    if DEFAULT_MODEL_KEY in tied:
        return DEFAULT_MODEL_KEY

    return tied[0]


def generate_routing(report: dict) -> dict:
    accuracy_by_dt = report.get("accuracy_by_doc_type", {})
    summary = report.get("summary", {})

    overrides = {}
    routing_reasons = {}

    for doc_type, accuracies in sorted(accuracy_by_dt.items()):
        best = pick_best_model(accuracies, summary)
        if best != DEFAULT_MODEL_KEY:
            reg = MODEL_REGISTRY[best]
            overrides[doc_type] = {
                "provider": reg["provider"],
                "model": reg["model"],
            }
            routing_reasons[doc_type] = {
                "winner": best,
                "accuracy": accuracies.get(best, 0),
                "default_accuracy": accuracies.get(DEFAULT_MODEL_KEY, 0),
                "all_scores": accuracies,
            }

    return overrides, routing_reasons


def write_yaml(overrides: dict, report_name: str) -> None:
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
# Auto-generated from bake-off results on {now}.
# Source: {report_name}
#
# Default: {DEFAULT_MODEL_KEY} ({default_reg['provider']}/{default_reg['model']})
# Re-run bake-off: python scripts/extraction_bakeoff.py --limit 50
# Regenerate this file: python scripts/generate_model_routing.py
"""

    with open(OUTPUT_PATH, "w") as f:
        f.write(header + "\n")
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    report = load_report(path)
    overrides, reasons = generate_routing(report)

    report_file = path.name if path else "latest"
    write_yaml(overrides, report_file)

    print(f"\nGenerated {OUTPUT_PATH}")
    print(f"Default: {DEFAULT_MODEL_KEY}")
    if overrides:
        print(f"Overrides ({len(overrides)} doc types):")
        for dt, cfg in overrides.items():
            r = reasons[dt]
            print(f"  {dt}: {r['winner']} ({r['accuracy']*100:.1f}%) vs default ({r['default_accuracy']*100:.1f}%)")
    else:
        print("No overrides — default model wins everywhere.")


if __name__ == "__main__":
    main()
