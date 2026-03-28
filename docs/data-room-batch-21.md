# Data Room Batch 21

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 21 manifest

This batch materializes the early multilingual resume archive so historical career materials remain versioned and searchable instead of sitting outside the typed data-room path.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `resume_cv220428_en` | `CV & Cover Letters/CV220428/Chenyu Li Resume - English version.pdf` | early English resume | `resume` |
| `resume_cv220428_cn` | `CV & Cover Letters/CV220428/李宸宇简历2022.pdf` | early Chinese resume | `resume` |
| `resume_cv220913_en` | `CV & Cover Letters/CV220913/Chenyu Li Resume - English version.pdf` | September 2022 English resume | `resume` |
| `resume_cv220913_cn_2022` | `CV & Cover Letters/CV220913/李宸宇简历2022.pdf` | September 2022 Chinese resume | `resume` |
| `resume_cv220913_cn_2023` | `CV & Cover Letters/CV220913/李宸宇简历2023.pdf` | updated Chinese resume | `resume` |
| `resume_cv230217_en` | `CV & Cover Letters/CV230217/Chenyu Li Resume.pdf` | February 2023 English resume | `resume` |
| `resume_cv230217_en_0521` | `CV & Cover Letters/CV230217/Chenyu Li Resume_0521.pdf` | May 2023 English resume | `resume` |
| `resume_cv230217_en_0522` | `CV & Cover Letters/CV230217/Chenyu Li Resume_0522.pdf` | May 2023 English resume variant | `resume` |
| `resume_cv230217_jp` | `CV & Cover Letters/CV230217/リシンウ履歴書.pdf` | Japanese resume | `resume` |
| `resume_cv230217_cn` | `CV & Cover Letters/CV230217/李宸宇中文简历.pdf` | February 2023 Chinese resume | `resume` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The resume family already covered these multilingual and date-stamped archive variants cleanly.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized, validated, and recorded as an explicit resume-history slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 21`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 21 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-21-25`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-21-25/20260328T213608Z-03`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Keep these early resume variants in the versioned archive path unless a concrete retrieval or ranking issue appears.
