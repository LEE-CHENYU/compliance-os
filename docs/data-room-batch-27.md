# Data Room Batch 27

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 27 manifest

This batch closes the remaining straightforward employment continuity anchors: late paystubs, employer letters, E-Verify evidence, a bank record, and H-1B filing-fee receipts.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `vcv_paystub_20241106_2` | `employment/VCV/paystubs_2024/Paystub20241106-2.pdf` | late 2024 VCV paystub | `paystub` |
| `vcv_paystub_20241108` | `employment/VCV/paystubs_2024/Paystub20241108.pdf` | late 2024 VCV paystub | `paystub` |
| `vcv_paystub_20241122_1` | `employment/VCV/paystubs_2024/Paystub20241122-1.pdf` | late 2024 VCV paystub | `paystub` |
| `vcv_paystub_20241122_2` | `employment/VCV/paystubs_2024/Paystub20241122-2.pdf` | late 2024 VCV paystub | `paystub` |
| `clinipulse_offer_letter` | `employment/CliniPulse/Offer Letter.pdf` | CliniPulse employment offer | `employment_letter` |
| `yangtze_employment_letter` | `employment/Yangtze Capital/Employment_Letter_Li_Chenyu.pdf` | Yangtze employment letter | `employment_letter` |
| `bitsync_everify_email` | `employment/Bitsync/Gmail - Urgent_ E-Verify Information Required.pdf` | E-Verify follow-up evidence | `e_verify_case` |
| `wolff_current_view_csv` | `employment/Wolff & Li/CHK_6544_CURRENT_VIEW.csv` | bank current-view record | `bank_statement` |
| `h1b_fee_receipt_44620897` | `legal/Transaction #44620897.pdf` | H-1B filing-fee receipt | `h1b_filing_fee_receipt` |
| `h1b_fee_receipt_45359451` | `legal/Transaction #45359451.pdf` | H-1B filing-fee receipt | `h1b_filing_fee_receipt` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `10/10`
- No new intake gap surfaced in this slice. The remaining payroll, employer-letter, bank, and filing-fee anchors already fit the current contract cleanly.

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- No batch-specific code changes were required. This slice now stands as a validated continuity anchor batch.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 27`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 27 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-26-30`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-26-30/20260328T215409Z-03`
  - focused tests: `54 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Keep payroll and filing-fee continuity in typed storage unless review rules later need direct cross-checking against offer and onboarding records.
