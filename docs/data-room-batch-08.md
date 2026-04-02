# Data Room Batch 08

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 08 manifest

This batch stresses STEM OPT history with additional I-983 versions and a small set of support artifacts that should not disappear into the generic bucket.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `claudius_i983_v1` | `stem opt/i983/claudius/i983-241001-1.pdf` | Claudius training plan version | `i983` |
| `claudius_i983_v2` | `stem opt/i983/claudius/i983_claudius_121624_revised_v2.pdf` | revised Claudius training plan | `i983` |
| `clinipulse_i983_signed` | `stem opt/i983/clinipulse/i983-signed_02:23:25.pdf` | signed CliniPulse training plan | `i983` |
| `vcv_i983_signed` | `stem opt/i983/vcv/Cheney i983 Form_signed_120924.pdf` | signed VCV training plan | `i983` |
| `vcv_i983_full` | `stem opt/i983/vcv/i983-241001.pdf` | VCV training plan full copy | `i983` |
| `vcv_i983_outdated` | `stem opt/i983/vcv_outdated_versions/i983_edited_1026 v3.pdf` | prior VCV training plan version | `i983` |
| `wolff_i983_signed` | `stem opt/i983/wolff-and-li/i983-wolff-and-li-signed.pdf` | signed Wolff & Li training plan | `i983` |
| `stem_i94_2023` | `stem opt/I94 - Official Website - 20230919.pdf` | earlier status-entry control | `i94` |
| `stem_employer_letter` | `stem opt/letter/stemoptemployerletter.pdf` | STEM employer letter | `employment_letter` |
| `stem_support_request` | `stem opt/request/Requests for Employment and Immigration Support& Support.pdf` | STEM support-request artifact | `support_request` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `8/10`
- Strong today:
  - all seven selected `i983` files classify correctly
  - the earlier `I-94` classifies correctly
- Remaining misses:
  - `stem opt/letter/stemoptemployerletter.pdf` currently misclassifies as `i983`
  - `stem opt/request/Requests for Employment and Immigration Support& Support.pdf`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- The STEM employer-letter filename no longer misclassifies as `i983`.
- A dedicated `support_request` family now exists for the support-correspondence artifact.

## Validation

- Real-source validator:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 08`
- Loop-compatible logging command:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 08 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
- Current recorded run:
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T083149Z-01`
  - superseded baseline run only
- Current passing validator run:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 08`
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 08 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T155831Z`
  - focused tests: `45 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Add deeper retrieval or review logic for `support_request` only if a concrete workflow needs it.
