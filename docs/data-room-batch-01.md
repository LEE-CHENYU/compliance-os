# Data Room Batch 01

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 01 manifest

First pass used 10 representative files across immigration, employment, tax, and entity records.

| Label | File | Intended use | Data room classification result |
| --- | --- | --- | --- |
| `i983_current` | `stem opt/i983/vcv/Chenyu_i983 Form_100124_ink_signed.pdf` | STEM OPT training plan | unclassified |
| `offer_clinipulse` | `employment/CliniPulse/chenyu_offer_signed.pdf` | employment letter | unclassified |
| `offer_bitsync` | `employment/Bitsync/signed offer letter bitsync.pdf` | prior employment letter | unclassified |
| `i20_stemopt` | `i20/cu_stemopt_23_signed.pdf` | I-20 | unclassified |
| `i94_recent` | `H1b Petition/Employee/I-94/I-94 Official Website - Get Most Recent I-94 Response.pdf` | I-94 | `i94` |
| `tax_2024` | `Tax/2024/2024_TaxReturn.pdf` | tax return | `1040` |
| `tax_2023` | `Tax/2023/2023_TaxReturn.pdf` | tax return | `1040` |
| `ein_cp575` | `BSGC/Filing/CP575Notice_1686945041312.pdf` | EIN letter | `ein_letter` |
| `w2_2024` | `Tax/2024/Form_W-2_Tax_Year_2024.pdf` | W-2 | `w2` |
| `ead_opt` | `Personal Info Archive/EAD (OPT).jpeg` | EAD card | unclassified |

## Batch 01 extraction results

### STEM OPT check

Uploaded docs:
- `i983_current`
- `offer_clinipulse`
- `i20_stemopt`
- `i94_recent`
- `ead_opt`

Observed after OCR adapter fix:
- `i983` extracted strongly: student, SEVIS, school, employer, work site, title, start date, compensation, duties, supervisor.
- `employment_letter` extracted strongly.
- `i20` extracted strongly for student/program/travel signature fields.
- `i94` and `ead` stored successfully but extracted nothing because no schema exists yet.

Cross-check results:
- `mismatch`: employer name, job title, start date, supervisor
- `match`: compensation, full-time
- `needs_review`: work location, duties

Findings generated:
- employer mismatch
- job title mismatch
- location mismatch
- start date mismatch
- I-983 12-month evaluation due

### Entity check

Uploaded docs:
- `tax_2024`
- `ein_cp575`
- `w2_2024`

Observed:
- `tax_return` extracted strongly: `1040`, tax year `2024`, filing status `Single`, total income `67068`, schedules `B/C/D`, no `5472`, no `3520`, no `8938`, state return `NY`.
- `ein_letter` and `w2` stored successfully but extracted nothing because no schema exists yet.

Cross-check results:
- `mismatch`: `form_5472`, `form_type`
- `match`: `entity_type` currently reports a match, but this is logic debt in review code rather than a trustworthy result

Findings generated:
- missing `5472`
- foreign capital transfer without documentation
- wrong form type (`1040` vs expected `1040-NR`)
- filing-required advisory set

## Retry after fixes

After fixing the OCR adapter, broadening classifier coverage, adding schemas for the unsupported Batch 01 document families, and tightening entity review logic, the same current batch was rerun.

### Data room classification retry

- `10/10` files classified successfully.
- New classifications now working on the same source files:
  - `i983_current` -> `i983`
  - `offer_clinipulse` -> `employment_letter`
  - `offer_bitsync` -> `employment_letter`
  - `i20_stemopt` -> `i20`
  - `ead_opt` -> `ead`
  - `tax_2024` / `tax_2023` now normalize to `tax_return` instead of `1040`

### STEM retry

New extraction coverage on the same uploaded set:
- `i94` now extracts `admission_number`, `most_recent_entry_date`, `class_of_admission`, `admit_until_date`
- `ead` now extracts `card_number`, `uscis_number`, `category`, `card_expires_on`, `date_of_birth`, `full_name`

The main STEM mismatches remain real and consistent with the documents:
- employer name
- job title
- start date
- supervisor

### Entity retry

New extraction coverage on the same uploaded set:
- `ein_letter` now extracts entity name, EIN, assigned date, and business address
- `w2` now extracts employee name, employer name, EIN, wages, withholding, and state

The entity comparison was corrected:
- `entity_type` is now `needs_review` for foreign-owned `smllc` + `1040`
- it is no longer reported as a clean `match`

## Lineage regression and final rerun

When the versioned retrieval layer landed, one regression surfaced on a full rerun of the same Batch 01 files: `i983`, `employment_letter`, and `ead` were incorrectly chained into one `document_family`. That made retrieval prefer the EAD as the active document for the whole family and pushed the I-983 and offer letters into history, which was incorrect.

Fix applied:
- storage lineage is now scoped to `doc_type`
- existing `documents_v2` rows are repaired on startup so previously written bad chains are normalized

Final rerun on the same Batch 01 source files:
- `10/10` files classified correctly
- STEM families normalized correctly:
  - `i983` -> active v1
  - `employment_letter` -> `signed offer letter bitsync.pdf` v1 inactive, `chenyu_offer_signed.pdf` v2 active
  - `i20` -> active v1
  - `i94` -> active v1
  - `ead` -> active v1
- Entity families normalized correctly:
  - `tax_return` -> `2023_TaxReturn.pdf` v1 inactive, `2024_TaxReturn.pdf` v2 active
  - `ein_letter` -> active v1
  - `w2` -> active v1

Cross-check results stayed stable after the repair:
- STEM mismatches remained real: employer name, job title, start date, supervisor
- STEM matches remained stable: compensation, full-time
- Entity remained: `entity_type=needs_review`, `form_5472=mismatch`, `form_type=mismatch`

## Validation and deploy

Validation run after the lineage repair:
- `conda run -n compliance-os pytest tests/test_checks_router_v2.py tests/test_extractor.py tests/test_auth.py`
- result: `32 passed`

Deployment status:
- deployed to Fly after the clean rerun
- live health checks passed on `guardian-compliance.fly.dev` and `guardiancompliance.app`

## Remaining gaps

1. The v1 case/data-room intake path is still separate from the v2 versioned document store, so classification quality and storage semantics differ across the two paths.
2. Intake classification on unsupported documents is still weak and can produce false positives after OCR, especially when unrelated forms mention `I-94`, passport, or EIN-like text.
3. Family identity is still too coarse for recurring or parallel documents of the same type; `doc_type` alone is not enough to distinguish separate leases or annual tax forms.
4. Retrieval is version-aware and OCR-backed now, but it is still lexical over OCR text and extracted fields rather than embedding-based.
5. Unsupported but high-value families remain outside the current schema set: company formation docs, leases, insurance/medical records, `1042-S`, and other business support records.

## Next queue

1. Batch 02 is now complete; the next modeling task is replacing raw `doc_type` lineage with a more precise family key for recurring documents and parallel documents of the same type.
2. Keep the v1 intake classifier aligned with the v2 document flow so uploads do not drift by route again.
3. Validate and normalize field extraction on dense financial forms, starting with `1042-S`.
4. Add semantic retrieval on top of persisted OCR text and field snippets after the document-family model is stable.
5. Continue into Batch 03 on payroll, `I-9` / E-Verify, `I-765`, and H-1B support records.
