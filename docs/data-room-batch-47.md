# Data Room Batch 47

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 47 manifest

This batch closes the remaining section assets in the second numbered Bitsync chat-export archive copy.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_2_section_other` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_other.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_other_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_other@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_photos` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_photos.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_photos_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_photos@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_sessions` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_sessions.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_sessions_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_sessions@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_stories` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_stories.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_stories_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_stories@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_web` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_web.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_web_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_web@2x.png` | chat-export section icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The current `chat_export_asset` contract already covers these archive assets.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required for this batch slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 47`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 47 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-46-50`
- Passing session:
  - `logs/data-room-batch-loop-round-46-50/20260328T230349Z-03`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_codex_loop_scripts.py -q`
  - Result: `67 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue into the final mixed archive slices and keep the asset contract stable.
