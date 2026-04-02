# Data Room Batch 29

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 29 manifest

This batch captures the remaining support artifacts around identity, payroll tax proof, residence, CPT administration, and filing confirmations so these records are not left as opaque uploads.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `mom_id_front_image` | `Mom ID/Weixin Image_20260209181329_349_168.jpg` | family identity support image | `identity_document` |
| `mom_id_back_image` | `Mom ID/Weixin Image_20260209181436_350_168.jpg` | family identity support image | `identity_document` |
| `mom_id_pdf_scan` | `Mom ID/dy1OZSrN3UWLhn-27SRSWg.pdf` | family identity support scan | `identity_document` |
| `uscis_backup_codes_qq` | `i20/I20/2fa_backup_code_USCIS_myAccount_qq.pdf` | USCIS account backup codes | `recovery_codes` |
| `w2_form_2024` | `W2/Form_W-2_Tax_Year_2024.pdf` | 2024 W-2 tax proof | `w2` |
| `w2_us_2024` | `W2/US_W-2_Li_Chenyu_7757869443021865.pdf` | 2024 W-2 tax proof | `w2` |
| `berkeley_family_housing_lease` | `Lease/Fang, Yuchen_293947.pdf` | Berkeley family housing lease | `lease` |
| `icdata_paper_modification_confirmation` | `ICDATAx2725 Confirmation of paper modification 7.pdf` | conference system modification confirmation | `filing_confirmation` |
| `ciam_cpt_application` | `employment/Yangtze Capital/CIAM_CPT_App_Li_Chenyu.pdf` | CIAM CPT course application | `cpt_application` |
| `bitsync_stem_opt_compliance_email` | `employment/Bitsync/Gmail - Urgent_ Compliance with STEM OPT Requirements.pdf` | STEM OPT compliance escalation email | `support_request` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `6/10`
- Surfaced gaps:
  - Berkeley family housing lease was unsupported on the fast path
  - the ICDATA paper-modification confirmation was unsupported on the fast path
  - the CIAM CPT course form was unsupported on the fast path
  - the Bitsync STEM OPT compliance email was unsupported on the fast path

## Post-fix result

- Current fast-path match rate against intended doc types: `10/10`
- Identity, tax, residence, CPT, and filing-confirmation support artifacts now classify cleanly under typed families instead of staying opaque.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 29`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 29 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-26-30`
- Current passing validator run:
  - result: real-source checks passed for `10/10` manifest files
- Current passing loop assessment:
  - session log: `logs/data-room-batch-loop-round-26-30/20260328T215409Z`
  - focused tests: `54 passed`
  - real-source checks: `10/10`
  - batch state: `resolved: true`

## Current batch blockers

None.

## Next queue

1. Decide later whether CPT course forms should stay in the student-admin path or become part of employment review when a check needs CPT authorization evidence.
