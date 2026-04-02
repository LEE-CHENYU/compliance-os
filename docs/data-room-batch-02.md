# Data Room Batch 02

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Inventory snapshot

Folder snapshot used for batching:
- total files excluding `.DS_Store` and `Thumbs.db`: `585`
- directly ingestible by the current v1 data-room upload path (`pdf/png/jpg/jpeg/csv/txt`): `483`
- largest top-level buckets:
  - `employment`: `240`
  - `CV & Cover Letters`: `107`
  - `stem opt`: `54`
  - `[root]`: `34`
  - `H1b Petition`: `25`
  - `BSGC`: `23`
  - `i20`: `20`
  - `Tax`: `16`

Batch status after this run:
- Batch 01: core STEM OPT and entity docs, completed
- Batch 02: formation, lease, insurance/medical, `1042-S`, and passport control, completed

## Batch 02 manifest

This batch targeted the next unsupported but high-signal document families plus one supported control document.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `articles_org` | `BSGC/Filing/Articles of Organization.pdf` | Wyoming LLC formation filing | `articles_of_organization` |
| `good_standing` | `BSGC/Filing/CertOfGoodStanding.pdf` | Certificate of good standing | `certificate_of_good_standing` |
| `registered_agent_consent` | `BSGC/Filing/Consent to Appointment by Registered Agent.pdf` | Registered agent consent form | `registered_agent_consent` |
| `lease_master` | `Lease/Complete_with_DocuSign_Standard_Lease_-_The_.pdf` | Primary residential lease | `lease` |
| `lease_sublease` | `Lease/sublease agreement.pdf` | Sublease agreement | `lease` |
| `nomad_insurance` | `Medical/Nomad Insurance.pdf` | Travel/health insurance card | `insurance_policy` |
| `covered_ca_application` | `Medical/CA.pdf` | Covered California health application | `health_coverage_application` |
| `1042s_2024` | `Tax/2024/1042S - 2024_2025-03-15_619.PDF` | `1042-S` for tax year 2024 | `1042s` |
| `1042s_2025` | `Tax/2025/1042S - 2025_2026-03-10_619.PDF` | `1042-S` for tax year 2025 | `1042s` |
| `passport_control` | `passport.jpeg` | Passport identity page control document | `passport` |

## Data room intake results

The old v1 case/data-room intake path stored all 10 files, but classification quality was poor outside the already-supported families.

Classification results:
- `articles_of_organization` -> unclassified
- `certificate_of_good_standing` -> unclassified
- `registered_agent_consent` -> unclassified
- `lease` (`Complete_with_DocuSign_Standard_Lease_-_The_.pdf`) -> incorrectly classified as `ein_letter`
- `lease` (`sublease agreement.pdf`) -> unclassified
- `insurance_policy` -> unclassified
- `health_coverage_application` (`CA.pdf`) -> incorrectly classified as `i94`
- `1042s` 2024 -> incorrectly classified as `ead`
- `1042s` 2025 -> incorrectly classified as `ead`
- `passport` -> correctly classified as `passport`

Net result:
- correct classifications: `1/10`
- false positives: `4/10`
- unclassified: `5/10`

Operational note:
- this intake path is also slow for unsupported documents because upload and OCR-backed classification are synchronous
- this 10-file run took roughly `2.5` minutes on the v1 path before extraction even started

## Post-fix intake rerun

After tightening the classifier and removing full OCR from the v1 upload critical path, the same Batch 02 intake set was rerun through the live `/api/cases/{case_id}/documents` path.

Post-fix result:
- `10/10` classified correctly
- `0` false positives
- total upload + classification time for the same 10-file batch: about `0.09s`

Correct classifications after the fix:
- `Articles of Organization.pdf` -> `articles_of_organization`
- `CertOfGoodStanding.pdf` -> `certificate_of_good_standing`
- `Consent to Appointment by Registered Agent.pdf` -> `registered_agent_consent`
- both lease docs -> `lease`
- `Nomad Insurance.pdf` -> `insurance_policy`
- `CA.pdf` -> `health_coverage_application`
- both `1042-S` docs -> `1042s`
- `passport.jpeg` -> `passport`

## V2 storage and extraction results

The v2 versioned document store handled all 10 uploads correctly and persisted OCR/provenance for every document.

Observed results:
- `10/10` documents stored successfully with `source_path`, `content_hash`, OCR provenance, and retrieval-ready text
- OCR engine was `mistral_ocr` for all 10 documents
- structured extraction coverage:
  - `passport` extracted successfully with 6 fields: full name, passport number, country of issue, date of birth, issue date, expiration date
  - the other 9 document types extracted `0` structured fields because no schema exists yet for those families

Control result:
- the passport image validated that the OCR + structured extraction path still works on non-PDF identity documents

## Post-fix schema rerun

After adding extraction schemas for the Batch 02 families, the same v2 check flow was rerun.

New structured extraction coverage:
- `articles_of_organization` extracted `8` populated fields:
  - entity name, filing state/date, entity ID, registered agent, registered agent address, mailing address, principal office address
- `certificate_of_good_standing` extracted `7` populated fields:
  - entity name, jurisdiction, entity type, formation date, entity ID, standing status, duration
- `registered_agent_consent` extracted `6` populated fields:
  - entity name, registered agent, registered office address, consent date, signer name, signer title
- `lease` docs extracted real lease fields:
  - master lease: landlord, tenant list, property address, start/end dates, rent, deposit
  - sublease: lease type, property address, start/end dates, rent, deposit
- `insurance_policy` extracted `5` populated fields:
  - carrier, insured name, membership ID, start date, support phone
- `health_coverage_application` extracted `10` populated fields:
  - applicant name, application date, phone, email, address, county, subsidy requested
- both `1042-S` docs extracted `9` populated fields:
  - tax year, recipient name/address, account number, date of birth, income code, gross income, tax withheld, withholding agent
- `passport` remained strong with `6` populated fields

Net result:
- all `10/10` Batch 02 documents now produce structured fields on the v2 path

Follow-up validation was still required at this point for:
- within-type family over-grouping (`lease`, `1042s`)
- numeric/date-heavy `1042-S` field normalization

## Retrieval and family behavior

### Retrieval quality

Retrieval over OCR text worked well even without structured schemas.

Representative query hits:
- formation query -> `Articles of Organization.pdf`, then `Consent to Appointment by Registered Agent.pdf`
- good standing query -> `CertOfGoodStanding.pdf` as top hit
- lease query -> master lease and sublease were the top two hits
- insurance query -> `Nomad Insurance.pdf`, then `CA.pdf`
- `1042-S` query -> 2025 form, then 2024 form
- passport query -> `passport.jpeg` as top hit

Conclusion:
- OCR persistence + lexical retrieval are already useful for unsupported documents
- the main missing layer is schema coverage, not raw text availability

### Family/version behavior

The initial rerun exposed a real modeling issue:
- both lease documents were treated as one `lease` version chain
- both `1042-S` documents were treated as one `1042s` version chain

That behavior was internally consistent with the old `doc_type`-scoped lineage model, but it was semantically wrong for:
- parallel documents of the same type but different subject matter
- recurring annual documents that should be grouped by series or period, not blindly superseded

After adding `document_series_key` and rerunning the same live API flow on the target documents, family behavior matched the intended semantics:
- `Complete_with_DocuSign_Standard_Lease_-_The_.pdf` -> `lease:lease:complete-with-docusign-standard-lease-the`, `v1`, active, no prior versions
- `sublease agreement.pdf` -> `lease:sublease:sublease-agreement`, `v1`, active, no prior versions
- `1042S - 2024_2025-03-15_619.PDF` -> `1042s:2024`, `v1`, active, no prior versions
- `1042S - 2025_2026-03-10_619.PDF` -> `1042s:2025`, `v1`, active, no prior versions

Retrieval context also reflected the new grouping correctly:
- both lease series were returned as distinct active families
- both annual `1042-S` forms were returned as distinct active families

### Post-fix normalization rerun

The same live rerun confirmed that the targeted `1042-S` normalization fix worked on the real 2024 document:
- `1042S - 2024_2025-03-15_619.PDF` now stores `date_of_birth = 1998-09-18`
- both yearly forms now store `recipient_account_number = 7689-2619`
- both yearly forms now store canonical currency strings:
  - `gross_income = 3.00`
  - `federal_tax_withheld = 5.00` on 2024, `0.00` on 2025
- the yearly split remains intact after extraction, not just on upload

## Findings

1. The v1 case upload path, the v2 check upload path, and the dashboard data-room upload path now share the same intake policy for file validation, doc-type normalization, and auto-detection when `doc_type` is omitted.
2. OCR/provenance persistence is working as intended on the v2 path, and the new schemas turned these documents from retrieval-only evidence into structured records.
3. `document_series_key` fixes the immediate lineage problem for parallel leases and annual `1042-S` forms, and retrieval now exposes the correct family boundaries to the LLM context layer.
4. The `1042-S` normalization pass is now verified on the real yearly forms: birthdate, account number, and currency fields are being stored consistently.

## Task queue

1. Expand series-key heuristics beyond the current lease and `1042-S` cases as more recurring document families appear in later batches.
2. Add broader normalization coverage for other dense financial and payroll forms as they enter later batches.
3. Keep `passport` as a regression control in future batches because it exercises image OCR plus structured extraction.
4. Move into Batch 03 on payroll, `I-9` / E-Verify, `I-765`, and H-1B support records.

## Proposed Batch 03

Next high-value batch after these fixes:
- paystubs and payroll records
- `I-9` / E-Verify evidence
- `I-765` filings and notices
- `W-9` / EIN application / entity setup support docs
- H-1B registration and petition support documents
