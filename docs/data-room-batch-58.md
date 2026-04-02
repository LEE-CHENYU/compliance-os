# Data Room Batch 58

Source folder: `/Users/lichenyu/Desktop/accounting-not-in-important-docs-20260329/files`

## Batch 58 manifest

This batch groups CIAM, school, and immigration support records that sit outside the original `Important Docs` corpus but matter for education, CPT, and status continuity.

| Label | File | Intended use | Intended doc type |
| --- | --- | --- | --- |
| `i20_financial_affidavit` | `legal/immigration/i20_affidavit_financial_support.pdf` | I-20 financial-support affidavit | `financial_support_affidavit` |
| `i94_recent_accounting` | `legal/immigration/i94_most_recent.pdf` | most recent I-94 record | `i94` |
| `ciam_sample_offer_letter` | `outgoing/ciam/CIAM - CPT F-1 Sample Employment Offer Letter.pdf` | CPT sample employment offer letter | `employment_letter` |
| `ciam_fall_intro_packet` | `outgoing/ciam/CIAM Fall II 2025 Introduction (10.22.2025).pdf` | CIAM intro packet | `school_policy_notice` |
| `ciam_internship_course_packet` | `outgoing/ciam/CIAM Internship Courses (INT501 & INT599) 10.22.2025.pdf` | CIAM internship course guidance | `school_policy_notice` |
| `ciam_cpt_app_completed` | `outgoing/ciam/CIAM_CPT_App_Li_Chenyu.pdf` | completed CIAM CPT application | `cpt_application` |
| `ciam_cpt_application_template` | `outgoing/ciam/CIAM_CPT_Application.pdf` | CIAM CPT application template | `cpt_application` |
| `ciam_non_cpt_course_packet` | `outgoing/ciam/INT501 INT599 Application Non-CPT.pdf` | non-CPT course application packet | `school_policy_notice` |
| `yangtze_cpt_offer_letter` | `outgoing/ciam/yangtze_cpt_offer_letter_031526.pdf` | Yangtze CPT offer letter | `employment_letter` |
| `ciam_1098t` | `tax/2025/1098T_CIAM_2025.pdf` | CIAM 1098-T tuition statement | `tuition_statement` |
| `ciam_1098t_decrypted` | `tax/2025/1098T_CIAM_2025_decrypted.pdf` | decrypted CIAM 1098-T statement | `tuition_statement` |
| `drivers_license_cn_tmp` | `tmp/dl_cn.jpeg` | Chinese driver license image | `drivers_license` |
| `i20_compiled_after_nov2023` | `tmp/mt_law_dropbox_upload/4_I20_All_After_Nov2023.pdf` | compiled I-20 packet after Nov 2023 | `i20` |
| `waseda_transcript_tmp` | `tmp/mt_law_dropbox_upload/5_Waseda_University_Transcript.pdf` | Waseda university transcript | `transcript` |

## Baseline current-state result

- Current fast-path match rate against intended doc types: `7/14`
- Already matched on the first validator pass:
  - `i94`
  - `employment_letter`
  - `cpt_application`
  - `i20`
  - `transcript`
- Missed or misrouted families on the first pass:
  - `i20_affidavit_financial_support.pdf` was collapsing into generic `i20`
  - CIAM intro/course packets had no `school_policy_notice` family
  - `1098-T` tuition statements were unsupported, and one decrypted copy drifted into `identity_document`
  - `tmp/dl_cn.jpeg` needed a more robust driver-license shorthand path/filename rule

## Post-fix result

- Current fast-path match rate against intended doc types: `14/14`
- New school/support families now exist as first-class types:
  - `financial_support_affidavit`
  - `school_policy_notice`
  - `tuition_statement`
- CIAM guidance packets now stay separate from employment letters and CPT forms instead of disappearing into unresolved support.
- `1098-T` files now classify as tuition statements on both regular and decrypted copies.
- The temp-path Chinese driver-license image now resolves correctly without needing corpus-specific patch logic.

## Validation

- Real-source validator:
  - `conda run -n compliance-os python scripts/validate_data_room_batch.py --manifest config/data_room_batches.yaml --batch-number 58`
  - Result: `14/14`
- Focused regression suite:
  - `conda run -n compliance-os pytest tests/test_classifier_service.py tests/test_extractor.py tests/test_batch_validation.py tests/test_data_room_batch_loop.py tests/test_checks_router_v2.py -q`
  - Result: `133 passed`
- Loop-compatible logging command:
  - `conda run -n compliance-os python scripts/data_room_batch_loop.py --manifest config/data_room_batches.yaml --batch-number 58 --run-validation-hooks --json --log-root logs/data-room-batch-loop-round-56-60`
  - Passing session:
    - `logs/data-room-batch-loop-round-56-60/20260329T180219Z`

## Current batch blockers

None.

## Next queue

1. Batch 59: H-1B intake worksheets and counsel forms
2. Batch 60: payroll, tax-support, and standalone forms
