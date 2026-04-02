# Data Room Batch 14

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 14 manifest

This batch targets remaining personal-support records: health coverage, insurance images, club or membership packets, residence proof, and family identity files.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `coveredca_application_overview` | `Medical/Marketplace :Individual & Families: OverviewMy ApplicationMy AccountEligibility Determination Manage Plans Verification My AppealsAddress History.pdf` | health-coverage application packet | `health_coverage_application` |
| `insurance_card_image` | `Medical/Medicard02.png` | medical insurance card | `insurance_card` |
| `medical_record_template_012` | `Medical/N250714184955_Template012_235756780_03_12_2025_03_05_11_EN.pdf` | medical or insurance record | `insurance_record` |
| `medical_record_template_101` | `Medical/N250714231370_Template101_235756777_03_12_2025_03_05_11_EN.pdf` | medical or insurance record | `insurance_record` |
| `membership_packet` | `Personal Info Archive/New Member Packet - Welcome.pdf` | membership welcome packet | `membership_welcome_packet` |
| `penn_club_welcome` | `Personal Info Archive/Gmail - Welcome to The Penn Club.pdf` | club welcome message | `membership_welcome_packet` |
| `nanjing_residence_certificate` | `Personal Info Archive/南京居住证明.pdf` | residence certificate | `residence_certificate` |
| `mom_id_image_1` | `Mom ID/Weixin Image_20260209173713_337_168.jpg` | family identity image | `identity_document` |
| `mom_id_image_2` | `Mom ID/Weixin Image_20260209175326_346_168.jpg` | family identity image | `identity_document` |
| `mom_id_image_3` | `Mom ID/Weixin Image_20260209175328_347_168.jpg` | family identity image | `identity_document` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Remaining misses:
  - `health_coverage_application`
  - `insurance_card`
  - `insurance_record`
  - `membership_welcome_packet`
  - `residence_certificate`
  - `identity_document`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Medical, residence, membership, and family-identity support files now classify cleanly, including generic `Mom ID/Weixin Image...` artifacts through controlled folder-context matching

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 14`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 14 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-11-15`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-11-15/20260328T161804Z`
  - focused tests: `48 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Add downstream handling only if medical or identity-support records need review logic or retrieval weighting beyond intake and extraction schema support.
