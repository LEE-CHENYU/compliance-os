# Guardian — Figma Spec Sheet for Slides 1, 2, 5, 6, 7, 8

**Format:** Each slide is a 1270×760 frame. Use Figma "Frame" → custom size.
**Brand palette (paste into Figma color styles):**

| Token | Hex | Usage |
|---|---|---|
| `--brand-blue` | `#5b8dee` | Primary CTA, accents, glow |
| `--brand-deep` | `#3d6bc5` | Headlines accent, badges |
| `--brand-text` | `#0d1424` | Primary text |
| `--brand-mute` | `#556480` | Body text |
| `--brand-soft` | `#7b8ba5` | Labels, captions |
| `--surface-1` | `#e8eff6` | Slide bg start |
| `--surface-2` | `#dce4f0` | Slide bg end |
| `--glass-light` | `rgba(255,255,255,0.6)` | Glass cards |
| `--glass-stroke` | `rgba(255,255,255,0.85)` | Glass card border |
| `--accent-emerald` | `#10b981` | "Ready" / passing states |
| `--accent-amber` | `#f59e0b` | Warnings |
| `--accent-red` | `#ef4444` | Conflicts |

**Background gradient (every slide):** `linear-gradient(135deg, #e8eff6 0%, #dce4f0 100%)` plus two radial glows of `rgba(91,141,238,0.15)`. Reuse the same background frame across all 8 slides.

**Type:**
- Display: SF Pro Display Semibold (Inter Semibold fallback). Headline 52px / line-height 1.05 / tracking -1%.
- Body: SF Pro Text / Inter. 18-20px / line-height 1.4.
- Labels: 11-13px / uppercase / tracking 0.14em.

**Glass card recipe (apply to every card):**
- Fill: `--glass-light`
- Stroke: 1px `--glass-stroke`
- Corner radius: 16-20px
- Effect: Background blur 20, drop shadow `0 8 30 rgba(13,20,36,0.06)`

---

## Slide 1 — Hero

**Purpose:** Stop the scroll. Lead with the wedge, hint at the potential.

**Layout (left-aligned, 60/40 split):**

| Region | Content |
|---|---|
| Left column (60%) | EYEBROW: `GUARDIAN COMPLIANCE` (uppercase, 14px tracking 0.2em, `--brand-deep`)<br/>**HEADLINE:** *Reconcile every filing.<br/>Match the right pro.* (52px, `--brand-text`, "Match the right pro." in `--brand-deep`)<br/>**SUB:** *Drop your filings. We surface conflicts across immigration, tax, and corporate — then match you with the lawyer or CPA who fits what we found. Personal data room for self-directed legal/tax navigators — built for the driver's seat, not the hand-off.* (20px, `--brand-mute`, max-width 580px)<br/>**Dual CTA pills (visual only):** `Drop your filings →` (white on `--brand-blue`, primary) + `Free Form 8843` (text-only `--brand-deep` underline, secondary). Spacing 16px between. |
| Right column (40%) | **Visual:** glassmorphic 3D card cluster suggesting a *data room*, not a single doc. Four stacked translucent cards rotated -10°/-3°/+3°/+10°, each labeled with a vertical: top "Immigration" (I-983 + green check), then "Tax" (1040 + yellow flag), then "Corporate" (board resolution), bottom "Healthcare" (greyed out at 40% opacity, signaling future). Faint connection lines between the docs in `--brand-blue` 40% opacity. Position behind a `--brand-blue` 30% radial glow. |
| Footer strip | Tiny logo + URL: `guardiancompliance.app` 14px `--brand-soft`, bottom-left padding 64px |

**Why this hero changed:** old version led with an agency-fear frame ("Check your immigration docs before USCIS does") that locked us into one vertical. New hero leads with the wedge (lawyer/CPA) and shows the potential (data room across verticals) in a single visual — the greyed-out "Healthcare" card on the right does the heavy lifting on the trajectory story.

**File:** Save as `slide-01-hero.fig` and export PNG at 1270×760.

---

## Slide 2 — Problem Framing

**Purpose:** Make the user feel the pain in one stat. **Stat verified against NAFSA / USCIS data — see sources at the bottom of this file.**

**Layout (centered, two-stat dramatic):**

| Region | Content |
|---|---|
| Top eyebrow | `THE PROBLEM` 14px tracking 0.2em `--brand-deep` |
| Center stat | **`6% → 10%`** at 180px font-weight 600, `--brand-text`. Render as two numbers separated by a thin arrow `→` in `--brand-deep`. |
| Stat caption | *STEM OPT RFEs nearly doubled in two years. The #1 cause: incomplete or inconsistent Form I-983 fields.* 22px `--brand-mute`, max-width 760px, centered |
| Bottom card | Glass card centered, 800×140, containing a screenshot of Guardian's "I-983 conflict" flag UI cropped tight. Add a `--brand-blue` glow ring around it. |
| Bottom right | *Source: NAFSA Fall 2024 USCIS Q&A; USCIS H-1B Characteristics Report FY 2024* 11px `--brand-soft`, italic. |

---

## Slide 5 — Free Form 8843 Wedge

**Purpose:** Convert at the bottom of the funnel. Free product, no signup.

**Layout (50/50, screenshot + copy):**

| Region | Content |
|---|---|
| Left (50%) | **Eyebrow:** `FREE FOR STUDENTS`<br/>**Headline:** *Form 8843 in 90 seconds.* (52px, "90 seconds" in `--brand-deep`)<br/>**Body:** *Every international student on F-1, J-1, M-1, or Q-1 must file Form 8843. Most don't, because the IRS instructions are 9 pages of jargon. Guardian asks four questions, fills the form, and exports a print-ready PDF.*<br/>**Bullet checklist** (each row: emerald checkmark + 16px text):<br/>✓ No signup required<br/>✓ Includes filing instructions for your school<br/>✓ Saves a copy to your data room (optional)<br/>**CTA pill:** `useguardian.ai/8843` |
| Right (50%) | Live screenshot of the Form 8843 generator — preferably the "preview" step showing a rendered PDF page with green checkmarks. Glass frame around it, `--brand-blue` glow underneath. |

---

## Slide 6 — Built For (Three Personas)

**Purpose:** Reader self-identifies. Drives engagement from each segment.

**Layout (3-column equal cards):**

| Region | Content |
|---|---|
| Top eyebrow | `BUILT FOR THE DRIVER'S SEAT` |
| Headline | *Three users. One pre-intake layer.* 44px |
| Card 1 — Founder | Icon: rocket / building. Tag: `O-1 / EB-1 / H-1B` `--brand-blue` pill. Title: **The Founder.** Body: *Sponsoring your own visa? Guardian cross-checks your incorporation docs, board resolutions, and immigration filings — so legal isn't a surprise three weeks before your closing.* |
| Card 2 — Student | Icon: graduation cap. Tag: `OPT → H-1B` pill. Title: **The Student.** Body: *From Form 8843 freshman year to the H-1B lottery, Guardian holds the thread. Every doc you've ever filed lives in one timeline.* |
| Card 3 — Early employee | Icon: briefcase. Tag: `Small-co employee` pill. Title: **The Solo Filer.** Body: *Your company sponsors your visa, but they don't have Fragomen. Guardian gives you the second pair of eyes a corporate immigration team would.* |

Each card: glass treatment, padding 28px, icon 36px in a `--brand-blue/10` rounded square, title 22px, body 14px.

---

## Slide 7 — Social Proof (OPTIONAL)

**Skip if you don't have a real quote by launch day.** Don't fake testimonials — PH community will smell it.

**Layout (centered quote, single panel):**

| Region | Content |
|---|---|
| Eyebrow | `EARLY USERS` |
| Quote | Big serif/italic 36px: *"Guardian caught a duty-description mismatch on my I-983 that my school's DSO missed. STEM OPT approved."* |
| Attribution | Avatar 56×56 + "**Name**, Title at Company" + small grayscale company logo strip |
| Trust strip | Logos of YC, Alma, JustiGuide if any are users — gray at 60% opacity, 32px height, 24px gap |

If no real quote, **drop this slide and re-number 8 → 7.**

---

## Slide 8 — CTA / Closing

**Purpose:** Tell viewer exactly what to do next.

**Layout (centered, dramatic):**

| Region | Content |
|---|---|
| Top | Logo mark 64px (just the icon, not wordmark) centered |
| Headline | *Don't wait for the RFE.* 56px `--brand-text` |
| Sub | *Run your first cross-check, free.* 24px `--brand-mute` |
| Primary CTA | Pill 18px white-on-`--brand-blue`, padding 16×40: `Try Guardian Free →` |
| Secondary CTA | Text link `--brand-deep` underline: *or get the free Form 8843* |
| Footer URL | `useguardian.ai` 16px `--brand-soft` 80px from bottom |
| Background detail | Add a soft animated-feeling radial glow centered behind the CTA — `--brand-blue` 30% opacity 600px radius. This is the "click me" beacon. |

---

## Stat Sources (verified 2026-04-30)

- **STEM OPT RFE rate 6% → 10%:** NAFSA unofficial polling, reported in [usaadmission.com — USCIS Is Issuing More STEM OPT RFEs—Here Are the Top 5 (2025)](https://usaadmission.com/uscis-is-issuing-more-stem-opt-rfes-here-are-the-top-5-2025/). Cross-confirmed by Fall 2024 USCIS Q&A with NAFSA advisors.
- **Top STEM OPT RFE causes (I-983, CIP code, multi-worksite, dates):** same NAFSA Q&A summary.
- **H-1B context (33,393 RFEs / 407,625 petitions = 8% in FY 2024):** [USCIS Characteristics of H-1B Specialty Occupation Workers, FY 2024 Congressional Report](https://www.uscis.gov/sites/default/files/document/reports/ola_signed_h1b_characteristics_congressional_report_FY24.pdf).
- **H-1B post-RFE approval rate 85.4% in FY 2025:** Boundless / immigration legal coverage; available in [CampLegal — Common Reasons USCIS Issues RFEs](https://camplegal.com/common-reasons-uscis-issues-requests-for-evidence-rfes/).

If a Battlefield/Inception application asks for a primary citation, lead with the USCIS Congressional report — it's the most authoritative.

---

## Export Checklist

For each slide:
1. Frame size: 1270×760
2. Export: PNG, 2x scale, no compression
3. File names: `slide-01-hero.png`, `slide-02-problem.png`, ... `slide-08-cta.png`
4. Total file size budget: ≤2MB per slide (PH limit). Compress with TinyPNG if needed.
5. Upload order on PH: 1, 2, 3 (HTML), 4 (HTML), 5, 6, 7 (or skip), 8

---

## Time Budget

| Slide | Estimated build time in Figma |
|---|---|
| 1 Hero | 45 min (3D doc cluster takes longest) |
| 2 Problem | 20 min |
| 3 Cross-domain | ⏩ already done in HTML |
| 4 Form Filler | ⏩ already done in HTML |
| 5 Wedge | 25 min (needs real screenshot) |
| 6 Built For | 30 min |
| 7 Social Proof | 15 min (or skip) |
| 8 CTA | 20 min |
| **Total** | **~2.5 hours** |
