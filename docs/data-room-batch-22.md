# Data Room Batch 22

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 22 manifest

This batch continues the resume archive with later role-targeted and date-stamped variants so the remaining career-material history is explicitly typed as resume evidence.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `resume_cv230217_cn_0522` | `CV & Cover Letters/CV230217/李宸宇中文简历_0522.pdf` | Chinese resume variant | `resume` |
| `resume_cv230217_cn_0718` | `CV & Cover Letters/CV230217/李宸宇中文简历_0718.pdf` | later Chinese resume | `resume` |
| `resume_cv230217_bilingual` | `CV & Cover Letters/CV230217/李宸宇中英文简历_0522.pdf` | bilingual resume | `resume` |
| `resume_cv240403_ra` | `CV & Cover Letters/CV240403/Chenyu Li Resume_RA.pdf` | research-assistant targeted resume | `resume` |
| `resume_cv240712_0712` | `CV & Cover Letters/CV240712/Chenyu Li Resume_0712.pdf` | July 2024 resume | `resume` |
| `resume_cv240712_0721` | `CV & Cover Letters/CV240712/Chenyu Li Resume_0721.pdf` | July 2024 resume refresh | `resume` |
| `resume_cv240712_0827` | `CV & Cover Letters/CV240712/Chenyu Li Resume_0827.pdf` | August 2024 resume | `resume` |
| `resume_cv240712_tech` | `CV & Cover Letters/CV240712/Chenyu Li Resume_1028_Tech.pdf` | tech-targeted resume | `resume` |
| `resume_cv240830_0712` | `CV & Cover Letters/CV240830/Chenyu Li Resume_0712.pdf` | archived July 2024 resume copy | `resume` |
| `resume_cv241028_tech` | `CV & Cover Letters/CV241028/Chenyu Li Resume_1028_Tech.pdf` | later tech-targeted resume | `resume` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. Later role-targeted and dated resume variants already classify cleanly as `resume`.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized and validated as the later resume-history continuation.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 22`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 22 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-21-25`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-21-25/20260328T213608Z-01`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether to collapse obviously duplicated resume variants into stronger document-series heuristics or keep them as filename-distinct history.
