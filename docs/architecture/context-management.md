# Context Management — Guardian's Single-Source-of-Truth Model

> **Status:** Design spec, not yet implemented (2026-05-22). Reviewing the
> shape before building. Adapted from `/Users/lichenyu/accounting/CLAUDE.md`
> §290-380 (the consolidation + archive policy used in the accounting
> project) and projected onto Guardian's multi-user backend.

## 1. Why this exists

The value prop that distinguishes Guardian from a generic Claude Code
extension is not search quality — it's **knowing which document is
authoritative right now**. A user accumulates 47 I-797s, 12 paystubs,
3 versions of the same I-983, and 9 RFE drafts over a multi-year
visa journey. Claude Code can grep all of them; only Guardian can
say "the H-1B classification end date is 2030-09-30 per the amendment
of 2027-02-10, superseding the original 2029-09-30."

Without this layer, the LLM agent reads all 47 documents and picks
one ~uniformly at random when answering a question. The user has to
remember which one is current. That defeats the point of the
extension.

The accounting project has solved this for one user over ~6 months
of attorney/CPA engagements. The pattern is reusable; this doc
defines how Guardian adopts it.

## 2. Core principle

> **Keep all facts in one authoritative place, without omission,
> except items with truly no value. Bias toward consolidation
> (merging facts into authoritative sources), not archival (hiding
> sources). Archival is the last step, only after every unique fact
> has been verified-captured elsewhere. NEVER delete — always
> archive.**

Doc proliferation is a smaller cost than information loss. If
unsure, keep.

## 3. Storage layers

Three layers, in order of authority. Each layer's role is fixed —
data does not migrate freely between them.

| Layer | What it holds | Primary table / file | Authority |
|---|---|---|---|
| Primary documents | Raw source material — uploaded PDFs, IRS forms, USCIS notices, lease agreements, bank statements. | `documents_v2` (existing) | Highest. The actual artifact the user (or USCIS) signed. |
| User facts (SoT) | Distilled facts derived from primary documents + decision locks. Per-user, semi-structured. | `user_facts` (new) | Authoritative for locked decisions and current-state facts. |
| Workstream trackers | Time-bound action items, engagements, communications. | `professional_search_requests`, `cases`, deadline rows | Authoritative for "what's next" / "who's engaged" — never for the underlying facts. |

MEMORY (auto-memory at
`~/.claude/projects/-Users-lichenyu-compliance-os/memory/`) is
**working notes only, not SoT.** Useful for cross-session continuity
of conversation context; never authoritative for facts.

## 4. `user_facts` schema (new)

```python
class UserFactRow(Base):
    __tablename__ = "user_facts"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Controlled-vocabulary key + free label.
    # fact_key draws from compliance_os/facts/vocabulary.py (shared
    # across users for analytics) but accepts ad-hoc keys with a
    # "custom:" prefix.
    fact_key = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False)
    category = Column(String)  # immigration | tax | corporate | personal | employment
    track = Column(String)     # young_professional | student | entrepreneur | shared

    # Semi-structured value: JSON so the same column can hold a
    # string, number, ISO date, or structured object without schema
    # migrations. Always wrapped in a JSON object so future readers
    # can attach metadata: {"v": <value>, "unit": "USD", "as_of": "2026-04-01"}.
    value = Column(JSON, nullable=False)
    notes = Column(Text)  # long-form qualifiers (accounting's notes:|)

    # Provenance — replaces accounting's "Authoritative source" column.
    source_type = Column(String, nullable=False)
    # document | decision_lock | gmail | external_api | user_input
    source_ref = Column(JSON)
    # document  → {"document_id": uuid, "page": 1, "field": "h1b_end_date"}
    # decision  → {"locked_at": "2026-04-29", "note": "user-confirmed in chat"}
    # gmail     → {"thread_id": "...", "msg_id": "...", "sender": "..."}
    # external  → {"api": "uscis_case_status", "fetched_at": "..."}
    # user_input→ {"prompt_id": "...", "ui_path": "/profile"}

    # Decision-lock metadata. Lock = "no future doc should silently
    # override this without surfacing the conflict to the user."
    locked_at = Column(DateTime, nullable=False, default=_now)
    superseded_by_id = Column(String, ForeignKey("user_facts.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    # Auto-detected conflicts — list of {document_id, claimed_value,
    # detected_at}. Populated when a new document extraction
    # contradicts this row. Surfaced in the dashboard for
    # disambiguation. Never auto-resolved.
    detected_conflicts = Column(JSON, default=list)

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    __table_args__ = (
        UniqueConstraint("user_id", "fact_key",
                         name="uq_user_fact_active"),
    )
```

The unique constraint plus `is_active=False` on superseded rows
ensures one active fact per (user, key). Historical values stay
queryable via `is_active=False` rows — same pattern as
`documents_v2.supersedes_document_id` already uses.

## 5. Canonical vocabulary

`compliance_os/facts/vocabulary.py` defines ~80 canonical keys:

```python
CANONICAL_FACTS = {
    # Shared across all tracks
    "current_employer_legal_name":   FactDef("Current employer (legal name)",   "employment", "shared"),
    "current_employer_ein":          FactDef("Current employer EIN",            "employment", "shared"),
    "current_immigration_status":    FactDef("Current immigration status",      "immigration","shared"),
    "current_residential_address":   FactDef("Current residential address",     "personal",   "shared"),
    "ssn_last4":                     FactDef("SSN (last 4)",                    "personal",   "shared"),

    # Young Professional / H-1B chain
    "h1b_classification_end_date":   FactDef("H-1B classification end date",    "immigration","young_professional"),
    "h1b_receipt_number":            FactDef("H-1B receipt number (I-797)",     "immigration","young_professional"),
    "h1b_amendment_dates":           FactDef("H-1B amendments (date list)",     "immigration","young_professional"),
    "stem_opt_end_date":             FactDef("STEM OPT end date",               "immigration","young_professional"),

    # International Student / F-1
    "i20_program_end_date":          FactDef("I-20 program end date",           "immigration","student"),
    "sevis_id":                      FactDef("SEVIS ID",                        "immigration","student"),
    "dso_contact":                   FactDef("DSO contact",                     "immigration","student"),
    "cpt_term_dates":                FactDef("CPT term dates",                  "immigration","student"),

    # Entrepreneur / foreign-owned entity
    "entity_legal_name":             FactDef("Entity legal name",               "corporate",  "entrepreneur"),
    "entity_ein":                    FactDef("Entity EIN",                      "corporate",  "entrepreneur"),
    "entity_state_of_formation":     FactDef("Entity state of formation",       "corporate",  "entrepreneur"),
    "entity_naics_code":             FactDef("NAICS code",                      "corporate",  "entrepreneur"),
    "form_5472_filing_status":       FactDef("Form 5472 filing status",         "tax",        "entrepreneur"),

    # Tax (shared)
    "tax_filing_status_latest":      FactDef("Latest tax filing status",        "tax",        "shared"),
    "form_8843_filed":               FactDef("Form 8843 filed (y/n + year)",    "tax",        "shared"),
    "fbar_filed":                    FactDef("FBAR filed (y/n + year)",         "tax",        "shared"),
    # ...
}
```

The vocabulary is the controlled side of "semi-structured." Users
who need a fact outside the catalog can store it under `custom:<key>`
— it's queryable but not part of the canonical track template.

## 6. Authority hierarchy

When two layers disagree, the higher layer wins. From most to least
authoritative:

1. **Primary source documents** (`documents_v2` with `is_active=True`).
   USCIS I-797, signed lease, tax-return PDF, bank statement. The
   raw artifact.
2. **`user_facts` with `source_type=decision_lock`** — explicitly
   user-locked decisions ("I've decided to file as resident alien
   this year"). Overrides document-derived facts intentionally.
3. **`user_facts` with `source_type=document`** — facts auto-extracted
   from a primary document. Inherits the authority of that document.
4. **Workstream trackers** — engagement status, professional search
   reports, deadline rows. Authoritative for "what's next," never
   for the underlying facts.
5. **MEMORY / chat working notes** — recent context only. Verify
   against trackers/SoT before treating as authoritative; update or
   remove stale entries proactively.

A `user_facts` row with `source_type=document` whose source document
becomes `is_active=False` (superseded) must either be auto-superseded
itself or surfaced as a conflict. See §8.

## 7. Consolidation triggers

The system auto-detects these. Each triggers a UI prompt or
background job — never a silent rewrite of authoritative state.

| Trigger | Detection | Action |
|---|---|---|
| Same fact extracted from 3+ documents with identical value | Background sweep over `documents_v2` extractions | Promote to `user_facts`, link all three documents in `source_ref.evidence[]`. |
| Same fact in 3+ docs with conflicting values | Same sweep | Create or update `user_facts` row; populate `detected_conflicts`; surface in dashboard. |
| New document upload contains a fact already in `user_facts` | Post-upload hook in `dashboard.py` | If the new doc supersedes (later effective date, amends, or is in the same `document_series_key` chain), auto-supersede the old row. If unclear → record conflict. |
| User edits a fact in the UI | `POST /api/facts/{key}` | Lock as `decision_lock`. Snapshot prior version as `is_active=False`. |
| Workstream closes (engagement declined, case filed) | Manual user action OR background sweep | Suggest archival of working files. |

## 8. Auto-supersession on document upload

When `POST /api/dashboard/upload` lands a new document:

1. **Classify** → produces `doc_type`.
2. **Series-key lookup** — compute `document_series_key` (e.g., for
   I-797: `i797:<beneficiary_ssn_last4>:<petition_type>`). Find
   existing `documents_v2` rows with the same series_key.
3. **If a same-series doc exists and is older (by effective_date
   from the extracted metadata, falling back to uploaded_at)**:
   - Mark the older row `is_active=False`, set
     `supersedes_document_id` on the new row.
   - Record the supersession in the new row's `provenance`:
     `{"supersedes": [<old_id>], "supersession_reason": "newer_in_series"}`.
4. **Extract facts** from the new document. For each extracted
   field that maps to a `fact_key`:
   - If the user has an active `user_facts` row with the same key
     whose `source_ref.document_id` points to the now-superseded
     document → auto-supersede the fact row to the new value.
   - If the user has an active row sourced from a different document
     and the new value differs → record in `detected_conflicts` and
     emit a dashboard prompt.
   - If no active row exists → create one.

The doc upload never silently overwrites an active fact whose source
is unrelated to the new upload.

## 9. Archive policy

Mirrors accounting's `archive/<original-relative-path>` pattern, but
soft-archived inside the same tables:

- **Documents**: `is_active=False`. Excluded from default
  `smart_search`, `query_documents`, and dashboard listings.
  Reachable via `?include_archived=1` query param or "Show archived"
  toggle.
- **Facts**: `is_active=False`. Same exclusion rules.
- **Hard delete** is never automatic. The only delete path is the
  bulk-delete UI on `/dashboard?view=documents` (already exists; see
  `dashboard/page.tsx:2552`), which the user must explicitly trigger.

What's archive-eligible (both conditions must hold):

1. All unique facts the document established have been
   verified-captured in `user_facts` (and `user_facts` rows still
   reference it via `source_ref.document_id` even after archival —
   the link survives).
2. The document has no expected future reference value (not
   historical record value, not analytical reference value).

What's NOT archive-eligible — keep `is_active=True` even when
"superseded":

- Outreach correspondence to declined counterparties — historical record.
- Due-diligence files for declined attorneys/CPAs — analytical content.
- Older strategy memos that informed current decisions — reasoning history.
- Session notes that recorded decisions — audit trail.
- Research files for paths not chosen — future-pivot reference.

## 10. UI exposure

| Surface | What it shows | Source query |
|---|---|---|
| `/dashboard` → "My Profile" tab (new) | Active `user_facts` grouped by category, sortable by `locked_at`. Each row links to its source document. Conflict badge on rows with non-empty `detected_conflicts`. | `SELECT * FROM user_facts WHERE user_id=? AND is_active=true ORDER BY category, label` |
| `/dashboard` → Documents view | Active documents only by default. "Show archived" toggle reveals superseded ones in a separate section. | existing `documents_v2` query + `is_active=true` filter |
| `/dashboard` → Conflict prompts | Modal/banner when an upload triggers `detected_conflicts`. Two CTAs: "Use new value (supersede)" / "Keep current". | post-upload hook returns conflict list |
| `/dashboard` → Track-template progress | "12 of 18 STEM-OPT facts captured" — shows missing canonical keys for the user's track. | `vocabulary.py` filter + `user_facts` join |

## 10b. Intent detection (no magic word)

The MCP server does not require a slash-command trigger or a fixed
magic phrase. The model decides when to call `upload_document` based
on natural intent. The `FastMCP(instructions=...)` block is extended
with:

> When the user expresses intent to save, file, record, add, ingest,
> remember, or pin a document, image, attachment, or piece of
> evidence they just provided or referenced — call `upload_document`
> with the file path. Examples of intent phrases (not exhaustive):
> "save this", "file this", "add this to my data room", "remember
> this", "for the record", "ingest this", "pin this as current",
> "supersede the old one with this". Default to ingest (do not pass
> `defer_ingest=True`) unless the user explicitly says they want to
> review extraction before facts land in their profile.

The point is to be permissive — the model already handles natural-
language intent detection; surfacing a closed vocabulary of trigger
words would just create a footgun when users phrase it differently.

## 11. MCP tool contracts (new + updated)

New tools:

- `get_user_facts(category: str = "", track: str = "")` — return
  active `user_facts` for the caller. Filter by category or track.
- `set_user_fact(fact_key: str, value: any, source_note: str = "")` —
  user-driven decision lock. Creates or supersedes.
- `list_archived_documents()` — return `is_active=False` documents
  with their `superseded_by` chain.
- `resolve_fact_conflict(fact_id: str, choice: str)` — `choice` is
  "use_new" | "keep_current" | "user_value:<v>".

Updated tools:

- `query_documents` — already implemented; `smart_search` now
  defaults to `is_active=true` and accepts `include_archived=True`.
- `upload_document` — backend post-hook (§8) runs automatically; tool
  response includes `superseded` and `conflicts` summaries.

## 12. What we borrow verbatim from accounting

| Accounting rule | Guardian implementation |
|---|---|
| "NEVER delete — always archive" (§290) | `is_active=False`, never `DELETE FROM` |
| "Same fact in 3+ docs → consolidate" (§302) | §7 trigger #1 |
| "Read primary source before treating tracker claim as authoritative" (§80) | UI links every fact row to its source document; clicking opens it |
| "Memory is not SoT" (§66) | Auto-memory at `~/.claude/projects/...` excluded from authority hierarchy (§6, layer 5) |
| Authoritative-source hierarchy (§351) | §6 |
| Archive-eligibility two-condition test (§309) | §9 |
| Locked-decision concept (`Decision-locked 2026-04-29`) | `source_type=decision_lock` + `locked_at` |

## 13. What's different from accounting

- **Multi-user**: every table is keyed by `user_id`. Vocabulary is
  shared; values are tenant-scoped.
- **Per-user, not per-project**: no `concerns/<topic>_<date>.txt`
  pattern. Workstream trackers stay in the DB.
- **Auto-extraction**: accounting's facts are user-curated by hand
  into CLAUDE.md tables. Guardian extracts them from document OCR +
  classifier output, then surfaces conflicts for review. The user
  approves, doesn't transcribe.
- **No `archive/` directory on disk**: superseded artifacts stay in
  the same tables with `is_active=False`. The file blob stays in
  the data room; only the row's visibility changes.

## 14. Rollout plan

1. **Spec review (this doc)** — confirm shape before coding.
2. **Vocabulary file** — `compliance_os/facts/vocabulary.py` with
   ~80 canonical keys + `FactDef` schema.
3. **`user_facts` table + migration** — schema above, plus an
   Alembic migration. Backfill nothing on first deploy; the
   extractor populates as users upload.
4. **Extractor wiring** — extend `compliance_os/web/services/extraction`
   to write `user_facts` rows alongside the existing `extracted_fields`
   table.
5. **Post-upload supersession hook** — implement §8.
6. **`smart_search` `is_active` filter** — default `is_active=true`,
   `include_archived` flag for the toggle.
7. **MCP tools** — `get_user_facts`, `set_user_fact`,
   `list_archived_documents`, `resolve_fact_conflict`.
8. **Dashboard UI** — "My Profile" tab, archive toggle, conflict
   prompt modal.
9. **Re-run search eval** — once `user_facts` is populated for the
   eval-fixture user, add a "fact lookup" question class to the
   bank to confirm `smart_search` surfaces facts cleanly.

After rollout, re-tune the embedding bakeoff against the user's
actual on-file corpus (compliance-os/uploads, accounting/, anything
else they want indexed) instead of the synthetic 20-doc fixture set.
That feeds back into the default model selection for both Guardian
and the to-be-built accounting search upgrade.

## 15. References

- `/Users/lichenyu/accounting/CLAUDE.md` — source policy (§290-380
  consolidation/archive, §155-189 factual consistency, §351
  authoritative-source hierarchy).
- `/Users/lichenyu/accounting/docs/project_tracker.md` — multi-layer
  source-of-truth navigation pattern.
- `/Users/lichenyu/accounting/concerns/priorities.yaml` — semi-
  structured YAML pattern with `notes:` escape hatch.
- `compliance_os/web/models/tables_v2.py` — existing `documents_v2`,
  `subject_chains`, `subject_document_links` (already partly support
  this model; see schema table in §4).
- `docs/architecture/search.md` (TODO, separate doc) — how
  `smart_search` interacts with `is_active` filtering once §9 lands.
