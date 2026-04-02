# Data Room Batch 56

Source folder: `/Users/lichenyu/Desktop/accounting-not-in-important-docs-20260329/files`

## Batch 56 manifest

This batch opens the accounting-derived follow-on queue with bank exports, brokerage statements, and wire-transfer evidence that were not present in the original `Important Docs` corpus.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `boa_personal_export` | `bank_statements/boa/boa_personal_20240408_20251007.csv` | BOA personal account export | `bank_statement` |
| `citi_llc_export` | `bank_statements/citibank/citibank_llc_chk5039_20240409_20250929.csv` | Citi LLC account export | `bank_statement` |
| `citi_personal_export_aug` | `bank_statements/citibank/citibank_personal_chk6544_20240819_20260209.csv` | Citi personal account export | `bank_statement` |
| `citi_personal_export_oct` | `bank_statements/citibank/citibank_personal_chk6544_20241021_20251006.csv` | Citi personal account export | `bank_statement` |
| `citizens_payment_options` | `bank_statements/citizens_payment_options_2958.pdf` | Citizens payment-options notice | `payment_options_notice` |
| `schwab_llc_export_oct` | `bank_statements/schwab/schwab_llc_xxx239_20250225_20251006.csv` | Schwab LLC transaction export | `bank_statement` |
| `schwab_llc_export_feb` | `bank_statements/schwab/schwab_llc_xxx239_20250225_20260212.csv` | Schwab LLC transaction export | `bank_statement` |
| `schwab_personal_export_jan` | `bank_statements/schwab/schwab_personal_xxx619_20230120_20260107.csv` | Schwab personal transaction export | `bank_statement` |
| `schwab_personal_export_oct` | `bank_statements/schwab/schwab_personal_xxx619_20241030_20251006.csv` | Schwab personal transaction export | `bank_statement` |
| `schwab_llc_stmt_jul` | `bank_statements/schwab/statements/schwab_brokerage_stmt_xxx239_2025-07.pdf` | Schwab LLC July brokerage statement | `bank_statement` |
| `schwab_llc_stmt_sep` | `bank_statements/schwab/statements/schwab_brokerage_stmt_xxx239_2025-09.pdf` | Schwab LLC September brokerage statement | `bank_statement` |
| `schwab_personal_stmt_jul` | `bank_statements/schwab/statements/schwab_brokerage_stmt_xxx619_2025-07.pdf` | Schwab personal July brokerage statement | `bank_statement` |
| `wells_fargo_export` | `bank_statements/wells_fargo/wf_personal_20251023_20260209.csv` | Wells Fargo personal account export | `bank_statement` |
| `wire_ewb_eastwest` | `bank_statements/wire_transfers_2026/EWB_ChenChunjiang_to_EastWestBank_030226.JPG` | East West wire-transfer image evidence | `wire_transfer_record` |
| `wire_icbc_hsbc` | `bank_statements/wire_transfers_2026/ICBC_28000_ChenYunhong_to_HSBC_HK_030626.JPG` | ICBC to HSBC HK wire image evidence | `wire_transfer_record` |
| `wire_minsheng_citi` | `bank_statements/wire_transfers_2026/Minsheng_50000_ChenChunlei_to_Citibank_ChenyuLi.JPG` | Minsheng to Citibank wire image evidence | `wire_transfer_record` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `1/16`
- Only matched on the first validator pass:
  - `boa_personal_export` -> `bank_statement`
- Missed or misrouted families on the first pass:
  - Citi, Wells Fargo, and Schwab exports were unresolved or lacked bank-statement path coverage
  - Schwab brokerage CSVs were false-positive routed as `drivers_license` because `CLASS` and `EXP` text anchors were too permissive
  - Schwab brokerage statement PDFs were unresolved on the non-OCR path
  - wire-transfer images had no dedicated family
  - the Citizens notice needed a dedicated `payment_options_notice` family instead of collapsing into generic bank-account evidence

## Post-fix result

- Current fast-path match rate against intended doc types: `16/16`
- Shared bank-export coverage now handles:
  - Citi CSV exports
  - Wells Fargo CSV exports
  - Schwab brokerage CSV exports
  - Schwab statement PDFs
- `drivers_license` text classification is tightened so brokerage exports no longer false-positive on `CLASS` + `EXP` alone.
- Two new accounting families now exist as first-class types:
  - `payment_options_notice`
  - `wire_transfer_record`
- Minimal structured extraction schemas and lineage support now exist for the new families.
- `bank_statement` series keys now preserve institution/account/date granularity instead of collapsing the whole family.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 56`
  - Result: `16/16`
- Focused regression suite:
  - `conda run -n compliance-os pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_data_room_batch_loop.py tests/test_checks_router_v2.py -q`
  - Result: `129 passed`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 56 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-56-60`
  - Passing session:
    - `logs/data-room-batch-loop-round-56-60/20260329T175140Z`

## Current batch blockers

None.

## Next queue

1. Batch 57: entity and corporate legal packets
2. Batch 58: CIAM, school, and immigration support
3. Batch 59: H-1B intake worksheets and counsel forms
4. Batch 60: payroll, tax-support, and standalone forms
