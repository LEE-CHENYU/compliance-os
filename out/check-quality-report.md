# Check Quality Scorecard

Generated 2026-04-15 06:18 UTC — judge: claude-opus-4-6 (adaptive thinking)

**Totals:** 0 pass · 8 partial · 4 fail · 12 cases
**Tokens:** 20,931 in · 28,187 out

## h1b_doc_check

_0 pass · 1 partial · 2 fail_

### ⚠️  `clean_packet` — PARTIAL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The output makes no incorrect factual or regulatory claims. Entity-name comparisons ('Orbital Robotics Inc' ↔ 'Orbital Robotics Inc'), amount comparisons ('$2780' ↔ '$2780'), and signatory-cardholder matches ('Alice Chen' ↔ 'Alice Chen') are all accurately assessed as matching with confidence 1.0. The verdict of 'pass' is defensible given the internally consistent dataset. |
| actionability | ⚠️  partial | The sole next step—'The packet looks internally consistent based on the uploaded documents.'—is a declarative observation, not an actionable instruction. A self-directed beneficiary without counsel needs concrete guidance such as the petition filing deadline, what supporting documents to gather next, or whether to confirm E-Verify enrollment with the employer. The output gives the user nothing to execute. |
| tone_severity | ✅ pass | The summary '0 critical, 0 warning, and 0 informational items' with a 'pass' verdict appropriately reflects a consistent packet. There is no alarmism and no under-warning; the severity framing matches the actual risk level. |
| completeness | ✅ pass | For a document-consistency check on a clean packet, the output covers the key cross-document comparisons: entity names (registration ↔ G-28, registration ↔ invoice), authorized signatory ↔ cardholder, and invoice ↔ receipt amounts. It also confirms all 5 expected doc types are present. A minor gap is the absence of a beneficiary-name cross-check (G-28 client_name vs. invoice beneficiary_name), but both say 'Wei Zhang' so no finding was missed. |
| clarity | ✅ pass | The summary is concise and the structured comparisons (with 'status: match' labels) are easy to parse for a non-expert. No unexplained jargon is used, and the document-summary echo lets the user verify what was extracted. |

**Notes:** The output correctly handles the clean-packet scenario with accurate comparisons and appropriate severity, but the next_steps section is functionally empty for a self-directed user. Even for a passing packet, guidance like 'file before the petition window closes on [date]' or 'confirm your employer's E-Verify enrollment' would materially improve usefulness.

### ❌ `entity_suffix_mismatch` — FAIL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ❌ fail | The field `"immigration_impact": false` is factually incorrect. An Inc-vs-LLC entity-type mismatch across petition documents is a well-known USCIS rejection trigger, not merely a billing discrepancy. The consequence text ('Billing mismatches can indicate the wrong entity is being prepared for filing') omits the regulatory reality that USCIS will reject the petition if entity names are inconsistent. |
| actionability | ⚠️  partial | The sole next step—'Confirm the billing record is tied to the same petitioner listed in the registration'—is too vague for a self-directed beneficiary. It does not tell the user which document to correct (invoice), who to contact (employer or attorney), or what the correct entity name is. A competent recommendation would instruct the user to verify the employer's legal entity name via incorporation documents and obtain a corrected invoice before filing. |
| tone_severity | ❌ fail | The finding is rated `"severity": "warning"` and counted as '0 critical' in the summary. Because Inc ≠ LLC is a USCIS rejection trigger per standard practice, this should be critical. Framing the issue as 'Billing mismatches can indicate the wrong entity is being prepared for filing' seriously under-warns a self-directed user who may treat it as a minor administrative matter and proceed to file. |
| completeness | ⚠️  partial | The cross-document comparison correctly detects the Inc/LLC mismatch and the missing status summary document. However, the finding never states that all entity names must match exactly across the petition packet, nor that this specific type of mismatch is a known rejection reason. A competent practitioner would also note that the G-28 says 'Orbital Robotics Inc' consistent with the registration, isolating the invoice as the outlier document—this is not surfaced. |
| clarity | ⚠️  partial | The comparison detail 'Base names match (100%) but entity types differ: inc vs llc' is admirably clear. However, the finding title 'Invoice petitioner name does not match the registration' and its billing-focused consequence could mislead a non-expert into thinking this is only a financial record-keeping issue, not a petition-threatening legal inconsistency. |

**Notes:** The system correctly detects the Inc/LLC mismatch at the comparison layer but critically mischaracterizes it at the finding and severity layers. For a self-directed user without counsel, under-flagging a known USCIS rejection trigger as a non-immigration-impact 'warning' is the most consequential error: the user could proceed to file and face rejection. The finding, next steps, and severity should all be upgraded to convey that this mismatch must be resolved before the petition is submitted.

### ❌ `only_one_doc_uploaded` — FAIL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ⚠️  partial | The verdict ('incomplete'), missing-document list, and summary ('Only 1 of 5 expected') are all factually correct. However, the findings make false factual claims: 'Entity names do not align across the registration and G-28' is incorrect because no G-28 was uploaded — there is no misalignment, only absence. Similarly, 'Invoice petitioner name does not match the registration' and 'Invoice total and payment receipt amount do not match' assert discrepancies that cannot exist given the missing documents. The comparisons section is more honest ('One or both values missing'), but the findings contradict it. |
| actionability | ⚠️  partial | The next_steps list is specific and executable: 'Upload the h1b_status_summary document', etc. — a self-directed user knows exactly what to do. However, the 4 findings inject premature action items (e.g., 'Make sure the same petitioner legal name appears in both the USCIS registration and the G-28') that are not actionable because the referenced documents have not been uploaded. This dilutes the clear guidance with noise the user cannot act on yet. |
| tone_severity | ❌ fail | The first finding is marked 'critical' severity with the title 'Entity names do not align across the registration and G-28', but the G-28 does not exist in the packet — there is literally no consequence to flag. Labeling a phantom comparison as 'critical' is alarmist and directly contradicts the scenario expectation of 'specific guidance on what's still needed, not a noise-filled cross-check report.' The output produces exactly the noise it was supposed to avoid: 4 findings with severities (critical, warning, warning, info) all based on comparisons against null values. |
| completeness | ✅ pass | All four missing document types are correctly enumerated in both 'missing_doc_types' and 'next_steps'. The summary correctly notes that cross-checks are unreliable on a partial packet. Given only a registration was uploaded, there is nothing else a competent practitioner would flag beyond the incompleteness itself. |
| clarity | ⚠️  partial | The summary is clear and well-written for a non-expert: 'cross-checks are unreliable on partial packets' sets appropriate expectations. However, the findings undermine this by presenting phantom issues as real problems. A beneficiary without counsel reading 'Entity names do not align' or 'Invoice total and payment receipt amount do not match' is likely to think something is wrong with the documents they have, rather than understanding these are artifacts of missing uploads. |

**Notes:** The output correctly identifies the packet as incomplete and provides clear upload guidance in the summary and next_steps. The core problem is that it also emits 4 cross-check findings — including one at 'critical' severity — against documents that were never uploaded. This is the exact anti-pattern the scenario warns against ('not a noise-filled cross-check report'). Suppressing or gating these findings behind document upload would fix most issues.

## fbar_check

_0 pass · 3 partial · 0 fail_

### ⚠️  `under_threshold_no_filing` — PARTIAL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ⚠️  partial | The aggregate calculation ($4,000 + $3,500 = $7,500) and the no-filing conclusion are correct. However, providing a 'filing_deadline' of '2025-10-15' for a user who has no filing obligation is misleading — it implies a deadline they must meet. More critically, the artifacts section offers a 'Download FBAR draft packet' which directly contradicts the 'requires_fbar: false' determination and could imply the user still needs to take filing action. |
| actionability | ⚠️  partial | The next steps ('Keep a record of the balances…', 'Re-check the aggregate maximum balance if you open new foreign accounts…') are specific and appropriate for a no-file scenario. However, the artifact 'Download FBAR draft packet' introduces an ambiguous action: a self-directed user seeing a downloadable draft packet alongside a no-filing conclusion will not know whether they should download and file it or ignore it. |
| tone_severity | ✅ pass | The summary ('does not trigger an FBAR filing requirement') is appropriately reassuring without being dismissive. There is no alarmism, which matches the low-risk outcome. The tone is well-calibrated for a user who should walk away unburdened. |
| completeness | ⚠️  partial | The output never states the $10,000 threshold, so the user cannot understand how close they are to triggering a filing obligation or why $7,500 is below the line. A competent practitioner would cite the threshold for context. Additionally, a brief note distinguishing FBAR from FATCA/Form 8938 (which has different thresholds) would help the typical non-resident audience avoid conflating the two. |
| clarity | ⚠️  partial | The summary sentence is clear and accessible. However, the juxtaposition of 'requires_fbar: false' with the artifact labeled 'Download FBAR draft packet' creates a contradictory signal that would confuse a non-expert user — they may reasonably wonder why a draft is being generated for a form they supposedly don't need to file. |

**Notes:** The core determination (no FBAR required, aggregate $7,500) is correct and clearly stated. The main defects are (1) the contradictory FBAR draft packet artifact, which undermines the no-filing conclusion, (2) a populated filing_deadline field that is irrelevant to this user, and (3) the absence of the $10,000 threshold citation that would give the user the 'why' behind the result.

### ⚠️  `over_threshold_must_file` — PARTIAL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | Aggregate balance ($8,500 + $7,200 + $6,000 = $21,700) is correctly computed. The threshold is correctly stated as '$10,000'. Filing via 'BSA E-Filing System' (not IRS) is accurate. The deadline of '2025-10-15' is effectively correct given the automatic extension (post-2017 SAT); omitting the April 15 original date is a simplification but not an error since no action is required to obtain the extension. |
| actionability | ⚠️  partial | 'Use the BSA E-Filing System to submit FinCEN Form 114 online' names the correct system but does not provide the URL (bsaefiling.fincen.treas.gov), which would meaningfully reduce friction for a self-directed user. The output also omits the important instruction that all three accounts must be reported on the FBAR (not just those individually over $10K), which a first-time filer could easily misunderstand. |
| tone_severity | ⚠️  partial | The output is calm and matter-of-fact, which avoids alarmism. However, it entirely omits any mention of non-filing penalties (non-willful up to ~$16K/year; willful up to the greater of ~$129K or 50% of balance). For a filing obligation with consequences this severe, a brief note about the importance of timely compliance would be appropriate and is an under-warning. |
| completeness | ⚠️  partial | A competent practitioner would note: (1) penalty exposure for non-compliance — not mentioned; (2) that FBAR is separate from Form 8938/FATCA, which has a higher threshold and different filing channel — not mentioned; (3) that all three accounts must be listed on the filing even though none individually exceeds $10K — not mentioned. These are standard advisory points for a user in this scenario. |
| clarity | ✅ pass | The summary is concise and plainly worded: 'Your reported aggregate maximum balance was $21,700.00, which is above the $10,000 threshold.' Technical terms like 'BSA E-Filing System' and 'FinCEN Form 114' are unavoidable official names and are presented in context ('submit … online'). The output structure (summary, next steps, account echo-back) is easy to follow for a non-expert. |

**Notes:** The output gets the core determination right and is clearly written, but falls short on practitioner-level completeness: no penalty warnings, no FBAR-vs-FATCA disambiguation, and no explicit instruction that all accounts must be reported. Adding a BSA E-Filing URL would also meaningfully improve actionability.

### ⚠️  `fractional_boundary` — PARTIAL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The aggregate balance is correctly computed as $10,000.01 (9999.50 + 0.51), the filing determination is correct ('above the $10,000 threshold'), the BSA E-Filing System is correctly named as the filing channel, and the 2025-10-15 deadline reflects the automatic extension. No legal or regulatory inaccuracies detected. |
| actionability | ✅ pass | Steps name the specific filing system ('BSA E-Filing System'), the specific form ('FinCEN Form 114'), the exact deadline ('2025-10-15'), and what to verify ('maximum balance and account numbers'). The rubric flags 'review' without a named target, but here the targets are explicit. A URL for BSA E-Filing would strengthen this but its absence isn't disqualifying. |
| tone_severity | ✅ pass | The output uses a matter-of-fact tone ('FinCEN filing is required') without alarmism or downplaying. Given the user has a genuine filing obligation and ample time (automatic extension to October 15), the framing is proportionate. No 'URGENT' flags or inappropriate hedging. |
| completeness | ⚠️  partial | The aggregate is only $0.01 over the $10,000 threshold. A competent practitioner would prominently flag this razor-thin margin and urge the user to verify reported balances to the cent, since a $0.02 difference eliminates the filing obligation. The output's generic 'Review each foreign account one more time' does not call attention to how consequential small rounding could be. Additionally, no mention of non-filing penalties (~$16K non-willful) or the distinction from Form 8938/FATCA. |
| clarity | ✅ pass | Language is plain and accessible. Necessary jargon ('FinCEN Form 114', 'BSA E-Filing System') is unavoidable and the user needs these terms to act. 'Aggregate maximum balance' is clear enough in context. No run-on findings or unexplained acronyms. |

**Notes:** The output handles fractional-dollar arithmetic correctly and gets the core determination right, but the near-miss scenario ($0.01 over threshold) is exactly the kind of situation where a practitioner would add an explicit caution about verifying balances to the cent. The omission is meaningful because a tiny adjustment could flip the filing requirement entirely.

## student_tax_1040nr

_0 pass · 1 partial · 2 fail_

### ❌ `clean_w2_only` — FAIL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ❌ fail | Two factual errors. First, the output contains contradictory deadlines: top-level `"filing_deadline": "2025-04-15"` (correct) vs. `filing_context.filing_deadline: "2026-04-15"` and `deadline_label: "April 15, 2026"` (both wrong for TY 2024). Second, `"claim_treaty_benefit": false` is incorrect for a Chinese F-1 student: Article 20(c) of the China-US treaty exempts up to $5,000/yr of student-earned income, which should be claimed on a $25K wage return. |
| actionability | ⚠️  partial | The next steps name specific documents (W-2, 1042-S) and a deadline, which is good. However, they omit the most valuable concrete action: claiming the China-US treaty Article 20(c) benefit and attaching the required Form 8833 or treaty-based position. Mentioning '1042-S' in step 1 without explaining whether the user should expect one is also potentially confusing when no treaty claim is being made. |
| tone_severity | ⚠️  partial | Presenting '0 issues worth checking' when the student is leaving ~$500+ on the table by not claiming an applicable treaty benefit constitutes under-warning on a financially meaningful omission. The calm tone is appropriate in general, but the missing treaty benefit warrants at least an informational finding. |
| completeness | ❌ fail | A competent practitioner would immediately identify the China-US treaty Article 20(c) $5,000 exemption for a Chinese F-1 student earning wages. The output completely misses this, resulting in higher taxable income ($25,000 instead of $20,000). The internal deadline inconsistency (2025 vs. 2026) is also an obvious quality-control miss. |
| clarity | ✅ pass | The summary, mailing instructions, and next steps are written in plain language and are easy to follow for a non-expert international student. Terms like '1040-NR' and 'Form 8843' are used in context with clear actions attached. |

**Notes:** The two critical issues are (1) the contradictory filing deadline (2025-04-15 at top level vs. 2026-04-15 in filing_context), which could cause a student to miss their deadline by a full year, and (2) the failure to surface the China-US treaty Article 20(c) $5,000 exemption, which directly costs the student money. Despite the scenario expecting 0 findings, these are genuine deficiencies a competent practitioner would catch.

### ❌ `turbotax_user_no_itin` — FAIL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ❌ fail | The output contains a contradictory filing deadline: top-level `filing_deadline` is '2025-04-15' (correct for TY2024) but `filing_context.filing_deadline` is '2026-04-15' (wrong). Additionally, `claim_treaty_benefit` is false and `treaty_country` is null despite the user being an Indian citizen on F-1, where the India-US treaty permits claiming the standard deduction—an applicable benefit the system should surface. Finally, characterizing $0 withholding on $30K wages only as a data-quality issue ('Missing withholding data can distort the draft payment/refund expectation') ignores the near-certain substantial tax liability and possible underpayment penalties. |
| actionability | ⚠️  partial | The resident-software finding says 'Double-check that your preparer or software is using the nonresident return path before filing,' which is too vague—it should explicitly name nonresident-specific tools (e.g., Sprintax, Glacier Tax Prep) and clearly state that TurboTax cannot produce a valid 1040-NR. The ITIN finding helpfully names Form W-7 and the concurrent-filing option. However, no step addresses the likely tax balance due or how to pay, which is critical for a user who will owe thousands. |
| tone_severity | ❌ fail | The missing SSN/ITIN finding is labeled 'warning' despite the consequence stating the return 'will be rejected by the IRS'—this should be 'critical.' The $0-withholding finding is labeled 'info' even though $30K in wages with zero withholding implies thousands owed and potential penalties—'info' dramatically understates the risk. The summary ('flagged 3 issues worth checking before filing') reads as casual despite the scenario containing multiple blocking problems. The overall tone fails to 'reflect urgency' as the scenario requires. |
| completeness | ❌ fail | A competent practitioner would flag at least three additional issues the output misses entirely: (1) the India-US treaty standard-deduction benefit, which could materially reduce tax owed; (2) the likely substantial tax liability (rough estimate or at minimum a warning) given $30K wages and $0 withholding; (3) potential underpayment/estimated-tax penalties. The output also never explicitly tells the user to stop using TurboTax—only to 'double-check'—leaving the door open for re-filing with the same wrong software. |
| clarity | ⚠️  partial | The language is generally accessible, and terms like 'Form W-7' are accompanied by brief context. However, the contradictory deadlines ('2025-04-15' vs. '2026-04-15') could confuse a first-time filer. The breezy summary ('Your student tax package for tax year 2024 is ready') combined with three serious issues creates a mixed message that may lead a non-expert to underestimate the gravity of their situation. |

**Notes:** The output identifies the correct top-level issues (wrong software, missing TIN, zero withholding) but severely mis-calibrates their severity, omits the India treaty standard-deduction benefit entirely, contains a contradictory deadline, and never warns the user they likely owe a significant tax balance. For a scenario designed to test urgent multi-problem handling, the output reads as inappropriately reassuring.

### ⚠️  `treaty_multistate` — PARTIAL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ⚠️  partial | The top-level 'filing_deadline' is correctly stated as '2025-04-15', but 'filing_context.filing_deadline' contradicts it with '2026-04-15' and 'deadline_label' reads 'April 15, 2026'. For tax year 2024 the correct deadline is April 15, 2025; the filing_context value is off by a full year and could mislead a self-directed filer. All other factual claims (1040-NR as the correct form, Form 8843 requirement, Article 20(c) applicability for Chinese students) are accurate. |
| actionability | ⚠️  partial | The step 'Confirm the treaty article and support before claiming treaty benefits in the return package' is vague — it does not explain what 'support' means or what the user should confirm, especially since they already have a 1042-S. The output also never tells the user which software or service can correctly prepare Form 1040-NR (e.g., Sprintax, GLACIER Tax Prep) nor warns against using TurboTax/FreeTaxUSA, which is critical for a self-directed nonresident filer. The multi-state step 'Check each state's nonresident filing rules' could be improved by naming the relevant forms (CA 540NR, NY IT-203). |
| tone_severity | ✅ pass | The multi-state finding is appropriately tagged 'info' with 'immigration_impact: false', matching the actual low-urgency nature of the issue. The consequence 'Missing state returns can lead to back-tax notices from the state revenue department' is proportionate and factual. No alarmism is present, consistent with the scenario expectation of 'useful guidance, not alarmism.' |
| completeness | ⚠️  partial | A competent practitioner would note that Article 20(c) exempts only $5,000 of the $22,000 wage income, making roughly $17,000 federally taxable — this critical detail is absent. The output also omits any mention of FICA exemption (F-1 students in years 1–5 are generally FICA-exempt; if FICA was withheld, a refund may be available). Finally, the warning against using resident-return software (TurboTax, H&R Block, FreeTaxUSA) is a standard practitioner flag that is missing. The multi-state catch is good. |
| clarity | ✅ pass | The language is accessible to a non-expert international student. Terms like '1040-NR,' 'Form 8843,' and 'treaty article' are necessary and used in context. The mailing instructions and artifact labels ('Download Form 8843,' 'Download treaty review memo') are clearly labeled and easy to follow. No run-on findings or unexplained jargon. |

**Notes:** The contradictory filing deadlines (2025-04-15 vs. 2026-04-15) are the most concerning issue — a user reading the filing_context section would see an incorrect year. The missing $5,000 treaty exemption limit and lack of software guidance are meaningful completeness gaps for a self-directed user. The overall structure, tone, and multi-state flag are well-handled.

## election_83b

_0 pass · 3 partial · 0 fail_

### ⚠️  `normal_grant` — PARTIAL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The filing deadline of 2026-04-26 (30 days from 2026-03-27) is correctly computed, and '25 days from today' is consistent with a grant 5 days ago. The verdict of 'pass' is appropriate. The mailing-instructions summary says 'the election was mailed within 30 days' which is substantively correct, though the more precise term is 'postmarked'; no material legal misstatement. |
| actionability | ⚠️  partial | Steps like 'Print the election letter,' 'Sign the election letter before mailing it,' and 'Use USPS Certified Mail' are specific and executable. However, the output never specifies the IRS service center mailing address for a California filer. A self-directed user cannot complete the mailing without that destination address, which is a significant gap. |
| tone_severity | ✅ pass | The tone is calm and informational, matching a clean-pass scenario with 25 days remaining. There is no alarmism, and the deadline is stated plainly in the summary. Appropriately framed for the actual risk level. |
| completeness | ⚠️  partial | A competent practitioner would always include the destination IRS service center address (determined by the taxpayer's filing address in CA). The output omits this entirely. It also does not mention providing a copy to the company/transfer agent, which is standard best practice. The post-2020 guidance about not needing to attach a copy to the return is correctly handled by omission. |
| clarity | ✅ pass | The output is well-organized with a clear summary, numbered steps, and labeled artifacts. Language is accessible to a first-time founder; no unexplained jargon. The distinction between 'election letter' and 'cover sheet' artifacts is intuitive. |

**Notes:** The main shortcoming is the omission of the IRS mailing address. For a self-directed user in Palo Alto, CA, the output should specify the relevant IRS service center (e.g., Ogden, UT). Everything else — deadline math, tone, document artifacts, Certified Mail guidance — is solid.

### ⚠️  `deadline_passed` — PARTIAL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | All factual and legal claims are accurate. The 30-day deadline calculation ('filing_deadline: 2026-03-17') is correct (30 days from Feb 15). 'A late 83(b) election is generally invalid and cannot be cured' correctly states the rule. The mention of Section 83(i) as a discussion topic is a real code provision, and framing it as something to raise with an advisor is appropriate. |
| actionability | ⚠️  partial | The next_steps are specific and executable: 'Do not mail this packet before speaking with a tax advisor' and 'Bring the grant documents, vesting schedule, and this summary to the advisor' are both concrete. However, providing 'artifacts' with labels like 'Download 83(b) election letter' and 'Download 83(b) cover sheet' without any caveat creates ambiguity — a self-directed user may download and mail them despite the warning, undermining the otherwise clear instructions. |
| tone_severity | ✅ pass | 'URGENT: the 30-day deadline for this 83(b) election has already passed' is appropriately alarming for a situation with no cure provision. The 'block' verdict correctly prevents casual action. 'Do not mail this packet' is repeated in next_steps and mailing_instructions, matching the gravity of a missed, irrecoverable deadline. |
| completeness | ⚠️  partial | The output correctly identifies the passed deadline, blocks the filing, and recommends advisor consultation. However, it still generates and exposes downloadable artifacts ('83b-election-letter.pdf', '83b-cover-sheet.pdf') for an election that should not be mailed. A competent practitioner would suppress these artifacts entirely or label them 'FOR ADVISOR REVIEW ONLY' to prevent the user from self-filing a counterproductive late election. |
| clarity | ⚠️  partial | The summary and next_steps are clearly written and accessible. However, the simultaneous presence of 'Do not mail this packet' alongside download links for the election letter and cover sheet sends a contradictory signal to a non-expert user. Additionally, 'alternative tax planning such as Section 83(i) or voluntary recognition' introduces jargon ('voluntary recognition' is not a standard term) without brief explanation, though framing it as an advisor discussion topic partially mitigates this. |

**Notes:** The output handles the critical blocking behavior and deadline messaging very well. The main deficiency is that ready-to-mail artifacts are still surfaced with no suppression or caveat, which directly contradicts the 'do not mail' guidance and poses a real risk for a self-directed user who may ignore the text and just click download. Suppressing or strongly caveating those artifacts would bring this to a pass.

### ⚠️  `texas_service_center` — PARTIAL

| Dimension | Rating | Reasoning |
|---|---|---|
| correctness | ✅ pass | The filing deadline of 2026-04-21 (30 days after 2026-03-22) is correctly computed. Certified Mail guidance, record-keeping advice, and the omission of any requirement to attach a copy to the annual return are all legally accurate post-2020. The claim '20 days from today' is unverifiable without knowing the run date but the hard deadline itself is correct. |
| actionability | ⚠️  partial | The four mailing steps are concrete and executable, but the instructions never state the specific IRS service center mailing address. A self-directed user reading the steps would not know WHERE to mail the packet without opening the cover-sheet PDF and hoping the address is there. The scenario specifically requires the Austin, TX service center address to be surfaced, yet the output text only says 'Mail your 83(b) election with proof' with no destination address. |
| tone_severity | ✅ pass | The tone is appropriately informational. The summary conveys a clear deadline without alarmism ('must be mailed no later than 2026-04-21'). There is no misuse of 'URGENT' or critical-level framing, which is correct given the deadline has not yet passed. |
| completeness | ⚠️  partial | The scenario explicitly requires the Austin IRS service center to appear (not a generic fallback), but the output JSON contains no mailing address anywhere—neither in 'mailing_instructions' nor 'next_steps'. Additionally, a competent practitioner would note the $0 income inclusion amount (FMV equals exercise price at $0.005), which is the whole economic reason for filing; the output is silent on this. |
| clarity | ✅ pass | The language is plain and accessible to a first-time founder. Steps are numbered and use everyday verbs ('Print', 'Sign', 'Use USPS Certified Mail', 'Keep a complete signed copy'). No unexplained jargon is present. |

**Notes:** The main gaps are (1) the IRS mailing address is absent from the output text, which the scenario specifically tests, and (2) the recognized income amount ($0, since FMV equals exercise price) is not mentioned anywhere, missing a key reassurance for the filer. The legal mechanics and tone are otherwise solid.
