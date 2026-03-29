# Data Room Batch 59

Source folder: `/Users/lichenyu/Desktop/accounting-not-in-important-docs-20260329/files`

## Batch 59 manifest

This batch covers H-1B intake worksheets, counsel packets, and filing invoices from the accounting corpus and staging areas.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `arora_datasheet_filled` | `outgoing/h1b_arora_021326/Data Sheet for H1B Electronic Registration 2026 - FILLED.docx` | filled H-1B registration data sheet | `h1b_registration_worksheet` |
| `arora_datasheet_blank` | `outgoing/h1b_arora_021326/Data Sheet for H1B Electronic Registration 2026.docx` | blank H-1B registration data sheet | `h1b_registration_worksheet` |
| `arora_worksheet_blank` | `outgoing/h1b_arora_021326/Data_Sheet_H1B_Registration_2026_BLANK.docx` | blank H-1B registration worksheet | `h1b_registration_worksheet` |
| `arora_worksheet_bsgc_filled` | `outgoing/h1b_arora_021326/Data_Sheet_H1B_Registration_2026_BSGC_FILLED.docx` | filled BSGC H-1B worksheet | `h1b_registration_worksheet` |
| `arora_employer_sheet_filled` | `outgoing/h1b_arora_021326/Employer Data Sheet for H1B or H1B1 Petition - FILLED.docx` | filled employer H-1B data sheet | `h1b_registration_worksheet` |
| `arora_employer_sheet_blank` | `outgoing/h1b_arora_021326/Employer Data Sheet for H1B or H1B1 Petition.docx` | blank employer H-1B data sheet | `h1b_registration_worksheet` |
| `murthy_capreg_packet` | `outgoing/murthy_law/H1BcoCapReg_PS_FY27.pdf` | Murthy cap-registration packet | `h1b_registration_worksheet` |
| `murthy_intake_packet` | `outgoing/murthy_law/H1BcoII_PS.pdf` | Murthy H-1B intake packet | `h1b_registration_worksheet` |
| `wolf_group_fee_schedule` | `outgoing/wolf_group/2025_welcome_letter_fee_schedule.pdf` | law-firm fee schedule and welcome packet | `fee_schedule_notice` |
| `tmp_datasheet_blank` | `tmp/Data Sheet for H1B Electronic Registration 2026.docx` | staged H-1B registration data sheet | `h1b_registration_worksheet` |
| `tmp_datasheet_yangtze_filled` | `tmp/Data_Sheet_H1B_Registration_2026_Yangtze_FILLED.docx` | staged Yangtze H-1B data sheet | `h1b_registration_worksheet` |
| `tmp_bsgc_part1_worksheet` | `tmp/H-1B Part I_Registration Worksheet_BSGC_FILLED.docx` | staged BSGC H-1B worksheet | `h1b_registration_worksheet` |
| `tmp_employee_part1_worksheet` | `tmp/H-1B Part I_Registration Worksheet_Employee_BSGC_FILLED.docx` | staged employee H-1B worksheet | `h1b_registration_worksheet` |
| `tmp_invoice_due` | `tmp/Invoice_Part I_LI, Chenyu_due.pdf` | H-1B filing invoice due notice | `h1b_filing_invoice` |
| `tmp_invoice_paid` | `tmp/Invoice_Part I_LI, Chenyu_paid.pdf` | H-1B filing invoice paid receipt | `h1b_filing_invoice` |

## Baseline current-state result

Pending first validation.

## Current batch blockers

- Confirm current coverage for fee schedules and whether they warrant a dedicated `fee_schedule_notice` family.
- Check whether all worksheet and data-sheet variants can live under `h1b_registration_worksheet` without losing useful distinctions.

## Next queue

1. Batch 60: payroll, tax-support, and standalone forms
