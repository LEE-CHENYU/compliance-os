# Data Room Batch 44

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 44 manifest

This batch starts the second numbered Bitsync chat-export archive copy with back-navigation and media-type icon assets from `ChatExport_2024-12-14 (2)`.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_2_back` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/back.png` | chat-export back-navigation asset | `chat_export_asset` |
| `chat_export_2_back_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/back@2x.png` | chat-export back-navigation asset | `chat_export_asset` |
| `chat_export_2_media_call` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_call.png` | chat-export call icon asset | `chat_export_asset` |
| `chat_export_2_media_call_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_call@2x.png` | chat-export call icon asset | `chat_export_asset` |
| `chat_export_2_media_contact` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_contact.png` | chat-export contact icon asset | `chat_export_asset` |
| `chat_export_2_media_contact_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_contact@2x.png` | chat-export contact icon asset | `chat_export_asset` |
| `chat_export_2_media_file` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_file.png` | chat-export file icon asset | `chat_export_asset` |
| `chat_export_2_media_file_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_file@2x.png` | chat-export file icon asset | `chat_export_asset` |
| `chat_export_2_media_game` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_game.png` | chat-export game icon asset | `chat_export_asset` |
| `chat_export_2_media_game_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_game@2x.png` | chat-export game icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The second numbered archive copy already fits the current `chat_export_asset` contract.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized and validated as the fourth chat-export asset slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 44`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 44 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-41-45`
  - Passing session: `logs/data-room-batch-loop-round-41-45/20260328T224622Z-01`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py -q`
  - Result: `58 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue through the second numbered archive copy until the uncovered asset pool is exhausted or a true mismatch appears.
