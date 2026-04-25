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
    lead_attorney: "First Last"
    role: "Partner" | "Founder" | "Managing Attorney" | ...
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
    all_personas = {p.id: p for p in list_personas(vertical)}
    if personas:
        missing = [p for p in personas if p not in all_personas]
        if missing:
            raise ValueError(
                f"Unknown persona(s) for {vertical}: {missing}. "
                f"Available: {sorted(all_personas)}"
            )
        selected = [all_personas[p] for p in personas]
    else:
        selected = list(all_personas.values())

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
        "ingest_call": ingest_call,
        "dispatch_hint": (
            "Dispatch one sub-agent per persona in parallel (e.g. via the Task tool "
            "with subagent_type=general-purpose). Each sub-agent's only job is to "
            "research firms matching its persona and write a YAML to its output_path. "
            "When every sub-agent has finished, call lawyer_search_ingest with the "
            "list of output_paths to merge results into the diligence DB."
        ),
    }
