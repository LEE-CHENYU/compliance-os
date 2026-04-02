# Data Room Batch 54

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 54 manifest

This batch captures the DOCX cover-letter and employer-support slice that previously failed the fast path because cover letters were not a first-class family and one employer-assistance letter stayed unresolved.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `cover_letter_blackrock` | `CV & Cover Letters/CV230217/CL_sample/Chenyu Li Cover Letter - BlackRock.docx` | role-specific cover letter | `cover_letter` |
| `cover_letter_citi` | `CV & Cover Letters/CV230217/CL_sample/Chenyu Li Cover Letter - Citi.docx` | role-specific cover letter | `cover_letter` |
| `cover_letter_deutsche_bank` | `CV & Cover Letters/CV230217/CL_sample/Chenyu Li Cover Letter - Deutsche Bank.docx` | role-specific cover letter | `cover_letter` |
| `cover_letter_hebbia` | `CV & Cover Letters/CV260325/cover_letters/Hebbia - Solutions Engineer - Cover Letter.docx` | role-specific cover letter | `cover_letter` |
| `cover_letter_temasek` | `CV & Cover Letters/Chenyu Li Cover Letter - Temask.docx` | role-specific cover letter | `cover_letter` |
| `cover_letter_unops` | `CV & Cover Letters/Chenyu Li Cover Letter - UNOPS.docx` | role-specific cover letter | `cover_letter` |
| `cover_letter_world_bank` | `CV & Cover Letters/Chenyu Li Cover Letter - World Bank.docx` | role-specific cover letter | `cover_letter` |
| `employment_contract_bd_manager` | `BSGC/Contract of Employment - BD Manager.docx` | company employment agreement | `employment_contract` |
| `employment_offer_clinipulse` | `employment/CliniPulse/offer_letter/employment_offer.docx` | employment offer letter | `employment_letter` |
| `employment_letter_vcv_full_time` | `stem opt/letter/Employer Letter_VCV_Full Time.docx` | STEM OPT employer letter | `employment_letter` |
| `support_request_employer_assistance` | `stem opt/request/Issues Requiring Employer Assistance & Support.docx` | employer assistance request letter | `support_request` |
| `support_request_employment_immigration` | `stem opt/request/Requests for Employment and Immigration Support& Support.docx` | employment and immigration support request | `support_request` |

## Baseline current-state result

- Prior to this pass, cover letters were unresolved or misread as `resume`, and `Issues Requiring Employer Assistance & Support.docx` stayed unresolved on the fast path.
- `Contract of Employment - BD Manager.docx` also lacked a strong enough filename anchor for `employment_contract`.

## Post-fix result

- Current fast-path match rate against intended doc types: `12/12`
- Cover letters now land in a dedicated `cover_letter` family.
- The employer-assistance request and the BSGC employment agreement now classify correctly without corpus-specific filename hacks.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 54`
  - Result: `12/12`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 54 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-51-55`
  - Passing session:
    - `logs/data-room-batch-loop-round-51-55/20260328T235244Z-01`
- Focused regression suite:
  - `conda run -n compliance-os pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_checks_router_v2.py -q`
  - Result: `106 passed`
- Batch state:
  - `resolved: true`

## Current batch blockers

None.

## Next queue

1. Close the DOCX work-sample and H-1B worksheet slice in Batch `55`.
