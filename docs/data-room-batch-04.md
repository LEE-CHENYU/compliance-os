# Data Room Batch 04

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 04 manifest

This batch covers H-1B petition lifecycle evidence beyond the raw registration artifact, including status summaries, attorney filings, and filing/payment proof.

| Label | File | Intended use | Current classification result |
| --- | --- | --- | --- |
| `h1b_status_overview_en` | `H1b Petition/FY 2026 H-1B Status Overview_for employee_Cindy-1.pdf` | H-1B status and filing timeline summary | `h1b_status_summary` |
| `h1b_status_handbook_zh` | `H1b Petition/2025 H-1B????_f or employee-1.pdf` | bilingual H-1B filing handbook and timeline summary | `h1b_status_summary` |
| `h1b_registration_bsgc` | `H1b Petition/Employer/H-1BR (1).pdf` | USCIS H-1B registration record | `h1b_registration` |
| `h1b_g28_entry` | `H1b Petition/Employer/G-28 (1).pdf` | attorney appearance and representation notice | `h1b_g28` |
| `h1b_invoice_part_i` | `H1b Petition/Employer/Invoice_Part I_LI, Chenyu_paid.pdf` | filing support invoice (legal + USCIS registration fee components) | `h1b_filing_invoice` |
| `h1b_transaction_receipt` | `H1b Petition/Transaction #45217993.pdf` | payment receipt with approval evidence | `h1b_filing_fee_receipt` |
| `h1b_employer_ein_notice` | `H1b Petition/Employer/CP575Notice_1686945041312.pdf` | employer EIN support filing | `ein_letter` |
| `h1b_employee_i94` | `H1b Petition/Employee/I-94/I-94 Official Website - Get Most Recent I-94 Response.pdf` | beneficiary immigration status evidence | `i94` |
| `h1b_employee_ead` | `H1b Petition/Employee/EAD/STEM OPT EAD.jpeg` | beneficiary work-authorization support record | `ead` |
| `h1b_employee_i20` | `H1b Petition/Employee/i20/i20_stemopt_23_signed.pdf` | beneficiary F-1/I-20 support record | `i20` |

## Baseline before support

Before this iteration, Batch 04 was still a proposal and this concrete 10-file set was not materialized in the record. On the existing intake path, Batch 04-specific petition support files were also partially unsupported:

- unclassified or partially modeled: bilingual H-1B status handbook, `G-28`, filing invoice, and transaction approval receipt
- already modeled controls: `h1b_registration`, `i94`, `ead`, and `i20`

## Post-fix intake and modeling result

After materializing the batch and extending Batch 04 family support:

- `10/10` manifest files classify on the current intake path (`allow_ocr=False`)
- all Batch 04 target families now have extraction schema coverage:
  - `h1b_status_summary`
  - `h1b_registration`
  - `h1b_g28`
  - `h1b_filing_invoice`
  - `h1b_filing_fee_receipt`

Normalization coverage added for Batch 04 financial/timeline artifacts:

- invoice and receipt amount fields now normalize to canonical currency strings (`NNN.NN`)
- invoice and receipt date fields now normalize to `YYYY-MM-DD`, including month-name formats such as `Mar 3, 2026`

## H-1B lifecycle review rules

`/api/checks/{check_id}/compare` for `data_room` now consumes Batch 04 extraction fields and emits cross-document consistency checks for H-1B petition lifecycle evidence:

- registration employer name ↔ `G-28` client entity name
- registration employer name ↔ filing invoice petitioner name
- registration authorized individual name ↔ payment receipt cardholder name
- filing invoice beneficiary name ↔ payment receipt cardholder name

## Validation

Focused Batch 04 regression suite:

- `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_checks_router_v2.py -q`
- result: `61 passed`
- `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 04`
- result: real-source checks passed for `10/10` manifest files against `/Users/lichenyu/Desktop/Important Docs `

Required loop validation command:

- `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 04 --run-validation-hooks --json --log-root logs/data-room-batch-loop-agent-validate`
- session log: `logs/data-room-batch-loop-agent-validate/20260328T074000Z`
- hook result: `batch_04_focused_tests` passed (`61 passed`)
- hook result: `batch_04_real_source_validation` passed
- batch state: `resolved: true` (remaining unresolved issues: `0`)
- residual-fix confirmation log: `logs/data-room-batch-loop-residual-fix/20260328T082648Z-01`

Post-update assessment confirmation:

- `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 04 --run-validation-hooks --json --log-root logs/data-room-batch-loop-agent-assess`
- session log: `logs/data-room-batch-loop-agent-assess/20260328T074012Z`
- hook result: `batch_04_focused_tests` passed (`61 passed`)
- hook result: `batch_04_real_source_validation` passed
- batch state: `resolved: true` (remaining unresolved issues: `0`)

## Current batch blockers

None.

## Deferred backlog

1. Standalone LCA filings (`ETA-9035`) and official USCIS `I-797` receipt/approval notices are not present in the current Batch 04 source slice and remain future-family expansion work.
2. Additional H-1B petition support artifact types can be added as new source evidence appears in later data-room batches.

## Next queue

1. Keep Batch 04 stable and proceed to Batch 05 on identity, travel, I-20 history, and overflow personal/tax records.
