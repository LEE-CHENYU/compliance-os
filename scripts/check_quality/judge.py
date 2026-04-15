"""Claude judge for check-service output quality.

For each (scenario, service_result) pair, ask Claude Opus 4.6 to score the
output on the rubric dimensions and return a structured verdict. Cache by
(scenario_id, service_result_hash, rubric_version) so unchanged outputs
don't re-incur cost.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import anthropic

from .rubrics import Rubric


CACHE_DIR = Path(__file__).resolve().parents[2] / "scripts" / "check_quality_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Opus 4.6 per claude-api skill rules.
JUDGE_MODEL = "claude-opus-4-6"


@dataclass
class DimensionScore:
    name: str
    rating: str  # "pass" | "partial" | "fail"
    reasoning: str


@dataclass
class JudgeVerdict:
    case_id: str
    service: str
    scenario_label: str
    overall: str  # "pass" | "partial" | "fail"
    dimensions: list[DimensionScore]
    notes: str
    cached: bool = False
    tokens_in: int = 0
    tokens_out: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


def _cache_key(scenario_id: str, service_output: dict, rubric: Rubric) -> str:
    canonical_output = json.dumps(service_output, sort_keys=True, default=str)
    payload = f"{scenario_id}|{canonical_output}|{rubric.version}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _read_cache(key: str) -> dict | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(key: str, payload: dict) -> None:
    _cache_path(key).write_text(json.dumps(payload, indent=2), encoding="utf-8")


SYSTEM_PROMPT = """You are an expert reviewer for immigration-tax compliance automation.

You will be shown:
  1. A synthetic user intake for a check service.
  2. The check service's output (summary, findings, next steps, verdict).
  3. A rubric describing the quality dimensions to evaluate.

Your job is NOT to re-compute the check. Your job is to evaluate whether
the output Guardian produced is accurate, useful, and appropriately framed
for a self-directed user. You must cite specific strings from the output
when explaining a partial/fail rating.

Respond with a single JSON object wrapped in ```json fences:

{
  "dimensions": [
    {"name": "<dimension_name>", "rating": "pass|partial|fail", "reasoning": "<1-3 sentences, cite output strings>"}
    // one entry per rubric dimension, in the order given
  ],
  "overall": "pass|partial|fail",
  "notes": "<optional freeform observations or caveats>"
}

Rules:
  - Overall rating: "fail" if ANY dimension is fail; "partial" if any is partial; else "pass".
  - Be willing to say "pass" when the output is genuinely good. Don't find problems to look thorough.
  - When citing, use short quoted strings like "'URGENT: the 30-day deadline...' is appropriately framed".
"""


def _build_user_prompt(scenario_description: str, intake: dict, service_output: dict, rubric: Rubric) -> str:
    dimension_block = "\n".join(
        f"  - {name}: {desc}" for name, desc in rubric.dimensions
    )
    return f"""## Service

{rubric.service}

## Context

{rubric.context}

## Scenario

{scenario_description}

## Intake (what the user submitted)

```json
{json.dumps(intake, indent=2, default=str)}
```

## Service output (what Guardian returned)

```json
{json.dumps(service_output, indent=2, default=str)}
```

## Evaluate the output on each dimension

{dimension_block}

Return JSON per the system prompt format.
"""


def _extract_json_block(text: str) -> dict:
    """Find and parse a ```json fenced block. Falls back to balanced-brace scan."""
    start = text.find("```json")
    if start != -1:
        start += len("```json")
        end = text.find("```", start)
        if end != -1:
            return json.loads(text[start:end].strip())
    # Fallback: find the first {...} that parses
    depth = 0
    begin = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                begin = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and begin is not None:
                candidate = text[begin:i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    begin = None
    raise ValueError(f"No JSON block found in judge response: {text[:200]}...")


def judge_case(
    *,
    scenario_id: str,
    service: str,
    scenario_label: str,
    scenario_description: str,
    intake: dict,
    service_output: dict,
    rubric: Rubric,
    client: anthropic.Anthropic | None = None,
    force: bool = False,
) -> JudgeVerdict:
    """Evaluate one (scenario, result) case, returning a verdict. Caches by content hash."""
    key = _cache_key(scenario_id, service_output, rubric)

    if not force:
        cached = _read_cache(key)
        if cached is not None:
            return JudgeVerdict(
                case_id=scenario_id,
                service=service,
                scenario_label=scenario_label,
                overall=cached["overall"],
                dimensions=[DimensionScore(**d) for d in cached["dimensions"]],
                notes=cached.get("notes", ""),
                cached=True,
                tokens_in=cached.get("tokens_in", 0),
                tokens_out=cached.get("tokens_out", 0),
                raw=cached.get("raw", {}),
            )

    client = client or anthropic.Anthropic()
    user_prompt = _build_user_prompt(scenario_description, intake, service_output, rubric)

    with client.messages.stream(
        model=JUDGE_MODEL,
        max_tokens=16384,  # adaptive thinking eats into this budget — keep headroom
        system=SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        final_message = stream.get_final_message()

    text_blocks = [b.text for b in final_message.content if getattr(b, "type", None) == "text"]
    raw_text = "\n\n".join(text_blocks)
    parsed = _extract_json_block(raw_text)

    dimensions = [
        DimensionScore(name=d["name"], rating=d["rating"], reasoning=d["reasoning"])
        for d in parsed["dimensions"]
    ]
    verdict = JudgeVerdict(
        case_id=scenario_id,
        service=service,
        scenario_label=scenario_label,
        overall=parsed["overall"],
        dimensions=dimensions,
        notes=parsed.get("notes", ""),
        cached=False,
        tokens_in=final_message.usage.input_tokens,
        tokens_out=final_message.usage.output_tokens,
        raw=parsed,
    )

    _write_cache(key, {
        "overall": verdict.overall,
        "dimensions": [asdict(d) for d in verdict.dimensions],
        "notes": verdict.notes,
        "tokens_in": verdict.tokens_in,
        "tokens_out": verdict.tokens_out,
        "raw": parsed,
    })

    return verdict
