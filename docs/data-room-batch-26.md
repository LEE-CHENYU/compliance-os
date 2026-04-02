# Data Room Batch 26

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 26 manifest

This batch captures the remaining resume-history overflow plus the adjacent education anchors that belong with career materials: transcript, language-test evidence, and degree-verification records.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `resume_cn_230718` | `CV & Cover Letters/CV230217/李宸宇18652053798_230718.pdf` | early Chinese resume archive | `resume` |
| `resume_analyst_copy_1` | `CV & Cover Letters/CV241028/jobright_previous_versions/Chenyu Li Resume_Analyst (1).pdf` | archived analyst resume copy | `resume` |
| `resume_analyst_copy_2` | `CV & Cover Letters/CV241028/jobright_previous_versions/Chenyu Li Resume_Analyst.pdf` | archived analyst resume copy | `resume` |
| `resume_250626` | `CV & Cover Letters/CV250626/Chenyu Li Resume_0626.pdf` | June 2025 resume variant | `resume` |
| `resume_250801` | `CV & Cover Letters/CV250626/Chenyu Li Resume_0801.pdf` | August 2025 resume variant | `resume` |
| `resume_plain_260325` | `CV & Cover Letters/CV260325/resume.pdf` | plain-named March 2026 resume | `resume` |
| `ecertification_transcript` | `H1b Petition/Employee/Transcript/40561322_eCertification(ElectronicAcademicCertification).pdf` | academic certification transcript | `transcript` |
| `jlpt_n1_record` | `CV & Cover Letters/transcript&diploma/JLPT_N1.jpg` | JLPT language-test proof | `language_test_certificate` |
| `masters_degree_jpg` | `CV & Cover Letters/transcript&diploma/硕士学历认证.jpg` | degree-verification image | `degree_certificate` |
| `masters_degree_pdf` | `硕士学历认证.pdf` | degree-verification PDF | `degree_certificate` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `9/10`
- Surfaced gap:
  - the early Chinese resume archive was being routed by first-page text to `language_test_certificate` instead of `resume`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Resume archive overflow plus adjacent credential anchors now classify cleanly end to end.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 26`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 26 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-26-30`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-26-30/20260328T215409Z-04`
  - focused tests: `54 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether multilingual resume archives need stronger version-series metadata than the current resume family.
