# Classifier gaps — backlog

Source: 145 upload rejections from the cl4183 dogfood on
2026-04-30 → 2026-05-01 (528 attempted uploads, 145 errors = 27.5%
miss rate). Clustered into 30 distinct gap types below, ranked by
fix-ROI (count × severity / effort). Each has a stable ID `Gnn` so
commits can reference it: `fix(classifier): G07 + G08 — schwab CSV +
brokerage filename patterns`.

**How to use:** pick a gap, implement, add a fixture entry under
`tests/fixtures/accounting_eval_set/manifest.yaml`, re-run
`scripts/run_pipeline_eval.py`. Tick the checkbox here, then commit.

## Cluster-count summary

| Fix type | Distinct gaps | Total errors | Cumulative % |
|---|---|---|---|
| A) Filename regex too narrow | 7 | 23 | 16% |
| B) Tie-breaker absent (specificity) | 3 | 25 | 33% |
| C) Missing doc_type entirely | 18 | 65 | 78% |
| D) Path-context stripped on upload | 2 | 21 | 92% |
| E) Mixed-content PDFs | 3 | 11 | 100% |

The fastest path to >50% reduction is C (new doc_types, ~2-4h each)
because it covers the long tail of corporate / immigration docs the
classifier has never seen.

## A — Filename regex too narrow (existing doc_type)

These have a `doc_type` already; just need broader filename patterns.
~15 minutes each.

- [ ] **G01 — `1099` numeric+letter suffix** (4 errors)
   - Files: `2024_1099int_citibank_bsgc.pdf`, `2024_1099b_schwab_xxx619_part1.pdf`, `03_2024_1099int_citibank_llc.pdf`
   - Root cause: regex `(?:^|[^a-z0-9])1099(?:[^a-z0-9]|$)` requires non-alnum directly after `1099`, so `1099int` / `1099b` / `1099r` fail
   - Fix: `r"(?:^|[^0-9])1099(?:[a-z]{0,4})(?:[^a-z0-9]|$)"`
   - File: `compliance_os/web/services/classifier.py` `FILENAME_PATTERNS["1099"]` and `PATH_CONTEXT_PATTERNS`

- [ ] **G02 — Schwab CSV filename pattern** (6 errors)
   - Files: `schwab_llc_xxx239_*.csv`, `schwab_personal_xxx619_*.csv`
   - Root cause: `bank_statement` PATH_CONTEXT requires `/bank_statements/schwab/` in path, but upload preflight strips dir context. Filename `schwab_llc_*.csv` has no FILENAME_PATTERN match.
   - Fix: add filename-only pattern `r"^schwab_(?:llc|personal|brokerage)_[^.]*\.csv$"` to `bank_statement.FILENAME_PATTERNS`
   - File: `compliance_os/web/services/classifier.py:32`

- [ ] **G03 — Schwab brokerage statement PDF** (2 errors)
   - Files: `schwab_brokerage_stmt_xxx239_2025-07.pdf`, `..._2025-09.pdf`
   - Root cause: brokerage statements aren't `bank_statement` proper (different format, holdings + activity vs deposits/withdrawals); no `brokerage_statement` doc_type exists
   - Fix: either treat as `bank_statement` with widened text patterns ("Holdings", "Activity Detail", "Account Value") OR add new `brokerage_statement` doc_type. Recommend latter — Schwab/Fidelity/Vanguard format is distinct.
   - File: `compliance_os/web/services/classifier.py` (new entries in `FILENAME_PATTERNS`, `PATTERNS`, `TEXT_MIN_MATCHES`, `DOC_TYPE_ALIASES`, `PATH_CONTEXT_PATTERNS`)

- [ ] **G04 — Wells Fargo CSV filename pattern** (1 error)
   - Files: `wf_personal_20251023_20260209.csv`
   - Same shape as G02. Combine fix with G02 by widening pattern to include `wf_`.

- [ ] **G05 — Degree certificate broader regex** (5 errors)
   - Files: `A3_columbia_degree.pdf`, `02_columbia_degree.pdf`, `09_columbia_degree.pdf`, `01_columbia_ms_diploma.pdf`, `04_sjtu_bachelor_diploma_cert.pdf`
   - Root cause: `degree_certificate` pattern is `r"degree[_ -]?certificate"` — requires the literal word "certificate" after "degree". Filenames with just `_degree.pdf` or `_diploma_cert.pdf` miss.
   - Fix: `[r"diploma", r"degree[_ -]?certificat(?:e|ion)", r"_degree(?:\.|_)", r"_diploma(?:_cert)?\.pdf$"]`
   - File: `classifier.py:43`

- [ ] **G06 — "Engagement letter" → legal_services_agreement** (3 errors)
   - Files: `BSGC_engagement_letter_040626.pdf`, `CL_personal_engagement_letter_SIGNED_040626.pdf`
   - Root cause: `legal_services_agreement` patterns are `fee_agreement|legal_services_agreement|retainer` — "engagement letter" isn't there
   - Fix: add `r"engagement[_ -]?letter"` to `legal_services_agreement.FILENAME_PATTERNS` AND `PATTERNS` (text)
   - File: `classifier.py:79`

- [ ] **G07 — California "Certificate of Status"** (1 error)
   - Files: `11_certificate_of_status_032826_compilation.pdf`
   - Root cause: `certificate_of_good_standing` regex is `cert(?:ificate)?[_ -]?of[_ -]?good[_ -]?standing`. CA terminology is "Certificate of Status" not "good standing"; DE / WY / NY use the latter.
   - Fix: add alias pattern `r"certificate[_ -]?of[_ -]?status"` to the same doc_type, OR introduce `certificate_of_status` as a CA-specific alias mapping back to `certificate_of_good_standing` via `DOC_TYPE_ALIASES`
   - File: `classifier.py:35`

## B — Tie-breaker absent (specificity ordering)

When 2+ doc_types match the filename equally, `_best_scored_match`
returns None (refuses to guess). Hard rejection. Three high-frequency
ties below.

- [ ] **G08 — `i20` vs `transfer_pending_letter`** (12 errors)
   - Files: `B07_i20_westcliff_transfer_pending.pdf`, `B09_i20_ciam_transfer_pending_sep2025.pdf`, `04_i20_07_westcliff_transfer_pending.pdf`, `18_i20_westcliff_transfer_pending.pdf`, `20_i20_ciam_transfer_pending_sep2025.pdf`
   - Both `i20` (regex matches `_i20_`) and `transfer_pending_letter` (matches `transfer_pending`) score equally → tie → None
   - Fix sketch: in `_best_scored_match`, when multiple winners, prefer the one whose triggered pattern is *longer* (specificity proxy). Or define an explicit specificity table: `{"transfer_pending_letter": 10, "i20": 5}` — higher wins ties.
   - Affects: G08, G09, G10, plus probably more we haven't seen
   - File: `classifier.py:1168` (`_best_scored_match`)

- [ ] **G09 — `cpt_application` vs `i983`** (1 error)
   - Files: `C2_ciam_cpt_application_training_plan.pdf`
   - Both match — `cpt_application` via `cpt_application` and `i983` via `training_plan`
   - Same fix as G08 (specificity ordering)

- [ ] **G10 — `articles_of_organization` vs `ein_application`** (12 errors)
   - Files: `01_BSGC_articles_and_ss4.pdf`, `D1_articles_of_incorporation_ss4.pdf`, `04_yangtze_articles_ss4.pdf`, `05_yangtze_articles_ss4.pdf`, `yangtze_capital_articles_and_ss4.pdf`
   - Filename matches `articles_of_organization` AND `ein_application` (via `ss4`)
   - Same fix mechanism, but ALSO see E12 (mixed-content PDFs are a separate root cause when text classification ties — these files genuinely contain both docs stapled together)

## C — Missing doc_type entirely

These have no doc_type at all. Each needs a new pattern group: filename
regex, text patterns, text min matches, alias entry. ~2-4h per type
including the alias / test-fixture work.

- [ ] **G11 — `corporate_resolution` / `board_resolution`** (12 errors)
   - Files: `D3_corporate_resolutions.pdf`, `D11_board_resolution_signing_authority.pdf`, `06_corporate_resolutions.pdf`, `04_yangtze_resolutions.pdf`, `04_yangtze_corporate_resolutions_2026.pdf`, `07_board_resolution_signing_authority.pdf`, `yangtze_capital_corporate_resolutions_2026.pdf`
   - Suggested doc_type: `corporate_resolution` (single category, ROC + board resolutions both fall here)
   - Patterns: filename `r"(?:corporate|board)[_ -]?resolution"`, text "RESOLVED" + "board of directors|sole shareholder"
   - High value — every formed entity has these

- [ ] **G12 — `bylaws`** (7 errors)
   - Files: `D2_bylaws.pdf`, `04_yangtze_bylaws.pdf`, `05_bylaws.pdf`, `yangtze_capital_bylaws_032626.pdf`
   - Filename `r"\bbylaws?\b"`, text "ARTICLE I" + "bylaws" + "shareholders|directors"

- [ ] **G13 — `ein_fax_notification`** (7 errors)
   - Files: `D8_ein_fax_notification.pdf`, `04_yangtze_ein_fax.pdf`, `03_ein_assignment_irs_fax.pdf`, `yangtze_capital_ein_fax_notification.pdf`
   - This is the IRS fax confirmation when EIN is assigned (different from CP-575 letter — the letter comes later by mail). Fax has different layout.
   - Suggestion: alias to existing `ein_letter` doc_type. Add filename `r"ein[_ -]?fax|ein[_ -]?assignment"` and text pattern "IRS Fax|Date Filed".

- [ ] **G14 — `governance_doc` / `eminutes_packet`** (7 errors)
   - Files: `D5_governance_docs_signed.pdf`, `04_yangtze_governance_signed.pdf`, `08_governance_signed_includes_stock_cert.pdf`, `yangtze_capital_eminutes_docs_signed_033026.pdf`
   - eMinutes-style multi-section governance package (resolutions + stock certs + officer appointments)
   - Single doc_type `governance_packet` makes sense, OR split into `corporate_resolution` (G11) + `stock_certificate` (new) + `officer_appointment` (new)
   - Pragmatic: ship as `governance_packet` with filename `r"governance(?:[_ -]?docs?)?(?:[_ -]?signed)?"` and treat as catch-all

- [ ] **G15 — `statement_of_information` / `state_filing`** (6 errors)
   - Files: `10_soi_filed_041326_latest.pdf`, `09_soi_initial_032826_sacramento.pdf`, `10_soi_updated_041326_berkeley.pdf`, `yangtze_capital_soi_041326.pdf`
   - California Secretary-of-State annual filing (Wyoming uses "annual report", DE uses different)
   - Doc_type `statement_of_information` with filename `r"\bsoi\b|statement[_ -]?of[_ -]?information"` and text "Statement of Information" + "Secretary of State"

- [ ] **G16 — `payroll_summary`** (5 errors)
   - Files: `wolff-li-capital-inc-payroll-summary-7757500971275864-2.pdf` (×5 variants)
   - QuickBooks / Justworks-style aggregate payroll report (different from individual paystubs)
   - Doc_type `payroll_summary` distinct from `paystub`. Filename `r"payroll[_ -]?summary"`, text "Total Gross|Total Net|Pay Period Range"

- [ ] **G17 — `termination_letter` / `employment_termination`** (4 errors)
   - Files: `F2_claudius_termination_letter.pdf`, `claudius_termination_020525.pdf`, `C_termination_email_thread_2024-12-05_to_29.pdf`
   - Currently `employment_correspondence` has resignation but not termination
   - Fix: add `r"termination[_ -]?letter|terminat(?:ion|ed)"` to `employment_correspondence` filename patterns. Or split out `termination_letter` as its own type — recommended because for H-1B chain reasoning, terminations have specific consequences (60-day grace period, etc.) and we want findings rules to fire on them specifically.

- [ ] **G18 — `employer_questionnaire`** (4 errors)
   - Files: `Beneficiary_Questionnaire_FILLED.docx`, `01_employer_questionnaire_filled.pdf`, `03_h1b_employer_questionnaire_filled.pdf`, `08_h1b_employer_questionnaire`
   - Standard H-1B intake document from immigration counsel
   - Doc_type `h1b_employer_questionnaire` (or general `attorney_intake_questionnaire`)
   - Filename `r"(?:employer|beneficiary)[_ -]?questionnaire"`

- [ ] **G19 — ITIN cluster** (3 errors)
   - Files: `itin_support_letter_042126.pdf`, `tarlson_itin_fact_sheet.pdf`, `Fact Sheet - Form W-7 ITIN Applications.pdf`
   - Different ITIN-related shapes: support letters from CAA, fact sheets, W-7 itself
   - Doc_types: `itin_support_letter` (CAA-issued), `itin_fact_sheet` (informational)
   - Filename `r"itin"` triggers either; text disambiguates

- [ ] **G20 — Litigation correspondence cluster** (3 errors)
   - Files: `2026-04-28_demand_letter_v1.pdf`, `2026-04-28_litigation_hold_v1.pdf`, `firm_intake_shortlist.pdf`, `2026-04-28_demand_letter_v1_clean.pdf`
   - Disputes / employment-litigation phase docs
   - Doc_types: `demand_letter`, `litigation_hold`, `attorney_intake_doc`
   - Filename: `r"demand[_ -]?letter"`, `r"litigation[_ -]?hold"`, `r"firm[_ -]?intake"`

- [ ] **G21 — Litigation chain correspondence (lettered exhibits)** (3 errors)
   - Files: `E_thunderbird_deck_delivered_2024-12-11.pdf`, `H_dochub_reminder_2024-12-13.pdf`, `G_dochub_finalized_audit_trail_2024-12-05.pdf`
   - Exhibit-prefixed correspondence (E/G/H/...) often used in legal demand-letter exhibits
   - Doc_type `litigation_exhibit` or treat as `email_correspondence_export`
   - Lower priority — niche to active litigation; defer

- [ ] **G22 — `business_plan`** (2 errors)
   - Files: `guardian_business_plan_v1.pdf`, `G2_guardian_ai_business_plan_v1.pdf`
   - High value for EB-5 / H-1B operating-entity narratives
   - Doc_type `business_plan`. Filename `r"business[_ -]?plan"`, text "Executive Summary|Market Analysis|Five-Year Projections|Capitalization"

- [ ] **G23 — `attorney_intake_doc`** (2 errors)
   - Files: `firm_intake_shortlist.pdf`, `consultation_playbook.pdf`
   - Already partially in G20 — but separate from demand_letter / litigation_hold
   - Doc_type `attorney_intake_doc`

- [ ] **G24 — `materiality_difference_memo`** (2 errors)
   - Files: `02_MATERIALITY_DIFFERENCE_MEMO_DRAFT.pdf`, `yangtze_materiality_difference_memo_042926_DRAFT.pdf`
   - H-1B-specific (registration vs petition material-changes memo)
   - Doc_type `h1b_materiality_memo`. Niche but specific to the workflow we support.

- [ ] **G25 — `bank_kyc_doc`** (2 errors)
   - Files: `ewb_kyc_crossborder.pdf`, `ewb_kyc_crossborder_FILLED.pdf`
   - Bank Know-Your-Customer / cross-border-payments form
   - Doc_type `bank_kyc_form`. Filename `r"\bkyc\b"`, text "Know Your Customer|cross-border|sanctions screening"

- [ ] **G26 — `exhibit_index`** (1 error)
   - File: `00_README_exhibit_index.pdf`
   - Cover index for an exhibit bundle
   - Doc_type `exhibit_index` — but this is borderline noise (covers bundle, not a primary doc itself). Consider whether to admit at all.

- [ ] **G27 — `i129_support_letter`** (1 error)
   - File: `yangtze_i129_support_letter_outline_042926.pdf`
   - Standard H-1B petition support letter (employer's narrative)
   - Doc_type `i129_support_letter` — high value for H-1B chain. Should land soon.

- [ ] **G28 — `transaction_ledger`** (1 error)
   - File: `Master_Transaction_Ledger.csv`
   - User-maintained ledger CSV (different from bank_statement)
   - Doc_type `transaction_ledger` OR alias to `bank_statement` — defer pending more samples

## D — Path-context stripped on upload

Filenames are generic ("01_articles.pdf"); the *parent directory*
(`/01_employer_yangtze_corporate/`) carries the doc_type signal. The
upload preflight strips that to `/tmp/.preflight_<uuid>_01_articles.pdf`,
losing context. The PATH_CONTEXT_PATTERNS in classifier.py never match
post-strip.

- [ ] **G29 — Numbered-prefix filename + dir context** (14 errors)
   - Files: `04_yangtze_resolutions.pdf`, `11_ciam_current.pdf`, `02_columbia_travel_22.pdf`, `05_columbia_stemopt.pdf`, `08_westcliff_continued.pdf`, `01_columbia_original.pdf`, `09_ciam_transfer_pending.pdf`, etc.
   - Root cause: filename's only signal is what comes after the numeric prefix; PATH_CONTEXT lives in the dir
   - Fix: thread the original filename + parent-dir-name through to the classifier in `_resolve_doc_type_for_upload_file`. Either:
     (1) Pass `original_filename` as a separate arg to `classify_file`
     (2) Save preflight to a *dirname-preserving* temp dir like `/tmp/preflight_<uuid>/<original_relpath>` so PATH patterns still match
     (3) Add a second-pass classification using `original_filename` only (no path) when the temp-path classification returns None
   - Recommend (3) — simplest, no signature changes
   - File: `compliance_os/web/routers/dashboard.py:139` `_resolve_doc_type_for_upload_file`

- [ ] **G30 — Multi-doc compilation filename** (7 errors)
   - Files: `D6_key_documents_compilation.pdf`, `04_yangtze_key_documents.pdf`, `05_yangtze_key_documents_2026.pdf`, `11_key_documents_compilation.pdf`
   - Compilation of multiple distinct docs concatenated
   - Resolution: introduce `multi_doc_compilation` as a "needs split" classification that prompts the user to break the file into pages. Or just admit as catch-all `compilation` and skip extraction.

## E — Mixed-content PDFs

Single PDF contains 2+ distinct doc_types (Articles + SS-4 stapled).
Text classifier ties between the two and returns None. Different from
G29 because the file is *legitimately ambiguous* — splitting is the
right answer.

- [ ] **G31 — `articles_and_ss4` combined PDFs** (12 errors)
   - Same files as G10. After tie-breaker (G08 mechanism) lands, this
     resolves to `articles_of_organization` from page 1.
   - Better fix: when text classifier ties between two doc_types,
     prefer the doc_type matched on **page 1 only** (the "cover" doc).
     `pdf_reader.extract_first_page` already exists.
   - File: `classifier.py:1244` `classify_file` — when tie at text stage, fall back to first-page-only classification

- [ ] **G32 — `cpt_application + training_plan`** (1 error)
   - Same root as G31. Fix together.

- [ ] **G33 — `articles + bylaws + corporate_resolution` triple** (counts within G14 governance_packet)
   - Some governance_signed packets contain 3+ stapled docs. After G14, classify as `governance_packet` and skip cover-page tie-break (composite is the right answer here).

## Unmatched (no obvious cluster — review individually)

Files that didn't fit a pattern in the cluster analysis. Likely
one-offs that don't justify a new doc_type yet.

- `2025_welcome_letter_fee_schedule.pdf` — bank welcome letter, defer
- `H1BcoCapReg_PS_FY27.pdf` — H-1B cap registration confirmation, low frequency
- `case_summary_for_kuck_042826.pdf` — case-summary memo, internal/derived (skip)
- `Invoice_151411369.pdf` — generic invoice, doc_type `invoice` exists? check classifier.py
- One Stripe webhook fixture that isn't a real doc

## Suggested order of attack

1. **G29 (path-context fix)** — biggest single win (14 errors), unlocks all numbered-prefix files. ~2h.
2. **G08 (tie-breaker)** — 12 errors; mechanism reused for G09, G10. ~1h.
3. **G02 + G04 (Schwab + WF CSV filename patterns)** — 7 errors with one regex. ~15 min.
4. **G11 (corporate_resolution)** — 12 errors. ~3h end-to-end.
5. **G12 (bylaws)** — 7 errors. ~2h.
6. **G15 (statement_of_information)** — 6 errors. ~2h.
7. **G16 (payroll_summary)** — 5 errors. ~2h.
8. **G05 (degree_certificate)** — 5 errors. 30 min.
9. **G01 (1099 letter suffix)** — 4 errors. 15 min.
10. **G06 (engagement_letter)** — 3 errors. 15 min.

After 10: 75/145 errors fixed (52%). Diminishing returns past that
unless dogfooding surfaces new clusters.

## Workflow

For each gap:
1. Add the regex/doc_type/alias to `classifier.py`
2. Add 2-3 representative fixture entries to `tests/fixtures/accounting_eval_set/manifest.yaml` with `expected_doc_type: <new_or_existing>`
3. Run `python scripts/run_pipeline_eval.py --manifest tests/fixtures/accounting_eval_set/manifest.yaml --user-email eval-20260430@guardian.local`
4. Confirm dim 1 (ingest) and dim 2 (classification accuracy) move in the right direction
5. Tick the box, commit with `fix(classifier): G<nn> — <short>`, push
6. Optionally smoke-test on cl4183 by re-uploading the affected file with `?duplicate_action=keep`
