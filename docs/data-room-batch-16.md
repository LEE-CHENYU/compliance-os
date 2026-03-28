# Data Room Batch 16

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 16 manifest

This batch covers remaining employment-support records that sit between formal offer letters and payroll continuity: invention-assignment agreements, wage notices, EIN or tax forms, and residual payroll evidence.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `claudius_final_evaluation_page5` | `employment/Claudius/12 month (page-5) .pdf` | final-evaluation support page | `final_evaluation` |
| `claudius_invention_assignment_unsigned` | `employment/Claudius/Form of Employee Invention Assignment, Confidentiality and Non-Solicitation Agreement, Chenyu Li.pdf` | employment agreement | `employment_contract` |
| `claudius_invention_assignment_signed` | `employment/Claudius/Form of Employee Invention Assignment, Confidentiality and Non-Solicitation Agreement, Chenyu Li_signed.pdf` | signed employment agreement | `employment_contract` |
| `claudius_wage_notice` | `employment/Claudius/Wage Theft Prevention Act Notice_Signed.pdf` | wage-notice record | `wage_notice` |
| `wolff_cp575` | `employment/Wolff & Li/CP575Notice_1741982620352-3.pdf` | employer EIN notice | `ein_letter` |
| `wolff_w2` | `employment/Wolff & Li/US_W-2_7757616926033936.pdf` | wage statement | `w2` |
| `wolff_offer_letter` | `employment/Wolff & Li/Wolff_&_Li_Capital_Offer_Letter.pdf` | employment offer letter | `employment_letter` |
| `wolff_i9` | `employment/Wolff & Li/wolff-li-capital-i-9.pdf` | employment eligibility verification | `i9` |
| `wolff_paystub_packet` | `employment/Wolff & Li/wolff-li-capital-inc-paystubs-chenyu-li.pdf` | payroll support packet | `paystub` |
| `bitsync_i983_request` | `employment/Bitsync/BitSync Mail - Request for Ink-Signed I-983 Form.pdf` | I-983 request thread | `i983` |

## Baseline current-state result

- Current fast-path match rate against the initial batch intent: `6/10`
- Already strong:
  - `ein_letter`, `w2`, `employment_letter`, `i9`, `paystub`, and `i983`
- Surfaced gaps:
  - `employment/Claudius/12 month (page-5) .pdf` did not classify as `final_evaluation`
  - `employment/Claudius/Wage Theft Prevention Act Notice_Signed.pdf` did not classify as `wage_notice`
  - the invention-assignment PDFs were landing on the canonical `employment_contract` family, so the batch intent was tightened to that normalized family instead of leaving a duplicate `employment_agreement` label in the manifest

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- This batch now classifies cleanly across:
  - final-evaluation support pages
  - employment-contract / invention-assignment packets
  - wage notices
  - Wolff payroll and employment support records

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 16`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 16 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-16-20`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-16-20/20260328T183154Z-02`
  - focused tests: `51 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Keep `employment_contract`, `wage_notice`, and `final_evaluation` stable as more employment-admin overflow enters later batches.
