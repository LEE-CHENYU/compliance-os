# Onboarding Grounding — Plans 2–4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Executed on branch `feat/tool-grounding-foundation` (stacked on Plan 1). Steps tracked via the task list.

**Goal:** Finish the remaining tool-layer + instruction work from the cold-start onboarding spec (`docs/superpowers/specs/2026-06-08-cold-start-onboarding-design.md`) so the document-grounded workflows (H-1B/5472/I-485/J-1/founder/dependents) can actually classify+extract, the case templates stop leaking a real user's PII, and the extension's server instructions encode the cold-start behavior.

**Env/test conventions:** interpreter `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python`; run pytest from repo root; ruff `/Users/lichenyu/miniconda3/envs/compliance-os/bin/ruff`. Pre-existing lint (E402 mcp_server, F401 `Path`, F541) is not ours.

---

## Plan 2 — Document classifier + extraction labels (spec §8.4)

Add 6 fully-wired doc types so grounded extraction works: `i797` (full add — only its extraction-map rows exist today), `i130`, `i485`, `lca` (ETA-9035), `ds2019`, `advance_parole` (I-512). All edits are **additive** (append to dicts); no existing lines change.

**Touch points (append-only):**
- `compliance_os/web/services/classifier.py` — `FILENAME_PATTERNS`, `PATTERNS`, `TEXT_MIN_MATCHES` (use 2), `DOC_TYPE_ALIASES`. Adding to `PATTERNS` auto-includes the type in `SUPPORTED_DOC_TYPES`.
- `compliance_os/facts/vocabulary.py` — new `FactDef`s (category ∈ immigration/tax/corporate/personal/employment/education; track ∈ shared/young_professional/student/entrepreneur). All `h1b_*`, `legal_name`, `worksite_address`, `lca_case_number`, `current_*` already exist.
- `compliance_os/facts/extraction_map.py` — `EXTRACTION_TO_FACT_KEY` rows ((doc_type,field)→fact_key); these double as the extraction schema + SoT projection. `i797` rows already present.

**New FactDefs:** `i130_receipt_number`, `aos_receipt_number`, `priority_date`(date, shared by i130/i485), `lca_soc_code`, `lca_job_title`, `lca_wage_level`, `lca_prevailing_wage`(number), `ds2019_program_sponsor`, `ds2019_program_end_date`(date), `exchange_visitor_category`, `advance_parole_expiry`(date), `advance_parole_document_number`.

**Key decision:** `advance_parole` maps its `valid_to`→`advance_parole_expiry` (its OWN date fact), NEVER `ead`'s `stem_opt_end_date`.

**Tests** (`tests/test_classifier_service.py` style — inline `classify_text(text).doc_type == "..."`; `tests/test_extraction_rehome.py` style — `schema_for_doc_type(...)`): one classify test per type (text must hit ≥2 PATTERNS anchors), plus schema tests confirming `lca`→`lca_soc_code` and `advance_parole`→`advance_parole_expiry` (NOT `stem_opt_end_date`). Run: `pytest tests/test_classifier_service.py tests/test_extraction_rehome.py -q`.

**Decomposition:** 1 implementer task (all 6 types are the same additive pattern, non-conflicting), then spec + quality review.

---

## Plan 3 — PII-free case templates (spec §8.2)

`h1b.py` (59 slots) and `cpa.py` (28 slots) are hardcoded to one real user's case (Columbia/CIAM/Westcliff, SJTU/Waseda, Wolff & Li/Yangtze/BitSync/Tiger/Claudius, VCV, TD Ameritrade/Schwab/Citibank, Wyoming, USCIS receipts IOE9041477055/IOE9733115480). `case_active_search('h1b'|'cpa')` runs them blindly.

**Task A — Sanitize** `compliance_os/case_templates/h1b.py` + `cpa.py`: replace every real-identifier slot title/description/keyword/filename_pattern + both docstrings with generic equivalents (full old→new list lives in the Task A implementer prompt). **Invariants the tests enforce (must stay true):** exactly **59** h1b slots; sections **A–G**; B-section lineage orders **1→13**; all slot ids unique; template ids stay **`h1b_petition`** / **`cpa_nr_entity`**. Strip the two USCIS receipt numbers (A7/A8). Generalize F4a–d patterns to `i[-_]?983` + their `^F4x[_-]` prefix (the slot-id prefix disambiguates).

**Task B — Add 4 generic templates** as new files + register in `validator.py` (short alias + `template.id`) and `__init__.py`:
- `founder_h1b.py` → `Template(id="founder_h1b_petition")` — Beneficiary / E-Verify enrollment / Ownership & cap table / Corporate governance / Employer-employee relationship / Registration.
- `form_5472.py` → `Template(id="form_5472_dre")` — Summary / Entity & EIN (CP-575, formation cert, operating agreement) / Foreign owner / Reportable transactions (pro-forma 1120) / Filing.
- `eb1a.py` → `Template(id="eb1a_evidence")` — Petition core + the 8 CFR 204.5(h)(3) criteria buckets (3-of-8, most `required=False`).
- `dependent_status.py` → `Template(id="dependent_status")` — Principal linkage / Dependent identity / Relationship evidence / Status docs (F-2/J-2/H-4).

The matcher is fully data-driven — new templates work once registered (no matcher changes).

**Decision — skip the interim guard.** The spec's "never run `case_active_search` for arbitrary users" was an *interim* measure pending sanitization. Sanitization (Task A) removes the actual leak, so a `contains_pii` guard would be dead code; omit it.

**Tests:** keep `tests/test_case_templates.py` + `tests/test_validator.py` green (the 59-slot / sections / lineage / id assertions). Add a small `tests/test_new_case_templates.py` asserting each of the 4 new templates resolves via `validator.resolve_template(...)`, has its expected sections, and has unique slot ids. Run: `pytest tests/test_case_templates.py tests/test_validator.py tests/test_new_case_templates.py -q`.

**Decomposition:** Task A (sanitize) → review; Task B (new templates + register) → review.

---

## Plan 4 — Cold-start server instructions (spec §3–§7)

Rewrite the `GatedMCP(instructions=...)` block in `compliance_os/mcp_server.py` to encode the cold-start design: the scope gate (fail closed, not into the nearest box), value-before-extraction + triage-before-route, the routing signals (ownership splits CPT vs founder; principal/dependent gate; I-485-in-US vs consular; three-way income fork with scholarship→1040-NR), **label reasoning when no check exists** + the real check inventory (`h1b_doc_check, fbar, student_tax, 83b_election`; `get_filing_guidance` only `form_8843`), document-first with an OS-correct copy-path how-to, **artifact honesty** (use the new `save_artifact` tool; don't claim "saved" otherwise), the mandatory consult-an-attorney hedge for unverified travel/status verdicts, Gmail draft-by-default, "don't call READ-STATE tools at cold start", and a canonical `set_user_fact` track taxonomy (`f1_cpt, f1_status, foreign_owned_llc, fbar, h1b_petition, dependent_status, …`).

**Tests:** instruction text isn't unit-testable, so add `tests/test_server_instructions.py` asserting `mcp_server.mcp.instructions` (or the module-level instructions string) contains the load-bearing guidance markers (e.g. substrings: "save_artifact", "not a computed check"/"reasoning", "consult", scope-gate language, "8843", the four real check names). This locks the guidance in against accidental deletion. Run: `pytest tests/test_server_instructions.py -q`.

**Decomposition:** 1 implementer task → review.

---

## Completion
After all three: run the full touched-area suites, confirm no NEW failures vs. the Plan-1 baseline (15 pre-existing failures on main), update PR #8 to describe all four plans.
