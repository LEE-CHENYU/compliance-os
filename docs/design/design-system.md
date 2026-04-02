# Guardian Design System

## Brand Identity

**Name:** Guardian
**Tagline:** Your compliance memory
**Positioning:** We check the things your DSO might not tell you and your employer might not know about.

**Tone:** Calm, procedural, evidence-based. Never alarmist. The product reduces cognitive burden — it surfaces what matters and explains why, without overwhelming.

**Core message:** "Check your documents before USCIS does."

## Content Rules

1. **No jargon in user-facing text.** The whole purpose of this product is to alleviate the burden of remembering form numbers and legal terms. When we need to confirm information, ask in plain English. "As a foreign-owned LLC, you're required to file Form 5472 every year — have you ever filed this form?" is better than "Your answers show 'Required' but your tax return shows 'False' for form 5472."

2. **No emojis.** Use letter labels (A, B), numbers (1, 2, 3), or nothing. The product should feel trustworthy and professional.

3. **No raw field values in questions.** Follow-up questions must translate extracted data into human-readable context. If a comparison finds a mismatch, explain what it means in one sentence before asking the user to confirm.

4. **Form names are acceptable in document labels** (upload slots, document pills) because users who have the form will recognize it. But always pair with a plain description: "Form I-983 — Training Plan signed by you, your employer, and your DSO."

5. **If the user might not have a form, say so.** "Don't have these? Upload whatever document you have — we'll work with it."

6. **Explain consequences in 2-4 words.** Not paragraphs. Severity tags are pills, not banners.

7. **One question at a time in follow-ups.** Each question stands alone with context for why it matters.

## Color Palette

### Primary
| Token | Hex | Usage |
|---|---|---|
| `blue-500` | `#5b8dee` | Primary accent, CTAs, active states, links |
| `blue-600` | `#4a74d4` | Gradient end, hover states |
| `navy` | `#0d1424` | Headlines, primary text |
| `navy-light` | `#1a2036` | Nav CTA background, dark buttons |

### Text
| Token | Hex | Usage |
|---|---|---|
| `text-primary` | `#0d1424` | Headlines, titles, emphasis |
| `text-body` | `#556480` | Body text, descriptions |
| `text-muted` | `#7b8ba5` | Labels, captions, nav links |
| `text-faint` | `#8e9ab5` | Timestamps, proof labels, footer |
| `text-disabled` | `#b0bdd0` | Placeholder text, empty states |

### Surfaces
| Token | Value | Usage |
|---|---|---|
| `bg-page` | `linear-gradient(180deg, #d5dded, #dde5f0, #e8eff6, #f0f4f9)` | Page background |
| `bg-glass` | `rgba(255,255,255,0.45)` + `backdrop-blur-xl` | Glass panels (sections, cards) |
| `bg-glass-hover` | `rgba(255,255,255,0.65)` | Glass panel hover state |
| `bg-glass-subtle` | `rgba(255,255,255,0.30)` | Table headers, sub-panels |
| `border-glass` | `rgba(255,255,255,0.60)` | Glass panel borders |
| `border-blue` | `rgba(91,141,238,0.08)` | Subtle accent borders |

### Semantic
| Token | Hex | Usage |
|---|---|---|
| `warning-bg` | `rgba(251,191,36,0.06)` | Warning finding backgrounds |
| `warning-text` | `#a16207` | Warning consequence labels |
| `critical-bg` | `rgba(239,68,68,0.06)` | Critical finding backgrounds |
| `critical-text` | `#c0392b` | Critical section headers |
| `success-bg` | `rgba(16,185,129,0.06)` | Match/good backgrounds |
| `success-text` | `#059669` | Success labels |
| `info-text` | `#3d6bc5` | Form names, advisory titles |

## Typography

**Font:** Inter (400, 500, 600, 700, 800)

| Element | Size | Weight | Tracking | Color |
|---|---|---|---|---|
| Page headline (h1) | 50px | 800 | -0.04em | `navy` |
| Section headline (h2) | 36px | 800 | -0.03em | `navy` |
| Card title (h3) | 20px | 700 | -0.02em | `navy` |
| Section label | 12px | 600 | 0.06em uppercase | `text-muted` |
| Body text | 15-17px | 400 | normal | `text-body` |
| Small text | 13px | 400-500 | normal | `text-body` |
| Caption/label | 12px | 500 | normal | `text-faint` |
| Tag/badge | 12.5px | 500-600 | normal | `info-text` |

## Component Patterns

### Glass Panel (primary container)
Used for: section wrappers, form cloud, track cards container, result sections

```
bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60
shadow-[0_4px_24px_rgba(91,141,238,0.06)]
```

Padding: `px-6 py-5` (cards) or `px-16 py-20` (full sections)

### Glass Card (interactive)
Used for: track selector cards, follow-up question cards, finding cards

```
bg-white/50 backdrop-blur-xl rounded-2xl border border-white/60
shadow-[0_4px_24px_rgba(91,141,238,0.06)]
hover:shadow-[0_8px_32px_rgba(91,141,238,0.1)]
hover:-translate-y-0.5 transition-all
```

### Primary Button
```
px-8 py-4 rounded-xl
bg-gradient-to-br from-[#5b8dee] to-[#4a74d4]
text-white font-semibold text-[15px]
shadow-[0_4px_16px_rgba(74,116,212,0.3)]
hover:shadow-[0_8px_28px_rgba(74,116,212,0.4)]
hover:-translate-y-0.5 transition-all
```

### Secondary Button
```
px-8 py-4 rounded-xl
bg-white/70 backdrop-blur border border-blue-100/20
text-[#3a5a8c] font-medium text-[15px]
hover:bg-white/85 hover:border-blue-200/40
```

### Chip (unselected)
```
px-5 py-2.5 rounded-xl text-sm font-medium
bg-white/70 backdrop-blur border border-blue-100/30
text-[#3a5a8c]
hover:bg-white/90 hover:border-blue-200/40 hover:shadow-sm
```

### Chip (selected)
```
px-5 py-2.5 rounded-xl text-sm font-medium
bg-gradient-to-br from-[#5b8dee] to-[#4a74d4]
text-white shadow-[0_2px_12px_rgba(74,116,212,0.3)]
```

### Tag (form cloud)
```
px-4 py-2 rounded-lg text-[12.5px] font-medium
bg-white/65 backdrop-blur border border-blue-200/10
text-[#3d6bc5]
hover:bg-white/85 hover:-translate-y-0.5 transition-all
```

### Badge (status pill)
```
text-xs px-3 py-1 rounded-lg font-medium
border border-{color}-100/50 bg-{color}-50/80
```

### Timeline Dot
- Past events: `bg-gradient-to-br from-emerald-400 to-emerald-500 border-[3px] border-white shadow-sm`
- Current (today): `bg-gradient-to-br from-[#5b8dee] to-[#4a74d4] border-[3px] border-white shadow-sm`
- Future events: `bg-gray-200 border-[3px] border-white`
- Timeline line: `border-l-2 border-[#5b8dee]/20`

### Nav Bar
```
fixed top-0 left-0 right-0 z-50
px-10 py-3.5
bg-[#e0e8f3]/60 backdrop-blur-2xl
border-b border-blue-200/20
```

### Loading Spinner
Wrap in a glass panel:
```
bg-white/50 backdrop-blur-xl rounded-3xl border border-white/60
shadow-[0_8px_40px_rgba(91,141,238,0.08)]
```
Spinner inside a gradient icon container:
```
w-14 h-14 rounded-2xl bg-gradient-to-br from-[#5b8dee]/10 to-[#4a74d4]/5
```

## Layout Rules

1. **Max width:** 1360px for hero grid, 1200px for section panels, 680px for steps/forms
2. **Page padding:** `px-12` on landing, `px-6` on inner pages
3. **Section spacing:** `mb-10` between glass panels, `mb-6` between content blocks
4. **Grid:** Hero uses `grid-cols-[1fr_1.3fr]`, track cards use `grid-cols-2`
5. **Background texture:** Dot grid overlay `radial-gradient(rgba(91,141,238,0.05) 1px, transparent 1px)` at 32px spacing

## Design Principles

1. **Glass over opaque** — Every panel, card, and container uses frosted glass (`backdrop-blur-xl` + semi-transparent white). Nothing is pure opaque white.
2. **Depth through shadows** — Use blue-tinted shadows (`rgba(91,141,238, ...)`) not gray. Shadows increase on hover.
3. **Single color family** — Everything derives from the blue palette. No rainbow colors for categories. Differentiate through weight (bold/italic) not color.
4. **Calm severity** — Findings use subtle amber/red tints, never harsh solid backgrounds. Labels are small, pill-shaped, understated.
5. **Progressive disclosure** — Each screen earns the next. Don't show complexity upfront.
6. **Consistent motion** — `transition-all` on interactive elements. Hover lifts by `0.5-1px`. No bounce, no spring.

## Page-Specific Notes

### Landing Page
- 3D sliced cube: mechanical discrete animation, pure white faces, blue-tinted shadows
- Hero: split layout (text left, cube right), nothing behind headline
- Logo: "Guardian" at 18px/800 weight with 3-bar stacked icon

### Stage Select
- Centered, max-w-lg
- Options as selectable glass cards with blue border when active
- Number input for years

### Upload
- Centered, max-w-lg
- Dashed border drop zones, green state on upload complete
- Privacy note in green-tinted glass

### Review (Extraction → Follow-up → Snapshot)
- Single page, max-w-3xl
- Extraction grid: glass table with translucent header row
- Follow-ups: glass cards, no left accent borders, chip answers
- Snapshot: glass timeline panel, glass finding cards, glass advisory list
- CTA: gradient blue "Save as my case"
