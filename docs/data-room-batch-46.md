# Data Room Batch 46

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 46 manifest

This batch continues the second numbered Bitsync chat-export archive copy with voice and first section-navigation assets.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_2_media_voice` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_voice.png` | chat-export voice icon asset | `chat_export_asset` |
| `chat_export_2_media_voice_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_voice@2x.png` | chat-export voice icon asset | `chat_export_asset` |
| `chat_export_2_section_calls` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_calls.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_calls_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_calls@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_chats` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_chats.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_chats_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_chats@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_contacts` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_contacts.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_contacts_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_contacts@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_frequent` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_frequent.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_2_section_frequent_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/section_frequent@2x.png` | chat-export section icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The current `chat_export_asset` contract already covers these archive assets.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required for this batch slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 46`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 46 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-46-50`
- Passing session:
  - `logs/data-room-batch-loop-round-46-50/20260328T230349Z-01`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_codex_loop_scripts.py -q`
  - Result: `67 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue through the second numbered archive copy unless a true path-collision issue appears.
