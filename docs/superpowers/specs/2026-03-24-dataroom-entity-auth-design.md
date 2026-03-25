# Guardian: Data Room, Track B, and Auth — Design Spec

## Overview

Three interconnected features that complete the Guardian MVP:

1. **Track B (Entity Check)** — The entrepreneur compliance check flow, mirroring Track A's pipeline with entity-specific questions, tax return extraction, and entity rules.
2. **Personal Data Room** — A timeline-centered workspace where users store documents, see risks, and get prompted to upload what's missing.
3. **Auth** — Email/password account creation at the "Save as my case" moment. Google OAuth deferred to post-MVP.

**Spec dependency:** Builds on `2026-03-24-document-cross-checker-design.md`. All Track A infrastructure (rule engine, comparator, extractor, API routes) is reused.

---

## Track B: Entity Check

### Flow

Track B follows the same 5-screen pattern as Track A:

1. **B1 — Entity info** (questions, no document upload)
2. **B2 — Upload** (one document: tax return)
3. **B3 — Extraction + comparison** (tax return fields vs answers)
4. **B4 — Follow-up** (only for detected issues)
5. **B5 — Snapshot** (entity health view + advisories)

### B1 — Entity Info Questions

Six questions collected as `answers` on the check:

```yaml
b1_answers:
  entity_type:                  # Q1
    type: enum
    values: ["smllc", "multi_llc", "c_corp", "s_corp", "not_sure"]
    labels: ["Single-member LLC", "Multi-member LLC", "C-Corporation", "S-Corporation", "Not sure"]

  owner_residency:              # Q2
    type: enum
    values: ["us_citizen_or_pr", "on_visa", "outside_us"]
    labels: ["Yes", "No — on a visa", "No — outside US"]

  state_of_formation:           # Q3
    type: string
    description: "State abbreviation or name"

  separate_bank_account:        # Q4
    type: enum
    values: ["yes", "no", "not_sure"]

  foreign_capital_transfer:     # Q5
    type: enum
    values: ["yes", "no"]

  visa_type:                    # Q6 (shown only if owner_residency == "on_visa")
    type: enum
    values: ["f1_opt_stem", "h1b", "l1", "o1", "other"]
    labels: ["F-1 (OPT/STEM)", "H-1B", "L-1", "O-1", "Other"]
```

### B2 — Upload

One labeled drop zone:
- **Most recent tax return** — 1120, 1065, 5472 + pro forma 1120, or 1040 with Schedule C
- Same upload component as Track A, single slot instead of dual

### B3 — Extraction + Comparison

Tax return extraction uses the `tax_return` schema (already defined in the cross-checker spec):

```yaml
tax_return:
  form_type: string             # 1040, 1040-NR, 1120, 1120-S, 1065
  tax_year: number
  entity_name: string | null
  ein: string | null
  filing_status: string | null
  total_income: number
  schedules_present: string[]
  form_5472_present: boolean
  form_3520_present: boolean
  form_8938_present: boolean
  state_returns_filed: string[]
```

**Comparison logic for Track B:** Unlike Track A (which compares two documents), Track B compares the **extracted tax return fields** against the **user's answers from B1**. The comparison grid shows:

| Field | Your Answers | Tax Return | Status |
|---|---|---|---|
| Entity type | Single-member LLC | Filed 1120-S | Mismatch |
| Owner status | NRA (on visa) | — | — |
| Form 5472 | Required (foreign SMLLC) | Not detected | Missing |
| State | Delaware | Delaware | Match |

The compare endpoint checks:
- `entity_type` answer vs `form_type` extraction (SMLLC should not file 1120-S)
- `form_5472_present` when foreign-owned SMLLC
- `form_type` = 1040 when NRA (should be 1040-NR)
- `schedules_present` contains schedule_c when on OPT/STEM

### B4-B5 — Follow-up + Snapshot

Same UX as Track A. Follow-up questions generated from mismatches. Snapshot shows entity health: findings ranked by severity + advisory one-liners.

### Entity Rules

All rules from the original spec go into `config/rules/entity.yaml`:

**Logic rules:**
- `nra_scorp_invalid` — NRA + 1120-S filing = void S-Corp election (critical)
- `missing_5472` — Foreign SMLLC + no 5472 detected = $25K/year penalty (warning)
- `schedule_c_on_opt` — Schedule C + F-1 visa = unauthorized work risk (warning)
- `foreign_capital_undocumented` — Foreign capital transfer without documentation (warning)
- `corporate_veil_risk` — No separate bank account (warning)
- `wrong_form_type` — NRA + filed 1040 instead of 1040-NR (warning)

**Advisory rules:**
- `advisory_state_annual_report` — Always show for entities
- `advisory_registered_agent` — Always show
- `advisory_entity_fbar` — If owner is in the US
- `advisory_dividend_withholding` — C-Corp + NRA owner
- `advisory_form_3520` — If foreign capital transfer = yes
- `advisory_boi_foreign` — If owner is outside US

### Frontend Routes

```
/check/entity               Entity info questions (B1)
/check/entity/upload        Tax return upload (B2)
/check/entity/review        Extraction + follow-up + snapshot (B3-B5)
```

---

## Auth

### Account Creation Flow

1. User completes the triage flow (Track A or Track B)
2. Sees the case snapshot with findings
3. Clicks "Save as my case"
4. **Glass modal appears:** "Create your account to save this case"
   - Email input
   - Password input
   - "Create account" button
5. On success: JWT token stored in localStorage, redirect to `/dashboard` (data room)
6. The check session is linked to the new user via `user_id`

### Login Flow

- Landing page nav gets a "Sign in" link (shown when not logged in)
- Sign in page: email + password → JWT → redirect to `/dashboard`
- If user navigates to `/dashboard` without auth, redirect to sign in

### Data Model

```sql
users (
  id            UUID PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMP,
  updated_at    TIMESTAMP
)
```

The existing `checks` table gets a new nullable column:

```sql
ALTER TABLE checks ADD COLUMN user_id TEXT REFERENCES users(id);
```

Checks created before account creation have `user_id = NULL`. When the user creates an account from a snapshot, the current check's `user_id` is set to the new user.

### API Endpoints

```
POST   /api/auth/register          Create account (email, password) → JWT
POST   /api/auth/login             Login (email, password) → JWT
GET    /api/auth/me                Get current user (from JWT)
```

### JWT Implementation

- Token contains: `{ user_id, email, exp }`
- Expiry: 30 days
- Stored in localStorage on the client
- Sent as `Authorization: Bearer <token>` header
- Backend validates via a `get_current_user` dependency

### Security Notes (MVP)

- Passwords hashed with bcrypt
- No email verification for MVP
- No password reset for MVP
- Google OAuth deferred to post-MVP (will replace email/password as primary auth)
- JWT secret stored in `.env`

---

## Personal Data Room

### Purpose

The data room is the permanent home for returning users. It replaces the one-shot snapshot with a living workspace that grows with each upload, re-evaluates risks continuously, and prompts users to maintain their compliance record.

### Layout

**Three-column layout:**

1. **Sidebar** (260px fixed)
   - Views: Timeline (default) / All Documents
   - Categories: Immigration / Tax / Entity (with document counts, click to filter)
   - Risks: Needs Attention (count) / Advisories (count)
   - Checks: past checks listed with status + "+ Run new check" button

2. **Stats bar** (top of main area)
   - Four glass cards: Documents count, Risks count, Verified fields, Days until next deadline

3. **Timeline** (main content, max-width 900px)
   - Vertical timeline with events ordered by date
   - Past events: green dots
   - Today: blue glowing dot
   - Future/upcoming: gray dots
   - Overdue: amber dots

### Timeline Events

Each event on the timeline has:

```
Event:
  date: date
  title: string
  type: "milestone" | "filing" | "deadline" | "check"
  category: "immigration" | "tax" | "entity"
  documents: Document[]       # attached files
  risks: Finding[]            # inline risk cards
  prompts: UploadPrompt[]     # contextual upload suggestions
```

**Event sources:**
- **Extracted dates** from uploaded documents (I-983 start/end, tax year, etc.)
- **Computed deadlines** from the rule engine (12-month eval anniversary, grace period end)
- **User-set dates** (future: manual deadline entry)
- **Today marker** (always present)

### Documents on the Timeline

Documents are displayed as small glass pill cards attached to their relevant event:

```
📄 I-983 (signed)  [Immigration]
📄 Employment Letter  [Immigration]
```

Each document shows:
- Filename
- Category tag (Immigration / Tax / Entity) — Apple-style vibrancy pill
- Click to view/download

### Contextual Upload Prompts

Appear inline on the timeline at relevant events. Each prompt has:

```
UploadPrompt:
  target_event: string        # which timeline event this attaches to
  document_type: string       # what to upload
  prompt_text: string         # "Upload your completed 12-month evaluation"
  why_text: string            # "Must be signed by employer within 10 days..."
  resolved: boolean           # hidden once uploaded
```

Prompts are generated by the rule engine based on:
- Missing documents for the user's stage (e.g., on STEM OPT but no EAD uploaded)
- Approaching deadlines (e.g., 12-month eval anniversary)
- Resolved findings that could be verified with additional documents

### Auto-Check on Upload

When a user uploads a new document from the data room:

1. **Extract** — LLM extraction runs immediately on the new document
2. **Re-evaluate** — Rule engine runs against ALL documents and answers for this user
3. **Diff** — Compare new findings against previous findings
4. **Notify** — Toast notification: "2 new items found" or "1 issue resolved"
5. **Update timeline** — New document appears at relevant date, new/resolved risks update

The user never manually triggers re-evaluation.

### Sidebar Behavior

**Category filter:** Clicking "Immigration" filters the timeline to show only immigration-related events and documents. Clicking again shows all.

**Risk filter:** Clicking "Needs Attention" scrolls to and highlights the first unresolved risk on the timeline.

**"+ Run new check":** Opens the triage flow (Track A or Track B selector). On completion, results merge into the existing data room rather than creating a separate case.

### Data Model Changes

```sql
-- Timeline events table
timeline_events (
  id            UUID PRIMARY KEY,
  user_id       UUID REFERENCES users(id) NOT NULL,
  date          DATE NOT NULL,
  title         TEXT NOT NULL,
  event_type    TEXT,          -- milestone | filing | deadline | check
  category      TEXT,          -- immigration | tax | entity
  source        TEXT,          -- extracted | computed | manual
  source_field  TEXT,          -- which extracted field generated this event
  created_at    TIMESTAMP
)

-- Link documents to timeline events (many-to-many)
document_events (
  document_id   UUID REFERENCES documents_v2(id),
  event_id      UUID REFERENCES timeline_events(id),
  PRIMARY KEY (document_id, event_id)
)

-- Upload prompts
upload_prompts (
  id            UUID PRIMARY KEY,
  user_id       UUID REFERENCES users(id) NOT NULL,
  event_id      UUID REFERENCES timeline_events(id),
  document_type TEXT NOT NULL,
  prompt_text   TEXT NOT NULL,
  why_text      TEXT,
  resolved      BOOLEAN DEFAULT FALSE,
  resolved_at   TIMESTAMP,
  created_at    TIMESTAMP
)
```

The existing `documents_v2` table gets a `user_id` column:

```sql
ALTER TABLE documents_v2 ADD COLUMN user_id TEXT REFERENCES users(id);
```

### Frontend Routes

```
/dashboard                  Data room (requires auth)
/login                      Sign in page
/register                   Sign up page (also triggered by modal)
```

### API Endpoints

```
GET    /api/dashboard/timeline      Get timeline events with documents, risks, prompts
GET    /api/dashboard/stats         Get stats (doc count, risk count, etc.)
POST   /api/dashboard/upload        Upload document to data room (auto-extract + re-evaluate)
GET    /api/dashboard/documents     List all documents for user
DELETE /api/dashboard/documents/{id} Delete a document
```

---

## Design System Alignment

All data room components follow the Guardian design system:

- **Glass panels:** `bg-white/45 backdrop-blur-xl rounded-2xl border border-white/60 shadow-[0_4px_24px_rgba(91,141,238,0.06)]`
- **Category tags:** Apple-style vibrancy pills — `rounded-full backdrop-blur-sm` with `rgba(color, 0.1)` backgrounds
  - Immigration: `rgba(91,141,238,0.1)` / `#3d6bc5`
  - Tax: `rgba(16,185,129,0.1)` / `#059669`
  - Entity: `rgba(124,58,237,0.1)` / `#7c3aed`
- **Risk tags:** Same as snapshot — amber for warnings, red for critical
- **Upload prompts:** Dashed border, blue-tinted background, icon + text + why
- **Timeline dots:** Gradient fills with white border, blue glow on today
- **Stats cards:** Glass panels with large numbers
- **Sidebar:** Semi-transparent background, dot indicators, count badges

---

## Implementation Order

1. **Track B** — Entity questions page, entity upload page, entity review page, `entity.yaml` rules. Reuses all Track A backend infrastructure.
2. **Auth** — User model, register/login endpoints, JWT middleware, auth modal on "Save as my case", protected routes.
3. **Data Room** — Timeline events model, dashboard API, timeline page, sidebar, stats, document management, auto-check-on-upload.

Each can be built and shipped independently. Track B is the smallest increment. Auth is a prerequisite for the data room.

---

## Out of Scope

- Google OAuth (post-MVP)
- Email verification
- Password reset
- Document OCR (beyond PyMuPDF text extraction)
- Sharing/export of case data
- Mobile layout
- Multi-user collaboration on a case
- Manual deadline entry by user
