# Data Room Batch 41

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 41 manifest

This batch starts the remaining numbered Bitsync chat-export asset archive and captures the first icon slice from `ChatExport_2024-12-14 (1)`.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_1_media_location` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_location.png` | chat-export location icon asset | `chat_export_asset` |
| `chat_export_1_media_location_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_location@2x.png` | chat-export location icon asset | `chat_export_asset` |
| `chat_export_1_media_music` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_music.png` | chat-export music icon asset | `chat_export_asset` |
| `chat_export_1_media_music_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_music@2x.png` | chat-export music icon asset | `chat_export_asset` |
| `chat_export_1_media_photo` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_photo.png` | chat-export photo icon asset | `chat_export_asset` |
| `chat_export_1_media_photo_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_photo@2x.png` | chat-export photo icon asset | `chat_export_asset` |
| `chat_export_1_media_shop` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_shop.png` | chat-export shop icon asset | `chat_export_asset` |
| `chat_export_1_media_shop_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_shop@2x.png` | chat-export shop icon asset | `chat_export_asset` |
| `chat_export_1_media_video` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_video.png` | chat-export video icon asset | `chat_export_asset` |
| `chat_export_1_media_video_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_video@2x.png` | chat-export video icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The existing `chat_export_asset` path rules already cover these numbered archive icon assets cleanly.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized and validated as explicit chat-export asset history.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 41`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 41 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-41-45`
  - Passing session: `logs/data-room-batch-loop-round-41-45/20260328T224609Z`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py -q`
  - Result: `58 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue materializing the remaining numbered chat-export asset archive unless a concrete retrieval or duplication issue appears.
