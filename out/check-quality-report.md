# Check Quality Scorecard

Generated 2026-04-15 07:53 UTC — judge: claude-opus-4-6 (adaptive thinking)

**Totals:** 12 pass · 0 partial · 0 fail · 12 cases
**Tokens:** 23,686 in · 27,907 out

## h1b_doc_check

_3 pass · 0 partial · 0 fail_

### ✅ `clean_packet` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | All factual claims are accurate. E-Verify mention as 'required for STEM OPT continuity cases and a frequent USCIS Request-for-Evidence (RFE) trigger' is correct. The receipt-tracking URL 'egov.uscis.gov' and receipt-number prefixes '(IOE/EAC/WAC/LIN/SRC format)' are valid. Entity-name, amount, and signatory comparisons are properly evaluated as matches. No rules, deadlines, or thresholds are misstated. |
| actionability | ✅ pass | Each next step names a concrete target: 'Confirm your attorney has the original signed G-28 (Notice of Entry of Appearance) on file before USCIS submission' tells the user what document, who to ask, and the timing constraint. 'Track petition status at egov.uscis.gov using the receipt number' gives the specific URL and artifact to use. The E-Verify step could have specified how to verify (e.g., ask HR), but the instruction is sufficiently directed. |
| tone_severity | ✅ pass | '0 critical, 0 warning, and 0 informational items' and verdict 'pass' are appropriately calm for a fully consistent packet. No alarmist language is present. The next steps use advisory framing ('Confirm', 'Verify', 'Keep') without urgency markers, which correctly reflects the absence of problems. |
| completeness | ✅ pass | The output performs the key cross-document comparisons a practitioner would check: entity names across registration/G-28/invoice, signatory vs. cardholder, and invoice vs. receipt amounts. It proactively surfaces E-Verify enrollment and original G-28 signing—both common RFE triggers. A law-firm-name cross-check (status summary vs. G-28) isn't shown explicitly in comparisons but both values are surfaced in the document summary for user inspection. |
| clarity | ✅ pass | Jargon is consistently glossed: 'G-28 (Notice of Entry of Appearance)', 'Request-for-Evidence (RFE)'. Receipt-number formats are given as examples rather than assumed knowledge. The summary sentence '5 of 5 H-1B packet documents and found 0 critical, 0 warning, and 0 informational items' gives a non-expert an immediate read on status. Language is accessible to an international-student beneficiary without counsel. |

**Notes:** Clean packet, clean output. The synthetic dates (petition filing window 2028, employment start 2028) are inconsistent with an FY2026 registration number in real-world terms, but the scenario stipulates all docs are consistent and the window is open, so the system's clean verdict is appropriate for the test. The comparisons section is a nice transparency feature, though adding a beneficiary-name cross-check (G-28 client_name vs. invoice beneficiary_name) would round it out.

### ✅ `entity_suffix_mismatch` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The claim 'USCIS will reject a petition whose documents name different legal entities — including Inc vs LLC — regardless of whether the base name matches' is accurate; entity-type suffix mismatches are a known rejection trigger. The suggestion to verify against 'state incorporation records (Secretary of State business search) or their IRS EIN letter (CP-575)' is regulatorily sound. The missing-document flag for the status summary is correct (4 of 5 docs uploaded). No misstated rules or deadlines. |
| actionability | ✅ pass | Next steps name concrete targets: 'Secretary of State business search,' 'IRS EIN letter (CP-575),' and 'contact your employer's HR or the attorney who issued the invoice to have the invoice reissued.' The missing-doc step tells the user exactly what to upload and to 're-run the check.' These are executable without guessing. |
| tone_severity | ✅ pass | Marking the Inc/LLC mismatch as 'critical' with a 'block' verdict is proportionate to the actual consequence—USCIS petition rejection. The consequence text is direct ('USCIS will reject') without being unnecessarily alarmist, and the missing status summary is appropriately handled as a next step rather than inflated to a critical finding. |
| completeness | ✅ pass | The output catches the core Inc-vs-LLC mismatch, verifies the registration-G28 entity name match, confirms signatory name consistency (Alice Chen on registration and receipt), validates the fee amount match ($2780), and flags the missing status summary. These are the checks a competent practitioner would perform on this four-document subset. |
| clarity | ✅ pass | The finding title 'Petitioner name mismatch between registration and invoice' is plain-language. Technical references like 'CP-575' and 'Secretary of State business search' are named concretely enough to be searchable by a non-expert. The comparison detail 'Base names match (100%) but entity types differ: inc vs llc' clearly explains why the names look similar but are legally distinct. |

**Notes:** A strong output overall. The action field in the finding duplicates the first next_step verbatim, which is mildly redundant but not harmful. The comparisons block provides useful transparency for the user to see what was checked and what matched.

### ✅ `only_one_doc_uploaded` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The output correctly identifies 1 of 5 expected documents uploaded, lists the four missing document types accurately, and appropriately states 'cross-checks are unreliable on partial packets.' No USCIS rules, deadlines, or filing requirements are misstated. |
| actionability | ✅ pass | Each next step names the exact document and provides a plain-English gloss, e.g., 'Upload the Form G-28 (attorney's Notice of Entry of Appearance representing the petitioner).' The summary also tells the user to 're-run the check' after uploading. A self-directed beneficiary can act on every item without guessing. |
| tone_severity | ✅ pass | The verdict is 'incomplete' rather than 'fail' or 'URGENT,' which correctly matches the consequence of a partial upload. There is no alarmism; the tone is matter-of-fact. The empty findings array avoids manufacturing false warnings, matching the scenario expectation of no noise. |
| completeness | ✅ pass | The output delivers exactly what the scenario expects: an 'incomplete' verdict, a clear enumeration of the four missing documents, zero spurious findings ('finding_count': 0), and no noisy cross-check comparisons. A competent practitioner would likewise decline to cross-check on a single document and instead request the rest of the packet. |
| clarity | ✅ pass | Every jargon term is accompanied by a parenthetical explanation, e.g., 'Form G-28 (attorney's Notice of Entry of Appearance representing the petitioner)' and 'Payment receipt for the USCIS filing fee (credit-card or ACH confirmation).' The summary is one long but parseable sentence. Suitable for a beneficiary without dedicated counsel. |

**Notes:** The output is a textbook handling of an incomplete upload: it avoids generating noise, clearly enumerates what's missing with user-friendly descriptions, and sets the correct 'incomplete' verdict. The instruction to 're-run the check' after uploading remaining documents is a helpful touch.

## fbar_check

_3 pass · 0 partial · 0 fail_

### ✅ `under_threshold_no_filing` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The aggregate calculation ($4,000 + $3,500 = $7,500) is correct. The statement 'below the $10,000 threshold — no FBAR filing is required' is legally accurate; the filing trigger is when the aggregate *exceeds* $10,000. The FATCA/FBAR distinction note is also accurate. |
| actionability | ✅ pass | For a no-filing scenario, the next steps are appropriately scoped: 'No filing action needed,' keep records, re-check if accounts change, and be aware of the FATCA distinction. There is no vague 'review' or 'confirm' language; each step is concrete enough for the user's situation. |
| tone_severity | ✅ pass | The tone is calm and informational, matching the low-stakes outcome. There is no alarmist language; 'no FBAR filing is required' delivers the clear all-clear the user needs. The advisory about re-checking if circumstances change is appropriately framed as forward-looking guidance, not a warning. |
| completeness | ✅ pass | The output covers the key points a competent practitioner would raise: correct aggregate math, clear no-filing conclusion, record-keeping advice, reminder to re-assess if new accounts are opened or balances change, and the FBAR/FATCA distinction. A downloadable summary artifact is a nice touch. |
| clarity | ✅ pass | The summary is a single, plain-English sentence that a non-expert can immediately understand. 'Aggregate maximum balance' is contextualized by the dollar amount. Form references like 'FinCEN 114' and 'Form 8938' are paired with their common names (FBAR, FATCA), aiding comprehension. |

**Notes:** Clean, well-calibrated output for a below-threshold scenario. The user walks away with a definitive no-filing answer, understands the threshold, and knows to re-evaluate if circumstances change.

### ✅ `over_threshold_must_file` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | All factual claims are accurate: aggregate of $21,700 is correctly computed ($8,500+$7,200+$6,000), the $10,000 threshold is correctly stated, BSA E-Filing is correctly identified as the filing system (not IRS), the October 15 automatic extension is correct, and penalty figures (~$16K non-willful, ~$129K or 50% willful) match 2024 inflation-adjusted amounts. The FBAR/FATCA distinction is correctly drawn. |
| actionability | ✅ pass | Next steps include the specific filing URL ('bsaefiling.fincen.treas.gov'), the Treasury exchange-rate URL ('fiscal.treasury.gov/reports-statements/treasury-reporting-rates-exchange'), the concrete deadline ('2025-10-15'), and the instruction to keep the BSA confirmation page. The note to 'List every foreign account, not just those individually over $10,000' is a practical tip that prevents a common mistake. A downloadable draft packet artifact is also provided. |
| tone_severity | ✅ pass | The output says 'FinCEN filing is required' — direct and proportionate for someone who clearly exceeds the threshold by over 2×. Penalties are stated factually ('Non-filing penalties can reach ~$16K/year') without alarmist framing like 'URGENT' or 'you are at risk.' This matches the real consequence: filing is mandatory and penalties are significant but the situation is routine and remediable. |
| completeness | ✅ pass | The output covers the filing obligation, aggregate calculation, all three accounts echoed back, the correct filing system and deadline, currency conversion guidance, the all-accounts-must-be-listed rule, penalty ranges for both willful and non-willful, and the FBAR vs. FATCA distinction. A competent practitioner reviewing this scenario would flag the same points. No obvious issues are missed. |
| clarity | ✅ pass | The language is accessible to a non-expert: acronyms like FBAR, FATCA, and BSA are paired with their form numbers or full context. The next steps are a well-structured numbered list. Technical terms like 'aggregate maximum balance' are used in context ('the threshold is on the aggregate maximum balance'), making them understandable. No run-on sentences or unexplained jargon. |

**Notes:** This is a clean, well-executed output for a straightforward above-threshold FBAR scenario. The inclusion of both the BSA e-filing URL and the Treasury exchange-rate URL is a nice touch for self-directed users. One minor enhancement opportunity: the filing_deadline field shows only the extended date (2025-10-15); surfacing the original April 15 date in a structured field (not just in the next_steps text) could be marginally more transparent, but this does not rise to a deficiency.

### ✅ `fractional_boundary` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | Aggregate balance computed correctly as $10,000.01 (no truncation bug). Threshold determination is correct: '$10,000.01, which is above the $10,000 threshold' properly applies the strict-exceed rule. Filing deadline '2025-10-15' is accurate (automatic extension post-2017 SAT). Penalty figures '~$16K/year (non-willful) or the greater of ~$129K or 50% of balance (willful)' match 2024 inflation-adjusted amounts. BSA E-Filing as the filing venue and the FBAR/FATCA distinction are correctly stated. |
| actionability | ✅ pass | Steps include specific URLs ('bsaefiling.fincen.treas.gov', 'fiscal.treasury.gov/reports-statements/treasury-reporting-rates-exchange'), an explicit deadline date, and concrete instructions like 'List every foreign account, not just those individually over $10,000' and 'keep the BSA confirmation page.' A self-directed user can follow these without further research. |
| tone_severity | ✅ pass | The output correctly conveys that filing is required without alarmism. Penalties are mentioned factually in context ('Non-filing penalties can reach…') rather than headlined with 'URGENT' language. This is appropriate: the user has a real obligation but ample time (October 2025 deadline) and a marginal-threshold balance, so a measured, informative tone fits. |
| completeness | ✅ pass | Covers all key practitioner concerns: correct aggregate calculation with fractional cents, filing venue (FinCEN not IRS), deadline with automatic extension note, penalty exposure, exchange-rate guidance, the report-all-accounts rule, and the FBAR/FATCA distinction. The draft packet artifact is a useful addition. No obvious omissions for this straightforward two-account scenario. |
| clarity | ✅ pass | Jargon is introduced with explanation: 'FBAR (FinCEN 114) is filed with FinCEN, not the IRS. It is separate from FATCA Form 8938, which has a higher threshold and is attached to the 1040 return.' Sentences are concise, and the summary leads clearly with the bottom line. Accessible to a non-expert international user. |

**Notes:** This scenario specifically tests fractional-dollar arithmetic at the threshold boundary. The output correctly computes $9,999.50 + $0.51 = $10,000.01 and fires the filing requirement, demonstrating that the v1 int() truncation bug has been resolved. All dimensions are solid.

## student_tax_1040nr

_3 pass · 0 partial · 0 fail_

### ✅ `clean_w2_only` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | All factual claims are accurate: Article 20(c) $5,000 exemption for Chinese students, FICA exemption for F-1 students in their first 5 calendar years, 7.65% FICA rate, 2025-04-15 deadline, Form 8843 attachment requirement, and the correct warning that 'TurboTax, H&R Block, FreeTaxUSA cannot produce a valid 1040-NR.' The SPT exempt-individual determination (arrival 2022-08-15, 3rd calendar year, still nonresident) is correctly handled. Math on '$25,000 to $20,000' is correct. |
| actionability | ✅ pass | Next steps are highly specific: 'Check Box 4 (SS tax) and Box 6 (Medicare tax) on your W-2' tells the user exactly where to look; 'file Form 843 with Form 8316' names the remedy; Sprintax and GLACIER Tax Prep are named as compliant software alternatives; the deadline '2025-04-15' is explicit. The treaty finding instructs the user to 'Confirm eligibility and whether your payer issued a Form 1042-S before claiming,' which names the specific document to check. |
| tone_severity | ✅ pass | Both findings are marked 'info' severity, which correctly matches their nature as optimization tips rather than compliance failures. Language uses measured phrasing like 'may reduce,' 'typically exempts,' and 'generally exempt' without alarmism. The summary frames them as '2 tips that could save you money or clarify next steps,' which is proportionate. |
| completeness | ✅ pass | The scenario expected 0 findings, but the 2 info-level findings surfaced are things a competent practitioner would absolutely flag for a Chinese F-1 student: treaty Article 20(c) could save several hundred dollars, and an erroneous FICA withholding (~$1,912 on $25K) is a common and recoverable mistake. Surfacing these as informational tips adds value without creating false alarms. No obvious issues are missed. |
| clarity | ✅ pass | Jargon is consistently glossed: 'FICA (Social Security / Medicare),' 'Box 4 (SS tax) and Box 6 (Medicare tax).' Sentences are concise and structured with clear cause-effect ('If FICA was withheld, ask your employer to refund it first; if they refuse, you can file Form 843'). The mailing instructions are step-by-step and easy to follow for a first-time filer. |

**Notes:** The scenario expected 0 findings and a clean package, but the 2 info-level findings returned are substantively useful and factually correct. A competent practitioner advising a Chinese F-1 student with $25K in wages would flag both the treaty benefit and FICA exemption. The output is a stronger result than a bare 'clean package' for this user profile.

### ✅ `turbotax_user_no_itin` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | All factual claims check out: TurboTax/H&R Block/FreeTaxUSA cannot prepare 1040-NR, W-7 must accompany a paper 1040-NR with original or certified-copy identity documents, F-1 students in first 5 calendar years are FICA-exempt, India-US treaty allows the standard deduction on 1040-NR, and the deadline of 2025-04-15 for TY2024 is correct. The rough tax estimate of '$3,000+' is reasonable for $30K wages without standard deduction. 'suggested_treaty_article': 'Article 21(2) — standard deduction' is a defensible citation for the India-US treaty provision. |
| actionability | ✅ pass | Each finding names concrete targets: 'Use Sprintax or GLACIER Tax Prep or a CPA who files 1040-NR,' 'Check Box 4 (SS tax) and Box 6 (Medicare tax) on your W-2,' 'file Form W-7 to request an ITIN,' 'file Form 843 with Form 8316.' Even the informational treaty finding directs the user to 'Confirm with a nonresident-aware preparer,' which is appropriately scoped for an info-level item. Next steps are sequenced clearly with the deadline explicit. |
| tone_severity | ✅ pass | Two genuine filing blockers (wrong software, missing TIN) are marked 'critical'; the $0-withholding tax liability is a 'warning'; treaty optimization and FICA recovery are 'info.' The summary's '2 blocking issues' matches the critical count. Directive language like 'Stop using resident-return software' and 'do not submit the return without a valid TIN' is appropriately urgent for the scenario without being alarmist. The immigration_impact flag on the resident-software finding ('may surface during H-1B or green card adjudication') is warranted. |
| completeness | ✅ pass | The output catches all issues a competent practitioner would flag: wrong form, missing TIN with W-7 instructions, zero withholding with estimated-tax penalty warning, India treaty standard deduction, FICA exemption and refund procedure (Form 843/8316), Form 8843 requirement (in next_steps and artifacts), and the filing deadline. No obvious gap is present. |
| clarity | ✅ pass | Jargon is consistently glossed: 'FICA (Social Security / Medicare),' 'Box 4 (SS tax) and Box 6 (Medicare tax),' 'SSN or ITIN.' The distinction between 1040 and 1040-NR is explained in context rather than assumed. Consequences are stated in plain terms like 'can cost ~$1,000+ of federal tax' and 'create residency-status mistakes that trigger IRS notices.' The text is well-structured and scannable for a first-time international-student filer. |

**Notes:** This is a strong output that correctly escalates a multi-issue scenario. Minor note: the summary's 'Your student tax package for tax year 2024 has been prepared' could be slightly misleading since the service is surfacing blockers rather than delivering a ready-to-file return, but the immediate caveat 'but Guardian found 2 blocking issues that must be resolved before you file' adequately reframes expectations.

### ✅ `treaty_multistate` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | All factual claims check out. The $5,000 Article 20(c) exemption and the resulting $17,000 taxable wages are correct. FICA exemption for F-1 students in their first 5 calendar years (arrival 2022, so 3rd calendar year in 2024) is accurate. The 7.65% FICA rate, Form 843/8316 refund procedure, April 15, 2025 deadline, 1040-NR requirement, and consumer-software warning are all correct. The recommendation of NY IT-203 is defensible for a nonresident alien, and CA 540NR is the correct nonresident form. The note about Form 8833 for treaty disclosure is appropriately cautious. |
| actionability | ✅ pass | Next steps name specific forms (IT-203, 540NR, 843, 8316, 8833, 8843), specific software (Sprintax, GLACIER Tax Prep), specific W-2 boxes to check ('Box 4 (SS tax) and Box 6 (Medicare tax)'), specific websites ('tax.ny.gov', 'ftb.ca.gov'), and a concrete deadline ('2025-04-15'). The one 'confirm' instance ('confirm the physical-presence rule for CA') names the exact rule, which is enough for a self-directed user to search on. |
| tone_severity | ✅ pass | All three findings are appropriately rated 'info' severity with no alarmist language. Consequences are measured: 'the IRS may not apply the treaty benefit,' 'commonly costs ~7.65%,' 'can lead to back-tax notices.' This matches the scenario's expectation of 'useful guidance, not alarmism' for a treaty + multi-state case where the user has their documents in order. |
| completeness | ✅ pass | The output catches all key practitioner-level issues: treaty exemption with correct amount, FICA over-withholding risk, multi-state filing with physical-presence nuance, Form 8843, wrong-software warning, and Form 8833 treaty disclosure. The FICA finding is a valuable add that many students miss. No obvious gaps for this intake profile (SSN present, 1042-S present, well within the 5-year nonresident window). |
| clarity | ✅ pass | Technical terms are glossed on first use: 'FICA (Social Security / Medicare),' 'Box 4 (SS tax) and Box 6 (Medicare tax).' Findings are clearly structured with separate action and consequence fields. The multi-state explanation is plain: 'If all work was physically performed in your state of residence (NY), the employer state may have no sourcing claim.' No run-on findings or unexplained jargon. |

**Notes:** A strong output that balances detail with accessibility. The FICA finding and multi-state physical-presence caveat reflect practitioner-level awareness without overcomplicating the guidance. Minor quibble: IT-203 vs. IT-201 for an F-1 student who may be a statutory resident of NY is debatable, but IT-203 is the more commonly recommended form for nonresident aliens and is defensible.

## election_83b

_3 pass · 0 partial · 0 fail_

### ✅ `normal_grant` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The 30-day deadline of 2026-04-26 is correctly computed from a 2026-03-27 grant date. The taxable spread of $0.00 (FMV $0.001 − exercise price $0.001 × 100,000 shares) is correct. The Ogden, UT service center is appropriate for a CA filer. The irrevocability warning, the Treas. Reg. §1.83-2(d) company-copy requirement, and the post-TCJA note about not needing to attach to Form 1040 are all accurate. The statement 'for grants made in 2020 and later' is slightly imprecise (TCJA applied from 2018 tax year) but follows the service's own internal guidance and is correct for the user's 2026 situation. |
| actionability | ✅ pass | Steps are concrete and sequenced: print, sign, use USPS Certified Mail, deliver copy to 'MyStartup Inc,' keep a copy. The mailing address is given ('Internal Revenue Service, Ogden, UT 84201-0002') with a reasonable caveat to 'Confirm on irs.gov before mailing.' Downloadable artifacts (election letter, cover sheet) are provided. The taxable spread is calculated for the user so they know what to report. |
| tone_severity | ✅ pass | The verdict is 'pass' with a calm, informational tone that matches the clean scenario with 25 days remaining. The irrevocability warning ('If the stock later drops in value or you don't vest, you cannot get the tax paid back') is appropriately placed and proportionate—neither alarmist nor underweighted. No 'URGENT' flags appear, which is correct given ample remaining time. |
| completeness | ✅ pass | The output covers the filing deadline, mailing mechanics (certified mail, correct service center), company copy requirement citing the regulation, irrevocability caveat, taxable spread computation, record-keeping advice, and the Form 1040 attachment note. These are the key items a competent practitioner would address for a straightforward 83(b) election at FMV-equals-exercise-price. |
| clarity | ✅ pass | The language is accessible to a first-time founder. Jargon like 'taxable spread' is immediately explained ('FMV minus amount paid, per share, times shares'). The regulatory citation 'Treas. Reg. §1.83-2(d)' is parenthetical and follows a plain-English instruction. The structure—summary, next steps, mailing instructions, artifacts—is well-organized and easy to follow. |

**Notes:** The next_steps and mailing_instructions.steps arrays are identical, which is mildly redundant but not harmful. The 'Post-2020' threshold language could be tightened to match the actual TCJA effective date (2018 tax year), but this is immaterial for a 2026 grant and the output follows the service's own internal framing.

### ✅ `deadline_passed` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The deadline calculation of 2026-03-17 (30 days from 2026-02-15) is correct. The statement 'A late 83(b) election is generally invalid and cannot be cured' matches IRS rules. The alternatives described (fresh grant, ordinary-income recognition at vesting) are legally accurate for restricted stock. The explanation that vesting-time taxation means 'you'd pay income tax on the value of each batch of shares at the moment they become yours, rather than on the much lower value at the grant date' is correct. |
| actionability | ✅ pass | Next steps are concrete: 'Do not mail this packet before speaking with a tax advisor' is an unambiguous directive. 'Bring the grant documents, vesting schedule, and this summary to the advisor' specifies exactly what to prepare. The artifact is clearly labeled 'Download advisor review packet (do not mail)'. The alternatives are explained with enough detail that a user could meaningfully discuss them with an advisor. |
| tone_severity | ✅ pass | 'URGENT: the 30-day deadline for this 83(b) election has already passed' is appropriately framed given the irreversibility of a missed 83(b) deadline. The 'block' verdict correctly prevents the user from mailing a likely-invalid election. The repeated 'Do not mail' language matches the scenario's gravity without being hysterical. |
| completeness | ✅ pass | The output catches the critical late-filing issue, blocks mailing, directs to an advisor, and explains the two main alternatives (fresh grant with new 30-day window, or accepting ordinary-income at vesting). It notes the tax consequence difference between grant-date and vesting-date FMV. The artifact is reframed as an advisor review packet rather than a mailing packet, which is the right judgment call. |
| clarity | ✅ pass | Technical terms like 'ordinary-income recognition' are immediately followed by a plain-English parenthetical: 'which means you'd pay income tax on the value of each batch of shares at the moment they become yours.' The mailing_instructions headline 'Deadline passed 15 days ago' is immediately understandable. The overall structure—summary, next_steps, mailing_instructions—makes the critical message hard to miss. |

**Notes:** This is a well-constructed output for a critical scenario. The service correctly blocks the user from mailing, explains why in accessible language, and provides specific next steps centered on professional consultation. The only very minor omission is that it doesn't note the income amount recognized under 83(b) would have been $0 (FMV = exercise price), which underscores the stakes, but this is a nitpick rather than a gap.

### ✅ `texas_service_center` — PASS

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The 30-day deadline of 2026-04-21 from a grant date of 2026-03-22 is correctly computed. The mailing address 'Internal Revenue Service, Austin, TX 73301-0002' is the correct IRS service center for a TX filer, satisfying the scenario requirement. The taxable spread of $0.00 (FMV $0.005 − exercise $0.005 × 10,000) is correct. The post-2020 attachment rule, irrevocability, certified-mail requirement, and Treas. Reg. §1.83-2(d) company-copy requirement are all accurate. |
| actionability | ✅ pass | Steps are concrete and sequenced: print, sign, mail via certified mail to a specific address, deliver a copy to TexCo Inc, and keep records. Downloadable artifacts ('83b-election-letter.pdf', '83b-cover-sheet.pdf') are provided. The 'Confirm on irs.gov before mailing' hedge is slightly vague but reasonable as a safety measure alongside an already-specific address. |
| tone_severity | ✅ pass | The irrevocability warning ('If the stock later drops in value or you don't vest, you cannot get the tax paid back') is appropriately prominent without being alarmist. The deadline framing '20 days from today' conveys appropriate urgency. The verdict of 'pass' matches the straightforward facts: deadline not yet passed, zero spread, correct jurisdiction. |
| completeness | ✅ pass | The output covers all key compliance points: deadline, mailing address, certified mail, company copy, record-keeping, post-2020 return-attachment rule, irrevocability, and the spread calculation. A practitioner might additionally explain why filing at a $0 spread is still beneficial (future appreciation taxed as capital gains), but this is advisory rather than compliance and the service's scope is filing assistance. |
| clarity | ✅ pass | The language is accessible to a first-time founder. The one piece of jargon ('Treas. Reg. §1.83-2(d)') is used as a citation alongside a plain-English instruction ('Deliver a signed copy of the election to the company'). The spread is explained inline: 'FMV minus amount paid, per share, times shares'. Sentences are concise and well-structured. |

**Notes:** The output correctly uses the Austin, TX IRS service center address rather than a generic fallback, satisfying the scenario's key requirement. The 'for grants made in 2020 and later' phrasing is slightly imprecise (the TCJA change actually took effect for tax years beginning after 2017), but this has no practical consequence for a 2026 grant and the advice is correct.
