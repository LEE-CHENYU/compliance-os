# Pipeline eval — final report — 2026-04-30

This is the combined Phase 1 (local fixture) + Phase 2 (prod cl4183
dogfood) evaluation of the document-pipeline rubric defined in
`tests/eval/pipeline_rubric.md`.

The headline correction vs. the Phase 1 gap memo: **the pipeline's
finding/deadline extraction is not broken** — the local fixture was
just too narrow to trigger any rules. Prod cl4183 surfaces 3 findings,
6 deadlines (3 of which are *extracted* I-983 evaluation due-dates,
not rule-derived), 6 advisories, and 22 structured key facts including
SEVIS#, employer EIN, total income, and entity type. The classifier
gaps are real and growing — but they are upstream of a working
extraction layer.

## Files produced

- `tests/eval/pipeline_rubric.md` — the rubric (versioned)
- `tests/fixtures/accounting_eval_set/manifest.yaml` — 52 hand-labeled fixtures
- `scripts/run_pipeline_eval.py` — automated scorer
- `scripts/dogfood_cl4183.py` — Phase 2 prod uploader with primary-source filter
- `docs/pipeline_eval_2026-04-30.md` / `.json` — Phase 1 raw scores
- `docs/pipeline_eval_2026-04-30_gaps.md` — Phase 1 gap memo (now superseded by §4 below)
- `docs/dogfood_cl4183_2026-04-30.json` — Phase 2 upload result log
- `screenshots/eval/local-dashboard.png`, `screenshots/eval/local-documents.png` — local screenshots
- `screenshots/eval/prod-cl4183-deadlines.png`, `screenshots/eval/prod-cl4183-keyfacts.png` — prod screenshots

## §1 — Phase 1 scores (local, eval test user, 52 fixtures)

| Dim | Name | Score | Bar | Verdict |
|-----|------|-------|-----|---------|
| 1 | Ingest reliability | 82.7% raw / **90.7% on positive controls** | 98% | FAIL |
| 2 | Classification accuracy | 93.0% | 85% | PASS |
| 3 | Dedup correctness | 100% | 100% | PASS |
| 4 | Index coverage | 100% | 95% | PASS |
| 5 | Finding extraction | 0 / 5 (false negative — see §3) | 5/5 | inconclusive |
| 6 | Deadline detection | 0 / 5 (false negative — see §3) | 5/5 | inconclusive |
| 7 | Latency p50 / p95 | 5.7s / 10.2s | <30s | PASS |
| 8 | Cost / 100 docs | n/a | baseline | — |

## §2 — Phase 2 prod state (cl4183, after partial dogfood ~125/529)

The dogfood was still running at the time of this report (estimated
completion ~2 hours total). Snapshot at the 100-doc checkpoint:

- **Ingest**: 53 OK + 30 dedup + 19 errors / 102 attempts → ~81% effective
  (nearly identical to local positive-control rate; the gaps are the
  same classifier blind spots)
- **184 docs in cl4183 data room** (was 121 before dogfood + ~63 net new)
- **3 Needs attention** (top-bar count) — derived from open findings
- **6 Potential risks** (FBAR, Form 8938, etc.) — category-presence prompts
- **3 findings** extracted by rules:
  - `cumulative_5472_penalty` (critical) — Form 5472 missed years
  - `foreign_capital_undocumented` (warning) — capital injected without source docs
  - `no_revenue_still_must_file` (info) — pro forma 1120 obligation
- **6 deadlines**:
  - 3× I-983 12-month evaluation due (2025-10-30, 2025-12-16, 2026-02-20) — **all overdue, extracted from doc dates**
  - Wyoming annual report due 2026-12-31 (rule-derived)
  - 2026 tax return due 2027-04-15 (rule-derived)
  - Form 5472 + pro forma 1120 due 2027-04-15 (rule-derived from finding)
- **22 key facts extracted** — SEVIS# `N0032185878`, employer EIN `87-3138342`,
  total income `67068`, entity type `Single-member LLC`, state `Wyoming`,
  job title, supervisor, full address, etc.

## §3 — The Phase 1 false-negative on findings/deadlines

Phase 1 graded dim 5 (finding extraction) at 0/5 because the local
dashboard showed `findings: list[0]`. The Phase 1 gap memo proposed
this as the highest-severity issue (S1).

**That was wrong.** Phase 2 prod shows the rule engine works fine.
Two reasons it didn't fire on local:

1. **Eval fixture is student-tax-skewed.** It includes 5 W-2s, 4 1042-Ss,
   4 paystubs, 2 tax returns, etc. — but no entity-formation docs
   (Articles, EIN letter, operating agreement), no I-983s, no
   foreign-capital wires. The findings rules fire on entity / I-983 /
   foreign-capital combinations.
2. **Eval user has no historical case state.** cl4183 had 121 docs
   already in the data room before the dogfood, including months of
   case-type chains and integrity prompts that bias which rules
   activate. The eval user is a tabula-rasa.

**Implication for the rubric:** the manual dim 5/6 score is only
meaningful on a user with a realistic doc *combination*. The fixture
should be expanded to include a "founder track" subset (entity docs +
foreign capital evidence + I-983 with date) before re-running dim 5/6.

The rubric file and runner are unchanged; the interpretation of dim
5/6 results is what changes.

## §4 — Combined gap list (severity-ranked, replacing the Phase 1 memo)

### S1 — Classifier filename regex too narrow on numeric+letter forms

Rejects every variation that has a letter immediately after a digit.
Affects 1099B, 1099INT, 1099R, etc.

```python
"1099": [
    r"(?:^|[^0-9])1099(?:[a-z]{0,4})(?:[^a-z0-9]|$)",
],
```

**Confirmed prod failures:** `2024_1099int_citibank_bsgc.pdf`,
`03_2024_1099int_citibank_llc.pdf`, `2024_1099b_schwab_xxx619_part1.pdf`.

### S2 — Bank-statement path-context lost when classifier sees temp file

`_resolve_doc_type_for_upload_file` writes the upload to
`upload_dir / .preflight_<uuid>_<file_name>`. The classifier's
`PATH_CONTEXT_PATTERNS` (e.g.
`r"/bank_statements/(?:boa|citibank|wells_fargo|schwab)/[^/]+\.csv$"`)
require the original directory in the path, but it's stripped during
upload — only the filename survives.

This bites every Schwab CSV (`schwab_llc_*`, `schwab_personal_*`),
every Schwab brokerage statement PDF, and the Wells Fargo CSV. The
Citibank CSVs only classify because their content has `Beginning
Balance` etc. — they're surviving on text classification, not path
context.

**Fix:** thread `original_filename` (or just the original parent dir)
into `classify_file`, *or* add filename patterns that don't need path
context:

```python
"bank_statement": [
    ...,
    r"^(?:schwab|wf|wells[_ -]?fargo|boa|bank[_ -]?of[_ -]?america|citi(?:bank)?)_",
],
"bank_statement_brokerage": [r"^schwab_brokerage_stmt_"],
```

**Confirmed prod failures:** 4 Schwab CSVs, 2 Schwab brokerage PDFs,
1 WF CSV in the first 100 uploads.

### S3 — Tie-breaker absent — multi-pattern filenames reject as ambiguous

`_best_scored_match` returns None when ≥2 doc_types tie on score. This
fails benignly for ambiguous text but causes hard rejection on filenames
like `B07_i20_westcliff_transfer_pending.pdf` (matches both `i20` AND
`transfer_pending_letter`) and `C2_ciam_cpt_application_training_plan.pdf`
(matches both `cpt_application` AND `i983` via "training plan").

**Fix:** add a priority ordering — when filename matches both `i20`
and `transfer_pending_letter`, prefer the more-specific
`transfer_pending_letter`. Concretely:

```python
SPECIFICITY_TIE_BREAKS = {
    ("i20", "transfer_pending_letter"): "transfer_pending_letter",
    ("cpt_application", "i983"): "cpt_application",
    ("articles_of_organization", "ein_application"): "articles_of_organization",
    # etc.
}
```

Or simpler: weight regex matches by token length. `transfer_pending`
is more specific than `i20`.

**Confirmed prod failures:** `B07_i20_westcliff_transfer_pending.pdf`,
`B09_i20_ciam_transfer_pending_sep2025.pdf`,
`C2_ciam_cpt_application_training_plan.pdf`.

### S4 — Missing doc_types found in real user data

The classifier has no patterns for these document categories that
showed up in cl4183:

| Missing doc_type | Example file |
|------------------|--------------|
| `business_plan` | `guardian_business_plan_v1.pdf`, `G2_guardian_ai_business_plan_v1.pdf` |
| `itin_support_letter` | `itin_support_letter_042126.pdf`, `tarlson_itin_fact_sheet.pdf` |
| `corporate_resolution` / `board_resolution` | `D3_corporate_resolutions.pdf`, `D11_board_resolution_signing_authority.pdf` |
| `bylaws` | `D2_bylaws.pdf` |
| `termination_letter` | `F2_claudius_termination_letter.pdf` |
| `governance_document` (catch-all?) | `D5_governance_docs_signed.pdf` |
| `key_documents_compilation` (multi-doc) | `D6_key_documents_compilation.pdf` |
| `ein_fax_notification` | `D8_ein_fax_notification.pdf` (probably ein_letter w/ different format) |

These are entity-formation, immigration-support, and HR paper that any
realistic founder/LLC user generates.

### S5 — Mixed-content PDFs land "ambiguous None"

Files like `01_BSGC_articles_and_ss4.pdf` (Articles of Organization +
SS-4 EIN application stapled together) and `D1_articles_of_incorporation_ss4.pdf`
contain content for two distinct doc_types. Text classifier sees both
sets of patterns and ties.

**Fix sketch:** when text classification ties between two doc_types
that commonly co-bind (Articles+SS4, I-983+CPT, transfer_pending+I-20),
return the *cover-page* doc_type (from page 1) rather than None.
Requires page-by-page extraction, which `pdf_reader.extract_first_page`
supports.

### S6 — Markdown rejected at MIME gate

Carryover from Phase 1. `.md` returns `application/octet-stream` and
the MIME allowlist rejects it.

### S7 — Text patterns for `identity_document` and `insurance_record` too generic

Phase 1 finding (3 false-positives in fixture). Fix is to require
anchor co-occurrence (e.g. `identity_document` needs
`national_id|passport|driver_license` to co-occur with
`Identification|ID Number|Date of Birth`). Or raise `TEXT_MIN_MATCHES`
for these two from 2 → 4.

## §5 — Combined verdict

| Layer | State |
|-------|-------|
| Upload + dedup + index | **works** (dim 1 capped by classifier; dim 3, 4 pass) |
| Filename classifier | **leaky** — S1, S2, S3, S4 all fixable; estimated +10pp on dim 1 with the four fixes |
| Text classifier | **mostly works** — S7 is the main false-positive source |
| Finding/deadline extraction | **works on real users** (Phase 1 false negative was a fixture coverage bug) |
| Key-fact extraction | **works** — SEVIS#, EIN, addresses, income, entity type all surfaced on cl4183 |

## §6 — Recommendations

### Pre-Phase-3: classifier patches

Order by ROI:

1. **S2** (path-context lost) — biggest impact. Either thread
   original_filename or add filename-only patterns for Schwab/WF.
   ETA: 1 hour. Expected impact: +6pp ingest reliability on prod.
2. **S1** (1099 numeric+letter regex) — 15 min. +1pp.
3. **S3** (tie-breaker) — 1 hour. +2pp + clean prod telemetry.
4. **S4** (missing doc_types) — 2 hours per category. Pick the four
   most common: `business_plan`, `bylaws`, `corporate_resolution`,
   `itin_support_letter`. +3pp.
5. **S6** (markdown gate) — 15 min. +0pp on real users (no real user
   uploads .md), but quality-of-life.
6. **S7** (identity/insurance text patterns) — 30 min. Cleans up
   classification noise in dim 2.

Total: ~6 hours of classifier work for ~12pp ingest, ~5pp accuracy.

### Eval fixture

Add a "founder track" set (~20 docs) to `accounting_eval_set/manifest.yaml`:
- Articles of Organization
- EIN letter (CP-575)
- Operating agreement
- Schwab brokerage statement
- 1099-INT and 1099-B
- I-983 with end date (for deadline extraction)
- Foreign-capital wire transfer record

Without these, dim 5/6 is not measurable.

### Account strategy (the original question)

Confirmed: **two-account model is correct.**

- **eval-20260430@guardian.local** (local sqlite) — for rubric scoring,
  fast iteration on classifier patches, no PII risk
- **cl4183@columbia.edu** (prod) — for product-truth checks; the
  *findings/deadlines/key-facts that matter* surface only on a
  realistic user with the right doc combinations, which the test
  account can't simulate

Both already have `pro/active` tier so quotas don't gate the eval.

### Phase 3 (out of scope for today)

- Classifier patches above
- Re-run Phase 1 with expanded fixture → confirm dim 5/6 measurable
- Wire one regression-style test that fails if any of S1-S7 reverts
- Prod telemetry on classifier-rejection rate (currently we only know
  via dogfood; an `ingestion_issue` metric would catch this in real
  users)
