# Data Room Batch 60

Source folder: `/Users/lichenyu/Desktop/accounting-not-in-important-docs-20260329/files`

## Batch 60 manifest

This batch closes the accounting-derived queue with payroll, tax-support, and standalone form residue.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `filled_1098t_screenshot` | `1098t_form_filled.png` | filled 1098-T screenshot reference | `tuition_statement` |
| `filled_eminutes_form` | `eminutes_form_filled.png` | eMinutes form completion screenshot | `entity_service_form` |
| `claudius_termination_letter` | `legal/employment/claudius_termination_020525.pdf` | employment termination notice | `termination_letter` |
| `kaufman_schwab_yearend` | `outgoing/kaufman_rossin/data_room/03_2024_yearend_summary_schwab.pdf` | Schwab year-end account summary | `brokerage_year_end_summary` |
| `kaufman_claudius_w2` | `outgoing/kaufman_rossin/data_room/03_2025_w2_claudius.pdf` | packaged Claudius W-2 copy | `w2` |
| `tda_1042s_2023` | `tax/2024/2023_1042s_tda_xxx619.pdf` | 2023 1042-S statement | `1042s` |
| `schwab_1099b_part1` | `tax/2024/2024_1099b_schwab_xxx619_part1.pdf` | Schwab 1099-B part 1 | `1099` |
| `schwab_1099b_part2` | `tax/2024/2024_1099b_schwab_xxx619_part2.pdf` | Schwab 1099-B part 2 | `1099` |
| `claudius_w2_2025` | `tax/2025/W2_Claudius_Legal_Intelligence_2025.pdf` | 2025 Claudius W-2 | `w2` |
| `claudius_w2_2025_unlocked` | `tax/2025/W2_Claudius_Legal_Intelligence_2025_unlocked.pdf` | unlocked 2025 Claudius W-2 | `w2` |
| `irs_form_941` | `tmp/mendy_gusto_docs/US_941_7757616926033936.pdf` | IRS payroll tax filing | `form_941` |
| `payroll_summary_1275864_2` | `tmp/mendy_gusto_docs/wolff-li-capital-inc-payroll-summary-7757500971275864-2.pdf` | Gusto payroll summary | `payroll_summary` |
| `payroll_summary_1275864_3` | `tmp/mendy_gusto_docs/wolff-li-capital-inc-payroll-summary-7757500971275864-3.pdf` | Gusto payroll summary | `payroll_summary` |
| `payroll_summary_4730858_2` | `tmp/mendy_gusto_docs/wolff-li-capital-inc-payroll-summary-7757500974730858-2.pdf` | Gusto payroll summary | `payroll_summary` |
| `payroll_summary_6935644_3` | `tmp/mendy_gusto_docs/wolff-li-capital-inc-payroll-summary-7757500976935644-3.pdf` | Gusto payroll summary | `payroll_summary` |
| `payroll_summary_8097544_4` | `tmp/mendy_gusto_docs/wolff-li-capital-inc-payroll-summary-7757500978097544-4.pdf` | Gusto payroll summary | `payroll_summary` |
| `gusto_paystub_packet` | `tmp/mendy_gusto_docs/wolff-li-capital-inc-paystubs-2025-05-06.pdf` | Gusto paystub packet | `paystub` |

## Baseline current-state result

Pending first validation.

## Current batch blockers

- Establish current coverage for `form_941`, `payroll_summary`, `brokerage_year_end_summary`, `entity_service_form`, and `termination_letter`.
- Decide whether payroll summary packets should emit timeline events or remain supporting payroll evidence.

## Next queue

1. After `56-60`, reassess whether the next work is new-family coverage or review/retrieval depth on the accounting corpus.
