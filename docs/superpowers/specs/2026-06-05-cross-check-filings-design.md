# cross_check_filings: Chain-Aware Local Compliance Cross-Check

**Date:** 2026-06-05
**Status:** Draft — pending user review
**Author:** Cheney Li + Claude
**Related:**
- `compliance_os/facts/extraction_map.py` (`EXTRACTION_TO_FACT_KEY`) and `compliance_os/facts/vocabulary.py` (`CANONICAL_FACTS`) — the canonical fact keys the chains reference
- `compliance_os/web/services/user_facts.py` (`get_active_facts`, `serialize_fact`) — the facts SoT the check reads
- `compliance_os/web/models/tables_v2.py` (`UserFactRow.source_ref`/`detected_conflicts`, `DocumentRow`, `ExtractedFieldRow`) — per-document provenance
- `compliance_os/case_templates/` (`schema.py` Slot/Template, `matcher.py`) — the slot model reused for missing-doc detection
- `compliance_os/compliance/rules.py`, `deadlines.py`, `config/compliance_rules.yaml` — the rule engine reused for deadline/threshold risks
- `compliance_os/local_engine.py` — local-mode plumbing (`is_local_mode`, `get_local_user_id`, `get_session`)
- `accounting/docs/claude_supporting/factual_consistency.md` — the source document-chain taxonomy

---

## Overview

Add a first-class, local-first **`cross_check_filings`** capability to the Guardian extension: one deterministic, in-process pass over the on-device facts source-of-truth that produces a unified **"find my risks" report** — cross-document fact **mismatches**, **missing-from-chain documents**, and **deadline/threshold risks** — narrated by the user's own Claude. It delivers the literal landing-page promise ("cross-check your immigration and tax filings to find mismatches, missing forms, and deadline risks you don't know about yet") inside Claude Desktop, with no document data leaving the device.

This is the **unifying synthesizer** (chosen approach): it reuses the existing rule engine (deadlines/thresholds) and case-template slot model (missing docs), and adds the genuinely-missing piece — the **chain-aware fact-consistency check** — over the facts SoT. The new domain knowledge (which documents form a chain and which facts must agree across them) is encoded as **config**, sourced from the accounting factual-consistency taxonomy.

### What exists vs. what's new

| Capability | Today | This spec |
|---|---|---|
| Same-canonical-key value conflict | ✅ `record_extracted_facts` flags at record-time | reused (read from `UserFactRow.detected_conflicts`) |
| Deadline / threshold rules | ✅ `run_compliance_check` runners + rule engine | reused, fed from facts SoT |
| Missing-document / coverage | ✅ `case_active_search` (folder → template slots) | reused (slot model), driven by the data room not a folder scan |
| **Cross-document fact consistency over the SoT (chain-aware)** | ❌ | **new** (`document_chains.yaml` + engine) |
| **Auto-detect applicable chains from the data room** | ❌ | **new** |
| **One unified, narrated risk report** | ❌ (user/Claude assembles 3 tools) | **new** (`cross_check_filings` tool) |

---

## Goals

- One local tool call returns the complete risk picture for whatever filings the user has uploaded — no folder path, no hand-supplied inputs, no "pick a track."
- Chain knowledge is **config, not code** (`config/document_chains.yaml`) — adding a chain never touches Python.
- Reuse the existing rule engine and template slot model; the only new *logic* is the chain-consistency diff.
- Deterministic and explainable — every finding cites the documents and the conflicting values; the user's Claude narrates, but the findings themselves come from rules, not an LLM.
- Local-first: reads `~/.guardian/guardian.db`; nothing leaves the device.

## Non-Goals

- No new LLM call on our side (the user's Claude narrates the deterministic report).
- No fixing/auto-editing documents — the report surfaces risks + a recommended action per finding; remediation stays with the user.
- No chains outside Guardian's extracted doc-type coverage in v1 (insurance, real-estate, brokerage, aviation are in the source taxonomy but deferred — addable later as config).
- Not a replacement for `case_active_search`/`run_compliance_check` — it orchestrates them; they remain callable directly.

---

## The chain-spec config — `config/document_chains.yaml`

A chain encodes: which documents belong to it, which are required, the facts that must agree across it, and cross-fact relationship rules. Format:

```yaml
chains:
  stem_opt:
    name: "STEM OPT"
    # The chain applies when the data room contains any of these doc_types.
    detect_when_any: [i20, ead, i983]
    documents:
      - {doc_type: i20,               required: true,  label: "Form I-20 (STEM)"}
      - {doc_type: ead,               required: true,  label: "EAD / I-766"}
      - {doc_type: i983,              required: true,  label: "I-983 Training Plan"}
      - {doc_type: employment_letter, required: true,  label: "Employment/offer letter"}
      - {doc_type: i94,               required: false, label: "I-94"}
      - {doc_type: passport,          required: false, label: "Passport"}
    # Facts that must read identically wherever they appear in this chain.
    # Each key is a canonical fact_key from vocabulary.py; the engine compares
    # the value every source document contributed for that key.
    must_agree:
      - legal_name
      - sevis_id
      - current_employer_legal_name
      - current_employer_ein
      - current_position_title
      - worksite_address
      - current_annual_salary
    # Cross-fact relationship rules (beyond equality). Each rule names an
    # operator + the canonical keys it relates, with a human message.
    relationships:
      - {id: ead_covers_opt, op: date_within, of: [stem_opt_start_date, stem_opt_end_date],
         message: "STEM OPT period should fall within the EAD validity window"}
    # Deadlines to surface for this chain (delegated to the rule engine /
    # deadline config by key; the engine resolves the date from the SoT).
    deadlines: [stem_opt_end_date, i983_evaluation_due, opt_unemployment_90d]

  h1b:
    name: "H-1B"
    detect_when_any: [i797]
    documents:
      - {doc_type: i797,              required: true,  label: "I-797 Approval"}
      - {doc_type: employment_letter, required: false, label: "Offer/support letter"}
      - {doc_type: passport,          required: false, label: "Passport"}
    must_agree: [legal_name, current_employer_legal_name, current_immigration_status]
    relationships:
      - {id: h1b_after_opt, op: date_order, of: [stem_opt_end_date, h1b_classification_start_date],
         message: "H-1B start should not precede the STEM OPT end (cap-gap aside)"}
    deadlines: [h1b_classification_end_date, i94_admit_until_date]

  tax:
    name: "Federal + State Tax"
    detect_when_any: [w2, "1040_nr", "1042_s", form_8843, fbar]
    documents:
      - {doc_type: "1040_nr",  required: false, label: "Form 1040-NR"}
      - {doc_type: w2,         required: false, label: "W-2"}
      - {doc_type: form_8843,  required: false, label: "Form 8843"}
      - {doc_type: fbar,       required: false, label: "FBAR / FinCEN 114"}
    must_agree: [legal_name, ssn_last4, current_employer_legal_name, current_employer_ein]
    relationships: []
    deadlines: [tax_filing_deadline, fbar_due]
    # Conditional missing-doc rules delegated to the rule engine.
    rule_checks: [nra_requires_8843, fbar_threshold]

  corporate:
    name: "Corporate / Governance"
    detect_when_any: [articles, ein_letter, form_5472]
    documents:
      - {doc_type: articles,    required: false, label: "Articles of Incorporation"}
      - {doc_type: ein_letter,  required: false, label: "EIN / CP575"}
      - {doc_type: form_5472,   required: false, label: "Form 5472"}
    must_agree: [entity_legal_name, entity_ein, entity_address]
    relationships: []
    deadlines: []
```

**v1 ships these chains** (the Guardian-extractable subset of the accounting taxonomy): `stem_opt`, `h1b`, `tax`, `corporate`. Banking/KYC and DOL-PAF are stubs added when their doc types are extracted. The exact `must_agree` key lists are reconciled against `EXTRACTION_TO_FACT_KEY` during implementation (only keys that some doc type actually maps to are included; missing canonical keys like `i983_evaluation_due`, `entity_*`, `tax_filing_deadline` are added to `vocabulary.py`/the deadline config as part of the build).

---

## What it checks — three finding categories

For each chain whose `detect_when_any` matches a doc_type present in the data room:

### 1. Fact mismatches (the new core)

For each `must_agree` key, gather every *(document, value)* that contributed to it. Sources:
- `UserFactRow.detected_conflicts` (already-recorded conflicting values + their `source_ref.document_id`), plus
- `ExtractedFieldRow` joined back through `EXTRACTION_TO_FACT_KEY` (so we see each document's raw contribution even when the active fact "won").

If two source documents in the chain hold different normalized values for the same key → a **mismatch finding** (severity by key class: name/EIN/SEVIS = high; address/title = medium). Normalization: trim/case-fold for names, digit-only for EIN/SSN/SEVIS, ISO for dates, numeric for salary — so "Acme Inc" vs "Acme Incorporated" and "$135,000" vs "135000.00" are compared sensibly (with a "near-match, verify" sub-severity when normalization is ambiguous).

**Relationship rules** (`relationships`) evaluate the named operator (`date_within`, `date_order`, `<=`, etc.) over the canonical keys' SoT values; a violation is a mismatch finding.

### 2. Missing-from-chain

For each chain document with `required: true`, if no `DocumentRow` of that `doc_type` exists in the data room → a **missing finding** ("you have an I-20 + EAD but no I-983"). Reuses the `case_templates` Slot semantics (doc_type presence) rather than a folder scan.

### 3. Deadline / threshold risks

Resolve each chain's `deadlines` keys to dates from the facts SoT and surface those within a horizon (e.g. ≤ 180 days) or already past, via the existing `deadlines.py`. Run each `rule_checks` entry through the existing rule engine (`run_compliance_check` runners / `compliance_rules.yaml`) fed from the SoT. These reuse existing machinery — the engine just routes facts in and findings out.

---

## Output — `RiskReport` + the MCP tool

The engine returns a structured `RiskReport` (a dict); the MCP tool JSON-encodes it for the user's Claude to narrate.

```python
{
  "chains_detected": ["stem_opt", "tax"],
  "summary": {"mismatches": 2, "missing": 1, "deadlines": 3, "high_severity": 1},
  "findings": [
    {"category": "mismatch", "severity": "high", "fact": "current_employer_legal_name",
     "chain": "stem_opt",
     "values": [{"value": "Acme Inc", "doc": "i983", "doc_id": "..."},
                {"value": "Acme Incorporated", "doc": "employment_letter", "doc_id": "..."}],
     "message": "Employer name differs between your I-983 and offer letter — USCIS cross-references these.",
     "recommended_action": "Confirm the exact legal name and correct the document that's wrong."},
    {"category": "missing", "severity": "high", "chain": "stem_opt",
     "doc_type": "i983", "label": "I-983 Training Plan",
     "message": "You have an I-20 (STEM) and EAD but no I-983 on file.",
     "recommended_action": "Upload your signed I-983 (required within 10 days of STEM OPT start)."},
    {"category": "deadline", "severity": "medium", "chain": "stem_opt",
     "fact": "stem_opt_end_date", "date": "2027-05-14", "days_out": 343,
     "message": "STEM OPT (EAD) expires 2027-05-14.", "recommended_action": "..."}
  ]
}
```

### MCP tool contract

```
@mcp.tool  cross_check_filings(chain: str = "") -> str
  """Cross-check the user's uploaded filings for mismatches, missing forms,
  and deadline risks — entirely on-device. With no argument, auto-detects
  and checks every chain the data room implies; pass a chain id (stem_opt,
  h1b, tax, corporate) to scope to one. Returns a structured risk report
  to narrate; runs no model and sends no data off-device."""
```

Local-mode only for the data path (reads the local facts SoT via `get_session` + `get_local_user_id`), consistent with the other Plan-2 tools.

---

## Architecture & file structure

- **Create** `config/document_chains.yaml` — the chain spec (v1: stem_opt, h1b, tax, corporate).
- **Create** `compliance_os/compliance/cross_check.py` — the deterministic engine: `cross_check(db, user_id, chain=None) -> RiskReport`, plus the chain-spec loader, the normalizer, and the relationship-operator table. One module, one responsibility (compute the report); reuses `user_facts`, `EXTRACTION_TO_FACT_KEY`, `deadlines.py`, the rule runners.
- **Modify** `compliance_os/facts/vocabulary.py` / deadline config — add any canonical keys / deadline keys the chains reference that don't yet exist (e.g. `entity_legal_name`, `i983_evaluation_due`).
- **Modify** `compliance_os/mcp_server.py` — register the `cross_check_filings` MCP tool (local-mode data path).
- **Create** `tests/test_cross_check.py` — unit tests per finding category + an end-to-end fixture (seed a data room with a deliberate employer-name mismatch + a missing I-983 + an expiring EAD → assert all three surface).

The engine never re-reads files or calls the network; it operates on the SoT + extracted-field rows. The MCP tool is a thin local-mode wrapper.

---

## Testing

- **Fact mismatch:** seed two docs mapping to `current_employer_legal_name` with different values → one high-severity mismatch with both sources cited. Normalization: "Acme Inc" vs "Acme Incorporated" → flagged; "$135,000" vs "135000" → not flagged.
- **Relationship rule:** seed `h1b_classification_start_date` before `stem_opt_end_date` → `h1b_after_opt` violation.
- **Missing-from-chain:** seed `i20` + `ead`, no `i983` → missing-required finding for the STEM OPT chain; no finding for chains not detected.
- **Deadline:** seed `stem_opt_end_date` 60 days out → deadline finding; 2 years out → not surfaced (beyond horizon).
- **Auto-detect:** data room with only tax docs → `chains_detected == ["tax"]`, no immigration findings.
- **End-to-end:** the seeded "messy data room" returns the expected `summary` counts and ordered findings.
- **Reuse parity:** the deadline/threshold findings match what the existing rule engine returns for the same inputs.

---

## Open questions / deferred

1. **Cross-key fact pairs** — v1 compares values within a single canonical key (which already spans doc types via `EXTRACTION_TO_FACT_KEY`). True cross-*key* pairs (a value that should match across two *different* canonical keys) are rare in the current vocabulary; deferred until a concrete case appears.
2. **Banking/KYC + DOL-PAF chains** — defined in the taxonomy but their doc types aren't extracted yet; added as config when extraction supports them.
3. **Severity tuning** — initial key→severity map (name/EIN/SEVIS = high) is a starting point; tune against real reports.
4. **2.0.x delivery** — like the index/batch local-mode fixes, this reaches the installed extension only via a new PyPI release; bundle into the next version bump.

---

## Build sequence (high level — detailed plan to follow)

1. **Chain spec + loader** — `config/document_chains.yaml` (v1 chains) + a loader/validator in `cross_check.py`.
2. **Fact-consistency core** — gather per-doc contributions per `must_agree` key, normalize, diff → mismatch findings; relationship-operator table.
3. **Missing-from-chain + deadlines** — required-doc presence; wire chain `deadlines`/`rule_checks` to the existing engine.
4. **Assemble `RiskReport` + the `cross_check_filings` MCP tool** (local-mode).
5. **Vocabulary/deadline-key additions** for any keys the chains reference.
6. **Tests + end-to-end fixture.**
