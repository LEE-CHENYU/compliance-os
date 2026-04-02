# Data Room Batch 06

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 06 manifest

This batch targets root-level identity and education anchors that should be retrievable as first-class evidence rather than falling into generic OCR text.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `visa_stamp_root` | `visa.jpeg` | passport visa page for status-history review | `visa_stamp` |
| `ssn_card_root` | `SSN.jpg` | Social Security identity control | `social_security_card` |
| `student_id_root` | `Student ID.jpg` | school identity anchor | `student_id` |
| `drivers_license_root` | `Driver’s license （中）.jpeg` | government photo ID anchor | `drivers_license` |
| `ead_root_image` | `STEM OPT EAD.jpeg` | active EAD image control | `ead` |
| `ead_root_pdf` | `stem_ead.pdf` | archived EAD PDF control | `ead` |
| `diploma_root_pdf` | `diploma.pdf` | degree completion proof | `degree_certificate` |
| `diploma_root_image` | `columbia diploma.JPG` | degree image proof | `degree_certificate` |
| `waseda_transcript_root` | `Transcript for Waseda University.pdf` | school transcript anchor | `transcript` |
| `undergrad_transcript_root` | `李宸宇_本科生英文成绩单.pdf` | undergraduate transcript anchor | `transcript` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `2/10`
- Matched:
  - `STEM OPT EAD.jpeg` -> `ead`
  - `stem_ead.pdf` -> `ead`
- Missed target families:
  - `visa_stamp`
  - `social_security_card`
  - `student_id`
  - `drivers_license`
  - `degree_certificate`
  - `transcript`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- The batch now classifies all root-level identity and education anchors on the non-OCR intake path.
- Minimal structured extraction schemas now exist for:
  - `visa_stamp`
  - `social_security_card`
  - `student_id`
  - `drivers_license`
  - `degree_certificate`
  - `transcript`

## Validation

- Real-source validator:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 06`
- Loop-compatible logging command:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 06 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
- Current recorded run:
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T083149Z`
  - superseded baseline run only
- Current passing validator run:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 06`
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 06 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T155831Z-02`
  - focused tests: `45 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Add review/comparison coverage only when a concrete check path needs these new identity or education families.
