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

## Legacy intake convergence rerun

The legacy case upload route (`/api/cases/{case_id}/documents`) now writes into the
v2 store with the same core intake semantics used by v2 check uploads:

- optional `doc_type` and `source_path` are accepted on upload
- mirrored v2 rows now persist canonical `source_path` instead of UUID destination paths
- lineage registration uses canonical source paths, so series/version behavior no longer drifts by route
- legacy classification edits and deletes now update and reindex mirrored v2 lineage metadata
- focused regression test for this bridge path now passes (`pytest tests/test_documents_router.py -q`: `13 passed`)

## OCR intake precision hardening

To reduce false positives on unsupported uploads that only reference identity/tax identifiers,
OCR fallback classification is now stricter for high-risk doc families:

- `i94` now requires a stronger OCR score plus an `Arrival/Departure Record` anchor
- `passport` now requires a stronger OCR score to avoid classifying casual passport mentions
- `ein_letter` now requires a stronger OCR score plus a `CP 575` anchor

Focused regression coverage added in `tests/test_classifier_service.py`:

- incidental OCR references to `I-94`/passport/EIN no longer force classification
- true OCR-like `i94` and `ein_letter` text still classifies
- focused test result: `19 passed`

## Current batch blockers

None. Batch 01 is resolved on its own scope: STEM OPT and entity core records classify, extract, review, and validate cleanly across the legacy bridge and the v2 store.

## Deferred backlog

These items are real backlog, but they are not Batch 01 blockers and should not keep the loop on Batch 01:

1. Unsupported-document false-positive hardening belongs to later unsupported-family coverage work, not the now-resolved Batch 01 manifest.
2. Same-type family identity for leases and annual `1042-S` forms was a Batch 02 modeling issue and is tracked there.
3. Embedding-based retrieval remains a platform enhancement, but Batch 01 validation does not depend on it.
4. Additional support for company formation docs, leases, insurance/medical records, and `1042-S` is Batch 02 scope and is no longer part of Batch 01.

## Next queue

1. Batch 02 is already complete and should stay out of the blocking path for Batch 01.
2. The next unresolved batch is Batch 03 on payroll, `I-9` / E-Verify, `I-765`, and H-1B support records.
3. Retrieval upgrades and other platform work should stay in deferred backlog unless a batch validation hook depends on them.
