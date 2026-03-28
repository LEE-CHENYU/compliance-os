# Data Room Batch 49

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 49 manifest

This batch continues the final primary Bitsync chat-export archive section assets.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `chat_export_primary_section_calls` | `employment/Bitsync/ChatExport_2024-12-14/images/section_calls.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_calls_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_calls@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_chats` | `employment/Bitsync/ChatExport_2024-12-14/images/section_chats.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_chats_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_chats@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_contacts` | `employment/Bitsync/ChatExport_2024-12-14/images/section_contacts.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_contacts_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_contacts@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_frequent` | `employment/Bitsync/ChatExport_2024-12-14/images/section_frequent.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_frequent_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_frequent@2x.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_other` | `employment/Bitsync/ChatExport_2024-12-14/images/section_other.png` | chat-export section icon asset | `chat_export_asset` |
| `chat_export_primary_section_other_2x` | `employment/Bitsync/ChatExport_2024-12-14/images/section_other@2x.png` | chat-export section icon asset | `chat_export_asset` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The current `chat_export_asset` contract already covers these archive assets.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No code changes were required for this batch slice.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 49`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 49 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-46-50`
- Passing session:
  - `logs/data-room-batch-loop-round-46-50/20260328T230349Z-02`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_codex_loop_scripts.py -q`
  - Result: `67 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Close the remaining primary archive assets and the final opaque identifier artifact.
