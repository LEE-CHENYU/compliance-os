# Data Room Batch 51

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 51 manifest

This batch captures the earliest Word resume archive so the DOCX intake contract covers the pre-2024 resume history instead of stopping at the PDF archive.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `resume_220428_english` | `CV & Cover Letters/CV220428/Chenyu Li Resume - English version.docx` | early English resume variant | `resume` |
| `resume_220428_professional` | `CV & Cover Letters/CV220428/Chenyu Li Resume - Professional v1.1.docx` | early professional resume variant | `resume` |
| `resume_220428_chinese` | `CV & Cover Letters/CV220428/李宸宇简历2022.docx` | early Chinese resume variant | `resume` |
| `resume_220913_english` | `CV & Cover Letters/CV220913/Chenyu Li Resume - English version.docx` | updated English resume variant | `resume` |
| `resume_220913_chinese` | `CV & Cover Letters/CV220913/李宸宇简历2023.docx` | updated Chinese resume variant | `resume` |
| `resume_230217_0214` | `CV & Cover Letters/CV230217/Chenyu Li Resume_0214.docx` | dated English resume variant | `resume` |
| `resume_230217_0521` | `CV & Cover Letters/CV230217/Chenyu Li Resume_0521.docx` | dated English resume variant | `resume` |
| `resume_230217_0705` | `CV & Cover Letters/CV230217/Chenyu Li Resume_0705.docx` | dated English resume variant | `resume` |
| `resume_230217_chinese_base` | `CV & Cover Letters/CV230217/李宸宇中文简历.docx` | Chinese resume base version | `resume` |
| `resume_230217_chinese_0522` | `CV & Cover Letters/CV230217/李宸宇中文简历_0522.docx` | Chinese resume dated variant | `resume` |
| `resume_230217_chinese_0718` | `CV & Cover Letters/CV230217/李宸宇中文简历_0718.docx` | Chinese resume dated variant | `resume` |

## Baseline current-state result

- Before this pass, these files were newly ingestible because DOCX support had just been added, but they had not yet been materialized into the numbered batch program.

## Post-fix result

- Current fast-path match rate against intended doc types: `11/11`
- All early Word resume variants classify cleanly as `resume` on the shared intake path.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 51`
  - Result: `11/11`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 51 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-51-55`
  - Passing session:
    - `logs/data-room-batch-loop-round-51-55/20260328T235244Z-04`
- Focused regression suite:
  - `conda run -n compliance-os pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_checks_router_v2.py -q`
  - Result: `106 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue the DOCX resume archive into Batch `52`.
