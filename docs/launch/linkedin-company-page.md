# Guardian — LinkedIn Company Page Setup

**Drafted:** 2026-04-30
**For:** Cheney Li to copy-paste into LinkedIn's "Create a Company Page" flow
**Setup URL:** https://www.linkedin.com/company/setup/new/

---

## Strategic Note: Personal LinkedIn vs Company Page

Your **personal account** (913 connections) is your highest-leverage asset — self-directed filers trust people, not brands. The company page exists to:

1. Be the linkable "official" entity when you post / get tagged
2. Host future job listings (you'll need this for any H-1B sponsorship downstream)
3. Carry the verified brand identity that programs like NVIDIA Inception and TechCrunch Battlefield will check
4. Run LinkedIn Ads later (requires a company page)

**Posting cadence:** 80% from personal account (story, founder voice, comments on others), 20% from company page (product updates, milestones, hiring). Don't reverse this — empty company pages with founder-style posts feel hollow.

---

## Step 1: Create Page (Setup Fields)

Paste these into the "Create a Company Page" form at linkedin.com/company/setup/new/.

### Page Type
**Company** (not "Showcase Page" — those are sub-pages of a parent company; not "Educational Institution" or "Nonprofit")

### Page Identity

| Field | Value |
|---|---|
| **Name** | Guardian Compliance |
| **LinkedIn public URL** | `linkedin.com/company/guardian-compliance` |
| **Website** | `https://guardiancompliance.app` |
| **Industry** | **Software Development** (primary). LinkedIn allows only one — don't pick "Legal Services" because that limits the audience LinkedIn surfaces you to and triggers different ad-policy rules. |
| **Company size** | **2-10 employees** (use this even if it's just you + part-time professionals; "1" looks like a hobby project) |
| **Company type** | **Privately Held** |
| **Founded** | **2026** |
| **Tagline** (120 chars max) | *AI pre-intake compliance for self-directed legal/tax navigators — catch document errors before USCIS, IRS, or state agencies do.* (118 chars ✓) |

### Logo
- **Spec:** 300×300 PNG, transparent background preferred
- **Source:** export from your existing brand kit; the glassmorphic mark (no wordmark) at 300px square
- **File path on your machine:** likely `frontend/public/` — check for `logo.png` or `guardian-icon.svg`

### Cover Image
- **Spec:** 1128×191 (4:1 ultrawide), PNG/JPG, ≤4MB
- **Content recommendation:** soft glassmorphic blue gradient (`#e8eff6` → `#dce4f0`) + tagline left-aligned: *"Check your immigration docs before USCIS does."* in `#0d1424`, 48px SF Pro Display Semibold. Right third: three stacked translucent doc icons with the Guardian logo overlay.
- **Build in:** Figma (1128×191 frame), or Canva LinkedIn cover template.

---

## Step 2: About Section (Edit after page is live)

### Description (2,000 chars max — paste into "About" → "Overview")

> Guardian is the AI pre-intake compliance layer for self-directed legal/tax navigators — founders, international students, and early employees at small companies who navigate their own paperwork because they don't have a corporate immigration team behind them.
>
> We're the only tool that cross-checks immigration, tax, and corporate documents *together*. Real life isn't compartmentalized: a 1099-NEC line on your tax return can raise an H-1B question, a duty description on your I-983 can contradict your offer letter, and a board resolution can quietly conflict with your O-1 petition. Single-domain tools miss these. Guardian doesn't.
>
> **What we do**
> - **Cross-check** your I-983, employment letter, 1040, board resolutions, and visa petitions in a single pass
> - **Form Filler** that reads any USCIS, IRS, or state PDF and fills it from your existing documents — every value cited back to its source
> - **Free Form 8843 generator** for international students — no signup, no credit card, takes 90 seconds
> - **Personal data room** that holds every document you've ever filed, organized by person, year, and filing
>
> **Who we're for**
> - Founders sponsoring their own visa (O-1, EB-1, H-1B via own company)
> - International students moving from OPT to STEM OPT to H-1B
> - Early employees at small companies whose employer sponsors the visa but doesn't retain Fragomen or BAL
> - Bilingual users who'd prefer Mandarin and English alongside USCIS-required English filings
>
> **Why now**
> STEM OPT RFE rates nearly doubled from 6% to 10% over two years (NAFSA, 2024). H-1B specialty-occupation challenges remain the most common RFE category. Self-directed filers — without a $300/hr lawyer reading every line — bear the cost.
>
> Guardian was built by an immigrant who almost lost his STEM OPT to a six-word duty-description mismatch. It's the tool we wish we'd had.
>
> **Free today:** useguardian.ai/8843 — Form 8843 generator for students, no signup required.

(That's ~1,820 chars — leaves room to grow.)

### Specialties (LinkedIn allows up to 20; pick 8-12 for SEO)

```
Immigration compliance
Document cross-checking
USCIS forms
STEM OPT
H-1B
Form 8843
Tax compliance
Corporate compliance
Legal tech
AI document review
Form Filler
Pre-intake automation
```

### Hashtags (up to 3, choose strategically — these become your default "tagged with" hashtags)

```
#ImmigrationTech
#LegalAI
#STEMOPT
```

**Why these three:** `#ImmigrationTech` is the primary discovery tag (low-noise, high-relevance), `#LegalAI` rides a high-traffic category, `#STEMOPT` targets your wedge audience directly. Avoid `#AI` (too noisy), `#StartupLife` (irrelevant), `#Compliance` (wrong audience — finance/healthcare swamp this tag).

### Location

| Field | Value |
|---|---|
| **Address line 1** | (Your SF coworking address or registered agent) |
| **City** | San Francisco |
| **State** | California |
| **Country** | United States |
| **Postal code** | (your real one) |
| **Headquarters** | Yes (toggle on) |

If you don't have an SF address, use your registered C-corp address from incorporation docs. **Do not put your home address.**

### Custom Button (top of page, replaces default "Visit website")

| Option | When to use |
|---|---|
| **Visit website** ⭐ | Recommended for now — sends visitors to guardiancompliance.app to convert |
| Contact us | Use if you want sales-style intros via LinkedIn DM |
| Learn more | Generic, weak CTA |
| Sign up | Only if you have a sign-up flow that's friction-free |
| Register | Don't use — sounds enterprise/event |

**Recommend: "Visit website" → guardiancompliance.app**

---

## Step 3: First-Week Posts (paste into Company Page after setup)

### Post 1 — Page Launch (publish immediately after setup, day of)

> 👋 We're Guardian.
>
> The first AI tool that cross-checks your immigration, tax, and corporate documents *together* — catching the inconsistencies that get H-1Bs and STEM OPTs RFE'd.
>
> Built for the self-directed filers: founders sponsoring their own visa, international students juggling OPT and H-1B, and early employees at small companies whose employer doesn't retain a corporate immigration firm.
>
> Free Form 8843 generator for international students, live now. No signup. → guardiancompliance.app/8843
>
> Big launch coming May 12 on Product Hunt. Follow along.
>
> #ImmigrationTech #LegalAI #STEMOPT

### Post 2 — Founder Story (publish from PERSONAL account, not company page; T-7d before PH launch)

> Two years ago, six words on my I-983 almost cost me my STEM OPT.
>
> My training plan said "machine learning pipelines."
> My offer letter said "backend infrastructure."
> Same job. Different language. To USCIS — two different jobs.
>
> My lawyer caught it the night before filing. Most self-directed filers don't have a lawyer reading every line.
>
> So I built one.
>
> Guardian cross-checks your immigration, tax, and corporate documents in a single pass. STEM OPT, H-1B, O-1, EB-1 — anything that gets rejected for inconsistencies a human eye would tire of catching.
>
> We launch on Product Hunt May 12. Free Form 8843 generator is live now if you want to try the wedge: guardiancompliance.app/8843
>
> If you've ever filed your own immigration paperwork, what's the *one* check you wish existed? Reply or DM — I'm building this for you.

### Post 3 — PH Launch Day (May 12, from BOTH personal + company page; coordinate via Typefully or Buffer)

**Personal account:**
> Guardian is live on Product Hunt today 🛡️
>
> The first AI tool that cross-checks your immigration, tax, and corporate documents together — catching the inconsistencies that quietly trigger RFEs.
>
> If you find it useful, your feedback in the comments would mean everything: [PH link]
>
> Free Form 8843 generator + first cross-check free. Built for self-directed filers.

**Company page (post 30 min later — staggered avoids LinkedIn algorithm flagging both as spam):**
> We're live on @ProductHunt 🚀
>
> Guardian — pre-intake compliance for self-directed legal/tax navigators. Cross-checks your I-983, offer letter, tax returns, and more in 30 seconds.
>
> Try free today: [PH link]
>
> #ProductHunt #ImmigrationTech #LegalAI

---

## Step 4: Admin & Permissions

After page is live:

1. **Add page admins:** yourself (Super admin). Don't add anyone else yet.
2. **Verify the page** — LinkedIn now requires verification for company pages with >1 employee or >10 followers. You'll need to upload your incorporation document (Articles of Incorporation or LLC operating agreement). Takes 1-3 days.
3. **Connect the page to your personal profile:** in your personal profile → Experience → add Guardian Compliance as your current role → search and select your newly created page (this links them so your personal posts can tag the company).
4. **Invite connections to follow** the page — LinkedIn gives you a free quota of ~250 invites/month. Use this on Day 1: invite your 913 connections, prioritizing the 19 YC founders + Tier 1 outreach list.

---

## Step 5: Pre-Launch Calendar (LinkedIn-specific, anchored to PH launch May 12)

| Date | Action |
|---|---|
| May 1 | Create company page; add cover image, description, specialties |
| May 2 | Verify page (upload Articles of Incorporation) |
| May 2 | Connect personal profile → company page |
| May 3 | Post 1 (page launch) from company page |
| May 3-4 | Send invite-to-follow batch 1 (~250 to Tier 1 + Tier 2 contacts) |
| May 5 | Founder story (Post 2) from PERSONAL account |
| May 6 | Engage with replies on founder story; DM anyone who replies with a question |
| May 8 | Tier 1 DM blast — "launching May 12, would love your feedback" |
| May 11 | Schedule Post 3 (launch-day) in Typefully for May 12 12:30 AM PT (personal) + 1:00 AM PT (company) |
| **May 12** | PH launch + LinkedIn launch posts go live |
| May 13 | Recap post on personal account: "Guardian launched on PH yesterday — here's what I learned" |

---

## Open Items

- [ ] Confirm SF address for HQ (or use registered agent address)
- [ ] Verify guardiancompliance.app domain is purchased before publishing the page (LinkedIn will flag links to non-existent domains)
- [ ] Have Articles of Incorporation PDF ready for verification
- [ ] Decide whether to also create a Showcase Page for the Form 8843 wedge (recommend: skip for now — adds setup work, splits follower base)
