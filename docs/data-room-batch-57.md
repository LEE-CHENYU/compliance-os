# Data Room Batch 57

Source folder: `/Users/lichenyu/Desktop/accounting-not-in-important-docs-20260329/files`

## Batch 57 manifest

This batch captures accounting-derived entity and corporate legal packets, including H-1B representation materials and registration drafts that were not part of the original data-room source.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `yangtze_fee_agreement` | `legal/corporate/Fee Agreement - Signed Electronically.pdf` | signed corporate fee agreement | `legal_services_agreement` |
| `yangtze_ein_cancellation` | `legal/corporate/Yangtze Capital 2nd EIN Cancellation Letter.pdf` | entity EIN cancellation notice | `entity_notice` |
| `bsgc_g28_mt_law` | `legal/immigration/bsgc_h1b_g28_mt_law_031026.pdf` | BSGC H-1B G-28 | `h1b_g28` |
| `bsgc_h1b_beneficiary_roster` | `legal/immigration/bsgc_h1b_registration_beneficiaries_031026.csv` | BSGC H-1B beneficiary roster export | `h1b_registration_roster` |
| `bsgc_h1b_registration_draft` | `legal/immigration/bsgc_h1b_registration_draft_031026.pdf` | BSGC H-1B registration draft | `h1b_registration` |
| `h1b_lottery_registration_docx` | `legal/immigration/h1b_2026_lottery_registration.docx` | H-1B lottery registration draft | `h1b_registration` |
| `h1b_legal_services_agreement` | `legal/immigration/h1b_cap_legal_services_agreement.pdf` | H-1B legal-services agreement | `legal_services_agreement` |
| `h1b_legal_services_signed` | `legal/immigration/h1b_cap_legal_services_docusign.pdf` | signed H-1B legal-services agreement | `legal_services_agreement` |
| `hibee_retainer` | `legal/immigration/h1b_retainer_hibee.pdf` | H-1B retainer agreement | `legal_services_agreement` |
| `yangtze_withholding_notice` | `legal/immigration/yangtze_capital_ftb_withholding_notice_022526.pdf` | California withholding notice | `tax_notice` |
| `yangtze_g28_arora_v1` | `legal/immigration/yangtze_h1b_g28_arora_031026.pdf` | Yangtze H-1B G-28 | `h1b_g28` |
| `yangtze_g28_arora_v2` | `legal/immigration/yangtze_h1b_g28_arora_031226.pdf` | Yangtze H-1B G-28 revision | `h1b_g28` |
| `yangtze_h1b_beneficiary_roster` | `legal/immigration/yangtze_h1b_registration_beneficiaries_031026.csv` | Yangtze H-1B beneficiary roster export | `h1b_registration_roster` |
| `yangtze_h1b_registration_draft_v1` | `legal/immigration/yangtze_h1b_registration_draft_031026.pdf` | Yangtze H-1B registration draft | `h1b_registration` |
| `yangtze_h1b_registration_draft_v2` | `legal/immigration/yangtze_h1b_registration_draft_031226.pdf` | Yangtze H-1B registration draft revision | `h1b_registration` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `6/15`
- Already matched on the first validator pass:
  - `h1b_g28`
  - `h1b_registration` draft PDFs
- Missed or misrouted families on the first pass:
  - `legal_services_agreement` was unsupported for fee agreements and retainer packets
  - `entity_notice` was unsupported for the EIN cancellation letter
  - `tax_notice` was unsupported for the FTB withholding notice
  - beneficiary-roster CSVs were collapsing into `h1b_registration`
  - `h1b_2026_lottery_registration.docx` was misread as `identity_document`
  - the old `h1b_registration` filename shortcut was too loose and caught non-registration `h1b_r*` files

## Post-fix result

- Current fast-path match rate against intended doc types: `15/15`
- New accounting/legal families now exist as first-class types:
  - `legal_services_agreement`
  - `entity_notice`
  - `tax_notice`
  - `h1b_registration_roster`
- `h1b_registration` filename matching is tightened so retainer/legal-service packets no longer collide with actual registration drafts.
- The H-1B lottery DOCX now classifies into `h1b_registration` instead of `identity_document`.
- Minimal structured extraction schemas and lineage support now exist for the new legal and roster families.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 57`
  - Result: `15/15`
- Focused regression suite:
  - `conda run -n compliance-os pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_data_room_batch_loop.py tests/test_checks_router_v2.py -q`
  - Result: `132 passed`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 57 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-56-60`
  - Passing session:
    - `logs/data-room-batch-loop-round-56-60/20260329T175831Z`

## Current batch blockers

None.

## Next queue

1. Batch 58: CIAM, school, and immigration support
2. Batch 59: H-1B intake worksheets and counsel forms
3. Batch 60: payroll, tax-support, and standalone forms
