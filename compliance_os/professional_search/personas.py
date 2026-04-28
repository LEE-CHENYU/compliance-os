"""Persona loader and search-plan builder.

Each persona is a YAML file under `data/professional_search/personas/<vertical>/`.
Personas describe one *search axis* (e.g. elite boutique, startup-focused,
litigation-focused). The MCP `lawyer_search_plan` tool renders one prompt
per persona that a caller can Task-dispatch in parallel; each sub-agent
produces a YAML at the assigned output path, and `lawyer_search_ingest`
merges them into the diligence DB.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from compliance_os.settings import settings

# Personas live inside the package (so they ship with the wheel/image).
# A `data/professional_search/personas/` mirror in the repo can override
# any vertical for local dev — but the override is *per-vertical*: if a
# given vertical exists in the dev path it wins; otherwise we fall back
# to the bundled copy. This lets you hot-iterate on H-1B prompts in the
# dev tree without losing access to verticals that only exist bundled.
_BUNDLED_PERSONAS = Path(__file__).parent / "personas_data"
_DEV_PERSONAS = settings.project_root / "data" / "professional_search" / "personas"
METHODOLOGY_PATH = Path(__file__).parent / "tier_methodology.md"


def _persona_dir_for(vertical: str) -> Path:
    """Pick the dev override directory if it exists, else the bundled one."""
    dev = _DEV_PERSONAS / vertical
    if dev.is_dir() and any(dev.glob("*.y*ml")):
        return dev
    return _BUNDLED_PERSONAS / vertical


# Kept as a module-level alias for any existing import-time consumers; new
# call sites should prefer the lazy `_persona_dir_for(vertical)` helper so
# verticals can be added without restarting.
PERSONAS_ROOT = _DEV_PERSONAS if _DEV_PERSONAS.is_dir() else _BUNDLED_PERSONAS


@dataclass
class Persona:
    id: str
    vertical: str
    title: str
    path: Path
    raw: dict

    @classmethod
    def load(cls, path: Path) -> "Persona":
        raw = yaml.safe_load(path.read_text())
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: expected YAML mapping at root")
        return cls(
            id=raw.get("id", path.stem),
            vertical=raw.get("vertical", path.parent.name),
            title=raw.get("title", raw.get("id", path.stem)),
            path=path,
            raw=raw,
        )


@dataclass
class PersonaSelection:
    selected: list[Persona]
    skipped: list[dict[str, Any]]


def list_personas(vertical: str) -> list[Persona]:
    """Load every persona YAML for a given vertical."""
    vdir = _persona_dir_for(vertical)
    if not vdir.is_dir():
        raise FileNotFoundError(
            f"No personas for vertical '{vertical}' (looked under "
            f"{_DEV_PERSONAS / vertical} and {_BUNDLED_PERSONAS / vertical})."
        )
    files = sorted(vdir.glob("*.yaml")) + sorted(vdir.glob("*.yml"))
    if not files:
        raise FileNotFoundError(f"No YAML persona files in {vdir}")
    return [Persona.load(p) for p in files]


def _signal_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return []


def _matches(context: str, signals: list[str]) -> list[str]:
    normalized = context.lower()
    return [signal for signal in signals if signal.lower() in normalized]


def _score_persona(persona: Persona, context: str) -> dict[str, Any] | None:
    activation = persona.raw.get("activation")
    if not isinstance(activation, dict):
        return None

    strong = _signal_list(activation.get("strong_signals"))
    weak = _signal_list(activation.get("weak_signals"))
    exclusions = _signal_list(activation.get("exclude_signals"))
    strong_hits = _matches(context, strong)
    weak_hits = _matches(context, weak)
    excluded_hits = _matches(context, exclusions)
    score = len(strong_hits) * int(activation.get("strong_weight", 4))
    score += len(weak_hits) * int(activation.get("weak_weight", 1))
    score -= len(excluded_hits) * int(activation.get("exclude_weight", 6))

    threshold = int(activation.get("threshold", 4))
    return {
        "id": persona.id,
        "title": persona.title,
        "score": score,
        "threshold": threshold,
        "matched_signals": strong_hits + weak_hits,
        "excluded_signals": excluded_hits,
        "fallback": bool(activation.get("fallback")),
    }


def select_personas(
    vertical: str,
    *,
    case_brief: str,
    purpose: str = "",
    uploaded_notes: str | None = None,
    personas: list[Persona] | None = None,
    min_selected: int = 1,
) -> PersonaSelection:
    """Choose case-relevant canonical personas for a search.

    Persona YAMLs can opt into deterministic activation with:

        activation:
          strong_signals: [...]
          weak_signals: [...]
          threshold: 4
          fallback: true

    Verticals without activation metadata preserve the old behavior and run
    every canonical persona. This lets us migrate verticals one at a time.
    """
    all_personas = personas if personas is not None else list_personas(vertical)
    context = "\n".join([purpose, case_brief, uploaded_notes or ""])
    scored = [_score_persona(p, context) for p in all_personas]

    if not any(item is not None for item in scored):
        return PersonaSelection(selected=list(all_personas), skipped=[])

    selected: list[Persona] = []
    skipped: list[dict[str, Any]] = []
    scored_by_id = {item["id"]: item for item in scored if item is not None}

    for persona in all_personas:
        score = scored_by_id.get(persona.id)
        if score is None:
            selected.append(persona)
            continue
        if score["score"] >= score["threshold"]:
            selected.append(persona)
        else:
            skipped.append({
                **score,
                "status": "skipped",
                "reason": "No case-specific activation signals matched strongly enough.",
            })

    if len(selected) < min_selected:
        fallback_candidates = [
            p for p in all_personas
            if scored_by_id.get(p.id, {}).get("fallback")
        ]
        if not fallback_candidates:
            fallback_candidates = sorted(
                all_personas,
                key=lambda p: scored_by_id.get(p.id, {}).get("score", 0),
                reverse=True,
            )
        for persona in fallback_candidates:
            if persona not in selected:
                selected.append(persona)
                skipped = [s for s in skipped if s["id"] != persona.id]
                break

    selected.sort(
        key=lambda p: scored_by_id.get(p.id, {}).get("score", 0),
        reverse=True,
    )

    selected_ids = {p.id for p in selected}
    return PersonaSelection(
        selected=selected,
        skipped=[item for item in skipped if item["id"] not in selected_ids],
    )


# ---- output schema the sub-agent is asked to produce -----------------

OUTPUT_YAML_EXAMPLE = """\
agent: <persona_id>            # REQUIRED — copy the persona id you were given
vertical: <vertical>           # REQUIRED — copy the vertical you were given
purpose: <engagement purpose>  # REQUIRED — copy the case purpose you were given
case_risks:                    # optional; if provided, applied to each engagement
  - risk: "short risk text"
    severity: critical         # one of: low | medium | high | critical
    mitigation: "what to do"
firms:
  - name: "Full firm name, exactly as it appears on their website"
    lead_attorney: "First Last"  # for attorneys/law firms
    lead_contact: "First Last"   # for CPA, bank, CAA, or other non-attorney vendors
    role: "Partner" | "Founder" | "Managing Attorney" | "Relationship Manager" | ...
    city: "Washington"
    state: "DC"
    phone: "(202) 555-0100"
    email: "contact@firm.com"   # if not listed, omit rather than guess
    website: "https://..."
    consultation_fee_low: null  # number in USD or null
    consultation_fee_high: null
    petition_fee_low: 5000      # number or null
    petition_fee_high: 9000
    service_fee_label: "H-1B petition (estimated)"   # label for the petition fee row
    fee_basis: "firm website 2025"   # short attribution for the fee numbers — see fee-research rules below
    confidence: 70              # 0-100, per the methodology below
    why_fit: "2-4 sentences. Specifically what about THIS firm matches the search angle."
    credentials:
      - "Chambers USA Immigration Band 2 (2024)"
      - "AILA past National President 2007-2008"
    litigation_capability: "optional; only when this persona calls for it"
    risks:
      - "Practical or strategic risks of retaining this firm"
    sources:
      - "https://chambers.com/..."   # must be verifiable third-party links
      - "https://www.aila.org/..."
"""


def _methodology_excerpt() -> str:
    """Load the tier methodology doc verbatim — it's the single source of truth."""
    return METHODOLOGY_PATH.read_text()


def build_prompt(
    persona: Persona,
    *,
    case_brief: str,
    purpose: str,
    output_path: Path,
) -> str:
    """Render the sub-agent prompt for one persona."""
    raw = persona.raw
    must = "\n".join(f"- {s}" for s in raw.get("must_weight") or [])
    also = "\n".join(f"- {s}" for s in raw.get("also_value") or [])
    deprio = "\n".join(f"- {s}" for s in raw.get("deprioritize") or [])
    target = raw.get("target_count", 10)
    litigation = raw.get("litigation_capability_required", False)

    parts = [
        f"# Search persona: {persona.title}",
        f"Persona id: `{persona.id}`  |  Vertical: `{persona.vertical}`",
        "",
        "## Case brief",
        case_brief.strip(),
        "",
        f"## Purpose (engagement label)",
        purpose.strip(),
        "",
        "## Your search angle",
        raw.get("search_angle", "").strip(),
        "",
    ]
    if must:
        parts += ["## Weight these signals", must, ""]
    if also:
        parts += ["## Also value", also, ""]
    if deprio:
        parts += ["## Deprioritize / exclude", deprio, ""]
    if litigation:
        parts += [
            "## Litigation capability is required",
            "Only surface firms with verifiable federal-court or AAO track record.",
            "",
        ]
    if raw.get("fee_range_expected_usd"):
        parts += [f"## Expected fee range", str(raw["fee_range_expected_usd"]), ""]

    parts += [
        f"## Target: {target} firms",
        "Return fewer if you cannot find that many that meet the bar. Do not pad.",
        "",
        "## Stage 1 — preview research budget (shallow but honest)",
        "",
        "This is the FREE preview shown to the user before payment. They see "
        "the top 5 firms by score; we want them to make a confident pay/skip "
        "decision in 30 seconds. Stage 2 (post-payment, ~2-3min) verifies "
        "individual attorney bands, source URLs, and routing risk per firm. "
        "Don't do Stage 2's job here.",
        "",
        "Specifically:",
        "- 1 firm-level credential per firm (Chambers band, AILA leadership, etc.)",
        "- 1 source URL per firm (their best third-party citation)",
        "- 2-3 sentence why_fit",
        "- DO NOT verify the named lead_attorney's *individual* Chambers / "
        "  Legal500 / Best Lawyers band — that's Stage 2's responsibility. "
        "  Any band you list MUST be the FIRM's band, not the individual's.",
        "- DO NOT chase RFE history, federal-court appearances, or specialty "
        "  sub-rankings — Stage 2 handles deep diligence per firm.",
        "- Cap web_search at 8 calls per firm; skip the firm if you can't "
        "  satisfy the bar within budget rather than padding with weak signals.",
        "",
        "## Credential methodology (apply this verbatim)",
        "",
        _methodology_excerpt(),
        "",
        "## Output format",
        "Write your results as a YAML document to the file:",
        "",
        f"    {output_path}",
        "",
        "The YAML must match this schema exactly:",
        "",
        "```yaml",
        OUTPUT_YAML_EXAMPLE,
        "```",
        "",
        "Rules:",
        "- `confidence` is your score 0-100 against the methodology.",
        "- `credentials` list items must be *externally-verifiable* per the methodology — no self-published marketing.",
        "- `sources` must be third-party URLs (Chambers, AILA, PACER, state bar, news outlet). A firm's own site counts only for contact info, never as a credential source.",
        "- For most fields: if unknown, omit rather than guess.",
        "",
        "Fee research is the one exception to the no-guess rule. Users",
        "depend on fee guidance to short-list firms, so try harder than",
        "you would for other optional fields:",
        "",
        "  1. Check the firm's published fee schedule (firm website, intake",
        "     forms). Set `fee_basis` to e.g. \"firm website 2025\".",
        "  2. If absent, search third-party sources: EB5 Investors fee",
        "     surveys, AILA practice-management fee guides, attorney-fee",
        "     databases, news articles citing the firm's fees, court filings",
        "     showing fee awards. Set `fee_basis` to the source.",
        "  3. If still absent, provide a tier-typical estimate based on the",
        "     firm's market segment (boutique premium / mid-market / volume)",
        "     using *industry benchmarks for the vertical at hand* — not",
        "     made-up numbers. Set `fee_basis` to e.g. \"tier estimate — premium",
        "     EB-5 boutique\". Be honest that this is an estimate.",
        "  4. Only as a last resort, omit the fee fields and set",
        "     `fee_basis: \"not publicly available; quote required\"`.",
        "",
        "- Do NOT invent firms. If you cannot find enough that meet the bar, return fewer.",
    ]
    return "\n".join(parts)


def build_search_plan(
    *,
    case_brief: str,
    purpose: str,
    vertical: str = "immigration_attorney",
    personas: list[str] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Build dispatch plans for parallel sub-agent search.

    Returns a dict with one `prompts[]` entry per persona, plus an
    `ingest_call` string the caller can run after sub-agents finish.
    """
    loaded_personas = list_personas(vertical)
    all_personas = {p.id: p for p in loaded_personas}
    if personas:
        missing = [p for p in personas if p not in all_personas]
        if missing:
            raise ValueError(
                f"Unknown persona(s) for {vertical}: {missing}. "
                f"Available: {sorted(all_personas)}"
            )
        selected = [all_personas[p] for p in personas]
        selection = PersonaSelection(selected=selected, skipped=[])
    else:
        selection = select_personas(
            vertical,
            case_brief=case_brief,
            purpose=purpose,
            personas=loaded_personas,
        )
        selected = selection.selected

    out_dir = Path(output_dir) if output_dir else (
        settings.professional_search_output_dir
        / _dt.date.today().isoformat()
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    prompts = []
    output_paths = []
    for p in selected:
        op = out_dir / f"{p.id}.yaml"
        prompts.append({
            "persona_id": p.id,
            "title": p.title,
            "output_path": str(op),
            "prompt": build_prompt(p, case_brief=case_brief, purpose=purpose, output_path=op),
        })
        output_paths.append(str(op))

    ingest_call = (
        "lawyer_search_ingest(" + json.dumps(output_paths) + ")  "
        "# call after all sub-agents finish writing"
    )

    return {
        "vertical": vertical,
        "purpose": purpose,
        "output_dir": str(out_dir),
        "prompts": prompts,
        "output_paths": output_paths,
        "selected_personas": [p.id for p in selected],
        "skipped_personas": selection.skipped,
        "ingest_call": ingest_call,
        "dispatch_hint": (
            "Dispatch one sub-agent per persona in parallel (e.g. via the Task tool "
            "with subagent_type=general-purpose). Each sub-agent's only job is to "
            "research firms matching its persona and write a YAML to its output_path. "
            "When every sub-agent has finished, call lawyer_search_ingest with the "
            "list of output_paths to merge results into the diligence DB."
        ),
    }
