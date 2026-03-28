# Data Room Batch 24

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 24 manifest

This batch captures the second half of the uncovered VCV payroll stream so the later 2024 paystub continuity is fully typed in the data room.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `vcv_paystub_20240531` | `employment/VCV/paystubs_2024/Paystub20240531.pdf` | May 2024 month-end VCV paystub | `paystub` |
| `vcv_paystub_20240614` | `employment/VCV/paystubs_2024/Paystub20240614.pdf` | June 2024 VCV paystub | `paystub` |
| `vcv_paystub_20240628` | `employment/VCV/paystubs_2024/Paystub20240628.pdf` | June 2024 month-end VCV paystub | `paystub` |
| `vcv_paystub_20240715` | `employment/VCV/paystubs_2024/Paystub20240715.pdf` | July 2024 VCV paystub | `paystub` |
| `vcv_paystub_20240731` | `employment/VCV/paystubs_2024/Paystub20240731.pdf` | July 2024 month-end VCV paystub | `paystub` |
| `vcv_paystub_20240815` | `employment/VCV/paystubs_2024/Paystub20240815.pdf` | August 2024 VCV paystub | `paystub` |
| `vcv_paystub_20240830` | `employment/VCV/paystubs_2024/Paystub20240830.pdf` | August 2024 month-end VCV paystub | `paystub` |
| `vcv_paystub_20240913` | `employment/VCV/paystubs_2024/Paystub20240913.pdf` | September 2024 VCV paystub | `paystub` |
| `vcv_paystub_20240930` | `employment/VCV/paystubs_2024/Paystub20240930.pdf` | September 2024 month-end VCV paystub | `paystub` |
| `vcv_paystub_20241106_1` | `employment/VCV/paystubs_2024/Paystub20241106-1.pdf` | November 2024 VCV paystub packet one | `paystub` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The later VCV paystub stream also matches the existing `paystub` family cleanly.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized and validated as the later half of the uncovered VCV payroll continuity record.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 24`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 24 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-21-25`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-21-25/20260328T213608Z-02`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Extend payroll series-key heuristics later if these date-stamped files need stronger clustering than the current paystub-family logic.
