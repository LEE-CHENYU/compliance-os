# Data Room Batch 09

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 09 manifest

This batch is the BSGC archive slice that still sits outside the typed data room even though it contains the governance and EIN paperwork needed for entity review.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `archive_cp575` | `BSGC/Filing/Archive/CP575Notice_1684523211250.pdf` | archived EIN notice | `ein_letter` |
| `ein_request_instructions` | `BSGC/Filing/Archive/EIN Individual Request - Instructions.pdf` | EIN filing instructions | `ein_application_instructions` |
| `ein_request_online_copy_2` | `BSGC/Filing/Archive/EIN Individual Request - Online Application 2.pdf` | archived EIN online application | `ein_application` |
| `operating_agreement_smllc` | `BSGC/Filing/Archive/Wyoming-Single-Member-LLC-Operating-Agreement.pdf` | governance agreement | `operating_agreement` |
| `operating_agreement_template` | `BSGC/Filing/Archive/wyoming-multi-member-llc-operating-agreement-template.pdf` | governance template | `operating_agreement` |
| `consent_archive` | `BSGC/Filing/Consent.pdf` | filing consent record | `registered_agent_consent` |
| `ein_request_online_copy_1` | `BSGC/Filing/EIN Individual Request - Online Application.pdf` | EIN online application | `ein_application` |
| `tax_interview` | `BSGC/Filing/Tax-interview.pdf` | entity tax setup interview | `tax_interview` |
| `tda_form` | `BSGC/TDA1186.pdf` | linked account or bank application record | `bank_account_application` |
| `employment_contract_archive` | `BSGC/lawdepot.com-EMPLOYMENT CONTRACT.pdf` | employment contract archive | `employment_contract` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `3/10`
- Strong today:
  - archived `CP575` EIN notice
  - both archived EIN online application copies
- Remaining misses:
  - EIN instructions
  - both operating-agreement files
  - archived consent
  - tax interview
  - `TDA1186`
  - archived employment contract

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- The archive entity-governance slice now classifies cleanly, including:
  - `ein_application_instructions`
  - `operating_agreement`
  - `registered_agent_consent`
  - `tax_interview`
  - `bank_account_application`
  - `employment_contract`

## Validation

- Real-source validator:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 09`
- Loop-compatible logging command:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 09 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
- Current recorded run:
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T083149Z-02`
  - superseded baseline run only
- Current passing validator run:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 09`
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - `/Users/lichenyu/miniconda3/envs/compliance-os/bin/python scripts/data_room_batch_loop.py --manifest /Users/lichenyu/compliance-os/config/data_room_batches.yaml --batch-number 09 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-06-10`
  - session log: `logs/data-room-batch-loop-round-06-10/20260328T155831Z-01`
  - focused tests: `45 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Add richer extraction normalization for archive governance records if entity review starts consuming them directly.
