# Data Room Inventory

Source folder: `/Users/lichenyu/Desktop/Important Docs `

Snapshot date: `2026-03-27`

## Current inventory

- total files excluding `.DS_Store` and `Thumbs.db`: `585`
- directly ingestible by the current v1 data-room path (`pdf/png/jpg/jpeg/csv/txt`): `483`

Top-level file counts:
- `employment`: `240`
- `CV & Cover Letters`: `107`
- `stem opt`: `54`
- `[root]`: `34`
- `H1b Petition`: `25`
- `BSGC`: `23`
- `i20`: `20`
- `Tax`: `16`
- `公司信息`: `11`
- `Personal Info Archive`: `10`

Extension counts:
- `.pdf`: `265`
- `.png`: `151`
- `.docx`: `57`
- `.jpg`: `35`
- `.jpeg`: `25`
- `.odg`: `10`
- `.txt`: `6`
- `.heic`: `3`
- `.zip`: `3`
- `.rtf`: `3`

## Batch ledger

- Batch 01:
  - focus: STEM OPT and entity core records
  - status: completed
  - record: `docs/data-room-batch-01.md`
- Batch 02:
  - focus: company formation, leases, insurance/medical, `1042-S`, passport control
  - status: completed
  - record: `docs/data-room-batch-02.md`
- Batch 03:
  - focus: payroll, `I-9`, E-Verify, `I-765`, H-1B registration support
  - status: completed
  - record: `docs/data-room-batch-03.md`
- Batch 04:
  - focus: H-1B petition notices, status summaries, receipt/approval evidence, and supporting filings
  - status: planned
  - record: `docs/data-room-batch-04.md`
- Batch 05:
  - focus: identity, travel, `I-20` history, and overflow tax/personal archive records
  - status: planned
  - record: `docs/data-room-batch-05.md`

## Current priorities

1. Run the first-round batch loop across Batches `01` through `05` and keep unresolved batches in queue until their recorded gaps are cleared.
2. Add support for the H-1B status-summary / notice family if it proves operationally useful.
3. Extend rule-based review and retrieval prompts to use the new payroll, `I-9`, E-Verify, `I-765`, and H-1B registration fields.
