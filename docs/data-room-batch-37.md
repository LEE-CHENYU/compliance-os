# Data Room Batch 37

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 37 manifest

This batch captures the remaining root-level identity images and profile-photo assets that still bypass typed storage.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `root_id_front_medium` | `IMG_3721 Medium.jpeg` | national ID front image | `identity_document` |
| `root_id_back_medium` | `IMG_3722 Medium.jpeg` | national ID back image | `identity_document` |
| `root_archive_id_front` | `WechatIMG219.jpeg` | national ID front image | `identity_document` |
| `root_archive_id_back` | `WechatIMG220.jpeg` | national ID back image | `identity_document` |
| `root_profile_asset_hash` | `092e233d-f2e5-.jpg` | square profile-photo asset | `profile_photo` |
| `root_profile_photo` | `Photo.jpg` | profile or headshot photo | `profile_photo` |
| `cv230217_profile_asset_jpg` | `CV & Cover Letters/CV230217/IMG_10910411.JPG` | resume profile-photo asset | `profile_photo` |
| `cv230217_profile_asset_jpeg` | `CV & Cover Letters/CV230217/IMG_10910411.jpeg` | resume profile-photo asset | `profile_photo` |
| `cv230217_profile_asset_r0015961_copy` | `CV & Cover Letters/CV230217/R0015961 (1).jpeg` | resume profile-photo asset | `profile_photo` |
| `cv230217_profile_asset_r0015961` | `CV & Cover Letters/CV230217/R0015961.jpeg` | resume profile-photo asset | `profile_photo` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Surfaced gaps:
  - root-level identity images and profile-photo assets were fully unsupported on the fast path
  - the intake layer had no contextual handling for root archive ID images or CV profile-photo assets

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Root archive ID images and resume profile-photo assets now resolve to stable typed families.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 37`
  - Result: `10/10`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 37 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-36-40`
  - Passing session: `logs/data-room-batch-loop-round-36-40/20260328T224019Z-02`
- Focused regression suite:
  - `conda run -n compliance-os python -m pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py -q`
  - Result: `58 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Validate and wire fast-path support for the remaining root identity and profile-photo slice.
