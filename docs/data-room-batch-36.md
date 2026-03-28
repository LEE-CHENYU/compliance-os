# Data Room Batch 36

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 36 manifest

This batch captures the remaining BSGC identity scans and personal archive identity records that still sit outside typed intake.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `bsgc_passport_front_primary` | `BSGC/Docs/IMG_0991.jpeg` | passport identity page scan | `passport` |
| `bsgc_identity_scan_1708` | `BSGC/Docs/IMG_1708.jpeg` | personal identity-card style scan | `identity_document` |
| `bsgc_passport_mrz_scan` | `BSGC/Docs/IMG_1709.jpeg` | passport MRZ or identity-page scan | `passport` |
| `bsgc_social_security_card` | `BSGC/Docs/IMG_1792.jpg` | Social Security card scan | `social_security_card` |
| `bsgc_identity_scan_2070` | `BSGC/Docs/IMG_2070.JPG` | personal identity-card style scan | `identity_document` |
| `bsgc_identity_scan_2227` | `BSGC/Docs/IMG_2227.jpeg` | personal identity-card style scan | `identity_document` |
| `personal_ssnap_record` | `Personal Info Archive/IMG_1675.pdf` | SSNAP replacement-card printout | `social_security_record` |
| `personal_ny_state_id_scan` | `Personal Info Archive/IMG_1725.pdf` | New York state ID or driver-license scan | `drivers_license` |
| `personal_id_front_archive` | `Personal Info Archive/WechatIMG219.jpg` | national ID front scan | `identity_document` |
| `personal_id_back_archive` | `Personal Info Archive/WechatIMG220.jpg` | national ID back scan | `identity_document` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Surfaced gaps:
  - BSGC identity scans, SSNAP printout, and personal ID archive images were all unsupported on the fast path
  - the intake layer had no path-context support for BSGC `Docs` identity scans or the archived personal SSNAP and ID files

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- BSGC passport, identity-card, Social Security, and personal SSNAP or driver-license records now land on stable typed families.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 36`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 36 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-36-40`
  - Passing session: `logs/data-room-batch-loop-round-36-40/20260328T224019Z-04`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py -q`
  - Result: `58 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Validate and wire fast-path identity/archive support for the BSGC and personal-scan slice.
