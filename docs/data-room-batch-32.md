# Data Room Batch 32

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 32 manifest

This batch drains the first employment screenshot slice so Justworks, WhatsApp, and recruiter-chat captures stop remaining as opaque image uploads.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `rai_justworks_screenshot` | `employment/Rai/Screenshot from Justwork.png` | employment portal screenshot | `employment_screenshot` |
| `wolff_whatsapp_002859` | `employment/Wolff & Li/WhatsApp Image 2025-03-20 at 00.28.59.jpeg` | employment WhatsApp screenshot | `employment_screenshot` |
| `wolff_whatsapp_150154` | `employment/Wolff & Li/WhatsApp Image 2025-03-20 at 15.01.54.jpeg` | employment WhatsApp screenshot | `employment_screenshot` |
| `bitsync_will_9455` | `employment/Bitsync/Will Communications/IMG_9455.PNG` | recruiter chat screenshot | `employment_screenshot` |
| `bitsync_will_9456` | `employment/Bitsync/Will Communications/IMG_9456.PNG` | recruiter chat screenshot | `employment_screenshot` |
| `bitsync_will_9457` | `employment/Bitsync/Will Communications/IMG_9457.PNG` | recruiter chat screenshot | `employment_screenshot` |
| `bitsync_will_9458` | `employment/Bitsync/Will Communications/IMG_9458.PNG` | recruiter chat screenshot | `employment_screenshot` |
| `bitsync_will_9459` | `employment/Bitsync/Will Communications/IMG_9459.PNG` | recruiter chat screenshot | `employment_screenshot` |
| `bitsync_will_9460` | `employment/Bitsync/Will Communications/IMG_9460.PNG` | recruiter chat screenshot | `employment_screenshot` |
| `bitsync_will_9461` | `employment/Bitsync/Will Communications/IMG_9461.PNG` | recruiter chat screenshot | `employment_screenshot` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Surfaced gaps:
  - employment screenshots from Justworks, WhatsApp, and recruiter chat remained unsupported image uploads
  - no path-level screenshot family existed for these recurring employment captures

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Employment screenshots now land on a dedicated typed family instead of staying as opaque image evidence.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 32`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 32 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-31-35`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-31-35/20260328T221247Z-04`
  - focused tests: `56 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether employment screenshots need OCR-driven subtyping or can remain a retrieval-only evidence family.
