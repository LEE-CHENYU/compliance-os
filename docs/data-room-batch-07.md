# Data Room Batch 07

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 07 manifest

This batch expands employment continuity beyond the original sample with more pay periods, additional I-9 records, and generic offer-letter filenames that should still resolve correctly.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `bitsync_i9` | `employment/Bitsync/BitSync Mail - Form I-9.pdf` | employer onboarding record | `i9` |
| `claudius_offer` | `employment/Claudius/Employment Letter, Chenyu_signed.pdf` | employment letter | `employment_letter` |
| `claudius_paystub_0109` | `employment/Claudius/claudius paytubs/chenyu-li-paystub-2025-01-09.pdf` | payroll continuity | `paystub` |
| `claudius_paystub_0211` | `employment/Claudius/claudius paytubs/chenyu-li-paystub-2025-02-11.pdf` | payroll continuity | `paystub` |
| `claudius_paystub_0225` | `employment/Claudius/claudius paytubs/chenyu-li-paystub-2025-02-25.pdf` | payroll continuity | `paystub` |
| `vcv_full_time_letter` | `employment/VCV/vcv_full_time.pdf` | VCV full-time letter | `employment_letter` |
| `vcv_internship_letter` | `employment/VCV/vcv_internship.pdf` | VCV internship letter | `employment_letter` |
| `vcv_paystub_1115` | `employment/VCV/paystubs_2023/Paystub20231115.pdf` | payroll continuity | `paystub` |
| `vcv_paystub_1229` | `employment/VCV/paystubs_2023/Paystub20231229.pdf` | payroll continuity | `paystub` |
| `clinipulse_i9` | `employment/CliniPulse/i-9.pdf` | employer onboarding record | `i9` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `8/10`
- Strong today:
  - both `i9` files classify correctly
  - five paystubs classify correctly
  - one signed employment letter classifies correctly
- Remaining misses:
  - `employment/VCV/vcv_full_time.pdf`
  - `employment/VCV/vcv_internship.pdf`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Generic employment-letter filenames for the VCV records now resolve correctly on the intake path.

## Validation

- Real-source validator:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 07`
- Loop-compatible logging command:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 07 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
- Current recorded run:
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T083149Z-03`
  - superseded baseline run only
- Current passing validator run:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 07`
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 07 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T155831Z-04`
  - focused tests: `45 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Expand only when contract or wage-notice artifacts become concrete blockers in a later batch.
