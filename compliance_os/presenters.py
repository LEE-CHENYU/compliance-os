"""Render Guardian tool results as ready-to-display Markdown cards.

These are pure functions that turn the structured results the local services
return into compact, human-readable Markdown the agent shows the user
verbatim. The point: when a Guardian tool fires, the user sees a consistent
"here's what I just did" card — a source-of-truth wedge, a rule-check result,
a risk/deadline list, a document-mismatch diff — instead of a silent JSON
blob the model may or may not surface.

Design notes:
  * Markdown only (tables, bold, unicode) — the format that renders
    deterministically in Cowork, Claude Desktop, and Claude Code.
  * Severity markers are restrained: one small glyph, calm copy, never
    alarmist. 🔴 = blocking/overdue, 🟠 = warning/soon, 🔵 = informational.
  * Every function is defensive: missing keys degrade gracefully, never raise.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Untrusted document content flows into these cards, and the "SHOW WHAT YOU DID"
# instruction tells the model to echo them verbatim — so collapse every line /
# format separator (\n, \r, U+2028/2029) that could break a table row or inject
# a new Markdown line.
_LINE_SEP = re.compile("[\r\n\u2028\u2029]+")

# Restrained severity glyphs. Many callers use different vocabularies
# (critical/warning/advisory vs high/medium/low vs requires/info) — map them
# all onto three calm markers.
_SEV_GLYPH = {
    "critical": "🔴", "high": "🔴", "block": "🔴", "overdue": "🔴",
    "warning": "🟠", "medium": "🟠", "soon": "🟠",
    "advisory": "🔵", "info": "🔵", "low": "🔵", "informational": "🔵",
}
_SEV_ORDER = {"critical": 0, "high": 0, "warning": 1, "medium": 1,
              "advisory": 2, "info": 3, "low": 3}


def _glyph(severity: str | None) -> str:
    return _SEV_GLYPH.get((severity or "info").lower(), "🔵")


def _unwrap(value: Any) -> Any:
    """Pull the scalar out of the canonical {"v": ...} fact envelope."""
    if isinstance(value, dict) and "v" in value:
        return value["v"]
    return value


def _fmt(value: Any) -> str:
    """Render a fact value for INLINE display; em-dash for empty. Untrusted
    document text gets line separators collapsed and backticks neutralized so
    a poisoned value can't inject a new Markdown line or code span."""
    v = _unwrap(value)
    if v is None or v == "":
        return "—"
    return _LINE_SEP.sub(" ", str(v)).replace("`", "\\`").strip()


def _cell(text: Any) -> str:
    """Escape a value so it can't break out of a Markdown TABLE cell — every
    line separator (\\n, \\r, U+2028/2029) collapsed and the pipe escaped."""
    s = _LINE_SEP.sub(" ", str(text if text is not None else ""))
    return s.replace("|", "\\|").strip()


# ──────────────────────────────────────────────────────────────────
#  ① Source-of-truth wedge
# ──────────────────────────────────────────────────────────────────

def format_fact_wedge(result: dict) -> str:
    """Card for a single user-locked fact (set_user_fact).

    result = {"fact": <serialized fact>, "superseded": <fact>|None}
    """
    fact = (result or {}).get("fact") or {}
    superseded = (result or {}).get("superseded")
    label = fact.get("label") or fact.get("fact_key") or "fact"
    new = _fmt(fact.get("value"))

    lines = ["**✓ Locked into your source of truth**", ""]
    if superseded:
        lines.append(f"**{label}** → {new}  ·  _was: {_fmt(superseded.get('value'))}_")
    else:
        lines.append(f"**{label}** → {new}")
    lines.append("🔒 you locked this — checks, forms, and deadlines will use this value when they run")

    conflicts = fact.get("detected_conflicts") or []
    if conflicts:
        lines.append("")
        for c in conflicts:
            lines.append(
                f"🟠 a document claims **{_fmt(c.get('claimed_value'))}** — want me to reconcile?"
            )
    return "\n".join(lines)


def format_record_wedge(result: dict) -> str:
    """Card for facts read off a document (record_extracted_facts).

    result = {"recorded_fields": [str], "changes": [{fact_key,label,old,new}],
              "conflicts": [<fact>], "facts": [<fact>]}
    `changes` is the before→after diff of canonical facts; `conflicts` are
    facts where a document's claim disagrees with the locked value.
    """
    result = result or {}
    recorded = result.get("recorded_fields") or []
    changes = result.get("changes") or []
    conflicts = result.get("conflicts") or []

    n = len(recorded)
    lines = [f"**✓ Read {n} field{'s' if n != 1 else ''} into your source of truth**", ""]

    fresh = [c for c in changes if c.get("old") in (None, "", "—")]
    updated = [c for c in changes if c.get("old") not in (None, "", "—")]
    for c in fresh:
        lines.append(f"+ **{c.get('label') or c.get('fact_key')}** → {_fmt(c.get('new'))}")
    for c in updated:
        lines.append(
            f"~ **{c.get('label') or c.get('fact_key')}** → {_fmt(c.get('new'))}"
            f"  ·  _was: {_fmt(c.get('old'))}_"
        )
    if not changes and recorded:
        lines.append("_(recorded to the document; no canonical facts changed)_")

    if conflicts:
        lines += ["", f"🟠 **{len(conflicts)} need a decision:**"]
        for f in conflicts:
            label = f.get("label") or f.get("fact_key")
            cur = _fmt(f.get("value"))
            for c in (f.get("detected_conflicts") or []):
                lines.append(
                    f"- **{label}**: your record says _{cur}_, a document says "
                    f"_{_fmt(c.get('claimed_value'))}_"
                )
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
#  ② Rule check (run_compliance_check)
# ──────────────────────────────────────────────────────────────────

_CHECK_TITLES = {
    "h1b_doc_check": "H-1B packet review",
    "fbar": "FBAR check",
    "student_tax": "Student tax check",
    "83b_election": "83(b) election",
}
_VERDICT_LABEL = {
    "pass": "✓ pass", "block": "🔴 blocker", "investigate": "🟠 investigate",
    "incomplete": "🟠 incomplete",
}


def format_compliance_result(check_type: str, result: dict) -> str:
    """Card for a run_compliance_check result. Defensive across all four
    check shapes (h1b_doc_check / fbar / student_tax / 83b_election)."""
    result = result or {}
    title = _CHECK_TITLES.get(check_type, check_type)

    # Derive a verdict line (each check expresses it differently).
    verdict = result.get("verdict")
    if check_type == "fbar":
        verdict = "required" if result.get("requires_fbar") else "not required"
    badge = _VERDICT_LABEL.get(str(verdict), verdict)

    header = f"### {title}" + (f" — {badge}" if badge else "")
    lines = [header]
    if result.get("summary"):
        lines += ["", str(result["summary"])]

    findings = result.get("findings") or []
    if findings:
        lines += ["", "| | Finding | Why it matters |", "|---|---|---|"]
        for f in findings:
            lines.append(
                f"| {_glyph(f.get('severity'))} | {_cell(f.get('title'))} "
                f"| {_cell(f.get('consequence'))} |"
            )

    deadline = result.get("filing_deadline") or result.get("deadline")
    if deadline:
        lines += ["", f"**Deadline** {deadline}"]

    steps = result.get("next_steps") or []
    if steps:
        lines += ["", "**Next**"] + [f"- {s}" for s in steps[:4]]

    for art in (result.get("artifacts") or []):
        # Show only the basename — never the absolute, DATA_DIR-rooted path,
        # which would leak the home-dir layout and an internal order UUID.
        name = art.get("filename") or Path(str(art.get("path") or "")).name
        if name:
            lines.append(f"📄 {_cell(art.get('label', 'Download'))} → `{_cell(name)}`")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
#  ③ Risks & deadlines (guardian_risks / guardian_deadlines)
# ──────────────────────────────────────────────────────────────────

def format_risks(findings: list) -> str:
    """Card for the timeline `findings` array (guardian_risks)."""
    findings = findings or []
    if not findings:
        return "✓ No active compliance findings."
    findings = sorted(
        findings, key=lambda f: _SEV_ORDER.get((f.get("severity") or "info").lower(), 9)
    )
    lines = ["### Risks on your radar", "", "| | Finding | Do |", "|---|---|---|"]
    for f in findings:
        lines.append(
            f"| {_glyph(f.get('severity'))} | {_cell(f.get('title'))} "
            f"| {_cell(f.get('action'))} |"
        )
    return "\n".join(lines)


def format_deadlines(deadlines: list) -> str:
    """Card for the timeline `deadlines` array (guardian_deadlines)."""
    deadlines = deadlines or []
    if not deadlines:
        return "✓ No upcoming deadlines."
    deadlines = sorted(
        deadlines,
        key=lambda d: d["days"] if isinstance(d.get("days"), (int, float)) else 9999,
    )
    lines = ["### Deadlines", "", "| When | Item | Do |", "|---|---|---|"]
    for d in deadlines:
        days = d.get("days")
        if isinstance(days, (int, float)) and days < 0:
            glyph, when = "🔴", f"**{int(-days)}d overdue**"
        elif isinstance(days, (int, float)) and days <= 30:
            glyph, when = "🟠", f"**{int(days)}d**"
        else:
            glyph, when = "🔵", _cell(d.get("date") or (f"{int(days)}d" if isinstance(days, (int, float)) else ""))
        lines.append(
            f"| {glyph} {when} | {_cell(d.get('title'))} | {_cell(d.get('action'))} |"
        )
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
#  ④ Document mismatch (cross_check_filings)
# ──────────────────────────────────────────────────────────────────

def format_cross_check(result: dict) -> str:
    """Card for a cross_check report (cross_check_filings)."""
    result = result or {}
    chains = result.get("chains_detected") or []
    summary = result.get("summary") or {}
    findings = result.get("findings") or []

    header = "### Cross-check" + (f" · {', '.join(chains)}" if chains else "")
    lines = [header]

    counts = []
    if summary.get("mismatches"):
        n = summary["mismatches"]
        counts.append(f"{n} mismatch{'es' if n != 1 else ''}")
    if summary.get("missing"):
        counts.append(f"{summary['missing']} missing")
    if summary.get("deadlines"):
        n = summary["deadlines"]
        counts.append(f"{n} deadline{'s' if n != 1 else ''}")
    if counts:
        lines.append("**" + " · ".join(counts) + "**")
    elif not findings:
        lines.append("✓ No conflicts across your documents.")

    for f in findings:
        cat = f.get("category")
        glyph = _glyph(f.get("severity"))
        if cat == "mismatch" and f.get("sources"):
            lines += ["", f"{glyph} **{_cell(f.get('fact'))}** differs across documents:",
                      "", "| Value | Appears in |", "|---|---|"]
            for s in f["sources"]:
                docs = ", ".join(f"`{_cell(d)}`" for d in (s.get("docs") or []))
                lines.append(f"| {_cell(s.get('value'))} | {docs} |")
            if f.get("recommended_action"):
                lines.append(f"→ {_cell(f.get('recommended_action'))}")
        elif cat == "mismatch":  # date-order relationship — no sources table
            lines.append(f"{glyph} {_cell(f.get('message') or f.get('fact'))}")
            if f.get("recommended_action"):
                lines.append(f"→ {_cell(f.get('recommended_action'))}")
        elif cat == "missing":
            lines.append(
                f"{glyph} Missing: **{_cell(f.get('label') or f.get('doc_type'))}** — "
                f"{_cell(f.get('recommended_action'))}"
            )
        elif cat == "deadline":
            lines.append(f"{glyph} {_cell(f.get('message'))} — {_cell(f.get('recommended_action'))}")
    return "\n".join(lines)
