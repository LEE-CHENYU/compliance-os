# Data Room Batch 35

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 35 manifest

This batch captures the remaining education scans, student-admin screenshots, website filing artifacts, and account setup overflow that still sit outside typed storage.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `sjtu_bachelor_degree_pdf` | `CV & Cover Letters/transcript&diploma/20210713112836-0001.pdf` | scanned SJTU bachelor degree certificate | `degree_certificate` |
| `columbia_masters_degree_image` | `CV & Cover Letters/transcript&diploma/IMG_0514.JPG` | Columbia masters degree scan | `degree_certificate` |
| `i20_screenshot_primary` | `i20/I20/38911625468472_.pic.png` | visual I-20 screenshot | `i20` |
| `i20_travel_emailtracker` | `i20/I20/I-20 Travel.rtfd/EmailTracker.cfm.jpg` | I-20 travel-support screenshot | `i20` |
| `i20_travel_attachment` | `i20/I20/I-20 Travel.rtfd/unnamed.png` | I-20 travel-support screenshot | `i20` |
| `veeup_icp_record` | `Veeup.cc/网站备案.png` | website ICP filing record | `company_filing` |
| `veeup_authorization_1` | `授权书/29431747363841_.pic.jpg` | website filing authorization image | `company_filing` |
| `veeup_authorization_2` | `授权书/29441747363843_.pic.jpg` | website filing authorization image | `company_filing` |
| `treasurydirect_security_questions` | `treasury pass.png` | TreasuryDirect security-question setup screenshot | `account_security_setup` |
| `bsgc_bank_account_image` | `新春竹_对公账户.pic.jpg` | business bank-account screenshot | `bank_account_record` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Surfaced gaps:
  - scanned degree certificates, image-based `I-20` screenshots, ICP filing artifacts, TreasuryDirect setup screens, and the business bank-account image were unsupported on the fast path
  - the intake layer lacked path anchors for these education, student-admin, and website-filing image records

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Education scans, `I-20` screenshots, ICP filing artifacts, account-setup screens, and the bank-account image now resolve to stable typed families.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 35`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 35 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-31-35`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-31-35/20260328T221247Z`
  - focused tests: `56 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether visual student-admin screenshots should remain under the main `i20` family or move into a narrower screenshot-only subtype.
