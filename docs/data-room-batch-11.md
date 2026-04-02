# Data Room Batch 11

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 11 manifest

This batch covers academic credential anchors plus the remaining business-license images that are still outside the resolved data-room set.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `etrancript_pdf` | `transcript/40697019_eTranscript.pdf` | electronic transcript anchor | `transcript` |
| `ecertification_pdf` | `transcript/40561322_eCertification(ElectronicAcademicCertification).pdf` | academic certification support | `transcript` |
| `top_level_chinese_transcript` | ` Transcript(Chinese).pdf` | Chinese transcript record | `transcript` |
| `top_level_wes_transcript` | ` Transcript(WES).pdf` | WES transcript or evaluation record | `transcript` |
| `english_score_transcript` | `李宸宇_本科生英文等级成绩单.pdf` | undergraduate English score transcript | `transcript` |
| `education_certification` | `学历认证.pdf` | education certification artifact | `degree_certificate` |
| `business_license_star_algo_jpg` | `星辰算法营业执照.jpg` | business license image | `business_license` |
| `business_license_star_algo_medium` | `星辰算法营业执照 Medium.jpeg` | alternate business license image | `business_license` |
| `business_license_old_root` | `营业执照(旧).jpeg` | prior business license image | `business_license` |
| `business_license_companyinfo_old` | `公司信息/营业执照(老).jpg` | archived company business license | `business_license` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `3/10`
- Strong today:
  - transcript-style records already classified correctly
- Remaining misses:
  - `degree_certificate` for `学历认证.pdf`
  - `business_license` for the remaining license images
- Validator issue surfaced during the baseline run:
  - markdown manifest parsing incorrectly stripped leading spaces inside backticked file paths, which broke the two root transcript filenames that begin with a literal space

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- The batch now classifies cleanly across:
  - transcript and academic certification anchors
  - Chinese and archived business-license images
- The validator now preserves leading spaces inside backticked manifest file paths, so real-source checks are reliable for root files with literal leading-space names

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 11`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 11 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-11-15`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-11-15/20260328T161804Z-03`
  - focused tests: `48 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Pull the remaining academic overflow, such as `硕士学历认证.pdf`, into a later education-focused batch instead of reopening this anchor slice.
