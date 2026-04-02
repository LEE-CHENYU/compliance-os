# Data Room Batch 45

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 45 manifest

This batch continues the second numbered Bitsync chat-export archive copy with location, music, photo, shop, and video icon assets.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_2_media_location` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_location.png` | chat-export location icon asset | `chat_export_asset` |
| `chat_export_2_media_location_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_location@2x.png` | chat-export location icon asset | `chat_export_asset` |
| `chat_export_2_media_music` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_music.png` | chat-export music icon asset | `chat_export_asset` |
| `chat_export_2_media_music_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_music@2x.png` | chat-export music icon asset | `chat_export_asset` |
| `chat_export_2_media_photo` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_photo.png` | chat-export photo icon asset | `chat_export_asset` |
| `chat_export_2_media_photo_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_photo@2x.png` | chat-export photo icon asset | `chat_export_asset` |
| `chat_export_2_media_shop` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_shop.png` | chat-export shop icon asset | `chat_export_asset` |
| `chat_export_2_media_shop_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_shop@2x.png` | chat-export shop icon asset | `chat_export_asset` |
| `chat_export_2_media_video` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_video.png` | chat-export video icon asset | `chat_export_asset` |
| `chat_export_2_media_video_2x` | `employment/Bitsync/ChatExport_2024-12-14 (2)/images/media_video@2x.png` | chat-export video icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The second numbered archive media assets already classify cleanly as `chat_export_asset`.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required. This batch was materialized and validated as the fifth chat-export asset slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 45`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 45 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-41-45`
  - Passing session: `logs/data-room-batch-loop-round-41-45/20260328T224622Z-02`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py -q`
  - Result: `58 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue through the remaining numbered chat-export archive assets and then handle the residual photo and text artifacts.
