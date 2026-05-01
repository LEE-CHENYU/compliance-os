# Worth incorporating from `/Users/lichenyu/accounting/CLAUDE.md`

The accounting CLAUDE.md is mostly operating-mode rules for *Claude
Code working on the accounting case* (RAG-first answering, Gmail send
script, signing-authority discipline, attorney-credential verification).
Most of it doesn't translate to compliance-os because compliance-os is
the *product*, not the assistant. But several policies map directly to
features the product already half-implements or should.

I'd group them into three buckets: **ship soon** (high signal/effort
ratio, clear product surface), **bake into existing features**
(behavioral changes inside features that already exist), and **skip**
(accounting-case-specific or already covered).

## Ship soon

### 1. Cross-document fact-consistency finding

**Source policy:** "Factual Consistency Across Documents" (line 180-240)
— a single-source-of-truth table maintained by hand to catch the case
where two external-facing docs disagree on EIN, address, salary, etc.

**Why it fits compliance-os:** Prod cl4183 already surfaces 22 key
facts extracted across the data room (SEVIS#, employer EIN, total
income, employer address, etc.). The system has the *values* — but
nothing flags when two docs disagree. The user's accounting policy
exists *because they got bitten by this* (Yangtze HQ address with/
without unit number across forms; Wells Fargo email fabricated "Unit
101"). Real users with real legal/banking exposure care about this.

**Concrete change:** New rule in `compliance_os/web/services/rule_engine.py`
or a new finding extractor in `timeline_builder.py`:

```python
# pseudo-rule
for field_name in ("ein", "employer_ein", "address", "salary",
                   "entity_legal_name", "passport_number"):
    values = {f.field_value for f in extracted_fields_named(field_name)
              if f.field_value not in (None, "")}
    if len(values) > 1:
        emit_finding(
            rule_id="cross_doc_inconsistency",
            severity="warning",
            title=f"{field_name} differs across documents",
            details=[(doc.filename, val) for doc, val in occurrences],
            action="Review the conflicting documents and pick the canonical value",
        )
```

ETA: 1-2 days. Low frontend work — finding goes through the existing
findings pipeline. Big user trust win.

### 2. Provenance tags on extracted facts

**Source policy:** "Provenance check on facts surfaced from internal
documents" (line 67-89) — the user got bitten by treating a fact in
MEMORY.md as authoritative when it was actually an inference from a
prior file.

**Why it fits:** Today the dashboard shows `Total income: 67068`
without saying *which* doc that came from. If the user wants to trust
or correct it, they have no breadcrumb. The product already has the
data — `ExtractedFieldRow.document_id` joins back to the source — but
the dashboard renderer doesn't show it.

**Concrete change:** Add `source_document` to the key-facts payload in
`build_timeline()` (line ~1428 of timeline_builder.py); render as a
small "from W-2 (2025-09-30)" caption under each value on the Key
Facts tab in the frontend. Hover/click drills into the doc viewer.

ETA: half a day backend + half a day frontend. Pure UX win, no risk
of breaking anything.

### 3. Filename ↔ content classification disagreement → ingestion issue

**Source policy:** "Mislabeled-file propagation" (line 81) — a file
named `*yunhong_affidavit_financial_support.pdf` had completely
different content (Chenyu's I-20). The wrong identity propagated
through three downstream submissions before someone read the file.

**Why it fits:** compliance-os' classifier already runs both filename
and text classification. When they *disagree* — e.g., filename says
`affidavit` but text matches `i20` — we currently silently pick one
and store. The right behavior is to **flag the mismatch as an
ingestion issue** so the user can confirm.

**Concrete change:** In `_resolve_doc_type_for_upload_file`
(`compliance_os/web/routers/dashboard.py:139`), when filename and
text classifications return different `doc_type`s with both confident,
emit a `IngestionIssueRow` of type `filename_content_mismatch` with
both candidates. UI prompts user to pick.

ETA: 1 day. Tied to the Phase 1 S3/S5 gap from the eval rubric — both
are about "ambiguous classification handled poorly".

## Bake into existing features

### 4. Search-before-asking in the chat assistant

**Source policy:** "RAG-First Policy" (line 38-66). The assistant
should always run a search before asking the user a factual question.

**Why it fits:** The Guardian chat assistant exists
(`compliance_os/web/routers/chat.py`). Today it has retrieval but
doesn't enforce the "search first" discipline at the prompt level.

**Concrete change:** In the chat system prompt, add an explicit rule:
"Before asking the user any factual question (date, amount, name,
employer, etc.), run a retrieval search. Only ask the user if search
returns nothing or surfaces conflicts." Plus: cite the source doc on
every chat answer.

ETA: 2 hours of prompt engineering + a few traces to verify behavior
changes. Highest user-trust win for the chat product.

### 5. Default-to-minimum-defensible in Guardian recommendations

**Source policy:** "Default-to-Minimum-Defensible Policy" (line 242).

**Why it fits:** Guardian recommends services ("you might need a CPA
who handles non-resident filings"). Right now the recommendation can
default to expensive options. The policy: lead with the floor + small
buffer, not the comfortable middle.

**Concrete change:** The marketplace recommendation logic
(`dashboard_marketplace.py`) should sort by *minimum-fit-cost* by
default, not by some "best match" heuristic that may surface premium
firms first. Add a clear "starts at $X" anchor; let the user expand
to higher tiers explicitly.

ETA: copy + ranking change in marketplace, half a day.

### 6. No fabrication of document fields in Form 8843 generator

**Source policy:** "No Fabrication of Document Fields" (line 307).

**Why it fits:** `generate_form_8843` accepts user inputs and fills the
PDF. If the user leaves a field blank, the generator should output a
blank field, not infer one. Today this is probably already the case
but worth auditing.

**Concrete change:** Audit `compliance_os/web/services/form_8843.py`
for any `or "default"` fallbacks on user-provided fields. Replace
silent defaults with explicit "left blank — verify before signing"
warnings on the output.

ETA: 1-2 hours audit + small tweaks.

## Skip (accounting-case-specific or already covered)

- **Email-via-Gmail-script discipline** — no equivalent in compliance-os
- **Yangtze signing-authority rules** — case-specific
- **Diligence DB read-first / write-on-event** — compliance-os has its
  own diligence DB (`data/diligence.db`) with similar discipline already
  implicit in the `professional_search_runner.py` flow
- **The specific SoT table values** (Yangtze EIN, NAICS code, etc.) —
  user-specific, not a product feature
- **Anti-self-handicapping in attorney correspondence** — user-side
  drafting discipline, not a Guardian feature unless we ship lawyer-
  drafting templates (not on roadmap)
- **Plain-language register for retained counsel** — same — drafting,
  not product
- **Time awareness policy** — compliance-os already passes current
  date through to date-comparison logic
- **Information disclosure policy** — applies to outbound emails the
  *user* writes; Guardian's outbound (deadline reminders, FBAR alerts)
  should also follow this but it's a copy-review task, not a code
  change

## Recommendation

Do **#1 (cross-doc consistency)** first — it's a real product
differentiator, the data is already there, and it directly addresses
a class of bug the user *has personally been bitten by*. After that
#2 (provenance tags) is the most visible UX win for the lowest cost.
#3 (mismatch ingestion issue) folds neatly into the next pass on the
classifier rubric work.

#4-6 are smaller polish items that improve trust without adding new
surface area. Do them when touching the relevant feature anyway.
