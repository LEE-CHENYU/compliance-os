# Data Room Batch 10

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 10 manifest

This batch mixes tax overflow with H-1B employee identity evidence so the next round keeps pressure on both tax continuity and employee-support retrieval.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `w2_2023_tax_folder` | `Tax/2024/Form_W-2_Tax_Year_2023.pdf` | prior-year wage record | `w2` |
| `tda_1042s_2024` | `Tax/2024/TDA - 1042S - 2024_2025-03-12_619.PDF` | alternate withholding statement | `1042s` |
| `year_end_summary_2024` | `Tax/2024/Year-End Summary - 2024_2025-03-07_619.PDF` | annual account summary | `annual_account_summary` |
| `w2_2025_tax_folder` | `Tax/2025/US_W-2_Li_Chenyu_7757869443021865.pdf` | later wage record | `w2` |
| `w4_2024` | `Tax/2025/US_W-4_2024.pdf` | withholding election form | `w4` |
| `account_summary_2025` | `Tax/2025/Account Summaries - 2025_2026-02-21_239.PDF` | annual account summary | `annual_account_summary` |
| `h1b_passport_image` | `H1b Petition/Employee/Passport/IMG_0991大.jpeg` | passport identity page | `passport` |
| `h1b_visa_image` | `H1b Petition/Employee/Passport/visa.jpeg` | visa page support record | `visa_stamp` |
| `h1b_ead_image` | `H1b Petition/Employee/EAD/IMG_0996.jpeg` | employee EAD support image | `ead` |
| `h1b_transcript_pdf` | `H1b Petition/Employee/Transcript/40697019_eTranscript.pdf` | transcript support record | `transcript` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `3/10`
- Strong today:
  - both `w2` files classify correctly
  - the alternate `1042-S` file classifies correctly
- Remaining misses:
  - `annual_account_summary`
  - `w4`
  - `passport`
  - `visa_stamp`
  - `ead` image under generic filename
  - `transcript`

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Tax-overflow and H-1B employee-support files now classify cleanly, including:
  - `annual_account_summary`
  - `w4`
  - passport, visa, EAD, and transcript evidence under generic employee-support filenames

## Validation

- Real-source validator:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 10`
- Loop-compatible logging command:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 10 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
- Current recorded run:
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T083149Z-04`
  - superseded baseline run only
- Current passing validator run:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 10`
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 10 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T155831Z-03`
  - focused tests: `45 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Expand review logic only when these tax-overflow or employee-support families are pulled into a concrete check flow.
