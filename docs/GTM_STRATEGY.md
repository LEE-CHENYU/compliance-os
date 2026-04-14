# Guardian — Go-to-Market Strategy

**Version:** 1.0
**Date:** 2026-04-09
**Author:** Cheney Li + Claude

---

## Executive Summary

Guardian is an AI-powered compliance document cross-checker for immigrants. It sits **upstream** of lawyers and CPAs as a pre-intake layer — catching errors in immigration, tax, and corporate documents before they're filed with USCIS, the IRS, or state agencies.

**Unique positioning:** The only tool that cross-checks immigration, tax, and corporate documents together — catching the inconsistencies no single-domain tool can see.

**Target user:** The "DIY Immigration Navigator" — immigrant founders, early startup employees, and international students who personally handle their paperwork because they lack in-house legal teams or retained big firms.

**Niche strategy:** Start Chinese-focused (Mandarin + English, WeChat/Xiaohongshu distribution), expand to broader Asian and immigrant markets. The niche IS the moat.

**Wedge product:** Free Form 8843 generator for international students — lead magnet that captures users 7+ years before they become high-LTV founders.

**Revenue model:** Software-leveraged professional services. AI + non-credentialed staff do 90% of the work; one bar-licensed attorney (immigration) and one Enrolled Agent (tax) sign off on 10%. Client pays Guardian a flat fee; Guardian pays professionals a small subcontractor fee; Guardian keeps 60-80% margin. All professionals can be China-based at 60-70% below US cost.

---

## 0. Core Business Model: Software-Leveraged Professional Services

Guardian is NOT a pure SaaS play. It's a **software-leveraged professional services business** — software + AI does 90% of the work, one credentialed professional signs off on 10%, and Guardian captures the spread.

### How It Works

```
Client pays Guardian $X (flat fee per service)
         ↓
Guardian's AI + non-credentialed staff (90%):
  - Intake, document collection, form pre-filling
  - AI checks, cross-domain consistency scan
  - Draft preparation, PDF generation
  - Client communication, deadline management
         ↓
Credentialed professional (10%):
  - Reviews AI output
  - Makes judgment calls
  - Signs off (G-28 for immigration, preparer signature for tax)
  - Files with USCIS / IRS
         ↓
Guardian pays professional flat subcontractor fee ($Y)
         ↓
Guardian keeps: $X minus $Y (target: 60-80% gross margin)
```

### Two Verticals, One Model

| | Immigration | Tax |
|---|---|---|
| **Required credential** | US bar-licensed attorney (any state) | Enrolled Agent (EA) |
| **Why not CPA?** | N/A | EA has identical IRS representation rights, cheaper, federally licensed (no state issues), faster to credential (3 exams vs multi-year CPA) |
| **License scope** | Federal (immigration law) | Federal (IRS) |
| **Can be China-based?** | Yes | Yes |
| **Hire cost (China)** | $20-40K/year | $30-50K/year |
| **What they supervise** | Paralegals + AI | PTIN holders + AI |
| **Fee-sharing rules** | Strict (ABA 5.4 — no referral fees, must use subcontractor model) | Flexible (AICPA 503 — referral fees OK with disclosure) |
| **Limited scope allowed?** | Yes (ABA 1.2(c)) | Yes (Circular 230) |
| **Execution vs Advisory split?** | Yes | Yes |

### The Team at Steady State

```
GUARDIAN PROFESSIONAL STAFF (all part-time to start, all China-based)

Immigration:
  1 US bar-licensed attorney (LLM + NY bar)     ~$20-40K/year
  
Tax:
  1 Enrolled Agent                                ~$30-50K/year

Operations:
  1-2 non-credentialed staff (paralegal-type)    ~$15-25K/year each
  Handle intake, doc prep, form filling
  Work under attorney + EA supervision

Total team cost: ~$80-140K/year
Revenue capacity: $500K+ (software-leveraged)
```

### Why This Model Wins

1. **Margin:** Traditional law firm pays attorneys $150-500/hour with 30-40% margin. Guardian pays flat subcontractor fees with 60-80% margin because AI does 90% of the work.
2. **Scale:** One attorney can review 200+ Execution Mode cases per month (15-20 min each). Traditional model: ~40 cases/month at 8 billable hours/day.
3. **Price to client:** Guardian charges $299 for what a law firm charges $2,500. 85% discount enabled by AI leverage.
4. **Geographic arbitrage:** China-based professionals at 60-70% below US cost, fully legal for federal practice.
5. **Cross-domain moat:** No competitor has both an attorney AND an EA checking documents together. The inconsistency-catching feature requires both.

### Revenue Model by Tier

```
Tier 0  (pure software, no professional):    100% margin, $29-99/order
Tier 0.5 (clerical fulfillment):              ~60% margin, $19/order
Tier 1A (Execution Mode):                     65-75% margin, $199-399/order
Tier 1B (Advisory Mode):                      55-65% margin, $499-799/order
Tier 2  (Boundless assigned):                 55-65% margin, $999-1,999/order
Tier 3  (Panel specialist):                   50-60% margin, $3,500-6,000/order
Tier 4  (Premium cross-domain):               50-60% margin, $2,000-15,000/order
```

### Unit Economics Example

```
1,000 USERS/MONTH AT STEADY STATE

                  Volume   Revenue    Prof Cost   Margin
Tier 0 (free)      500      $0         $0          lead gen
Tier 0 (paid)      200      $10,000    $0          $10,000
Tier 1A Execution  150      $44,850    $15,000     $29,850
Tier 1B Advisory    50      $34,950    $15,000     $19,950
Tier 2 Boundless    20      $29,980    $12,000     $17,980
Tier 3 Panel         5      $25,000    $10,000     $15,000
Tier 4 Premium       2      $10,000     $4,000      $6,000

TOTAL/MONTH        927     $154,780    $56,000     $98,780
ANNUAL RUN RATE              $1.86M     $672K       $1.19M
Professional staff cost (annual):              ~$120K
Net margin after staff:                        ~$1.07M (57%)
```

This is a **$1.8M ARR business with 57% net margin**, run by a team of 5 professionals (all China-based) + software.

---

## 1. Target User: The DIY Immigration Navigator

### Who They Are
Immigrants who personally navigate their own US paperwork because they don't have corporate immigration support.

**Primary personas:**
- **Startup founders** — on O-1, EB-1, H-1B via their own company. No in-house counsel.
- **Early employees at small startups** — company sponsors but has no dedicated immigration team
- **International students on F-1/OPT** — navigating the H-1B lottery mostly alone
- **Freelancers/contractors** — on OPT or O-1, no employer support

### Who They Are NOT
- **Big corp employees** (Google, Goldman, Meta, Amazon, Citadel, Barclays, etc.)
  → These companies have Fragomen/BAL/in-house counsel handling everything
  → Their employees never touch the paperwork personally
  → **They are NOT our user** despite being statistically likely to be immigrants
- **Senior executives** who've been in the US 15+ years (likely already citizens)

### Why This Matters
When we first scored LinkedIn connections by "high H-1B sponsor company," we got a list of Goldman analysts and Meta engineers. Wrong. We re-weighted to penalize big-corp employees and reward startup founders, students, and small-company employees — and the top of the list became a much more accurate reflection of who'd actually benefit from Guardian.

**The heuristic:** If they have a corporate immigration lawyer assigned to them, Guardian is redundant. If they're Googling "how do I file my own O-1 petition" at 2am, Guardian is their answer.

---

## 2. Niche Strategy: Chinese-First

### Why Chinese
Out of all immigrant segments, Chinese immigrants are:
- **#2 H-1B nationality** (after India)
- **#1 international student population** (~300K in US)
- **Underserved**: No immigration AI tool is built Mandarin-first
- **Distinct channels**: They research on 小红书 (Xiaohongshu) and WeChat — zero competitor presence
- **Cultural trust**: Prefer services in their native language, with cultural context

### Why "Chinese-first" is a Moat
| Competitor | Target | Language | Chinese-focused? |
|-----------|--------|----------|------------------|
| JustiGuide | Global (Nigerian founder story) | 12 languages, English-first | No |
| Boundless | Family-based, US-broad | English | No |
| Alma | Corporate immigration, tech pros | English | No |
| Gale (YC W25) | Employer H-1B automation | English | No |
| OpenSphere | O-1A/EB-1A for founders (Indian founder) | English | No |
| Smart Green Card | High-achievers EB-1A | English | No |
| Caseblink | Lawyer-facing case prep | English | No |
| Docketwise | Lawyer-facing SaaS | English | No |
| **Guardian** | **Immigrant founders + students** | **Mandarin + English** | **YES** |

**No one owns this space.** A Mandarin-first tool with WeChat/小红书 distribution is genuinely differentiated and hard to replicate without cultural fluency.

### Expansion Path
```
Phase 1: Chinese immigrants (Mandarin + English)
  ↓
Phase 2: Indian immigrants (second largest H-1B nationality)
  ↓
Phase 3: Broader Asian market (Korean, Japanese, Taiwanese, Vietnamese)
  ↓
Phase 4: Global
```

---

## 3. Product Ladder (Customer Lifetime Journey)

Guardian grows with the customer across their entire immigration journey:

```
Year 1 (F-1 Student):
  Free Form 8843 Generator → $0 (lead magnet)
  Student Tax Filing → $29-99

Year 2 (OPT):
  OPT Document Check → $29
  EAD Renewal Check → $29

Year 3 (H-1B Lottery):
  H-1B Registration Review → $49
  H-1B Petition Doc Check → $99-199

Year 4 (H-1B Employee):
  FBAR + Tax Check → $99
  I-9 + Employment Doc Check → $49
  Visa Extension Doc Check → $99

Year 5-6 (Green Card Process):
  I-140 Petition Review → $199
  I-485 Document Check → $299-499
  Cross-domain tax/immigration consistency check → $199

Year 7+ (Founder Phase):
  Entity Formation Doc Check → $199
  83(b) Election Filing → $99
  O-1 Petition Support Package → $2,000-3,000
  EB-1A Self-Petition Support → $3,000-5,000
  Founder Tax Package → $1,500-3,000

Year 10+ (Exit Phase):
  Pre-immigration tax planning → $2,000-5,000
  Exit tax (surrendering green card) → $5,000-15,000
  QSBS qualification review → $2,000-5,000
```

**Total LTV per user: $10,000-30,000+**
**CAC (via free Form 8843 lead magnet): Near $0**

---

## 4. Wedge Product: Free Form 8843 Generator

### The Insight
Every international student on F-1/J-1/M-1/Q visa **must file Form 8843 every year, even with zero income**. It's called "Statement for Exempt Individuals" and tells the IRS their days in the US don't count toward tax residency.

**Most students don't know this.** Compliance is likely 30-50%. Universities mention it vaguely in ISSO emails. TurboTax doesn't handle it. Sprintax charges $50+ just for this one form.

### Why It's the Perfect Wedge
| Attribute | Value |
|-----------|-------|
| **Build effort** | ~1 weekend (simple form template + PDF generation) |
| **User pain** | High — students genuinely confused, fear IRS trouble |
| **Competition** | Minimal — no one gives it away free in Mandarin |
| **Monetization** | Free (lead generation) |
| **CAC** | Near zero via 小红书 + WeChat viral content |
| **Lead quality** | Captures: name, email, school, visa type, dates, dependents |
| **LTV conversion** | Students become OPT users → H-1B users → founders over 5-10 years |

### Distribution Channels (All Free/Organic)
1. **小红书 (Xiaohongshu) posts** — "留学生报税必看！Form 8843 你真的交了吗？"
2. **WeChat groups** at every major US university with Chinese students
3. **CUCSSA** (Columbia) and equivalent Chinese student associations at Cornell, NYU, Berkeley, Stanford, UIUC, UMich, Purdue, etc.
4. **Reddit** — r/f1visa, r/OPT, r/chinesestudentsinamerica
5. **University ISSO partnerships** — free tool offered to their students
6. **YouTube** — tax explainer content in Mandarin

### The Tax Season Timing
Tax season runs **January through April 15 each year**. Form 8843 deadline is **June 15** (later than normal tax deadline). If Guardian launches the generator by late 2026, it captures the entire 2027 tax season — potentially 50,000+ student leads in one season.

---

## 5. Service Catalog

### Core Principle: Execution vs. Advisory

Most immigration/tax services have two types of users:
- **Self-directed users** who already know what they need and want fast, cheap execution
- **Uncertain users** who need strategy and guidance first

Guardian offers both as separate products at different price points. Users self-select via a qualifying questionnaire. This structure is legally permitted as **"limited scope representation"** under ABA Model Rule 1.2(c).

### Tier 0: Mechanical (No Attorney Needed)
Pure software products. No legal advice, no attorney required. Zero legal risk.

| Service | Price | Purpose |
|---------|-------|---------|
| **Form 8843 Generator** | Free | Student lead generation |
| **Basic Immigration Doc Check** | Free (1/user) | Founder acquisition |
| **Tax Treaty Checker** | Free | Shows savings opportunity |
| **Document Data Room** | Free with signup | Ongoing organization |
| **Student Tax Filing** (1040-NR + 8843) | $29 | Student revenue wedge |
| **H-1B Document Check** | $49 | Spot errors before filing |
| **OPT Document Check** | $29 | Spot errors before filing |
| **Green Card Doc Check** | $99 | Pre-intake verification |
| **FBAR Compliance Check** | $49 | Penalty avoidance |
| **83(b) Election Filing** | $99 | 30-day deadline product |
| **ITIN Application Support** | $99 | Non-SSN holders |
| **Cross-Domain Inconsistency Check** | $99 | Guardian's unique value |

### Tier 1A: Execution Mode (Limited Scope Attorney)
**For self-directed users who already know what they need.** Attorney verifies info, signs G-28, files. ~15-20 minutes of attorney time. Limited scope agreement required.

| Service | Price | Attorney Keeps | Guardian Keeps | Attorney Time |
|---------|-------|---------------|----------------|---------------|
| **OPT Application Execution** | $199 | $80 | $119 | ~20 min |
| **STEM OPT Extension Execution** | $199 | $80 | $119 | ~20 min |
| **H-1B Registration Execution** | $299 | $100 | $199 | ~15 min |
| **H-1B Extension (no change) Execution** | $299 | $100 | $199 | ~20 min |
| **H-4 EAD Execution** | $249 | $100 | $149 | ~20 min |
| **I-9 Audit Support** | $149 | $60 | $89 | ~15 min |
| **Naturalization Form Execution** | $399 | $150 | $249 | ~30 min |

**User Flow:** Qualifying questionnaire → if self-directed criteria met → Execution Mode. Limited scope agreement signed. Attorney verifies + executes. If attorney finds red flags during review, user is notified and offered upgrade to Advisory Mode with credit applied.

### Tier 1B: Advisory Mode (Full Strategy + Execution)
**For uncertain users who need guidance.** Includes attorney consultation, strategy, and execution. ~60-90 minutes of attorney time.

| Service | Price | Attorney Keeps | Guardian Keeps | Attorney Time |
|---------|-------|---------------|----------------|---------------|
| **OPT Application Advisory** | $499 | $200 | $299 | ~60 min |
| **H-1B Registration Advisory** | $799 | $300 | $499 | ~90 min |
| **H-1B Extension Advisory** | $599 | $250 | $349 | ~60 min |
| **Naturalization Advisory** | $699 | $280 | $419 | ~90 min |
| **OPT/H-1B Strategy Consultation (30 min)** | $249 | $150 | $99 | ~30 min |

### Tier 2: Boundless Assigned Model ($999-1,999)
**Complex but standardized cases.** Guardian assigns attorney from panel. Full review, not just execution. Attorney choice not offered (keeps pricing low).

| Service | Price | Attorney Keeps | Guardian Keeps | Attorney Time |
|---------|-------|---------------|----------------|---------------|
| **H-1B Petition Standard** | $1,499 | $600 | $899 | ~3-5 hrs |
| **H-1B Transfer** | $1,299 | $500 | $799 | ~3-4 hrs |
| **I-485 Adjustment Standard** | $999 | $400 | $599 | ~2-3 hrs |
| **I-140 Standard** | $1,499 | $600 | $899 | ~3-4 hrs |

### Tier 3: Curated Panel (Specialist Attorney Choice)
**High-advisory cases requiring specialist expertise.** Client chooses from 3 panel attorneys with transparent match scoring.

| Service | Price | Attorney Keeps | Guardian Keeps | Attorney Time |
|---------|-------|---------------|----------------|---------------|
| **O-1 Petition** | $3,500 | $1,500 | $2,000 | ~10-15 hrs |
| **EB-1A Self-Petition** | $6,000 | $2,500 | $3,500 | ~20-30 hrs |
| **EB-2 NIW** | $5,000 | $2,000 | $3,000 | ~15-25 hrs |
| **L-1A/L-1B Intracompany** | $4,000 | $1,600 | $2,400 | ~12-18 hrs |
| **Complex I-140 (port/retain)** | $2,500 | $1,000 | $1,500 | ~8-12 hrs |

### Tier 4: Premium Cross-Domain Services ($2,000-15,000)
**Cross-domain cases requiring attorney + CPA + deep strategy.** Guardian's unique value (no competitor does this).

| Service | Price | Notes |
|---------|-------|-------|
| Founder Tax Package | $2,000-3,000 | 83(b), entity setup, RSU planning |
| Cross-Border Tax Planning (China ↔ US) | $3,000-10,000 | CFC, PFIC, FBAR, treaty, SAFE Circular 37 |
| EB-1A Self-Petition Full Support | $3,000-5,000 | 15 months profile building + filing |
| Pre-Immigration Tax Planning | $2,000-5,000 | Step-up basis, timing, structure |
| Exit Tax Planning (green card surrender) | $5,000-15,000 | Form 8854, mark-to-market |

### Tier 5: Enterprise (Future)
- Law firm SaaS (Guardian as intake layer)
- University partnership (free to students, paid by ISSO)
- Employer partnership (HR at small startups)

### Example Economics: March H-1B Lottery Window

```
100 H-1B REGISTRATION USERS (2-week March window)

Self-selection split (expected): 80% Execution, 20% Advisory

Execution Mode (80 × $299):        $23,920 revenue
  Attorney time: 80 × 15 min = 20 hrs
  Attorney payment: 80 × $100 = $8,000
  Guardian keeps: $15,920

Advisory Mode (20 × $799):          $15,980 revenue
  Attorney time: 20 × 90 min = 30 hrs
  Attorney payment: 20 × $300 = $6,000
  Guardian keeps: $9,980

TOTAL: $39,900 revenue
  Attorney total: $14,000
  Guardian keeps: $25,920 (65% margin)
  Attorney total time: 50 hours (one part-time attorney)
```

### Limited Scope Representation — Legal Framework

**ABA Model Rule 1.2(c):** "A lawyer may limit the scope of the representation if the limitation is reasonable under the circumstances and the client gives informed consent."

**Requirements for Execution Mode:**
1. **Written limited scope agreement** — signed before any work
2. **Clear scope boundaries** — what IS and ISN'T included
3. **Informed consent** — user understands they're not getting strategic advice
4. **Reasonableness** — the limited scope still serves the client competently
5. **"Stop and flag" safety net** — attorney must flag material red flags even in Execution mode, offering upgrade path

**Attorney protection checklist (Execution Mode):**
- Beneficiary info matches passport
- Employer info matches EIN database
- Job title/SOC code consistent with position
- Wage level specified and within legal bounds
- No obvious red flags (multiple registrations, status issues)
- LCA number provided and valid
- No prior denials flagged in intake

If all checked → proceed with execution. If any unchecked → flag to Guardian, offer upgrade.

### Self-Selection Intake Pattern

Users self-route via qualifying questionnaire:

```
Has your employer already provided you with:
  ☐ The LCA (Labor Condition Application)
  ☐ Your SOC code
  ☐ Your wage level
  ☐ Confirmed job title and duties

Is your situation straightforward?
  ☐ US bachelor's or higher in related field
  ☐ Only one employer registering for you
  ☐ Currently maintaining legal status
  ☐ No recent visa denials or RFEs
```

- **All boxes checked** → Execution Mode recommended
- **Any box unchecked** → Advisory Mode recommended
- **User override allowed** — can still choose either mode, but warning is documented

This protects everyone: user gets the service they want, attorney's ethical duty is preserved, Guardian's legal exposure is minimized.

---

## 6. Competitive Landscape

### Current Players

| Company | Focus | Target User | Funding | Guardian's Angle |
|---------|-------|-------------|---------|------------------|
| **JustiGuide** | AI marketplace + lawyer matching | Broad immigrants | Pre-seed (Right Side Capital) | They don't do pre-intake or cross-domain. Complementary. |
| **Boundless** | Family-based + O-1 filing | US-broad | 100k+ families | Target different segment (family vs founder) |
| **Alma** | Corporate immigration | Tech pros, startups | VC-backed | They're case management; we're pre-intake. 3 contacts in network. |
| **Gale** (YC W25) | Employer H-1B automation | Employers | $2.7M seed | Different buyer (employer not individual) |
| **OpenSphere** | O-1A/EB-1A AI filing | High-achievers, founders | Early stage | Direct overlap. Indian founder focus. Differentiate on Chinese niche. |
| **Smart Green Card** (Saiman Shetty) | EB-1A coaching + AI | High-achievers | Self-funded | Premium $17K, different price tier |
| **Caseblink** | AI for immigration lawyers | Law firms | $2M pre-seed | They sell to lawyers; we sell to individuals |
| **Docketwise** | Case management SaaS | Immigration lawyers | Established | Different layer entirely |
| **Visalaw.ai** | AI research/drafting for lawyers | Lawyers | Partnered with Fastcase | Different user |
| **Formally** (Amélie Vavrovsky) | Immigration forms | Unknown | Forbes 30u30 | Need to investigate product |
| **US Immigration AI** | Unified case solution | Law firms | Founded 2025 | Lawyer-facing |
| **Sprintax** | Non-resident tax | Students | Established | English-only, clunky. Guardian's tax side directly competes. |

### Guardian's White Space
```
                    CLIENT-FACING ←─────→ LAWYER-FACING
                         │                      │
    PRE-INTAKE           │                      │
    (before lawyer)      │   ★ GUARDIAN          │
                         │   (doc checking +     │
                         │    cross-domain)      │
                         │                      │
    ─────────────────────┼──────────────────────┤
    INTAKE               │  JustiGuide          │  Docketwise
    + MATCHING           │  OpenSphere          │  eImmigration
                         │                      │
    ─────────────────────┼──────────────────────┤
    CASE MANAGEMENT      │  Boundless           │  Alma, Visalaw.ai
    + FILING             │  Smart Green Card    │  US Immigration AI, Caseblink
                         │                      │
```

**No one owns pre-intake, client-facing, cross-domain (immigration + tax + corporate).** That's Guardian's unique position.

---

## 7. Legal & Regulatory Structure

### Operating Zones

```
ZONE 1: SAFE (No license needed)
✓ Document checking (typos, missing fields, inconsistencies)
✓ Form translation / explanation of what fields mean
✓ Organizing documents into a data room
✓ AI flagging "this field looks incomplete"
✓ General information about immigration/tax processes
✓ Connecting users to licensed attorneys/CPAs
→ Guardian's current product lives here. Zero risk.

ZONE 2: GRAY (Risky without licensed professional)
⚠ Suggesting which forms to file
⚠ Recommending visa categories
⚠ Proposing how to answer form questions
⚠ AI saying "your best path is..."
→ Requires attorney in the loop.

ZONE 3: UNAUTHORIZED PRACTICE OF LAW
✗ Filing forms on behalf of a client (requires G-28)
✗ Representing before USCIS
✗ Advising on strategy for compensation
✗ Interpreting law for specific cases
→ Only bar-licensed attorneys (or DOJ-accredited reps) can do this.
```

### The Attorney Question

**You don't need to be a law firm to build Guardian.** You only need a licensed attorney when you want to expand beyond Zone 1.

**Who can practice US immigration law:**
- JD + US state bar admission → Yes
- LLM + US state bar admission (NY, CA, DC, MA, IL, TX, GA, MD allow LLMs to sit) → Yes
- Foreign law degree + US LLM + US bar → Yes
- LLM without bar → No
- No law degree → No

**Physical location is not required.** US immigration law is federal. A US bar-licensed attorney can practice from anywhere in the world (including China) as long as they:
1. Maintain an active US bar license
2. Complete CLE requirements
3. Don't practice local law in their host country

**Optimal hiring target for Guardian:**
- Chinese law degree (LLB) + US LLM (NYU/Columbia/Fordham) + NY bar passed
- Based in China
- Mandarin + English fluent
- Cost: $20-40K/year (vs. $60-75K US-based)
- Covers Chinese-speaking users, US night shift timing works for Asia-Pacific users

### Delegation Rules (ABA Rule 5.3)

**What your team/AI can do (under attorney supervision):**
- ✓ Client intake and information gathering
- ✓ Document organization and data room building
- ✓ Form population based on client data
- ✓ Document checking (typos, missing fields)
- ✓ Factual research (processing times, fee schedules)
- ✓ Draft preparation and petition assembly
- ✓ Translation
- ✓ Case tracking and deadline management
- ✓ Client communication (non-advisory)

**What only the attorney can do:**
- ✗ Legal advice ("you should file X")
- ✗ Strategy decisions
- ✗ Sign G-28 (entry of appearance)
- ✗ Final petition review
- ✗ RFE responses
- ✗ USCIS interview representation
- ✗ Eligibility assessment
- ✗ Law interpretation

**The key insight:** ~90% of the work in any immigration filing is mechanical (intake, forms, doc prep). Only ~10% requires an attorney (strategy, final sign-off, filing). Guardian's AI + team handles 90%. Attorney handles 10%.

### Revenue Model: The Boundless Blueprint

**Attorneys: strict rules — cannot collect referral fees.**
Instead, use the subcontractor model:

```
Client pays Guardian $1,500 for "H-1B Petition Package"
                ↓
Guardian's AI + team does 90% of work
                ↓
Guardian pays attorney a flat $500 for review + signing
                ↓
Guardian keeps $1,000

This is NOT a referral fee.
This is Guardian selling a service with attorney as subcontractor.
```

**Legal requirements:**
- Guardian owns the client relationship
- Client pays Guardian directly
- Attorney is paid by Guardian (fixed fee, not % of revenue)
- Clear disclosures that Guardian is not a law firm
- Attorney exercises independent professional judgment

### CPAs: Much More Flexible

**CPAs CAN receive and pay referral fees** under AICPA Rule 503, with:
1. Written disclosure to the client
2. Not for clients where the CPA performs audit/review/compilation

Since Guardian's users need tax prep (not audits), the attest restriction doesn't apply.

**What Guardian can do with CPAs:**
- ✓ Collect referral fees from CPAs (disclosed)
- ✓ Pay CPAs for referrals
- ✓ Revenue-share with CPAs
- ✓ Subcontractor model
- ✓ Bundle tax prep into service packages

**The tax side is much easier to monetize than immigration.** Tax referral revenue can subsidize the immigration side while Guardian builds volume.

---

## 8. Tax Services for Immigrants (Detailed)

### Complexity Spectrum

```
SIMPLE ──────────────────────────────────── NIGHTMARE

Student     H-1B Employee    Immigrant    Immigrant        Immigrant
(F-1)                        w/ foreign   Founder          Founder w/
                             accounts     (small)          foreign ops
$0-30       $200-500         $500-1,500   $2,000-5,000     $10,000-30,000
```

### Tier 1: Student Tax (F-1 / J-1)
**Complexity:** Low
**Price point:** $0-99

**Forms:**
- Form 8843 (required even with $0 income) — THE FREE LEAD MAGNET
- Form 1040-NR (if had income)
- Form 8833 (treaty claim, China Art. 20 gives $5K exemption)
- State return (if applicable)

**Opportunity:** ~1M international students in US. Sprintax dominates at $50+. Guardian can undercut with free 8843 + $29 basic filing.

### Tier 2: H-1B Employee Tax
**Complexity:** Moderate
**Price point:** $99-500

**Key issues most tools miss:**
- Substantial Presence Test (resident vs non-resident)
- Dual-status return in arrival year
- Tax treaty benefits (first 5 years for China)
- RSU/ESPP double-counting on W-2s
- Multi-state allocation
- **FBAR (FinCEN 114)** — required if foreign accounts >$10K aggregate. $10K+ penalty per account per year for missing it.
- **Form 8938 (FATCA)** — required if foreign assets >$50-100K

**Opportunity:** Most Chinese/Indian H-1B holders still have bank accounts back home. TurboTax/H&R Block don't catch FBAR. Massive compliance gap.

### Tier 3: Immigrant Founder Tax (Small)
**Complexity:** High
**Price point:** $1,500-3,000

**Critical issues:**
- **83(b) Election** — 30-day deadline from stock grant. Missing it = paying tax on vesting over years instead of $0 at grant. Potentially $100K+ in extra tax.
- Founders stock vesting
- QSBS qualification ($10M+ potential exclusion on exit)
- Entity formation choice (LLC vs C-corp — non-resident implications)
- Delaware C-corp standard setup
- State tax planning

### Tier 4: Founders with Foreign Operations
**Complexity:** Very High
**Price point:** $3,000-10,000

**Nightmare forms:**
- **Form 5471** (foreign corporation ownership) — $10K penalty for missing
- **Form 5472** (foreign-owned US corp) — $25K penalty for missing
- **Form 8621** (PFIC) — harshest tax regime in the code
- **CFC/GILTI** rules (Controlled Foreign Corporation)
- **VIE structure** compliance (common for China-US startups)
- **SAFE Circular 37** (China State Administration of Foreign Exchange)
- **Transfer pricing** between US and foreign entities

**Most general CPAs cannot handle these.** This is a specialized market where fees are high and demand is growing.

### Tier 5: Cross-Border Exit Planning
**Complexity:** Extreme
**Price point:** $5,000-30,000

- Pre-immigration tax planning (step-up basis before becoming resident)
- Green card exit tax (Form 8854, mark-to-market)
- QSBS stacking strategies
- State tax arbitrage before exit

### The Cross-Domain Edge

Guardian's unique value is **cross-referencing tax + immigration + corporate docs** to catch errors no single-domain tool can see:

```
Example inconsistencies Guardian would catch:

❗ "Your I-485 lists $180K income but your 1040 shows $90K — 
   this mismatch could trigger an RFE"

❗ "You received stock options 45 days ago but no 83(b) election 
   in your data room — you're past the 30-day deadline"

❗ "Your H-1B petition mentions your startup but no Form 5471 
   for your Shanghai entity — $10K penalty exposure"

❗ "Your O-1 petition claims founder income but your tax returns 
   show no Schedule C or K-1 — credibility problem"

❗ "You have $15K in a Chinese bank account but no FBAR filing 
   in the last 3 years — $30K+ penalty exposure"

❗ "Your green card app's employment history doesn't match 
   your W-2 dates — USCIS will notice"
```

**No existing tool catches these.** This is Guardian's moat.

---

## 9. Outreach Plan

### Current Pipeline
- **913 DIY navigators** in existing LinkedIn network (scored by rubric)
- **46 external leads** from LinkedIn Premium searches
- **12 lawyer/CPA partnership targets**
- **5 communities** identified for distribution

### Priority 1: Warm Connections (Contact First)
- **Top scored**: Sagar Khatri (Multiplier, email available), Aizada Marat (Alma)
- **19 YC Founders** in network — highest urgency, active visa navigation
- **22 Stealth founders** — max DIY, early stage
- **Students with email** (5 direct leads)

### Priority 2: External LinkedIn Leads (Warmest by Mutual Connections)
- **Kai Cheng** — 97 mutual connections (!)
- **Madhav Goenka** — Stanford, 73 mutual connections
- **Fred von Graf** — 43 mutual connections
- **Bryan Huang** — LANDED, 33 mutual
- **Keyu Chen** — 21 mutual, Chinese founder in SF
- **Simon Chan** — FirsthandVC, 16 mutual
- **Zhou (Jo) Yu** — Columbia CS prof, 22K followers, Chinese founder

### Priority 3: Lawyer/CPA Partnerships
- **Sophie Alcorn** — Alcorn Law, TechCrunch "Ask Sophie" columnist (confirmed still active)
- **Nicole Gunara, J.D.** — "Tech Disruptor, Ally to Founders"
- **Jomana Abdallah** — Ex-Fragomen, stealth legaltech founder
- **Jianan Chen** — Chinese immigration attorney (perfect for niche)
- **Sylvia Gorajek** — America Unlocked, 7K followers, self-petition community

### Priority 4: Communities to Tap
1. **Unshackled Ventures** — THE immigrant founder VC. Partnership unlocks their entire portfolio.
2. **Immigrant Founders Mixer** — in-person meetup with Unshackled + One Way + Foothill
3. **NYCEDC Founder Fellowship 2026** — 60 startups, applications open
4. **Columbia CUCSSA** — direct WeChat access to Chinese students
5. **America Unlocked** (Sylvia Gorajek) — 7K-follower community, sponsorship/content opportunity

### Outreach Message Templates

**For founders:**
> "Hey [name], fellow founder here building Guardian — an AI tool that checks immigration docs before USCIS sees them. As someone navigating [visa type], I'd love your honest feedback on what we're building. 5 min? [link]"

**For students:**
> "Hi [name], I'm building Guardian — we just launched a free Form 8843 generator for international students (most of us don't realize we need to file this even with no income). Would love if you tried it and told us what sucks. [link]"

**For lawyers/CPAs:**
> "Hi [name], I'm building Guardian — an AI intake tool that checks clients' immigration/tax docs before they reach you, so your clients arrive with organized, error-checked files. Not a replacement for your work — a pre-intake layer that saves you hours. 15 min to show you? [link]"

---

## 10. Program Applications (Apply This Week)

### NVIDIA Inception Program
- **Status:** Apply immediately
- **Cost:** Free
- **Benefits:** Badge for credibility, GPU cloud credits, co-marketing, VC intros
- **Application:** Rolling, no deadline
- **URL:** https://www.nvidia.com/en-us/startups/
- **Why:** JustiGuide and Smart Green Card both display NVIDIA Inception badges. Low-effort credibility.

### NYCEDC Founder Fellowship 2026
- **Status:** Applications open
- **Cost:** Free to apply
- **Benefits:** Part of 60-startup cohort, mentorship, NYC ecosystem access
- **URL:** https://edc.nyc/founder-fellowship
- **Why:** Meet 59 other NYC immigrant founders = target user pipeline

### TechCrunch Battlefield 200 (2026)
- **Status:** Apply by **May 27, 2026**
- **Cost:** Free to apply
- **Benefits:** Thousands apply, 200 selected, 20 pitch live. Winner = $100K + massive press
- **URL:** https://techcrunch.com/startup-battlefield/
- **Why:** This is how JustiGuide got their TechCrunch article and the "Best Pitch in Policy + Protection" award that built their credibility. Replicable.

### TIME Best Inventions
- **Status:** Watch for 2026 nomination window (usually mid-year)
- **Cost:** Free
- **Benefits:** Editorial selection, massive press value
- **Why:** JustiGuide Relo was 2025. A Mandarin-first AI doc checker for immigrants has a similar "best invention" narrative.

### Future / Secondary Programs
- **Y Combinator** — consider for W27 or S27 batch
- **On Deck** — various fellowships
- **Pear VC, First Round** — if raising

---

## 11. Team & Hiring Path

### Current Team
- **Cheney Li** — Founder, product, engineering. Chinese immigrant. Trilingual (Mandarin/English/Japanese). Previous: HappyHunting (job platform for immigrants).

### Phase 1 Hires (Next 6 Months)
1. **Technical co-founder** (optional) — if Cheney wants engineering leverage
2. **China-based US-licensed attorney** — LLM + NY bar graduate, Mandarin fluent, $20-40K/year
   - Reviews immigration docs
   - Signs G-28s
   - Handles RFEs
   - Hire target: fresh LLM graduates from NYU/Columbia/Fordham who passed NY bar and returned to China
3. **Enrolled Agent (EA) for tax** — federally licensed (easier than CPA), can practice anywhere, ~$60-80K/year US or $20-30K China-based

### Phase 2 Hires (6-12 Months)
4. **Customer success / community manager** — Mandarin native, manages 小红书/WeChat content
5. **Second attorney** — for case volume
6. **Growth marketer** — SEO, content, 小红书 content creator

### What You DON'T Need Yet
- US office
- Multiple attorneys
- Full-time CPA
- Sales team
- Legal compliance officer (attorney handles this)

---

## 12. Key Strategic Insights

### 1. The Niche IS the Moat
Broad players (JustiGuide, Boundless) optimize for scale but sacrifice depth. A Mandarin-first, WeChat-distributed tool with cultural context cannot be replicated without cultural fluency. Cheney's Chinese + English + Japanese background IS the moat.

### 2. Free Lead Magnet → Long LTV
Form 8843 generator is free and takes 1 weekend to build. Every student captured today is a $10-30K LTV founder in 7 years. CAC approaches zero via organic Mandarin content.

### 3. Pre-Intake Is White Space
All competitors are either lawyer-facing (Docketwise, Alma, Caseblink) or full-service (Boundless, JustiGuide). Nobody owns "check your docs before you see a lawyer." Guardian can sit upstream of all of them and partner with them downstream.

### 4. Cross-Domain Is Genuinely Unique
No competitor cross-checks immigration + tax + corporate documents. Every immigrant founder has this pain. The inconsistency-catching feature is the "holy shit" moment no one else can replicate with a single-domain tool.

### 5. The Student Wedge Is Better Than Expected
Initial analysis dismissed student tax as "too simple" but the actual opportunity is:
- 1M+ international students (huge TAM)
- Massive compliance gap (Form 8843 unknown)
- Sprintax is English-only and clunky
- Near-zero CAC via organic channels
- Captures users at year 1 of a 10-year journey

### 6. China-Based Attorney Is a Strategic Advantage
Hiring a NY bar-licensed, Mandarin-fluent attorney in China at $20-40K/year:
- Serves Chinese users in their native language
- Covers Asian time zones
- 60-70% cheaper than US-based attorneys
- Fully legal (US immigration law is federal)

### 7. Tax Revenue Subsidizes Immigration
CPAs can take/pay referral fees (flexible). Attorneys cannot (strict). Guardian's tax side can grow faster with lower legal complexity while the immigration side builds volume.

### 8. The Target User Is Specific
NOT big corp employees with Fragomen on retainer. YES startup founders, early employees at small companies, and international students personally navigating paperwork. If they have a corporate immigration lawyer, Guardian is redundant. If they're Googling "how to file my own O-1" at 2am, Guardian is their answer.

### 9. Execution vs. Advisory — Two Products, Not One
Every attorney-involved service should exist in TWO modes:
- **Execution Mode** — for self-directed users who know what they need ($199-399)
- **Advisory Mode** — for uncertain users who need strategy ($499-799)

Users self-select via qualifying questionnaire. Legally permitted as "limited scope representation" under ABA Model Rule 1.2(c). This:
- Doubles the SKU count per service
- Improves margin on Execution mode (15-20 min attorney time vs 60-90 min)
- Lowers entry price for volume conversion
- Segments users automatically based on their actual needs
- Protects attorney with documented scope boundaries
- Requires signed limited scope agreement + "stop and flag" safety net

---

## 13. Risks & Open Questions

### Legal Risks
- **Unauthorized practice of law** if Guardian drifts from Zone 1 into Zone 2/3 without proper attorney supervision
- **Tax preparer regulations** (PTIN, EFIN, software certification) if expanding into actual filing
- **State-by-state variation** in UPL and referral fee rules

### Product Risks
- **LLM accuracy** — misleading a user about their visa eligibility could have real consequences
- **Document security** — immigrants are sharing sensitive docs (passports, tax returns, bank statements). Breach = catastrophic.
- **Liability coverage** — need professional liability insurance as soon as we expand beyond Zone 1

### Competitive Risks
- **JustiGuide adding Mandarin** — their biggest threat. Mitigate with cultural fluency + WeChat distribution that's hard to replicate.
- **Boundless acquiring smaller players** — well-funded, could roll up the market
- **OpenAI/Anthropic launching immigration templates** — generic AI tools could commoditize the basic doc checking

### Open Questions
- [ ] Should Guardian file its own Delaware C-corp before hiring the first attorney?
- [ ] What's the first pricing test? $29 student tax or $49 H-1B doc check?
- [ ] Should Form 8843 generator live on guardian.ai or a separate subdomain for SEO?
- [ ] Partner with America Unlocked for content cross-promotion, or build competing content?
- [ ] Investigate Formally (Amélie Vavrovsky) — is it a competitor or non-overlapping?
- [ ] How to structure the China attorney relationship legally (employee vs. contractor, who owns the IP)?

---

## 14. 90-Day Execution Plan

### Phase 1: Tier 0 Only (No attorney needed)

**Weeks 1-2: Foundation**
- [ ] Apply to NVIDIA Inception Program
- [ ] Apply to NYCEDC Founder Fellowship 2026
- [ ] DM/email the 60 Priority 1 contacts (YC founders, stealth founders, immigration-adjacent)
- [ ] Build Form 8843 generator MVP (1 weekend)
- [ ] Draft TechCrunch Battlefield 2026 application

**Weeks 3-4: Launch Wedge**
- [ ] Deploy Form 8843 generator publicly
- [ ] First 小红书 post in Mandarin about Form 8843
- [ ] First WeChat group distribution (CUCSSA, NYU Chinese students)
- [ ] Reddit r/f1visa post
- [ ] Partnership outreach to 2-3 university ISSO offices

**Weeks 5-6: Expand Tier 0 Products**
- [ ] Add student tax filing (1040-NR + 8843) at $29
- [ ] Add H-1B doc check at $49
- [ ] Add FBAR compliance check at $49
- [ ] Add 83(b) election filing at $99
- [ ] First paid customer
- [ ] Record first demo video

### Phase 2: Prepare Attorney Infrastructure

**Weeks 7-8: Attorney Hire + Legal Framework**
- [ ] Post job: "China-based US immigration attorney (Mandarin fluent, NY bar)"
- [ ] Interview 5 candidates
- [ ] Sign one on as part-time contractor ($3-5K/month retainer)
- [ ] Draft limited scope representation agreements (Execution Mode)
- [ ] Draft full representation agreements (Advisory/Boundless modes)
- [ ] Set up attorney sign-off checklists per service type
- [ ] Professional liability insurance (for Guardian, not attorney)

**Weeks 9-10: Partnerships + First Execution Product**
- [ ] Reach out to Sophie Alcorn (Ask Sophie column)
- [ ] Reach out to Unshackled Ventures for portfolio partnership
- [ ] Reach out to 3 CPAs serving Chinese community
- [ ] Attend Immigrant Founders Mixer in person
- [ ] **Launch first Execution Mode product: OPT Application Execution ($199)**
  - Qualifying questionnaire built
  - Limited scope agreement flow
  - Attorney review workflow
- [ ] Test with 10-20 users to iterate on questionnaire + flow

### Phase 3: Scale Execution Mode + Press

**Weeks 11-12: Press & Scale**
- [ ] Submit TechCrunch Battlefield application (before May 27)
- [ ] Pitch story to CBS / local press (immigrant founder angle)
- [ ] Add more Execution Mode products:
  - STEM OPT Extension Execution ($199)
  - H-1B Extension Execution ($299)
  - Naturalization Form Execution ($399)
- [ ] Add Advisory Mode variants for each
- [ ] Reach 100 paying customers across all tiers

### Deferred Until Phase 4 (Month 4+)
- H-1B Registration (time for March 2027 lottery — Months 7-9 to prepare)
- H-1B Petition Standard (Tier 2 Boundless assigned)
- O-1 Petition (Tier 3 panel — requires 3 attorneys on panel)
- EB-1A Self-Petition (Tier 3 panel)
- Cross-border tax planning (requires CPA partnership)

---

## 15. Product Design: Legal Service Integration

### Core Principle
**Reveal, don't push.** The attorney appears when Guardian's AI finds something that actually needs one — not as a constant upsell. Users should feel the AI is on their side, and the attorney is the safety net for when stakes are high.

### User Journey
```
1. User uploads documents
2. Guardian AI scans and classifies each check
3. Dashboard shows traffic-light results:
   ✓ Green — passed
   ⚠ Yellow — self-fixable
   🔴 Red — needs attorney review
4. Attorney CTA only surfaces when red items exist
5. User clicks for detail: what's wrong, why it matters, what the attorney will do, transparent pricing
6. Request attorney review → assigned to panel attorney
7. Attorney responds in 24-48h in Guardian's messaging
8. Attorney signs G-28 and files if applicable
9. Case tracking in dashboard
```

### Key UI Patterns

**Pattern A: Traffic Light Confidence System**
Every check gets green/yellow/red. Attorney CTA only surfaces when red items exist. No red = no upsell. This builds trust — Guardian isn't trying to push toward a lawyer unnecessarily.

**Pattern B: "What Would An Attorney Do?" Expansion**
When user clicks a red item, show:
- What we found (the specific issue)
- Why it matters (risk + penalty + business consequence)
- What the attorney would do (concrete actions)
- Transparent pricing (single issue vs. full review)
- Comparison to traditional law firm cost

**Pattern C: Attorney Profile Cards**
Attorneys appear as real people with: photo, bar number, school, specialties, languages (Mandarin highlighted for Chinese users), case count, review rating, response time. This is critical for trust — especially for Chinese users who want to know the attorney speaks their language.

**Pattern D: Compliance Disclosure Banner**
Every page with attorney interaction shows: "Guardian is not a law firm. Legal services are provided by independent licensed attorneys who exercise independent professional judgment."

**Pattern E: Smart Bundle Logic**
When user has multiple red items, show honest comparison: single issues total ($X) vs. full review ($Y). Even if the bundle is more expensive, show the value difference (unlimited fixes, RFE protection, etc.).

---

## 16. Product Design: Attorney Matching & Panel Model

### The Legal Line

| Activity | Legal Status |
|----------|-------------|
| Listing attorneys with objective info | ✅ Fine — it's a directory |
| Ranking by objective criteria + match quality | ✅ Fine — same as Avvo, LegalMatch |
| "We recommend Attorney X" | ⚠️ Gray/risky — can cross into UPL |
| Taking a % of legal fees | ❌ Banned — killed Avvo Legal Services in 2018 |

**Rule:** Subscription or flat per-lead fees = legal. Percentage of case fee = prohibited even if called "marketing fee."

### Recommended Structure: Four-Mode Hybrid

Attorney engagement varies by service complexity AND user certainty. Four distinct models:

| Service Tier | Model | Attorney Involved? | User Chooses Attorney? |
|-------------|-------|-------------------|----------------------|
| **Tier 0: Mechanical** | Pure software | No | N/A |
| **Tier 1A: Execution Mode** | Limited scope (Rule 1.2(c)) | Yes (verify + file) | No — assigned |
| **Tier 1B: Advisory Mode** | Full consultation + execution | Yes (strategy) | No — assigned |
| **Tier 2: Boundless Assigned** | Full representation | Yes (complete case) | No — assigned |
| **Tier 3: Curated Panel** | Full representation | Yes (specialist) | **YES — from 3** |

**Examples by service:**

| Service | Tier | Model | User Choice |
|---------|------|-------|-------------|
| Form 8843 (free) | 0 | Software | N/A |
| Student tax $29 | 0 | Software + EA | N/A |
| H-1B doc check $49 | 0 | Software | N/A |
| FBAR filing $99 | 0 | Software + EA | N/A |
| OPT application Execution $199 | 1A | Limited scope | No |
| OPT application Advisory $499 | 1B | Full advisory | No |
| H-1B registration Execution $299 | 1A | Limited scope | No |
| H-1B registration Advisory $799 | 1B | Full advisory | No |
| H-1B petition standard $1,499 | 2 | Boundless assigned | No |
| O-1 petition $3,500 | 3 | Panel | **Yes — 3 options** |
| EB-1A self-petition $6,000 | 3 | Panel | **Yes — 3 options** |
| Cross-border tax $5,000+ | 3 | Panel | **Yes — 3 options** |

**Key insight:** User self-selection happens at two levels:
1. **Execution vs. Advisory** (Tier 1) — via qualifying questionnaire
2. **Attorney choice within panel** (Tier 3) — via match scoring

**Simple execution cases** use limited scope representation (fast, cheap). **Complex specialist cases** use curated panel (client picks from 3 with transparent matching). **Everything in between** uses Boundless assigned model.

### Magic Words That Keep You Safe

**Use ✅:**
- "Match" (informational, not advisory)
- "Based on your case"
- "Filter" / "Sort"
- "Panel"
- "Information"
- "Independent professional judgment"
- "Not a law firm"
- "Choose your attorney"

**Avoid ❌:**
- "Recommend"
- "Best" / "Top-rated" as endorsement
- "We think you should"
- "Guaranteed results"
- "Our lawyer"
- "Endorse" / "Certify"

### Match Algorithm Transparency (Key Differentiator)

Go further than Avvo: show users exactly how matching works.

```
How We Matched You

Your inputs           | Weight | Attorney Wei
──────────────────────────────────────────────
Visa type: H-1B       |  25%  | ✓ 200+ cases
Language: Mandarin    |  25%  | ✓ Native speaker
Case complexity: Med  |  20%  | ✓ Experienced
Response time pref    |  15%  | ✓ <4h avg
Location pref: US     |  10%  | ⚠ China-based
Budget: Standard      |   5%  | ✓ Matches panel

TOTAL MATCH SCORE: 92/100

This is information, not a recommendation.
You choose the attorney who fits you best.
```

**Why this works:**
1. Legally bulletproof — algorithmic, objective, transparent
2. Builds user trust — they see what's in the score
3. Educates users on what to look for
4. Differentiates Guardian — no competitor shows this
5. Audit trail — deterministic algorithm stands up to legal review

### Attorney Revenue Streams (All Compliant)

| Model | Detail | % of Guardian's legal revenue |
|-------|--------|------------------------------|
| **Service packages (Boundless)** | Client pays Guardian, Guardian pays attorney flat fee | 80% |
| **Panel subscription** | Attorney pays $300-500/month for panel listing | 15% |
| **Per-lead fee** | Attorney pays flat $50-200 per qualified lead | 5% |

**Never:** % of legal fee, success fee, scaled "marketing fee," or referral kickback.

### Disclosure Pattern

Every attorney-matching page displays:
> ℹ **How Guardian Works**
> Guardian is not a law firm and does not recommend any particular attorney. We display information about licensed attorneys who participate in our panel. You select the attorney who is right for you. Attorneys on our panel pay a subscription fee for listing. [Learn more about our matching methodology]

This distances Guardian from "recommending," discloses the payment relationship (FTC + state bar rules), preserves user agency, and frames matching as informational.

---

## 17. Product Design: Form 8843 Conversion Funnel

### Core Principle
**Form 8843 is a gift, not a trick.** Genuinely help students. Play the long game — a student who trusts Guardian at year 1 becomes a $20K founder at year 7.

### User Journey
```
Day 1: Discovery on 小红书 / WeChat / Reddit
Day 1: Mandarin landing page
Day 1: Email signup (single field)
Day 1: 60-second onboarding (6 questions, one at a time)
Day 1: PDF delivered + "What's Next" reveal
Week 1-4: Educational email drip (value-first, not salesy)
Month 1: Immigration Roadmap dashboard
Months 2-12: Trigger-based reminders
Year 1 tax season: Upsell to 1040-NR filing ($29)
Year 2: OPT document check ($29)
Year 3: H-1B lottery prep ($49-99)
Year 4-5: Green card review ($199-499)
Year 7+: Founder phase ($2,000-5,000)
Year 10+: Exit planning ($5,000-15,000)

Total LTV: $10,000-30,000+
CAC via Form 8843: near $0
```

### Key UX Patterns

**Pattern A: 60-Second Onboarding**
Don't show all 6 questions at once. Animate one at a time with progress dots. Feels like a conversation, not a form. Under 60 seconds even if it takes 90.

**Pattern B: "What's Next" Reveal at Delivery**
When delivering the PDF, show:
- Main deliverable (Form 8843 PDF)
- Below: "Based on what you told us, you might also need..." with 3 cards
  - Form 1040-NR reminder ($29 offer)
  - Tax treaty benefit alert ("Save $500-1,200")
  - FBAR warning if student has Chinese bank account >$10K
- Prominent "Just the 8843, thanks" button — users who feel they can say no convert better later

**Pattern C: Immigration Roadmap Dashboard**
Visual timeline showing: F-1 → OPT → STEM OPT → H-1B → Green Card → Citizen, with "You are here" marker. Shows what's done, what's next, what it costs. Creates emotional investment in their journey and makes future upsells feel expected.

**Pattern D: Value-First Email Drip**
- Week 1-2: Educational only, zero sell ("Tax secrets most students don't know")
- Week 3-4: Soft product intro tied to real deadlines
- Week 8+: Trigger-based (not time-based) — "Your OPT window opens soon"

**Pattern E: The Annual Habit Hook**
Every January, bring them back: "Your Form 8843 reminder for 2027. We've pre-filled it based on last year's info. Takes 30 seconds." This annual ritual is the most valuable part — every year, a % converts to paid services.

### Design Principles Summary

| For Legal Integration | For Form 8843 Funnel |
|----------------------|---------------------|
| Reveal, don't push | Gift, not trap |
| Transparency over mystery | Discovery over pitch |
| Human attorney faces | Long-term horizon (year-7 LTV) |
| Compliance banner everywhere | Visual journey roadmap |
| Traffic light confidence tiers | One question at a time |
| Escape hatches always visible | Mandarin-first copy |
| Objective match scoring | Educational email drip |
| Match algorithm transparency | Annual ritual hook |

### MVP Build Order
1. **Week 1-2:** Form 8843 generator (free, Mandarin-first landing page)
2. **Week 3-4:** Immigration Roadmap dashboard (visual timeline)
3. **Week 5-6:** Email drip infrastructure
4. **Week 7-8:** $29 student tax filing product (first paid SKU)
5. **Week 9-10:** Attorney request flow (manual handoff to China attorney, automate later)
6. **Week 11-12:** Traffic light confidence system on doc checker

**Don't build yet:** Full case management dashboard, in-app messaging with attorney (use email first), complex payment flows, persistent user accounts with data rooms.

**First validation milestone:** 1,000 students on Form 8843 → 100 convert to $29 filing → $3,000 revenue with near-zero CAC. Proves the wedge works.

---

## Appendix A: Data Files Reference

| File | Contents |
|------|----------|
| `data/linkedin/guardian_scored_v2.json` | All 2,463 LinkedIn connections scored on DIY Navigator rubric |
| `data/linkedin/guardian_outreach_v2.json` | Connections categorized by wave |
| `data/linkedin/linkedin_search_candidates.json` | 46 external leads from LinkedIn Premium searches |
| `data/linkedin/OUTREACH_STRATEGY.md` | Detailed outreach plan with tier breakdowns |
| `data/linkedin/SCORING_RUBRIC.md` | Full scoring rubric documentation |
| `data/linkedin/JUSTIGUIDE_DEEP_DIVE.md` | Competitor analysis of JustiGuide |
| `data/linkedin/Connections.csv` | Raw LinkedIn connections export |

## Appendix B: Key Contacts Already Identified

### Tier 1 (Contact This Week)
1. Sagar Khatri (Multiplier CEO) — sagarkhatri1193@gmail.com
2. Aizada Marat (Alma CEO)
3. Matt Gale (Manifest O.S., Corporate Immigration)
4. Pegah Karimbakhsh Asli (Alma attorney)
5. Abhinav Kumar (Alma Chief of Staff)
6. Eric (Yuan) Cheng (Jobright.ai)
7-25. 19 YC founders in network
26-35. Top 10 warmest external leads (Kai Cheng, Madhav Goenka, etc.)

### Partnership Targets
1. Sophie Alcorn (Alcorn Law)
2. Jianan Chen (Chinese immigration attorney)
3. Unshackled Ventures (Manan M., Nitin Pachisia, Alexis Maciel)
4. Sylvia Gorajek (America Unlocked)
5. Fa Wang (Easton Tax CPA, Chinese community)

---

## Appendix C: Success Metrics (90 Days)

| Metric | Target |
|--------|--------|
| Form 8843 generator users | 1,000+ |
| Paying customers | 100+ |
| Revenue | $5,000-10,000 |
| LinkedIn connections messaged | 200+ |
| Response rate to outreach | 15%+ |
| Meetings booked | 30+ |
| Attorney partnerships | 1 contracted |
| CPA partnerships | 2 contracted |
| Press mentions | 1-2 |
| Programs admitted | NVIDIA Inception + TechCrunch Battlefield application submitted |
| User testimonials | 10+ |

---

**End of Document**
