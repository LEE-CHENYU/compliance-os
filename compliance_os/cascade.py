"""Reactive cascade: when the source-of-truth changes, surface what it
triggered.

MCP servers are request/response — nothing runs in the background. But a WRITE
tool can do more than write: when ``record_extracted_facts`` or
``set_user_fact`` lands new info in the SoT, it re-runs the cheap, local,
fact/doc-driven ``cross_check`` and reports only what's *new* (a fresh
mismatch, a now-missing required document, an upcoming deadline) — plus a flag
when the new facts make a rule check (FBAR / student-tax / H-1B packet)
runnable. The user *offers* to run those; the cascade never fires an
input-specific check unprompted.

This is honest: the new cross-check findings are real (re-run against the
just-written SoT), and the rule-check items are suggestions, not claims that a
check ran. Recording a fact still runs nothing else on its own.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

# A small, conservative map: when one of these canonical facts is freshly
# written, the named rule check becomes relevant. Kept to clear signal facts so
# the suggestion is precise, not noisy. (No 83(b) entry — its inputs
# (grant date / FMV / shares) aren't canonical SoT facts.)
RULE_CHECK_TRIGGERS: dict[str, tuple[str, str]] = {
    "foreign_account_aggregate_high": (
        "fbar", "you now have your foreign-account aggregate balance"),
    "tax_residency_classification": (
        "student_tax", "you've set your tax-residency classification"),
    "h1b_receipt_number": (
        "h1b_doc_check", "you've recorded an H-1B receipt number"),
    "lca_case_number": (
        "h1b_doc_check", "you've recorded an LCA case number"),
}


def _finding_key(f: dict) -> str:
    """A stable identity for a cross-check finding, for before/after diffing."""
    cat = f.get("category")
    if cat == "mismatch":
        return f"mismatch:{f.get('fact') or f.get('rule')}"
    if cat == "missing":
        return f"missing:{f.get('chain')}:{f.get('doc_type')}"
    if cat == "deadline":
        return f"deadline:{f.get('fact')}:{f.get('date')}"
    return f"{cat}:{f.get('message')}"


def crosscheck_keys(db: Session, user_id: str) -> set[str] | None:
    """Snapshot the keys of the current cross-check findings. Returns None if
    cross_check can't run (so the caller skips the diff rather than mislabeling
    every finding as 'new')."""
    from compliance_os.compliance.cross_check import cross_check
    try:
        res = cross_check(db, user_id, chain=None)
    except Exception:
        return None
    return {_finding_key(f) for f in res.get("findings", [])}


def suggested_checks(changed_fact_keys) -> list[dict]:
    """Rule checks the freshly-changed facts make runnable (deduped, offer-only)."""
    out: list[dict] = []
    seen: set[str] = set()
    for k in changed_fact_keys or []:
        trig = RULE_CHECK_TRIGGERS.get(k)
        if trig and trig[0] not in seen:
            seen.add(trig[0])
            out.append({"check": trig[0], "reason": trig[1]})
    return out


def cascade_after_write(
    db: Session, user_id: str, changed_fact_keys, before_keys: set[str] | None
) -> dict:
    """After a SoT write, return the NEW cross-check findings (vs before_keys)
    plus rule checks the changed facts make runnable. Best-effort: any failure
    yields an empty cascade so the write/wedge is never broken."""
    suggested = suggested_checks(changed_fact_keys)
    # A new cross-check finding can only arise from a fact change; on a no-op
    # write (nothing actually changed) skip the cross_check re-run entirely.
    if not changed_fact_keys:
        return {"new_findings": [], "suggested_checks": suggested}
    new_findings: list[dict] = []
    from compliance_os.compliance.cross_check import cross_check
    try:
        res = cross_check(db, user_id, chain=None)
        if before_keys is not None:
            new_findings = [
                f for f in res.get("findings", [])
                if _finding_key(f) not in before_keys
            ]
    except Exception:
        pass
    return {"new_findings": new_findings, "suggested_checks": suggested}
