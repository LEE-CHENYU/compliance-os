# Data Room Batch 50

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 50 manifest

This batch closes the remaining primary Bitsync chat-export archive assets and the last uncovered opaque identifier text artifact from the company-info slice.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_primary_section_photos` | `employment/Bitsync/ChatExport_2024-12-14/images/section_photos.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_photos_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_photos@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_sessions` | `employment/Bitsync/ChatExport_2024-12-14/images/section_sessions.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_sessions_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_sessions@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_stories` | `employment/Bitsync/ChatExport_2024-12-14/images/section_stories.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_stories_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_stories@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_web` | `employment/Bitsync/ChatExport_2024-12-14/images/section_web.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_web_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_web@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `company_identifier_txt` | `公司信息/Ns7NbZgE9k.txt` | low-signal opaque identifier or token record | `identifier_record` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `8/9`
- Surfaced gap:
  - plain-text uploads were not content-classified, so the opaque identifier file remained unsupported even though the remaining chat-export assets already fit the current contract

## Post-fix result

- Current fast-path match rate against intended doc types: `9/9`
- Plain-text uploads now participate in text classification, and low-signal one-line identifier records can land in a stable `identifier_record` family.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 50`
  - Result: `9/9`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 50 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-46-50`
- Passing session:
  - `logs/data-room-batch-loop-round-46-50/20260328T230349Z-04`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_codex_loop_scripts.py -q`
  - Result: `67 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. The ingestible pool is now exhausted through Batch `50`; the next step is contract hardening or non-ingestible format support rather than more backlog slicing.
