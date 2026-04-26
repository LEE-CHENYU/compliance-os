# Guardian Customer Success Training Guide

**Version:** 1.0  
**Date:** 2026-04-14  
**Audience:** Customer success consultants, onboarding specialists, and anyone speaking to prospective Guardian users  
**Purpose:** Enable every consultant to speak credibly about immigrant compliance pain points, position Guardian's value accurately, and guide users to the right service tier.

---

## Part 1 — What Guardian Is (and Is Not)

### What Guardian does

Guardian is an AI-powered compliance cross-checker for immigrants. It reads immigration documents, tax documents, and corporate documents **together** — and catches conflicts that no single-domain advisor ever sees.

- A user uploads their I-797 approval notice, their 1040-NR, and their cap table
- Guardian checks whether the visa type is consistent with the equity structure, whether FBAR was triggered when they became a resident alien, whether their 83(b) election was filed correctly given their immigration status at the time
- It surfaces risks, flags missing filings, and routes the user to the appropriate professional

### What Guardian is not

- Not a law firm. Guardian does not give legal advice.
- Not a CPA firm. Guardian does not prepare tax returns (at Tier 0; at Tier 1+ a licensed EA does).
- Not a document filing service unless the user purchases a professional service tier.

### The one-sentence pitch

> "Guardian is the only tool that checks your immigration status, your tax filings, and your corporate documents together — catching the conflicts no single attorney or accountant can see."

### Why this exists

Every immigrant in the US deals with at least two professional domains simultaneously — an immigration attorney for their visa, a CPA or TurboTax for their taxes. Immigrant founders add a third: an equity or corporate attorney. These advisors never talk to each other. The gaps between them are where the most expensive compliance mistakes happen.

---

## Part 2 — The Mental Model Every Consultant Must Own

### NRA vs. Resident Alien — the status that changes everything

| | Non-Resident Alien (NRA) | Resident Alien (RA) |
|---|---|---|
| Taxed on | US-source income only | Worldwide income |
| Tax return | 1040-NR | 1040 (same as US citizen) |
| FBAR required | No | Yes |
| Social Security / Medicare (FICA) | Exempt (F-1/J-1 students) | Required |
| Typical profile | F-1/J-1 first 5 years, new arrivals | H-1B year 3+, green card holders |
| Treaty positions | Most available | Some restricted |

### Substantial Presence Test (SPT) — how you become a RA

183+ days, calculated as: **all days this year** + **⅓ of last year's days** + **⅙ of the year before**.

F-1 and J-1 students are "exempt individuals" — their days don't count — for:
- **F-1:** First 5 calendar years in the US
- **J-1 students:** First 5 calendar years
- **J-1 researchers/scholars:** First 2 calendar years out of the last 6

After the exempt period expires, days start counting. Most people don't know when this happens.

### Why this matters for every conversation

The moment someone crosses from NRA to RA, **4–5 compliance obligations change simultaneously:**
- FBAR becomes required (all foreign accounts >$10K aggregate)
- Worldwide income becomes taxable
- FICA taxes kick in
- RSU tax treatment changes
- Some treaty positions become unavailable or must be re-evaluated

No single advisor tracks this transition across all domains. That's the gap Guardian fills.

---

## Part 3 — The User Lifecycle

Understanding where someone is in their immigration journey tells you exactly which Guardian services are relevant.

```
F-1/J-1 Student
    │  Form 8843 (annual), treaty benefits, 1040-NR
    │  Guardian: Free Form 8843 generator, treaty check
    ▼
OPT / STEM OPT
    │  I-983 compliance, unemployment clock, SEVIS reporting
    │  Guardian: OPT compliance check, FICA refund check
    ▼
H-1B
    │  FBAR triggers (if SPT met), LCA compliance, PERM starts
    │  Guardian: FBAR alert, cross-domain status check
    ▼
PERM / I-140 / I-485
    │  AC21 portability, priority dates, adjustment of status
    │  Guardian: Document cross-check before USCIS filing
    ▼
Green Card (Lawful Permanent Resident)
    │  Worldwide income, FBAR required, global asset reporting
    │  Guardian: Full residency compliance check
    ▼
Naturalization (optional)
    │  Citizenship, global tax obligations remain
```

**For founders, a parallel track runs alongside:**
```
Company formation (Day 1)
    │  83(b) election (30-day window), entity type, cap table
    ▼
Seed / Series A
    │  QSBS eligibility, RSU vs. restricted stock, 409A
    ▼
Liquidity / Exit
    │  QSBS exclusion, NRA→RA status at exit, FBAR current?
```

---

## Part 4 — User Segments

### Segment 1: International Students (F-1 / J-1)

**Who they are:** Undergraduate, graduate, and doctoral students. Typically age 18–30. Many are from China, India, South Korea, Taiwan.

**Their biggest compliance risks:**
- Not filing Form 8843 (required annually even with $0 income)
- Missing tax treaty benefits they're entitled to (often thousands of dollars/year)
- Not knowing when their 5-year exempt period expires and SPT clock starts
- F-2/J-2 dependents who also need to file 8843 — often completely overlooked

**What they fear:** Anything that jeopardizes their H-1B lottery chances or green card eligibility later. Most are thinking 10 years ahead.

**Guardian value prop:**
- Free Form 8843 generator — 2 minutes, no account needed, downloads ready-to-mail PDF
- Treaty benefit check — surfaces Article 20 (China), Article 21 (Korea), etc. and calculates approximate refund owed
- SPT proximity alert — warns them when their exempt window is about to expire

**Opening line:**
> "Form 8843 is due June 15 and most students have never heard of it. Missing it starts a clock that can make you a resident alien retroactively — which affects your taxes now and your H-1B eligibility later. Guardian generates it free in 2 minutes."

---

### Segment 2: J-1 Researchers and Scholars

**Who they are:** Visiting professors, postdoctoral researchers, research scientists at universities. Often mid-career (30s–50s), from China, Germany, Japan, Korea, India.

**Distinct from J-1 students:** Their exempt period is only **2 years out of the last 6**, not 5 years. Many J-1 scholars don't know this and assume they have the same 5-year window as students.

**Their biggest compliance risks:**
- Assuming they're still NRA when they've already hit SPT
- Missing Article 19 of the US-China treaty (3-year exclusion on teaching/research income for professors)
- J-2 spouse working without proper EAD authorization
- Missing FBAR after inadvertently becoming RA

**Guardian value prop:**
- SPT calculation with the 2-year J-1 research exception correctly applied
- Treaty benefit check with Article 19 specifically flagged for Chinese scholars
- FBAR trigger alert when SPT is met

**Opening line:**
> "Most J-1 researchers assume they have the same 5-year exempt window as students — they actually have 2 years. If you've been here 2+ years, you may already be a resident alien with FBAR and worldwide income obligations you didn't know about."

---

### Segment 3: OPT / STEM OPT Workers

**Who they are:** Recent graduates working their first US job. Often at tech companies, startups, or research roles. Typically age 22–28.

**Their biggest compliance risks:**
- Not tracking unemployment days (90-day limit for OPT, 150 combined for STEM OPT)
- Changing employers without updating I-983 training plan before start date
- Employer not on E-Verify list for STEM OPT (invalidates the extension)
- Missing that they may now owe FICA taxes (depends on SPT)
- Not realizing their treaty benefits from student days may no longer apply once employed

**What they fear:** Anything that disqualifies them from the H-1B lottery — STEM OPT violations are the most common disqualifier people don't see coming.

**Guardian value prop:**
- OPT compliance checklist — tracks unemployment days, employer changes, SEVIS status
- E-Verify employer verification
- FICA exemption check (still NRA during OPT? FICA exempt)
- H-1B preparation check — clean record before lottery

**Opening line:**
> "The most common reason H-1B petitions get flagged is a STEM OPT compliance gap the employer didn't catch. Guardian checks your OPT record before you apply."

---

### Segment 4: H-1B Tech Employees

**Who they are:** Engineers, scientists, product managers, researchers at US tech companies. Often 3–8 years into their US career. Predominantly Chinese and Indian nationals.

**Their biggest compliance risks:**
- FBAR not filed since becoming RA (often 2–4 years of missed filings)
- Foreign accounts they're signatories on (parents' joint accounts) crossing the $10K threshold
- Working remotely from a different metro than the LCA-approved worksite without amended LCA
- Job duty changes that technically require amended H-1B petition
- Employer layoff: not understanding the 60-day grace period
- RSU taxation shifting as they move from NRA to RA
- Missing the PERM filing window (priority dates for China and India are decades long)

**Key insight to always share:** Their employer's immigration attorney represents the company, not them. The attorney filed their H-1B correctly. They have zero visibility into the employee's FBAR exposure, treaty positions, or foreign accounts. That gap is Guardian's job.

**Guardian value prop:**
- FBAR exposure check with specific calculation of their likely required filing years
- Cross-domain status check: H-1B + tax residency + FBAR all together
- PERM timeline reality check (China and India backlogs — sets expectations)
- H-1B compliance audit (LCA worksite, duty changes)

**Opening line:**
> "Your employer's immigration attorney's client is the company, not you. They filed your H-1B correctly. They have no visibility into your FBAR obligations since you hit Substantial Presence — that's your responsibility, and Guardian checks it for you."

---

### Segment 5: PERM / Green Card Applicants

**Who they are:** H-1B holders who have been in the US 4+ years and are in the employer-sponsored green card process. Often dealing with long priority date backlogs (China/India).

**Their biggest compliance risks:**
- Not understanding AC21 portability (mistakenly staying in bad jobs)
- Job change after I-485 filing without invoking AC21 correctly
- Priority date retrogression not factored into career planning
- Concurrent filings (I-140 + I-485) creating document consistency requirements across three domains
- Not knowing that H-4 spouse can work if I-140 is approved (H-4 EAD)

**AC21 portability — the most misunderstood rule:**  
After an I-485 has been pending for 180+ days, the applicant can change employers to a "same or similar" role without restarting the green card process. Most people don't know this and stay in toxic jobs for years unnecessarily.

**Guardian value prop:**
- I-485 + job change consistency check (same/similar occupation determination)
- Document cross-check before I-485 filing (catch inconsistencies before USCIS sees them)
- H-4 EAD eligibility check for spouse

**Opening line:**
> "Most people think they're stuck at their employer until the green card is approved. After 180 days with your I-485 pending, you can change jobs under AC21 portability — if the role is same or similar. Guardian checks whether your new role qualifies."

---

### Segment 6: New Green Card Holders (Lawful Permanent Residents)

**Who they are:** Recently transitioned from H-1B or other visa to LPR status. Often don't realize their compliance obligations have changed significantly.

**Their biggest compliance risks:**
- Not knowing they now owe tax on worldwide income (not just US-source)
- FBAR now required on all foreign accounts (if they weren't already RA)
- Form 8938 (FATCA) — similar to FBAR but broader asset class, filed with tax return
- Foreign pension / retirement accounts now reportable
- Foreign gifts or inheritances: Form 3520 required for gifts >$100K from foreign persons
- Green card abandonment: if they spend too much time outside the US, they can lose LPR status — and there are exit tax implications

**What they fear:** They worked years to get the green card. They don't want to accidentally jeopardize it by not knowing the new rules.

**Guardian value prop:**
- New LPR compliance checklist — surfaces every new obligation from day 1 of green card
- FBAR + 8938 audit for prior years if they transitioned from NRA
- Foreign asset inventory prompt (foreign pensions, investment accounts, inheritance)

**Opening line:**
> "Getting the green card is step one. Most new green card holders don't realize they now owe tax on income worldwide, need to file FBAR and Form 8938 on foreign accounts, and report any foreign gifts over $100K. Guardian runs the new-LPR checklist so nothing slips through."

---

### Segment 7: Immigrant Founders (Pre-Seed to Series A)

**Who they are:** Immigrants who have started or co-founded a US company. May be on H-1B (complex — can you be employed by your own company?), O-1, or in the process of transitioning visa status. Age 25–40, often from China, India, Korea.

**Their biggest compliance risks:**
- 83(b) election missed or improperly completed (30-day window, no cure)
- Whether O-1 or H-1B is appropriate for a founder (H-1B requires employer-employee relationship, which is complex when you control the board)
- QSBS eligibility: was the company a C-corp? Were shares issued at original issuance? Was the $50M asset test met?
- Entity type: LLC vs. C-corp has immigration implications (H-1B can't be filed for LLC member in some cases)
- 83(b) × NRA status: many founders don't factor in their immigration status when making the election
- FBAR on foreign accounts while also managing a US company
- Cap table consistency with immigration documents

**The H-1B + founder problem:**  
An H-1B requires a bona fide employer-employee relationship. If a founder controls the board of directors, USCIS may question whether a true employment relationship exists. O-1 is often the better visa for founders. Most immigration attorneys advise on one path without knowing the equity structure.

**Guardian value prop:**
- 83(b) election audit — was it filed? Is the proof of mailing preserved? Was NRA status accounted for?
- Visa strategy check given equity structure and company stage
- QSBS eligibility check
- Cross-domain founder compliance scan (immigration + tax + corporate together)

**Opening line:**
> "Your immigration attorney, your tax accountant, and your equity attorney each only see one piece of your situation. Guardian reads all three together. The 83(b) window, your visa status at grant, your FBAR obligations — those conflicts only show up when you check all three simultaneously."

---

### Segment 8: YC and Accelerator-Backed Founders

**Who they are:** Same as Segment 7 but moving faster, with more formal equity structures, YC standard docs (SAFE, YC template operating agreements), and more investor scrutiny.

**Additional risks vs. general founders:**
- YC SAFEs converting to priced equity — conversion triggers 83(b) window restart in some structures
- Multiple co-founders with different immigration statuses — one may be NRA, one RA, one citizen — different tax treatment on the same equity event
- QSBS clock on YC companies often starts at SAFE conversion, not company formation
- Accelerator program stipends may have tax implications for NRA founders

**Guardian value prop:**
- Multi-founder status matrix — maps each co-founder's immigration status to equity treatment
- SAFE → priced round transition check
- QSBS clock calculation from correct start date

---

### Segment 9: O-1 Visa Holders

**Who they are:** Scientists, researchers, artists, engineers, entrepreneurs who have qualified as having extraordinary ability. Often on O-1 because H-1B lottery odds were unfavorable.

**Their biggest compliance risks:**
- O-1 is tied to a specific petitioner — changing employers or projects requires new petition
- O-1 has no cap or lottery but also has no "dual intent" — officially you cannot intend permanent residence (though EB-1 green card is the natural path)
- If an O-1 holder is also a founder: the petitioner (company) and the beneficiary (founder) overlap in ways that require careful structuring
- FBAR and tax residency: same as H-1B segment

**Guardian value prop:**
- O-1 + founder equity structure review
- O-1 → EB-1A green card pathway assessment
- Cross-domain O-1 compliance check

---

### Segment 10: H-4 EAD Spouses

**Who they are:** Spouses of H-1B holders on H-4 visas who have obtained Employment Authorization Documents. Often highly educated but underemployed, unclear on their own compliance obligations.

**Their biggest compliance risks:**
- H-4 EAD is tied to the principal's I-140 approval — if the I-140 is revoked, EAD becomes invalid
- Separate FBAR obligations if they are RA
- Working without checking that I-140 is still valid before EAD renewal
- Not knowing that they can file their own immigration petitions in some cases (EB-2 NIW self-petition)

**Guardian value prop:**
- I-140 status check linked to H-4 EAD validity
- EB-2 NIW self-petition eligibility assessment
- FBAR check for H-4 EAD holders who are RA

---

## Part 5 — Compliance Topics Reference

### Form 8843

**What it is:** Annual statement by F-1/J-1/M-1/Q visa holders declaring their days exempt from SPT. Not a tax return.

**Due:** June 15 (not April 15). Mail only. No e-file.

**Who:** Every exempt individual AND their F-2/J-2 dependents — even with $0 income.

**Critical points:**
- Must be filed every year, not just once
- Missing it = those days count toward SPT retroactively
- Entirely separate from income tax return
- Guardian generates this free in 2 minutes

---

### FBAR (FinCEN 114)

**Trigger:** Any US "person" (including RA) with >$10,000 aggregate in foreign financial accounts at any point during the year.

**Due:** April 15, auto-extended to October 15. Filed with FinCEN online (not IRS).

**Penalties:**
- Non-willful: $10,000/year per account
- Willful: greater of $100,000 or 50% of account balance per year
- Criminal exposure possible

**Key points:**
- Threshold is aggregate across all foreign accounts, not per account
- Includes accounts you're a signatory on (parents' joint accounts)
- Trigger is residency status (RA), not citizenship
- Many H-1B holders have owed FBAR for 2–4 years without knowing it

---

### Form 8938 (FATCA — Statement of Specified Foreign Financial Assets)

**Difference from FBAR:** Filed with the tax return (not FinCEN). Covers a broader asset class including foreign stocks, partnerships, financial instruments — not just bank accounts.

**Thresholds (higher than FBAR):**
- Single/MFS: $50,000 at year-end or $75,000 at any point
- MFJ: $100,000 at year-end or $150,000 at any point

**Key point for CS consultants:** FBAR and Form 8938 are both required when thresholds for both are met. They are not duplicates — they go to different agencies. Many users know about one and miss the other.

---

### Form 3520 (Foreign Gifts and Trusts)

**Trigger:** US person (including RA) who receives gifts from foreign persons exceeding $100,000 in a year (aggregate from all foreign individuals). Also required for transactions with foreign trusts.

**Why this matters:** Chinese immigrants commonly receive large gifts from parents — for down payments on property, to fund a startup, for investment. If the gift exceeds $100K, Form 3520 is required even though the gift itself is not taxable income. The penalty for failure to file is 35% of the gift amount.

**Guardian angle:** This is a completely overlooked obligation. No attorney or accountant brings it up unless asked. Guardian should surface this proactively for any RA user who has received significant foreign funds.

---

### 1040-NR vs. 1040

**1040-NR (Non-Resident Alien):**
- Only US-source income reported
- Cannot claim standard deduction (only itemized)
- Cannot file jointly with spouse (unless certain elections are made)
- Different capital gains rules: NRAs not taxed on capital gains from US stock market (unless US trade or business)
- Scholarship/fellowship income taxable for amounts above tuition and fees

**Common 1040-NR mistakes:**
- Using TurboTax or H&R Block (they only support 1040, not 1040-NR — NRAs must use Sprintax or a CPA)
- Claiming standard deduction (not allowed)
- Reporting capital gains incorrectly
- Not claiming applicable treaty benefits

**Guardian angle:** Many users don't know whether they should be filing 1040 or 1040-NR. Guardian's status check resolves this before they file the wrong form.

---

### FICA Exemption for F-1 and J-1 Students

**What it is:** F-1 and J-1 students who are NRAs are exempt from Social Security and Medicare taxes (FICA). This is automatic — employers should not withhold it.

**What often goes wrong:** Employers — especially large companies with automated payroll — often withhold FICA anyway. The student is owed a refund, but most don't know to ask.

**How to claim:** File Form 843 with the IRS to recover incorrectly withheld FICA.

**Guardian angle:** This is free money most students never claim. Guardian surfaces it during onboarding. It's a trust-builder — you found them a refund before they paid anything.

---

### H-1B Compliance

**Key compliance rules:**
- Tied to specific employer, job title, and worksite location
- Remote work from a different metro requires amended LCA
- Material job duty changes require amended H-1B petition
- Layoff: 60-day grace period to find new employer or depart
- Status vs. visa stamp: status matters for working; stamp only needed for re-entry

**The employer-attorney problem:** The employer's immigration attorney's client is the company. They represent the company's exposure, not the employee's interests. They have zero visibility into the employee's tax situation, FBAR obligations, or personal compliance.

---

### OPT / STEM OPT

**OPT:** 12 months post-graduation work authorization. Must work in a field related to the degree. 90-day unemployment limit.

**STEM OPT:** 24-month extension. Total 36 months. Employer must be E-Verify enrolled. Student must file I-983 within 10 days of new employer start. 6-month and annual evaluations required. 60 additional unemployment days (150 combined total).

**Most common violations:**
- Starting new job before I-983 is updated (technically out of status on day 1)
- Not tracking unemployment days across multiple short jobs
- Employer drops E-Verify without employee knowing

---

### 83(b) Election

**What:** Election to pay income tax on restricted stock at grant date (usually near-zero value) instead of at each vesting date.

**Deadline:** 30 days from grant. No exceptions. No extensions. No cure.

**Does not apply to RSUs** — only restricted stock (founder shares). Employees with RSUs cannot make an 83(b) election.

**For immigrant founders:**
- Must mail (certified mail with proof of mailing)
- NRA vs. RA status at grant affects how the election interacts with future tax treatment
- Missing it means ordinary income tax at vest on full FMV — potentially very large if company grows

---

### QSBS (§1202 Qualified Small Business Stock)

**What:** Up to $10M or 10× basis excluded from federal capital gains tax on sale of qualifying stock.

**Requirements:** US C-corp, company assets <$50M at issuance, original issuance (not secondary), held 5+ years.

**Critical points:**
- California and New York do NOT conform — full state tax regardless
- 5-year clock starts at grant (83(b) election), not at vest
- NRAs not taxed on US capital gains anyway — QSBS matters when you become RA before exit
- QSBS is not available for S-corps or LLCs

---

### Tax Treaties

| Country | Key provision | Benefit | Form to claim |
|---|---|---|---|
| China | Art. 20 | Students/trainees: stipend/scholarship excluded, 5 years | 8833 + 1040-NR |
| China | Art. 19 | Professors/researchers: teaching income excluded, 3 years | 8833 + 1040-NR |
| Japan | Art. 20 | Students: similar exemption | 8833 + 1040-NR |
| Korea | Art. 21 | Students: similar exemption | 8833 + 1040-NR |
| Germany | Art. 20 | Students/apprentices: exemption | 8833 + 1040-NR |
| **India** | **None** | **No US-India tax treaty** | N/A |
| UK | Art. 20 | Students: exemption | 8833 + 1040-NR |

**Always clarify:** Treaty benefits are not automatic. The user must claim them by filing Form 8833 and declaring the treaty position on their 1040-NR. IRS does not apply them automatically.

**Tension for H-1B holders:** Some treaty provisions require the person not to intend permanent residence. H-1B is dual intent. Claiming treaty benefits as an H-1B holder with a pending I-140 can create a documented inconsistency. IRS and USCIS share data. Guardian flags this risk.

---

## Part 6 — Cross-Domain Conflict Matrix

Each row is a moment in a user's life where obligations across immigration, tax, and corporate change simultaneously — and no single advisor catches all of them.

| Life event | Immigration sees | Tax sees | The gap Guardian catches |
|---|---|---|---|
| F-1 year 6 begins | Status unchanged | SPT clock starts | FBAR now required; worldwide income taxable; some treaty positions break |
| J-1 researcher year 3 | Status unchanged | SPT clock starts (2-year window) | Same as above — 3 years earlier than most expect |
| H-1B approved, 3rd year in US | Status maintained | Resident alien via SPT | FBAR required on foreign accounts; worldwide income taxable; FICA now owed |
| STEM OPT → new employer | I-983 update required | W-2 changes | Training plan gap; unemployment clock; SEVIS out of status risk |
| Founder issues equity (day 1) | Visa type noted | 83(b) deadline running | NRA/RA status at grant; QSBS eligibility; 30-day window |
| SAFE converts to priced equity | Not flagged | Possible tax event | 83(b) window may restart; QSBS clock re-evaluation needed |
| H-1B layoff | 60-day grace starts | W-2 ends | FBAR still required for year; OPT unemployment days if reverting |
| Green card approved | LPR status begins | Worldwide income begins | FBAR + Form 8938 + foreign pension reporting all trigger simultaneously |
| Company exit / liquidity event | Not immigration issue | Capital gains event | QSBS properly structured? 83(b) filed correctly as NRA? FBAR current? |
| Foreign gift received (>$100K) | Not flagged | Not income, not taxed | Form 3520 required — 35% penalty for non-filing |
| New green card + foreign inheritance | LPR status | Estate/gift check | Form 3520, possible Form 706-NA implications |

---

## Part 7 — Guardian Value Propositions

### 1. Price vs. traditional advisors

| Service | Traditional cost | Guardian cost |
|---|---|---|
| Form 8843 generation | $150–$300 (CPA) | Free |
| Treaty benefit analysis | $200–$500 (CPA) | Included in check |
| H-1B compliance audit | $500–$1,500 (immigration attorney) | $199 (Tier 1A) |
| Full cross-domain document check | $2,000–$5,000 (immigration attorney + CPA) | $199–$499 |
| FBAR filing assistance | $500–$1,500 (CPA) | Included in Tier 1 |
| Founder compliance scan | $3,000–$8,000 (law firm + CPA + equity attorney) | $499 |

### 2. The cross-domain capability no one else has

- Immigration-only tools (Boundless, SimpleCitizen): don't see your taxes or equity
- Tax-only tools (TurboTax, Sprintax): don't see your visa status or equity
- Equity tools (Carta, Pulley): don't see your immigration status or tax residency
- Traditional law firms: don't coordinate across practice areas
- **Guardian:** Reads all three together. The only tool that can catch cross-domain conflicts.

### 3. Free to start, no friction

- Form 8843: free, no account required, 2-minute download
- FICA refund check: free
- Treaty benefit estimate: free
- No credit card to start. No salesperson call to access free tools.

### 4. Bilingual (Chinese/English)

Guardian communicates in Mandarin and English. The 300,000+ Chinese international students and 400,000+ Chinese H-1B holders in the US are dramatically underserved by English-only compliance tools.

### 5. Speed and accessibility

- Form 8843 generated in 2 minutes (vs. waiting for a CPA appointment)
- Document check starts within hours of upload (vs. 2–4 week law firm turnaround)
- Available 24/7, not constrained by attorney office hours

---

## Part 8 — Competitive Landscape

| Competitor | What they do well | What they miss | How Guardian differs |
|---|---|---|---|
| **Boundless** | Visa preparation (green card, K-1) | No tax layer, no corporate layer | Guardian adds tax + equity cross-check |
| **SimpleCitizen** | DIY immigration forms | Same as Boundless | Same differentiation |
| **Sprintax** | 1040-NR tax returns for students | No immigration, no corporate layer | Guardian surfaces treaty + status + immigration issues together |
| **TurboTax / H&R Block** | 1040 tax returns | Cannot file 1040-NR; misses NRA rules | Guardian explicitly handles NRA; catches if user is filing wrong form |
| **Deel / Remote** | Global payroll compliance | Employer-facing, not individual immigrant | Guardian serves the individual worker |
| **Employer's immigration attorney** | H-1B petitions | Client is the company, not you; no tax visibility | Guardian is the employee's advisor, not the company's |
| **Your CPA** | Tax return preparation | No immigration knowledge | Guardian cross-checks both |

---

## Part 9 — CS Consultant Operational Guidelines

### How to qualify a lead

Ask these to determine which tier is right:

1. **What visa are you currently on?** → Determines immigration domain
2. **How many years have you been in the US?** → SPT calculation, FBAR exposure
3. **Do you have bank or investment accounts outside the US?** → FBAR/8938 exposure
4. **Are you a founder or do you have equity in a startup?** → 83(b)/QSBS layer
5. **Have you filed Form 8843 every year?** → Student segment trigger
6. **Are you currently in the green card process?** → PERM/I-485 layer

**Good fit for Guardian:**
- Any immigrant who has been in the US 2+ years and has not had a cross-domain review
- Any immigrant founder, regardless of visa status
- Any F-1/J-1 student approaching year 5 of their US stay
- Any H-1B holder with foreign bank accounts

**Not a good fit (refer out):**
- US citizens with no foreign assets or immigration history
- Someone seeking pure legal representation (they need an attorney)
- Someone in active USCIS proceedings who needs attorney of record

### Common objections and responses

**"My employer's immigration attorney handles everything."**
> "They handle your visa. Their client is your company, not you — they have no visibility into your FBAR obligations or how your tax residency has shifted since you became a resident alien. Guardian fills that gap."

**"I use TurboTax."**
> "TurboTax prepares 1040s for US citizens and residents. If you're on F-1, J-1, or H-1B and still a non-resident alien, you need to file a 1040-NR — TurboTax can't do that. And it has no immigration layer at all. You may be filing the wrong form entirely."

**"I already use Sprintax."**
> "Sprintax handles your 1040-NR well. What it doesn't do is check whether your immigration status, tax filing, and any equity documents are consistent with each other. That's the cross-domain check Guardian adds."

**"It's too expensive."**
> "The free tools — Form 8843, FICA refund check, treaty benefit estimate — cost nothing. If Guardian finds you're owed a FICA refund or treaty credits, that's money in your pocket before you spend a dollar. The professional tiers start at $29."

**"I have a CPA."**
> "Your CPA handles your tax return. Do they also check your immigration status, your FBAR exposure, and whether your equity structure is consistent with your visa? Most CPAs don't have immigration knowledge. Guardian is the check that sits across all three domains."

**"I don't have time right now."**
> "Form 8843 takes 2 minutes and the June 15 deadline is approaching. That one alone is worth doing today."

### Scope of service — what Guardian can and cannot say

**Guardian CAN:**
- Identify potential compliance risks based on documents and information provided
- Explain compliance rules and requirements in plain language
- Generate Form 8843 and other self-completion documents
- Flag likely FBAR obligations and explain filing requirements
- Identify missing filings or inconsistencies between documents
- Recommend relevant professional service tiers based on risk profile
- Refer users to licensed professionals for legal representation

**Guardian CANNOT:**
- Give legal advice or represent a user before USCIS, the IRS, or any court
- File documents on behalf of users without a licensed professional's oversight
- Guarantee a compliance outcome
- Interpret specific case facts for legal purposes without attorney involvement

**When in doubt:** If a user asks "will this keep me out of trouble?" or "can I rely on this for my case?" — the answer is always: "Guardian identifies the risk; a licensed professional who can represent you should advise on the specific legal question. Would you like to connect with one of our attorneys or enrolled agents?"

### Escalation paths

| Situation | Escalate to |
|---|---|
| Active USCIS denial or RFE | Immigration attorney (Tier 1B or above) |
| IRS audit or FBAR penalty | Enrolled Agent or tax attorney (Tier 1B) |
| USCIS court proceedings | Outside referral (Guardian does not cover litigation) |
| Complex equity structure (Series B+) | Equity attorney referral |
| Criminal FBAR exposure (willful) | Tax attorney referral immediately |

### Communication tone guidelines

- **Lead with empathy, not alarm.** These users are navigating a system that wasn't designed for them. Don't use fear. Use clarity.
- **Speak in plain language.** Avoid jargon. When a technical term is necessary, define it immediately.
- **Never over-promise.** Guardian finds risks — it does not guarantee clean status.
- **Respect the bilingual context.** For Mandarin-speaking users, offer Mandarin first. Never assume the user's English proficiency.
- **Avoid the word "illegal."** Use "out of status," "noncompliant," or "exposure."

---

## Part 10 — Conversation Playbooks by Segment

### For international students (Form 8843 funnel)

1. **Hook:** "Did you file Form 8843 this year? It's due June 15 and most students have never heard of it."
2. **Explain:** "It's required even with $0 income. Missing it can retroactively make you a resident alien — which matters for your H-1B eligibility later."
3. **Free action:** "Guardian generates it free in 2 minutes. No account needed."
4. **Second value:** "While you're at it — if you're Chinese, you're probably owed a refund under the US-China tax treaty that nobody told you about."
5. **Upsell trigger:** "How many years have you been in the US? If you're approaching year 5, we should run a full status check."

### For H-1B tech workers (FBAR / cross-domain)

1. **Hook:** "Has anyone ever cross-checked your FBAR obligations since you became a resident alien?"
2. **Qualify:** "Do you have bank accounts in China over $10K total? Even a joint account with your parents counts."
3. **Explain:** "Once you hit Substantial Presence — usually around year 2 or 3 — you're a resident alien. FBAR applies immediately. Many people have 2–4 years of unfiled FBAR."
4. **Stakes:** "Non-willful penalty is $10K per account per year. Willful is up to 50% of the balance."
5. **Guardian action:** "Guardian runs the full check — FBAR exposure, treaty positions, LCA compliance — for $199. If you're clean, you'll know. If you're not, you'll know what to fix."

### For immigrant founders (equity × immigration)

1. **Hook:** "When you issued your founder shares, did anyone check whether the 83(b) election was consistent with your immigration status?"
2. **Explain:** "The 30-day 83(b) window and your NRA/RA status at the time of grant determine whether you've set up your equity correctly for the eventual exit — and whether QSBS applies."
3. **Frame:** "Your immigration attorney, your accountant, and your equity attorney each see one piece. Nobody reads all three together."
4. **Guardian action:** "Guardian runs the full cross-domain founder scan — immigration, tax, and corporate — for $499. That's less than 2 hours of law firm time."

### For new green card holders

1. **Hook:** "Did anyone walk you through what changes on the compliance side when your green card was approved?"
2. **Explain:** "Worldwide income is now taxable. FBAR applies to all foreign accounts. Form 8938 kicks in. Foreign gifts over $100K need to be reported. It's a significant compliance shift."
3. **Guardian action:** "Guardian's new-LPR checklist goes through every obligation that changed on day one of your green card. It takes 20 minutes and surfaces everything you need to handle in year one."

---

## Appendix: Quick Reference Card

| Topic | Key fact | Guardian product |
|---|---|---|
| Form 8843 | Due June 15, required even with $0 income | Free generator |
| FBAR | >$10K aggregate foreign accounts, RA only | Cross-domain check |
| Form 8938 | Similar to FBAR, broader assets, higher thresholds | Included in full check |
| Form 3520 | Foreign gift >$100K, 35% penalty | LPR checklist |
| H-1B | Employer's attorney = company's attorney, not yours | $199 compliance audit |
| OPT unemployment | 90 days (OPT), 150 combined (STEM OPT) | OPT compliance check |
| 83(b) | 30 days from grant, no cure, mail with proof | Founder scan |
| QSBS | C-corp, <$50M assets, 5+ years, not CA/NY | Founder scan |
| Tax treaty (China Art. 20) | 5-year stipend exemption, must file Form 8833 | Treaty benefit check |
| FICA exemption (F-1) | NRA students exempt — employer may owe you a refund | Free FICA check |
| SPT | 183-day formula; F-1 exempt 5 years, J-1 research exempt 2 years | Status check |
| AC21 portability | Change jobs after I-485 pending 180+ days | I-485 job change check |
