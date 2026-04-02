# Data Room Batch 48

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 48 manifest

This batch bridges the second numbered archive copy into the remaining primary Bitsync chat-export archive assets.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_2_photo_full` | `employment/Bitsync/ChatExport_2024-12-14 (2)/photos/photo_1@08-12-2024_18-20-31.jpg` | chat-export photo asset | `chat_export_asset` |
| `chat_export_2_photo_thumb` | `employment/Bitsync/ChatExport_2024-12-14 (2)/photos/photo_1@08-12-2024_18-20-31_thumb.jpg` | chat-export photo thumbnail asset | `chat_export_asset` |
| `chat_export_primary_media_photo` | `employment/Bitsync/ChatExport_2024-12-14/images/media_photo.png` | chat-export photo icon asset | `chat_export_asset` |
| `chat_export_primary_media_photo_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_photo@2x.png` | chat-export photo icon asset | `chat_export_asset` |
| `chat_export_primary_media_shop` | `employment/Bitsync/ChatExport_2024-12-14/images/media_shop.png` | chat-export shop icon asset | `chat_export_asset` |
| `chat_export_primary_media_shop_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_shop@2x.png` | chat-export shop icon asset | `chat_export_asset` |
| `chat_export_primary_media_video` | `employment/Bitsync/ChatExport_2024-12-14/images/media_video.png` | chat-export video icon asset | `chat_export_asset` |
| `chat_export_primary_media_video_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_video@2x.png` | chat-export video icon asset | `chat_export_asset` |
| `chat_export_primary_media_voice` | `employment/Bitsync/ChatExport_2024-12-14/images/media_voice.png` | chat-export voice icon asset | `chat_export_asset` |
| `chat_export_primary_media_voice_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_voice@2x.png` | chat-export voice icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The current `chat_export_asset` contract already covers these archive assets.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required for this batch slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 48`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 48 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-46-50`
- Passing session:
  - `logs/data-room-batch-loop-round-46-50/20260328T230349Z`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_codex_loop_scripts.py -q`
  - Result: `67 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue through the remaining primary archive section assets and the final text artifact.
