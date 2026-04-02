# Data Room Batch 34

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 34 manifest

This batch captures the second ten Bitsync chat-export UI assets from the copied archive so duplicate exported chat bundles stop staying unsupported.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_copy_asset_back` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/back.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_back_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/back@2x.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_media_call` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_call.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_media_call_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_call@2x.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_media_contact` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_contact.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_media_contact_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_contact@2x.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_media_file` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_file.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_media_file_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_file@2x.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_media_game` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_game.png` | copied chat-export UI asset | `chat_export_asset` |
| `chat_copy_asset_media_game_2x` | `employment/Bitsync/ChatExport_2024-12-14 (1)/images/media_game@2x.png` | copied chat-export UI asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Surfaced gaps:
  - the copied Bitsync chat-export archive remained unsupported even though it was structurally identical to the original bundle
  - duplicate archive assets had no stable typed landing zone

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Copied chat-export UI assets now resolve to the same dedicated archive-asset family as the original bundle.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 34`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 34 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-31-35`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-31-35/20260328T221247Z-02`
  - focused tests: `56 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether duplicate chat-export bundles should stay separately indexed or collapse under the same archive series key.
