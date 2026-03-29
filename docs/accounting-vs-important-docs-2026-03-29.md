# Accounting Vs Important Docs

Date: `2026-03-29`

Compared:
- `/Users/lichenyu/accounting`
- `/Users/lichenyu/Desktop/Important Docs `

Method:
- Compared by `sha256` content hash, not filename.
- Considered follow-on data-room candidates in `pdf/png/jpg/jpeg/docx/csv`.
- Excluded repo/runtime noise such as `.git`, skills, scripts, `chroma_db`, and secrets.
- Excluded derived package copies such as `parsed`, `reports`, `docs`, `concerns`, `data_room`, and `upload_for_cpa` unless the only available copy of a real document existed there.
- Excluded obvious process screenshots and UI artifacts from `tmp/` and similar staging areas.

Output folder:
- `/Users/lichenyu/Desktop/accounting-not-in-important-docs-20260329`

Artifacts created there:
- `files/` with copied accounting-only documents, preserving relative paths from `/Users/lichenyu/accounting`
- `manifest.csv`
- `selection_summary.json`
- `batch_plan.json`
- `batch_plan.md`

Selection summary:
- Selected files copied: `77`
- By top-level area:
  - `bank_statements`: `16`
  - `legal`: `18`
  - `outgoing`: `18`
  - `tax`: `7`
  - `tmp`: `16`
  - top-level standalone forms: `2`

Derived-only exceptions kept:
- `outgoing/kaufman_rossin/data_room/03_2024_yearend_summary_schwab.pdf`
- `outgoing/kaufman_rossin/data_room/03_2025_w2_claudius.pdf`

Derived items intentionally not copied:
- `output/playwright/*`
- `reports/Master_Transaction_Ledger.csv`
- parsed summaries and generated data-room bundles that already had a raw or better source copy

## Proposed Batches

### Batch 56
Title: `Bank Statements And Transfer Evidence`

File count: `16`

Scope:
- BOA, Citi, Schwab, and Wells Fargo account exports
- Schwab brokerage statements
- 2026 wire transfer image evidence

### Batch 57
Title: `Entity And Corporate Legal Packets`

File count: `15`

Scope:
- Yangtze / BSGC corporate legal letters
- H-1B G-28 packets
- registration drafts
- withholding notices
- counsel agreements and retainers

### Batch 58
Title: `CIAM, School, And Immigration Support`

File count: `14`

Scope:
- CIAM CPT forms and course packets
- I-20 affidavit and recent I-94
- 2025 CIAM `1098-T`
- Waseda transcript
- China driver license image

### Batch 59
Title: `H-1B Intake Worksheets And Counsel Forms`

File count: `15`

Scope:
- Arora H-1B worksheets
- employer data sheets
- Murthy and Wolf Group counsel forms
- staging copies of BSGC/Yangtze H-1B intake packets
- invoice copies

### Batch 60
Title: `Payroll, Tax Support, And Standalone Forms`

File count: `17`

Scope:
- Claudius termination letter
- 2023 `1042-S`
- 2024 Schwab `1099-B` parts
- Claudius `W-2`
- Gusto `941` and payroll summaries
- `1098-T` and eMinutes filled forms
- retained derived-only year-end and Claudius tax copies

## Notes

- This is only a planning boundary. `config/data_room_batches.yaml` was not extended yet.
- If we process these next, `56-60` is the clean continuation after the prior `01-55` Important Docs program.
