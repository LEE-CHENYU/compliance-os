# Data Room Batch 23

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 23 manifest

This batch captures the first half of the uncovered VCV payroll stream so the paystub continuity record is no longer split between an early resolved sample and an unbatched archive.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `vcv_paystub_20231130` | `employment/VCV/paystubs_2023/Paystub20231130.pdf` | November 2023 VCV paystub | `paystub` |
| `vcv_paystub_20231215` | `employment/VCV/paystubs_2023/Paystub20231215.pdf` | December 2023 VCV paystub | `paystub` |
| `vcv_paystub_20240131` | `employment/VCV/paystubs_2024/Paystub20240131.pdf` | January 2024 VCV paystub | `paystub` |
| `vcv_paystub_20240215` | `employment/VCV/paystubs_2024/Paystub20240215.pdf` | February 2024 VCV paystub | `paystub` |
| `vcv_paystub_20240229` | `employment/VCV/paystubs_2024/Paystub20240229.pdf` | February 2024 month-end VCV paystub | `paystub` |
| `vcv_paystub_20240315` | `employment/VCV/paystubs_2024/Paystub20240315.pdf` | March 2024 VCV paystub | `paystub` |
| `vcv_paystub_20240329` | `employment/VCV/paystubs_2024/Paystub20240329.pdf` | March 2024 month-end VCV paystub | `paystub` |
| `vcv_paystub_20240415` | `employment/VCV/paystubs_2024/Paystub20240415.pdf` | April 2024 VCV paystub | `paystub` |
| `vcv_paystub_20240430` | `employment/VCV/paystubs_2024/Paystub20240430.pdf` | April 2024 month-end VCV paystub | `paystub` |
| `vcv_paystub_20240515` | `employment/VCV/paystubs_2024/Paystub20240515.pdf` | May 2024 VCV paystub | `paystub` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The existing `paystub` family already covered the early VCV payroll stream cleanly.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized and validated as the first half of the uncovered VCV payroll continuity record.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 23`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 23 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-21-25`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-21-25/20260328T213608Z`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Pull these paystubs into deeper cross-document payroll review only when a concrete compensation or employment-period check needs the full series.
