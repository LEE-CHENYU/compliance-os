# Data Room Batch 20

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 20 manifest

This batch consolidates the remaining I-20 overflow and student-admin continuity records: additional I-20 variants, transfer-pending letters, USCIS account backup codes, and identification-page support.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `i20_fa_2025` | `i20/I-20_Li_Chenyu_ FA 2025.pdf` | later I-20 record | `i20` |
| `cu_opt_i20` | `i20/cu_opt.pdf` | OPT I-20 archive | `i20` |
| `cu_stemopt_signed_i20` | `i20/cu_stemopt_23_signed.pdf` | signed STEM OPT I-20 archive | `i20` |
| `cu_travel_22_i20` | `i20/cu_travel_22.pdf` | 2022 travel-signed I-20 | `i20` |
| `cu_travel_23_i20` | `i20/cu_travel_23.pdf` | 2023 travel-signed I-20 | `i20` |
| `ciam_transfer_pending` | `i20/ciam_transfer_pending.pdf` | transfer-pending school letter | `transfer_pending_letter` |
| `westcliff_transfer_pending` | `i20/westcliff_transfer_pending.pdf` | transfer-pending school letter | `transfer_pending_letter` |
| `uscis_backup_codes_primary` | `i20/I20/2fa_backup_code_USCIS_myAccount.pdf` | USCIS account backup codes | `recovery_codes` |
| `uscis_backup_codes_secondary` | `i20/I20/2fa_backup_code_USCIS_myAccount_1105.pdf` | USCIS account backup codes | `recovery_codes` |
| `i20_identification_page` | `i20/I20/Identification Page.png` | identification-page support file | `identity_document` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `4/10`
- Already strong:
  - later `I-20` anchor
  - USCIS recovery-code PDFs
  - identification-page support image
- Surfaced gaps:
  - the additional `cu_*` I-20 variants were not being recognized as `i20`
  - transfer-pending school letters were unsupported

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- This batch now classifies cleanly across:
  - Columbia OPT / STEM OPT / travel-signed `I-20` variants
  - transfer-pending school letters
  - USCIS recovery-code continuity records

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 20`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 20 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-16-20`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-16-20/20260328T183154Z-01`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Keep these overflow `I-20` and transfer-pending families in the history path unless a review rule needs to compare them against later travel or enrollment evidence.
