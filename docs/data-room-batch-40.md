# Data Room Batch 40

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 40 manifest

This batch closes the current unresolved employment screenshot residue and starts the remaining Bitsync chat-export asset overflow.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `will_communications_chat_9468` | `employment/Bitsync/Will Communications/IMG_9468.PNG` | employment compliance chat screenshot | `employment_screenshot` |
| `will_communications_chat_9469` | `employment/Bitsync/Will Communications/IMG_9469.PNG` | employment compliance chat screenshot | `employment_screenshot` |
| `will_communications_chat_9470` | `employment/Bitsync/Will Communications/IMG_9470.PNG` | employment compliance chat screenshot | `employment_screenshot` |
| `will_communications_chat_9471` | `employment/Bitsync/Will Communications/IMG_9471.PNG` | employment compliance chat screenshot | `employment_screenshot` |
| `tiger_cloud_stem_employer_letter` | `stem opt/Tiger Cloud, LLC - New York. NY.pdf` | STEM OPT employer letter | `employment_letter` |
| `vcv_stem_signature_pages` | `stem opt/i983/vcv/Signature Pages.pdf` | STEM OPT signature-only packet | `signature_page` |
| `bitsync_chat_asset_media_location` | `employment/Bitsync/ChatExport_2024-12-14/images/media_location.png` | chat-export icon asset | `chat_export_asset` |
| `bitsync_chat_asset_media_location_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_location@2x.png` | chat-export icon asset | `chat_export_asset` |
| `bitsync_chat_asset_media_music` | `employment/Bitsync/ChatExport_2024-12-14/images/media_music.png` | chat-export icon asset | `chat_export_asset` |
| `bitsync_chat_asset_media_music_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_music@2x.png` | chat-export icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `5/10`
- Surfaced gaps:
  - the remaining Will Communications screenshots and Tiger Cloud STEM employer letter were unsupported on the fast path
  - the existing `signature_page` and `chat_export_asset` rules already handled the other five files in this batch

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- The remaining Will Communications screenshots and Tiger Cloud STEM employer letter now resolve correctly, while the chat-export asset path remains stable.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 40`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 40 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-36-40`
  - Passing session: `logs/data-room-batch-loop-round-36-40/20260328T224019Z-03`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py -q`
  - Result: `58 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Validate the remaining employment screenshot residue and confirm the first uncovered Bitsync asset slice still fits the existing chat-export contract.
