# Data Room Batch 42

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 42 manifest

This batch continues the numbered Bitsync chat-export asset archive with voice and section-navigation assets from `ChatExport_2024-12-14 (1)`.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_1_media_voice` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_voice.png` | chat-export voice icon asset | `chat_export_asset` |
| `chat_export_1_media_voice_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_voice@2x.png` | chat-export voice icon asset | `chat_export_asset` |
| `chat_export_1_section_calls` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/section_calls.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_1_section_calls_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/section_calls@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_1_section_chats` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/section_chats.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_1_section_chats_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/section_chats@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_1_section_contacts` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/section_contacts.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_1_section_contacts_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/section_contacts@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_1_section_frequent` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/section_frequent.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_1_section_frequent_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/section_frequent@2x.png` | chat-export section icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. Numbered archive voice and section assets already classify cleanly as `chat_export_asset`.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized and validated as the second chat-export asset slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 42`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 42 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-41-45`
  - Passing session: `logs/data-room-batch-loop-round-41-45/20260328T224622Z`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py -q`
  - Result: `58 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue materializing the numbered chat-export archive unless a concrete path-collision issue appears.
