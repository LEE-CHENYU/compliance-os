# Data Room Batch 03

Source folder: `/Users/lichenyu/Desktop/Important Docs `

## Batch 03 manifest

This batch shifts from Batch 02 formation and housing records into payroll, employment verification, work authorization filings, and H-1B registration support.

| Label | File | Intended use | Current classification result |
| --- | --- | --- | --- |
| `paystub_vcv_20240112` | `employment/VCV/paystubs_2024/Paystub20240112.pdf` | payroll record / paystub | `paystub` |
| `paystub_vcv_20241206` | `employment/VCV/paystubs_2024/Paystub20241206.pdf` | payroll record / paystub | `paystub` |
| `paystub_claudius_20250225` | `employment/Claudius/claudius paytubs/chenyu-li-paystub-2025-02-25.pdf` | payroll record / paystub | `paystub` |
| `i9_vcv` | `employment/VCV/I9.pdf` | Form I-9 employment eligibility verification | `i9` |
| `everify_wolff` | `employment/Wolff & Li/E-Verify Case Processing_ View_Print Details.pdf` | E-Verify case record | `e_verify_case` |
| `i9_wolff` | `employment/Wolff & Li/wolff-li-capital-i-9-signed.pdf` | signed Form I-9 | `i9` |
| `i765_stem` | `i765/I-765-stem opt.pdf` | STEM OPT work authorization filing | `i765` |
| `i765_opt` | `i765/I-765-opt.pdf` | OPT work authorization filing | `i765` |
| `h1b_status_overview` | `H1b Petition/FY 2026 H-1B Status Overview_for employee_Cindy-1.pdf` | H-1B status summary / process overview | unclassified |
| `h1b_registration` | `H1b Petition/Employer/H-1BR (1).pdf` | USCIS H-1B registration record | `h1b_registration` |

## Baseline before support

Before expanding the classifier and schema set for this batch, the same 10-file Batch 03 manifest was a complete miss on the current fast intake path:

- `0/10` classified
- unsupported families included payroll, `I-9`, E-Verify, `I-765`, and H-1B registration

## Post-fix intake result

After adding the new Batch 03 families and sharing intake semantics across the v1 case flow, the v2 check flow, and the dashboard upload path:

- `9/10` files classify correctly on the fast path
- all supported files classify directly from filename without requiring full OCR
- the remaining unsupported file is the H-1B status-summary document, which is not itself the primary filing artifact

Newly supported document families:

- `paystub`
- `i9`
- `e_verify_case`
- `i765`
- `h1b_registration`

## OCR spot checks used for pattern design

Representative OCR/text reads on the real source documents confirmed the family boundaries:

- paystub sample contains `Pay Period Start`, `Pay Period End`, `Pay Date`, and payroll amounts
- `I-9` sample contains `Employment Eligibility Verification` and `Form I-9`
- E-Verify sample contains `E-Verify Case Number`, company information, employee information, and first day of employment
- `I-765` sample contains `Application For Employment Authorization` and `USCIS Form I-765`
- H-1B registration sample contains `USCIS H-1B Registration` and the employer registration details

## Modeling updates

Batch 03 introduced the first payroll-specific lineage rule:

- `paystub` now uses a series key scoped by employer plus pay-period end date when that data is available
- this avoids collapsing unrelated paystubs into one active/prior chain once extraction is run

Follow-up lineage rules were added after the first real extraction pass exposed over-grouping:

- `i9` now uses employer-aware series keys, falling back to source-path context when the form itself does not expose the employer cleanly
- `i765` now uses eligibility-category-aware series keys so `C03B` and `C03C` filings do not supersede each other

## Real Anthropic extraction result

After switching the extraction runtime to the same Anthropic provider path used by the cloud deployment, the supported Batch 03 documents were rerun through the live local API.

- `9/9` supported documents uploaded, OCRed, and structurally extracted successfully
- paystubs remained independent records with stable series keys:
  - `paystub:justworks-employment-group-llc:2024-01-15`
  - `paystub:justworks-employment-group-llc:2024-11-30`
  - `paystub:claudius-legal-intelligence-inc:2025-02-28`
- the two `I-9` documents now stay separated correctly:
  - `employment/VCV/I9.pdf` -> `i9:vcv`
  - `employment/Wolff & Li/wolff-li-capital-i-9-signed.pdf` -> `i9:wolff-li`
- the two `I-765` documents now stay separated correctly:
  - `i765/I-765-stem opt.pdf` -> `i765:c03c`
  - `i765/I-765-opt.pdf` -> `i765:c03b`
- E-Verify extracted useful structured fields, including:
  - `case_number=2025079225618BC`
  - `case_status=Employment Authorized`
- H-1B registration extracted useful employer metadata:
  - `employer_name=Bamboo Shoot Growth Capital LLC`
  - `employer_ein=93-1924106`
  - `authorized_individual_name=Chenyu Li`
  - `registration_number` is still null on the current document

## Batch 03 outcome

The supported Batch 03 families are now in a materially usable state for the data room:

- intake classification: `9/10` on the batch manifest
- real extraction: `9/9` on the supported subset
- lineage: no regression after the series-key fixes for `I-9` and `I-765`
- remaining unsupported file: `H1b Petition/FY 2026 H-1B Status Overview_for employee_Cindy-1.pdf`

## Validation

Validation run after the Anthropic extraction pass and series-key fixes:

- `/Users/lichenyu/miniconda3/envs/compliance-os/bin/pytest tests/test_checks_router_v2.py tests/test_extractor.py tests/test_classifier_service.py tests/test_documents_router.py tests/test_dashboard_router.py tests/test_llm_runtime.py`
- result: `65 passed`

## Remaining gaps

1. The H-1B status-summary document is still unsupported as a distinct family.
2. The H-1B registration record still does not yield a usable `registration_number` on the current source file.
3. The signed Wolff `I-9` still extracts a likely suspect `employee_first_day_of_employment=2026-03-17` and should be cross-checked against related employment records before using it in review logic.
4. Review/comparison logic still does not consume payroll, `I-9`, E-Verify, `I-765`, or H-1B registration fields.
5. Additional series-key rules will likely be needed for future recurring payroll and notice families.

## Next queue

1. Add support for the H-1B status-summary / notice family if it proves operationally useful.
2. Extend rule-based review and retrieval prompts to use the new payroll and employment-verification fields.
3. Tighten extraction normalization for `I-9` first-day-of-employment and H-1B registration identifiers.
