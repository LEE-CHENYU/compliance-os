# Data Room Batch 33

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 33 manifest

This batch captures the first ten Bitsync chat-export UI assets so exported chat archives stop contaminating the remaining pool as unsupported files.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_asset_back` | `employment/Bitsync/ChatExport_2024-12-14/images/back.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_back_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/back@2x.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_media_call` | `employment/Bitsync/ChatExport_2024-12-14/images/media_call.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_media_call_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_call@2x.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_media_contact` | `employment/Bitsync/ChatExport_2024-12-14/images/media_contact.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_media_contact_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_contact@2x.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_media_file` | `employment/Bitsync/ChatExport_2024-12-14/images/media_file.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_media_file_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_file@2x.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_media_game` | `employment/Bitsync/ChatExport_2024-12-14/images/media_game.png` | chat-export UI asset | `chat_export_asset` |
| `chat_asset_media_game_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/media_game@2x.png` | chat-export UI asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Surfaced gaps:
  - chat-export UI assets under the Bitsync archive remained unsupported and kept polluting the uncovered file pool
  - the intake layer had no archive-asset family for exported chat bundle icons and thumbnails

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Chat-export UI assets now resolve to a dedicated archive-asset family and stop showing up as unsupported leftovers.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 33`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 33 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-31-35`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-31-35/20260328T221247Z-03`
  - focused tests: `56 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Continue draining the remaining exported chat assets only if they still materially affect the uncovered ingestible pool.
