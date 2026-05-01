# Pipeline eval — 2026-04-30

- API: `http://127.0.0.1:8000`
- User: `eval-20260430@guardian.local`
- Fixture size: 52
- Started: 2026-04-30T18:52:31.612128+00:00
- Finished: 2026-04-30T19:02:26.522408+00:00

## Scores

| Dim | Name | Score | Pass bar | Status |
|-----|------|-------|----------|--------|
| 1 | Ingest reliability | 82.7% | 98% | FAIL |
| 2 | Classification accuracy | 93.0% | 85% | PASS |
| 3 | Dedup correctness | 100.0% | 100% | PASS |
| 4 | Index coverage | 100.0% | 95% | PASS |
| 5 | Finding extraction (manual) | — | 5/5 | needs eyeball |
| 6 | Deadline detection (manual) | — | 5/5 | needs eyeball |
| 7 | Latency p50 / p95 | 5658ms / 10155ms | <30000ms | — |
| 8 | Cost / 100 docs | (logged below) | — | baseline |

**Overall (auto-only):** 69.4%

## Classification accuracy by expected type

| Expected | Score |
|----------|-------|
| `1042s` | 100% |
| `1099` | 0% |
| `annual_account_summary` | 50% |
| `bank_statement` | 100% |
| `degree_certificate` | 100% |
| `employment_letter` | 100% |
| `h1b_g28` | 100% |
| `h1b_registration` | 100% |
| `h1b_registration_worksheet` | 100% |
| `i94` | 100% |
| `lease` | 100% |
| `legal_services_agreement` | 67% |
| `payment_options_notice` | 100% |
| `paystub` | 100% |
| `tax_return` | 100% |
| `transcript` | 100% |
| `tuition_statement` | 100% |
| `w2` | 100% |
| `w4` | 100% |

## Confusion (expected → actual)

- `1042s` → `1042s`  ×4
- `1099` → `identity_document`  ×1  ← MISMATCH
- `annual_account_summary` → `annual_account_summary`  ×1
- `annual_account_summary` → `identity_document`  ×1  ← MISMATCH
- `bank_statement` → `bank_statement`  ×5
- `degree_certificate` → `degree_certificate`  ×1
- `employment_letter` → `employment_letter`  ×1
- `h1b_g28` → `h1b_g28`  ×2
- `h1b_registration` → `h1b_registration`  ×1
- `h1b_registration_worksheet` → `h1b_registration_worksheet`  ×1
- `i94` → `i94`  ×1
- `lease` → `lease`  ×2
- `legal_services_agreement` → `insurance_record`  ×1  ← MISMATCH
- `legal_services_agreement` → `legal_services_agreement`  ×2
- `payment_options_notice` → `payment_options_notice`  ×1
- `paystub` → `paystub`  ×4
- `tax_return` → `tax_return`  ×2
- `transcript` → `transcript`  ×3
- `tuition_statement` → `tuition_statement`  ×2
- `w2` → `w2`  ×5
- `w4` → `w4`  ×2

## Per-file first-pass results

| File | Expected | Classified | Status | ms |
|------|----------|------------|--------|----|
| `2025_w2_wolff_li_capital.pdf` | `w2` | `w2` | OK | 5704 |
| `W2_Claudius_Legal_Intelligence_2025_unlocked.pdf` | `w2` | `w2` | OK | 5658 |
| `2024_w2_bitsync.pdf` | `w2` | `w2` | OK | 6750 |
| `2024_w2_justworks_wolffli.pdf` | `w2` | `w2` | OK | 6987 |
| `2023_w2_justworks_vcv.pdf` | `w2` | `w2` | OK | 6926 |
| `2025_1042s_schwab_xxx619.pdf` | `1042s` | `1042s` | OK | 9747 |
| `2024_1042s_tda_xxx619.pdf` | `1042s` | `1042s` | OK | 6853 |
| `2024_1042s_schwab_xxx619.pdf` | `1042s` | `1042s` | OK | 7059 |
| `2023_1042s_tda_xxx619.pdf` | `1042s` | `1042s` | OK | 5755 |
| `2024_1099b_schwab_xxx619_part1.pdf` | `1099` | `identity_document` | OK | 5023 |
| `2024_1099int_citibank_bsgc.pdf` | `1099` | `None` | ERR 400 | 2907 |
| `1098T_CIAM_2025.pdf` | `tuition_statement` | `tuition_statement` | OK | 663 |
| `1098T_CIAM_2025_decrypted.pdf` | `tuition_statement` | `tuition_statement` | OK | 3379 |
| `2024_w4_claudius.pdf` | `w4` | `w4` | OK | 10155 |
| `2024_w4_bitsync.pdf` | `w4` | `w4` | OK | 11100 |
| `2023_TaxReturn.pdf` | `tax_return` | `tax_return` | OK | 8432 |
| `2024_TaxReturn.pdf` | `tax_return` | `tax_return` | OK | 9312 |
| `paystub_claudius_2025-01-09.pdf` | `paystub` | `paystub` | OK | 3688 |
| `paystub_claudius_2025-02-11.pdf` | `paystub` | `paystub` | OK | 2995 |
| `paystub_claudius_2025-02-25.pdf` | `paystub` | `paystub` | OK | 3282 |
| `2025_wolff_li_paystubs.pdf` | `paystub` | `paystub` | OK | 7690 |
| `citibank_llc_chk5039_20251219_20260122.pdf` | `bank_statement` | `bank_statement` | OK | 5464 |
| `citibank_llc_chk5039_20250920_20251021.pdf` | `bank_statement` | `bank_statement` | OK | 7000 |
| `citibank_llc_chk5039_20260221_20260319.pdf` | `bank_statement` | `bank_statement` | OK | 4158 |
| `citibank_llc_chk5039_202307.pdf` | `bank_statement` | `bank_statement` | OK | 3256 |
| `citibank_personal_chk6544_20241021_20251006.csv` | `bank_statement` | `bank_statement` | OK | 1326 |
| `wf_personal_20251023_20260209.csv` | `bank_statement` | `None` | ERR 400 | 47 |
| `citizens_payment_options_2958.pdf` | `payment_options_notice` | `payment_options_notice` | OK | 5351 |
| `2024_yearend_summary_schwab_xxx619.pdf` | `annual_account_summary` | `annual_account_summary` | OK | 3904 |
| `schwab_llc_xxx239_2025_account_summary.pdf` | `annual_account_summary` | `identity_document` | OK | 6148 |
| `BSGC_engagement_letter_040626.pdf` | `legal_services_agreement` | `insurance_record` | OK | 7311 |
| `CL_personal_engagement_letter_SIGNED_040626.pdf` | `legal_services_agreement` | `None` | ERR 400 | 3215 |
| `h1b_retainer_hibee.pdf` | `legal_services_agreement` | `legal_services_agreement` | OK | 5528 |
| `H-1B CAP Legal Services Agreement_LI, Chenyu.pdf` | `legal_services_agreement` | `legal_services_agreement` | OK | 4461 |
| `H-1B_registration-selection_notice-Li_Chenyu.pdf` | `h1b_registration` | `h1b_registration` | OK | 3814 |
| `bsgc_h1b_g28_mt_law_031026.pdf` | `h1b_g28` | `h1b_g28` | OK | 3473 |
| `yangtze_h1b_g28_arora_031026.pdf` | `h1b_g28` | `h1b_g28` | OK | 7316 |
| `H-1B Part I_Registration Worksheet_Employee_BSGC_FILLED.docx` | `h1b_registration_worksheet` | `h1b_registration_worksheet` | OK | 2921 |
| `yangtze_cpt_offer_letter_031526.pdf` | `employment_letter` | `employment_letter` | OK | 4082 |
| `i94_yunhong_chen.pdf` | `i94` | `i94` | OK | 3061 |
| `lease_extract_2pages.pdf` | `lease` | `lease` | OK | 5076 |
| `07_yangtze_office_lease_signed.pdf` | `lease` | `lease` | OK | 5833 |
| `columbia_transcript.pdf` | `transcript` | `transcript` | OK | 6484 |
| `columbia_degree_certification.pdf` | `degree_certificate` | `None` | ERR 400 | 5307 |
| `4_SJTU_Bachelor_Transcript_EN.pdf` | `transcript` | `transcript` | OK | 14476 |
| `3_Diploma_Columbia_Masters.pdf` | `degree_certificate` | `degree_certificate` | OK | 19156 |
| `5_Waseda_University_Transcript.pdf` | `transcript` | `transcript` | OK | 737 |
| `foster_consult_analysis_042726.md` | `None` | `None` | ERR 400 | 41 |
| `klasko_consultation_analysis_041026.txt` | `None` | `None` | ERR 400 | 150 |
| `business_description_alignment_040826.txt` | `None` | `None` | ERR 400 | 91 |
| `deadlines.txt` | `None` | `None` | ERR 400 | 162 |
| `Account_Analysis_Summary.txt` | `None` | `None` | ERR 400 | 123 |
