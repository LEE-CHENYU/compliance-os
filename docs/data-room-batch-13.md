# Data Room Batch 13

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 13 manifest

This batch consolidates the remaining I-20 timeline plus school admission and continued-attendance records that should sit together in retrieval and review.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `h1b_i20_original` | `H1b Petition/Employee/i20/i20_original.pdf` | original I-20 support file | `i20` |
| `h1b_i20_opt` | `H1b Petition/Employee/i20/i20_opt.pdf` | OPT I-20 support file | `i20` |
| `h1b_i20_stemopt_23` | `H1b Petition/Employee/i20/i20_stemopt_23.pdf` | STEM OPT I-20 support file | `i20` |
| `h1b_i20_travel_22` | `H1b Petition/Employee/i20/i20_travel_22.pdf` | travel-signed 2022 I-20 | `i20` |
| `h1b_i20_travel_23` | `H1b Petition/Employee/i20/i20_travel_23.pdf` | travel-signed 2023 I-20 | `i20` |
| `cu_i20_original` | `i20/cu_original.pdf` | university I-20 original | `i20` |
| `cu_i20_stemopt_23` | `i20/cu_stemopt_23.pdf` | university STEM OPT I-20 | `i20` |
| `admission_letter` | `i20/I20/Admission Letter.pdf` | school admission letter | `admission_letter` |
| `ciam_continued_attendance` | `i20/ciam_continued_attendence.pdf` | continued-attendance verification | `enrollment_verification` |
| `westcliff_continued_attendance` | `i20/westcliff_continued_attendence.pdf` | continued-attendance verification | `enrollment_verification` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `6/10`
- Strong today:
  - H-1B employee `I-20` records with explicit `i20` filenames already classified correctly
- Remaining misses:
  - `cu_original.pdf` did not inherit the `i20` family from path context
  - `Admission Letter.pdf` required the correct nested path plus an explicit admission-letter family
  - continued-attendance files were being absorbed into `i20` instead of their own verification family

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- The batch now separates:
  - core `i20` history
  - school admission evidence
  - continued-attendance or enrollment verification letters

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 13`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 13 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-11-15`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-11-15/20260328T161804Z-04`
  - focused tests: `48 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Keep transfer-pending and USCIS account-artifact files for a later student-admin or account-access batch instead of widening this slice.
