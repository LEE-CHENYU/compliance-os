# Data Room Batch 15

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 15 manifest

This batch turns the remaining career-material slice into explicit data-room families so resumes and work samples are not left as opaque uploads.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `resume_h1b` | `CV & Cover Letters/CV260306/Chenyu Li Resume_H1b.pdf` | H-1B-tailored resume | `resume` |
| `resume_260325` | `CV & Cover Letters/CV260325/Chenyu Li Resume_260325.pdf` | March 2026 resume version | `resume` |
| `resume_250930` | `CV & Cover Letters/CV250626/Chenyu Li Resume_0930.pdf` | September 2025 resume version | `resume` |
| `resume_analyst` | `CV & Cover Letters/CV241028/Chenyu Li Resume_Analyst.pdf` | analyst-targeted resume | `resume` |
| `resume_mba` | `CV & Cover Letters/CV241028/Chenyu Li Resume_MBA.pdf` | MBA-targeted resume | `resume` |
| `resume_enterprise_strategy` | `CV & Cover Letters/CV240830/Cheney (Chenyu) Li_Enterprise Strategy Full Time Analyst_20240829.pdf` | enterprise strategy application resume | `resume` |
| `resume_healthcare_data` | `CV & Cover Letters/CV240830/Cheney (Chenyu) Li_Healthcare Data Analyst_20240829.pdf` | healthcare data application resume | `resume` |
| `resume_251216` | `CV & Cover Letters/CV251216/Chenyu Li Resume_251216.pdf` | December 2025 resume version | `resume` |
| `technicals_packet` | `CV & Cover Letters/technicals.pdf` | technical work-sample packet | `work_sample` |
| `oxy_stock_pitch` | `CV & Cover Letters/CV241028/OXY Stock Pitch.pdf` | stock-pitch work sample | `work_sample` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Remaining misses:
  - `resume`
  - `work_sample`
- One false positive was also present before the fix:
  - `Chenyu Li Resume_MBA.pdf` was being misclassified as `drivers_license` from first-page text instead of matching a resume family at the filename layer

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Resume and work-sample materials now classify cleanly, and the earlier `drivers_license` false positive is removed because resume filenames now win before incidental text matching

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 15`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 15 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-11-15`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-11-15/20260328T161804Z-01`
  - focused tests: `48 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether resumes and work samples should participate in retrieval only, or whether they need stronger version-series modeling.
