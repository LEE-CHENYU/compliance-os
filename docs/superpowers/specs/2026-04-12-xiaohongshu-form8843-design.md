# Xiaohongshu Form 8843 GTM Cards — Design Spec

**Date:** 2026-04-12
**Author:** Cheney Li + Claude

---

## Overview

Standalone HTML image-cards at Xiaohongshu's native 1080×1440 (3:4) ratio, designed to be screenshot/exported as images for posting on 小红书. Two complete post sets plus a brand icon.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Visual style | Guardian Brand dark premium | Stands out against 小红书's typical pastel feed |
| Language | Chinese-dominant + English terms | Matches how 留学生 community actually communicates; keeps tax terms precise (Form 8843, IRS, etc.) |
| Icon | White-to-blue gradient cube with seams (Option C) | Derived from landing page 3D sliced cube; compact solid form with subtle seam lines; white top face, blue gradient sides |
| Dimensions | 1080×1440 (3:4 ratio) | Xiaohongshu native carousel format |
| Icon variants | All three kept (A: white/blue seams, B: blue/white seams, C: white-to-blue gradient) | C used for 小红书; A and B available for other contexts |

## Brand Icon

### White-to-Blue Gradient Cube (Primary — Option C)

One solid isometric cube form:
- **Top face:** White (`#f0f4fc`)
- **Left face:** Gradient from `#c4d4ea` → `#4A7AE8` → `#2A4DB0` (top to bottom)
- **Right face:** Gradient from `#dce6f3` → `#5B8DEE` → `#3461C7` (top to bottom)
- **Seam lines:** Two horizontal cuts across each side face, `rgba(255,255,255,0.2)`, stroke-width 1.5
- **Lockup:** Icon + "Guardian" (18px, weight 800) + "留学生合规助手" (10px, `#6b82a8`, letter-spacing 0.12em)

Sizes: 200px (card watermark lockup), 80px (profile picture), 52px (inline).

### Alternate Variants (Preserved)

- **Option A — White Cube, Blue Seams:** White faces matching landing page, blue seam lines. Best on dark backgrounds.
- **Option B — Blue Cube, White Seams:** Solid blue gradient faces, white seam lines. Works on any background without container.

## Post 1 — Problem → Solution (5 slides)

**Narrative:** Engagement-driven. Tension → release structure. Each swipe has a reason.
**Title for 小红书:** "留学生报税最容易忽略的一张表"

### Slide 0 (Cover)
- Top bar: "Guardian · 免费工具" pill badge + cube icon
- Headline: "留学生报税 / 最容易忽略的 / 一张表" (3 lines, 30px, weight 800)
- Subtitle: "Form 8843 — 零收入也必须提交"
- Bottom tags: "F-1 / J-1 签证" · "每年必交" · "不能电子提交"
- Background: `linear-gradient(160deg, #0f1728, #152040, #1a2a50)` with blue radial glow

### Slide 1 — What is Form 8843?
- Section label: "01 · 这是什么"
- Headline: "Form 8843 是什么？"
- Body: IRS requirement explanation for F-1/J-1/M-1/Q visa holders
- Highlight box: Days don't count toward tax residency test
- Key point: "即使你没有任何收入，Form 8843 也是必须单独提交的"

### Slide 2 — Why it matters
- Section label: "02 · 为什么重要"
- Headline: "不交会怎样？"
- Numbered list (3 items):
  1. IRS may treat you as tax resident → global income reporting
  2. Affects future green card/H-1B compliance record
  3. No clear statute of limitations — earlier is safer
- Highlight box: "大多数学校 ISSO 提过，但很少有人真的交了"

### Slide 3 — How Guardian helps
- Section label: "03 · 怎么提交"
- Headline: "Guardian 免费帮你一键生成"
- 3-step flow (numbered cards with arrows):
  1. Fill in visa, school, basic info
  2. Auto-generate complete PDF
  3. Print, sign, mail to IRS
- Highlight box: "完全免费 · 不需要注册 · 2分钟完成"

### Slide 4 — CTA
- Large cube icon + "Guardian" + "留学生合规助手"
- CTA box: "现在就生成你的 Form 8843"
- Details: "截止日期：6月15日 / 邮寄到 IRS Austin, TX"
- Button: "免费生成 →"
- Footer: "🔗 链接见评论区置顶" + URL

## Post 2 — Checklist Guide (4 slides)

**Narrative:** Saves-optimized reference cards. Utilitarian, bookmark-worthy.
**Title for 小红书:** "Form 8843 完全指南｜免费生成"

### Slide 0 (Cover)
- Top bar: "GUARDIAN · 指南" + cube icon
- Center: "Form 8843" (subtitle) → "完全指南" (headline, 32px) → blue accent line → "谁要交 · 怎么填 · 怎么寄 / 附免费生成工具"
- Stats row (3 cells): 免费 (生成费用) · 2min (填写时间) · 6/15 (截止日期)

### Slide 1 — Who must file
- Section label: "第一步 · 确认你需要交"
- Headline: "谁必须提交 Form 8843？"
- Checklist (all checked):
  - 持 F-1、J-1、M-1、Q 签证
  - 当年在美国待过至少 1 天
  - 即使零收入也必须提交
  - 每个税年单独提交一次
- Info card: "有收入随 1040-NR 一起寄。没收入就单独寄。"

### Slide 2 — Fill + mail process
- Section label: "第二步 · 填写和邮寄"
- Headline: "Guardian 帮你搞定前两步"
- Checklist (mixed state):
  - ✓ 填写信息 (dim: 姓名、签证、学校、在美天数)
  - ✓ 生成 PDF (dim: 自动填入官方模板，直接下载)
  - ○ 打印 + 签名 (dim: 你需要自己完成这步) — yellow/amber border
  - ○ 邮寄到 IRS (dim: Austin, TX · 地址显示在生成页) — yellow/amber border
- Info card: "Form 8843 不能电子提交，必须邮寄纸质版"

### Slide 3 — CTA
- Cube icon + "Guardian" + "留学生合规助手"
- CTA box: "收藏这篇 + 生成你的表"
- Details: "完全免费 · 不需要注册 / 截止日期 6月15日"
- Button: "免费生成 Form 8843 →"
- Footer: "🔗 链接见评论区置顶" + URL

## Shared Design Tokens

### Colors
| Token | Value | Usage |
|-------|-------|-------|
| Background primary | `#0f1728` | Slide backgrounds |
| Background gradient | `#152040` → `#1a2a50` | Cover slides |
| Brand blue | `#4A7AE8` | Accents, buttons, step numbers |
| Brand blue dark | `#2A4DB0` / `#3461C7` | Cube left face, button gradient end |
| Brand blue light | `#7BA3F0` / `#8cb4ff` | Section labels, highlight text |
| Text primary | `#ffffff` | Headlines, strong text |
| Text secondary | `#c9d5eb` | Body text, list items |
| Text tertiary | `#8ca2cc` | Subtitles, descriptions |
| Text muted | `#6b82a8` | Watermarks, dim labels |
| Pill bg | `rgba(74,122,232,0.15)` | Tag/pill backgrounds |
| Highlight box bg | `rgba(74,122,232,0.08)` | Info callouts |

### Typography
- Headlines: system-ui / PingFang SC / Microsoft YaHei, weight 800
- Body: weight 400, 13px, line-height 1.65
- Section labels: 11px, weight 700, `#4A7AE8`, letter-spacing 0.15em, uppercase

### Component Patterns
- **Pill badge:** `padding: 5px 12px`, `border-radius: 16px`, blue bg with border
- **Tag:** `padding: 5px 11px`, `border-radius: 14px`, white 6% bg
- **Highlight box:** `border-radius: 14px`, blue 8% bg, blue 15% border
- **Step card:** `border-radius: 12px`, white 3% bg, numbered blue square
- **Checkbox (checked):** Blue gradient fill, white checkmark
- **Checkbox (pending):** Yellow/amber border, transparent fill
- **CTA button:** `border-radius: 20px`, blue gradient, white text, blue shadow
- **Watermark:** Tiny cube SVG + "Guardian" text at bottom center

## Implementation Notes

- Each slide is a self-contained HTML file at 1080×1440px
- Output to `frontend/public/gtm/xiaohongshu/` for easy access
- Files named: `post1-cover.html`, `post1-slide1.html`, etc.
- Screenshot at 2x for retina-quality images
- No animation — pure static cards
- The cube icon SVG should be extracted as a reusable component

## File Structure

```
frontend/public/gtm/xiaohongshu/
├── post1-cover.html
├── post1-slide1.html
├── post1-slide2.html
├── post1-slide3.html
├── post1-cta.html
├── post2-cover.html
├── post2-slide1.html
├── post2-slide2.html
├── post2-cta.html
└── shared.css          # Shared design tokens and component styles
```
