# Data Room Batch 52

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 52 manifest

This batch extends the Word resume archive into the 2024 role-variant set so later DOCX resume versions are covered alongside the already-resolved PDF archive.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `resume_230217_chinese_2022` | `CV & Cover Letters/CV230217/李宸宇简历2022.docx` | Chinese resume archive carry-forward | `resume` |
| `resume_240403_cbs_ra` | `CV & Cover Letters/CV240403/Chenyu Li Resume_CBS_Econ_RA.docx` | targeted research-assistant resume | `resume` |
| `resume_240712_finance` | `CV & Cover Letters/CV240712/Chenyu Li Resume_0712_Finance.docx` | finance-focused resume variant | `resume` |
| `resume_240712_tech` | `CV & Cover Letters/CV240712/Chenyu Li Resume_0712_Tech.docx` | tech-focused resume variant | `resume` |
| `resume_240712_tech_0721` | `CV & Cover Letters/CV240712/Chenyu Li Resume_0721_Tech.docx` | updated tech resume variant | `resume` |
| `resume_240712_tech_1028` | `CV & Cover Letters/CV240712/Chenyu Li Resume_1028_Tech.docx` | later tech resume variant | `resume` |
| `resume_240830_0712` | `CV & Cover Letters/CV240830/Chenyu Li Resume_0712.docx` | archived general resume export | `resume` |
| `resume_241028_tech_copy` | `CV & Cover Letters/CV241028/Chenyu Li Resume_1028_Tech copy.docx` | copied tech resume variant | `resume` |
| `resume_241028_tech` | `CV & Cover Letters/CV241028/Chenyu Li Resume_1028_Tech.docx` | canonical tech resume variant | `resume` |
| `resume_241028_analyst` | `CV & Cover Letters/CV241028/Chenyu Li Resume_Analyst.docx` | analyst-targeted resume variant | `resume` |
| `resume_241028_mba` | `CV & Cover Letters/CV241028/Chenyu Li Resume_MBA.docx` | MBA-targeted resume variant | `resume` |

## Baseline current-state result

- Before this pass, these files were covered by the expanded DOCX intake logic but not yet locked into the batch ledger or real-source validator flow.

## Post-fix result

- Current fast-path match rate against intended doc types: `11/11`
- Mid-cycle Word resume variants now validate cleanly under the same `resume` family contract.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 52`
  - Result: `11/11`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 52 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-51-55`
  - Passing session:
    - `logs/data-room-batch-loop-round-51-55/20260328T235244Z-03`
- Focused regression suite:
  - `conda run -n compliance-os pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_checks_router_v2.py -q`
  - Result: `106 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue the late resume and H-1B resume overflow in Batch `53`.
