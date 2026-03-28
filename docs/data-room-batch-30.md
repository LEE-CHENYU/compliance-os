# Data Room Batch 30

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 30 manifest

This batch closes the remaining employment-side correspondence and agreement packet slice: contracts, signing reminders, legal responses, resignation notice, and related HR communications.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `clinipulse_attorney_response` | `employment/CliniPulse/Attorney Letter to Chenyu Li-03212025.pdf` | attorney response on unpaid wages and offer withdrawal | `employment_correspondence` |
| `clinipulse_stem_opt_salary_guidance` | `employment/CliniPulse/LionMail Mail - Guidance on STEM OPT Compliance and Unpaid Salary.pdf` | school-facing compliance and salary guidance request | `support_request` |
| `jz_contract_letter_jz_capital` | `employment/JZ/Contract & Signed Letter - JZ Capital LLC.pdf` | JZ Capital contract packet | `employment_contract` |
| `jz_contract_letter_vcv` | `employment/JZ/Contract & Signed Letter - VCV Digital LLC.pdf` | VCV contract packet | `employment_contract` |
| `jz_resignation_notice` | `employment/JZ/Resignation Notice - Commission Request and Return of Company Property.pdf` | resignation and commission request notice | `employment_correspondence` |
| `rai_finalized_packet_notice` | `employment/Rai/FINALIZED- RAI INC. - employment - Cheney (Chenyu) Li.pdf.pdf` | finalized employment packet notice | `employment_correspondence` |
| `rai_dochub_reminder` | `employment/Rai/LionMail Mail - REMINDER_ ACTION NEEDED_ RAI INC. - employment - Cheney (Chenyu) Li 20241212.pdf` | DocHub signing reminder for employment packet | `employment_correspondence` |
| `rai_employment_packet_v1` | `employment/Rai/RAI INC. - employment - Cheney (Chenyu) Li (1).pdf` | employment packet cover sheet | `employment_contract` |
| `rai_employment_packet_v2` | `employment/Rai/RAI INC. - employment - Cheney (Chenyu) Li 20241212.pdf` | revised employment packet cover sheet | `employment_contract` |
| `vcv_opt_employer_letter_signed` | `employment/VCV/Signed Letter May 23 2023.docx.pdf` | signed OPT employer letter | `employment_letter` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `0/10`
- Surfaced gaps:
  - attorney letters, resignation notices, finalized reminders, and DocHub employment wrappers were unsupported
  - contract-and-signed-letter packets were unsupported
  - the signed VCV OPT employer letter was misrouted from first-page text and missed `employment_letter`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Employment agreements, reminders, legal responses, and HR correspondence now land on stable typed families instead of staying as unstructured employment PDFs.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 30`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 30 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-26-30`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-26-30/20260328T215409Z-02`
  - focused tests: `54 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether DocHub email wrappers should remain employment correspondence or collapse into the same series as the underlying contract packet.
