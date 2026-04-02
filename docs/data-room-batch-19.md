# Data Room Batch 19

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 19 manifest

This batch continues the education stack with archived transcript, diploma, certification, and language-test records under the career-material archive.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `cv_transcript_cn` | `CV & Cover Letters/transcript&diploma/ Transcript(Chinese).pdf` | Chinese transcript archive copy | `transcript` |
| `cv_ecertification` | `CV & Cover Letters/transcript&diploma/40561322_eCertification(ElectronicAcademicCertification).pdf` | academic certification archive copy | `transcript` |
| `cv_etrancript` | `CV & Cover Letters/transcript&diploma/40697019_eTranscript.pdf` | electronic transcript archive copy | `transcript` |
| `sjtu_transcript_2021` | `CV & Cover Letters/transcript&diploma/Transcript for Shanghai Jiao Tong University 2021.pdf` | Shanghai Jiao Tong transcript | `transcript` |
| `cv_diploma_pdf` | `CV & Cover Letters/transcript&diploma/diploma.pdf` | diploma archive copy | `degree_certificate` |
| `cv_degree_certification` | `CV & Cover Letters/transcript&diploma/学位认证.pdf` | degree certification | `degree_certificate` |
| `cv_undergrad_education_certification` | `CV & Cover Letters/transcript&diploma/本科学历认证.pdf` | undergraduate education certification | `degree_certificate` |
| `cv_masters_education_certification` | `CV & Cover Letters/transcript&diploma/硕士学历认证.pdf` | master's education certification | `degree_certificate` |
| `jlpt_n1_certificate` | `CV & Cover Letters/transcript&diploma/JLPT_N1.pdf` | Japanese language proficiency result | `language_test_certificate` |
| `ielts_score_image` | `CV & Cover Letters/transcript&diploma/雅思2021-01-03 12.46.55.jpeg` | IELTS score report image | `language_test_certificate` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `8/10`
- Already strong:
  - transcript and diploma / certification records
- Surfaced gaps:
  - `JLPT_N1.pdf` was unsupported
  - `雅思2021-01-03 12.46.55.jpeg` was unsupported

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- The remaining language-test records now classify cleanly as `language_test_certificate`, so the education archive no longer leaves those credentials opaque

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 19`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 19 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-16-20`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-16-20/20260328T183154Z-04`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether language-test artifacts should remain retrieval-only or be promoted into education-specific comparison rules.
