# Service Marketplace: Form 8843 + Execution/Advisory Modes

**Date:** 2026-04-09
**Status:** Draft
**Related:** `docs/GTM_STRATEGY.md` (sections 5, 15, 16, 17)

## Overview

Transform Guardian from a document-checking tool into a tiered service marketplace with:

1. **Free Form 8843 generator** as the wedge (lead magnet for international students)
2. **Tier 0 and Tier 0.5 paid products** — pure-software services plus low-friction clerical fulfillment ($19-99) with no attorney required
3. **Execution Mode** — limited-scope attorney services ($199-399) for self-directed users
4. **Advisory Mode** — full-consultation attorney services ($499-799) for uncertain users
5. **Qualifying questionnaire** that routes users between Execution and Advisory Mode
6. **Attorney review workflow** with limited-scope representation agreements

This spec covers **Phase 1 (Tier 0 plus the first Tier 0.5 mail-fulfillment upsell) and Phase 2 (first Execution Mode product)** per the 90-day execution plan. Tier 2 (Boundless) and Tier 3 (Panel) are deferred.

## Goals

- **Phase 1:** Ship Form 8843 generator + 4 paid Tier 0 products + optional $19 Form 8843 mailing upsell in 6 weeks
- **Phase 2:** Ship OPT Application Execution Mode ($199) by end of Month 3
- **Legal safety:** All attorney interactions governed by written limited-scope agreements (ABA Rule 1.2(c))
- **User self-selection:** Qualifying questionnaire routes users to the right product tier
- **Conversion funnel:** Free 8843 → paid Tier 0 → attorney-backed Tier 1 (multi-year LTV)

## Non-Goals

- Full H-1B petition support (deferred to Phase 4)
- Attorney panel with user choice (Tier 3 — deferred)
- In-app messaging with attorney (use email for now)
- Mandarin localization (Phase 1 is English; Mandarin landing page only for Form 8843)
- Payment processing beyond simple Stripe Checkout
- CPA integration (deferred)

## User Personas

### Persona 1: "Jessica" — International Student
- Chinese, F-1 visa, Year 2 at Columbia
- Zero income, needs Form 8843
- Finds Guardian via 小红书 or university WeChat group
- Converts: free 8843 → $29 tax filing next year → $199 OPT application in year 3

### Persona 2: "Raj" — H-1B Employee at Small Startup
- Indian, H-1B, 2 years in US
- Small employer has no immigration counsel
- Found Guardian via Reddit r/h1b
- Converts: $49 H-1B doc check → $299 H-1B extension execution → $199 FBAR filing

### Persona 3: "Wei" — Immigrant Founder
- Chinese, O-1 visa, building AI startup in SF
- Previous O-1 attorney wants $15K for renewal
- Found Guardian via Unshackled Ventures newsletter
- Converts: $99 cross-domain inconsistency check → (future) $3,500 O-1 panel selection

---

## Feature 1: Form 8843 Generator (Free)

### User Flow

```
1. Landing page (Mandarin + English)
   ↓
2. Email signup (single field)
   ↓
3. 6-question onboarding (one at a time, animated)
   - Visa type (F-1, J-1, M-1, Q-1)
   - School (autocomplete)
   - Arrival date in US
   - Days present in US for each of the last 3 years
   - Country of citizenship
   - Dependents (if J-2 or F-2)
   ↓
4. Generate Form 8843 PDF (filled)
   ↓
5. Deliver: inline preview + email + download + filing instructions
   ↓
6. User sees mailing checklist + can mark "I mailed it"
   ↓
7. "What's Next" reveal with upsell cards
   ↓
8. Account created → added to email + reminder sequence
```

### Technical Details

**Form 8843** is a simple, non-calculating form. Field mapping:

| Form 8843 Field | User Input |
|----------------|-----------|
| Line 1a: First/Last Name | From onboarding |
| Line 1b: US Taxpayer ID (SSN/ITIN) | Optional — "I don't have one" |
| Line 2: Country of citizenship | From onboarding |
| Line 3a: Country of passport | Usually same as citizenship |
| Line 3b: Passport number | Optional |
| Line 4a: Visa type | From onboarding |
| Line 4b: Current nonimmigrant status | Inferred from visa type |
| Line 5: School name + address | From onboarding (autocomplete) |
| Line 6: Director of academic program | Can be "On file" if unknown |
| Line 7: Days present in US (3 years) | From onboarding |
| Line 8a-c: Previously filed 8843? | From onboarding |

**PDF generation:** Use PyMuPDF against the official Form 8843 template from IRS.gov. Do not assume the IRS PDF has usable AcroForm widgets; if the source is XFA or otherwise not directly fillable, use a deterministic overlay approach and preserve a machine-readable text layer for searchability and QA. Reuse `form_filler.py` patterns where helpful.

**No LLM needed** — this is deterministic form filling.

### Filing Reality (Must Be Part of the UX)

Guardian must not imply that generating the PDF means the user has finished filing.

- **If the user is filing Form 8843 by itself** because they had no U.S. income, they must print, sign, and mail it to the IRS. Default deadline: **June 15**.
- **If the user is filing Form 8843 with Form 1040-NR**, it is filed as part of the tax return package. Default deadline: **April 15**, subject to the actual return workflow.
- **Each family member files separately**. Do not imply one envelope covers multiple Form 8843 filers.
- Guardian should frame these as filing instructions, not legal or tax advice about the user's full return posture.

**Mailing address for Form 8843-only filings:**

```
Department of the Treasury
Internal Revenue Service Center
Austin, TX 73301-0215
```

### Email Capture + Drip

- Store user in `users` table with `source: "form_8843"`
- Trigger welcome email immediately with PDF attached
- Include filing instructions in the welcome email, including the mailing address and the default deadline
- Add reminder sequence:
  - 30-day reminder before the June 15 Form 8843-only deadline
  - "Did you mail it?" reminders at 2 weeks and 4 weeks unless user marks the order as mailed
- Trigger annual reminder email every January (cron job)

### Delivery + Mailing Checklist

The delivery screen is not just a download confirmation. It must explain the next offline step clearly:

```
✓ Your Form 8843 is ready [Download PDF] [Email]

─────────────────────────────────────

⚠ IMPORTANT: You still need to file this form.
Form 8843 by itself cannot be e-filed.

1. Print the PDF
2. Sign and date the form
3. Put it in an envelope
4. Mail it to:

Department of the Treasury
Internal Revenue Service Center
Austin, TX 73301-0215

5. Use USPS Certified Mail if possible
   so you have proof of filing

[Copy mailing address]
[Download mailing label]
[Mark as mailed]
```

The order should retain mailing state so Guardian can remind the user until they confirm completion.

### "What's Next" Reveal

After PDF delivery, show personalized upsell cards based on user inputs:

```
✓ Your Form 8843 is ready [Download] [Email]

─────────────────────────────────────

⚠️ Wait — there's more you should know

Based on what you told us, you might also need:

┌────────────────────────────────────┐
│ 📄 Form 1040-NR                    │
│    If you earned any income, you   │
│    need to file this too.          │
│    → We can file it for $29        │
│    [Check my return]               │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ 💰 Tax Treaty Benefits             │
│    China-US Art. 20 exempts $5,000 │
│    of scholarship income.          │
│    [Learn more - free]             │
└────────────────────────────────────┘

[Just the 8843, thanks →]  (prominent exit)
```

### Optional Tier 0.5 Upsell: White-Glove Mailing Service ($19)

Guardian can offer a clerical fulfillment upsell immediately after Form 8843 generation:

- **Free tier:** download + email + mailing instructions; user prints, signs, and mails the form themselves
- **Paid upsell ($19):** Guardian prints and mails the completed packet via certified mail and sends tracking/proof-of-mailing back to the user

This is useful for students without a printer, students unfamiliar with the U.S. postal system, and users who want proof-of-mailing without additional logistics.

**Important operational constraint:** this upsell is only launchable after Guardian validates the signature workflow. If the IRS requires an original wet signature for the mailed packet, Guardian cannot simply print and mail from its own office without a compliant chain-of-custody design. The spec should treat this as a gated launch item, not an assumed capability on day 1.

---

## Feature 2: Tier 0 and Tier 0.5 Paid Products (No Attorney)

### Products

| SKU | Name | Price | What It Does |
|-----|------|-------|-------------|
| `form_8843_mailing_service` | Form 8843 Mailing Service | $19 | Print + certified-mail fulfillment for a completed Form 8843 packet, with tracking proof sent back to the user |
| `student_tax_1040nr` | Student Tax Filing (1040-NR + 8843) | $29 | Generate both forms, flag treaty benefits, deliver as PDF package |
| `h1b_doc_check` | H-1B Document Check | $49 | Upload docs, AI checks for errors, inconsistencies, missing fields |
| `fbar_check` | FBAR Compliance Check | $49 | Intake of foreign accounts, flag filing obligation, generate FinCEN 114 |
| `election_83b` | 83(b) Election Filing | $99 | Form generation, timing alert, certified mail instructions |

`form_8843_mailing_service` is a post-generation upsell, not a standalone acquisition page. It should launch behind an operational readiness check for signature handling, label generation, certified-mail workflow, and proof capture.

### Common Purchase Flow

```
1. User clicks "Buy" on product page
   ↓
2. Stripe Checkout (no account required at this step)
   ↓
3. On success: redirect to /account/orders/{order_id}
   ↓
4. If user doesn't have account: create one (email from Stripe)
   ↓
5. Product-specific intake flow
   ↓
6. AI processing
   ↓
7. Deliver results (inline + email + filing instructions)
   ↓
8. If mail-only product: track mailing state or hand off to fulfillment ops
   ↓
9. Add to data room (if user accepts)
```

### Technical Details

Each Tier 0 product is a self-contained FastAPI route:
- `POST /api/marketplace/checkout/{sku}` — initiates Stripe Checkout session
- `POST /api/marketplace/order/{order_id}/intake` — saves user inputs
- `POST /api/marketplace/order/{order_id}/process` — runs the AI/rules
- `GET /api/marketplace/order/{order_id}/result` — fetches the deliverable

All products reuse existing services:
- `form_filler.py` for PDF generation
- `extractor.py` for OCR + extraction
- `rule_engine.py` for flagging issues
- `llm_runtime.py` with model routing

---

## Feature 3: Execution Mode — OPT Application ($199)

### User Flow

```
1. User clicks "OPT Application Service"
   ↓
2. Shown: Execution Mode ($199) vs. Advisory Mode ($499)
   ↓
3. Qualifying Questionnaire (8 checkboxes)
   ↓
4. Auto-recommend based on answers
   ↓
5. User chooses (can override recommendation)
   ↓
6. [Execution path] Stripe Checkout $199
   ↓
7. Intake form (upload passport, I-20, employment plan)
   ↓
8. AI pre-fills I-765 + supporting docs
   ↓
9. Limited Scope Agreement displayed + signed (e-signature)
   ↓
10. Case assigned to panel attorney (manual initially)
    ↓
11. Attorney reviews in dashboard
    → If clean: signs G-28, submits, notifies user
    → If red flags: flags to Guardian, user offered upgrade
    ↓
12. User notified of submission + receipt number
    ↓
13. Case tracked in user's Orders dashboard
```

### Qualifying Questionnaire

```yaml
title: "Let's find the right service for you"
description: "This helps us recommend Execution Mode ($199) or Advisory Mode ($499)"

checklist_sections:
  - title: "Your Situation"
    required_for_execution: all
    items:
      - "I'm currently on F-1 status in good standing"
      - "I've maintained full-time enrollment for at least one academic year"
      - "I have a clear employment plan (or I'm seeking one)"
      - "My school has confirmed I'm eligible for OPT"

  - title: "Your Documents"
    required_for_execution: all
    items:
      - "I have my current I-20 with OPT recommendation"
      - "I have my passport and visa documents"
      - "I have 2 passport-style photos ready"

  - title: "Complexity Flags"
    required_for_execution: all_unchecked
    items:
      - "I've been denied OPT before"
      - "I've had a prior visa refusal or RFE"
      - "I've had unauthorized employment issues"
      - "I'm applying post-completion with less than 30 days notice"

routing:
  execution_recommended: "all required items checked AND no complexity flags"
  advisory_recommended: "any required item unchecked OR any complexity flag checked"
  user_override_allowed: true
```

### Limited Scope Agreement

Displayed before payment, required signature (typed name = signature):

```
LIMITED SCOPE REPRESENTATION AGREEMENT

Client: [Name]
Attorney: [Assigned Attorney Name], [Bar Number]
Service: OPT Application Execution ($199)
Date: [Date]

INCLUDED SERVICES:
• Verification of your OPT application information
• Preparation of Form I-765 based on information you provide
• Electronic signing of Form G-28 as attorney of record
• Electronic filing of the I-765 with USCIS
• Confirmation of receipt

NOT INCLUDED:
• Strategic advice about whether to apply for OPT
• Employment plan evaluation
• Strategic advice on timing
• Preparation for RFEs or denials
• Representation in case of denial
• Any services beyond the I-765 filing

CLIENT RESPONSIBILITIES:
• Provide accurate and complete information
• Confirm your OPT eligibility with your school's DSO
• Review all prepared documents before filing
• Respond to any attorney requests within 48 hours

STOP AND FLAG PROVISION:
If during review, the attorney identifies material issues
that could affect the application's viability, you will be
notified and offered an upgrade to Advisory Mode. Any amount
you paid for Execution Mode will be credited toward Advisory
Mode pricing.

NO GUARANTEE:
The attorney makes no guarantee of USCIS approval. The
attorney's role is limited to the execution services above.

BY TYPING YOUR NAME BELOW, YOU AGREE TO THIS LIMITED SCOPE
REPRESENTATION:

[Type your full legal name]
```

### Attorney Dashboard

New interface for the assigned attorney to:
- See assigned cases (filtered by `status = "pending_review"`)
- Review AI-prefilled forms and supporting docs
- Run through sign-off checklist (Execution Mode specific)
- Either: "Approve & File" or "Flag for Upgrade"
- If flagged: note what needs Advisory Mode

### Attorney Sign-Off Checklist

```yaml
service: opt_application_execution
checklist:
  - id: passport_match
    label: "Beneficiary info matches passport (name, DOB, citizenship)"
  - id: i20_valid
    label: "I-20 has valid OPT recommendation from DSO"
  - id: employment_plan
    label: "Employment plan is coherent and related to major"
  - id: timing_ok
    label: "Filing window is appropriate (within 90 days of program end)"
  - id: no_prior_denials
    label: "No prior OPT denials disclosed"
  - id: no_unauthorized_work
    label: "No unauthorized employment disclosed"
  - id: photos_valid
    label: "Passport photos meet USCIS specs"
  - id: fee_payment_ready
    label: "USCIS filing fee payment method confirmed"

decision:
  all_checked: "Execute — sign G-28 and file"
  any_unchecked: "Flag to Guardian — offer Advisory upgrade"
```

---

## Data Model

### New Tables

```sql
-- Users (beyond existing auth)
users
  id (uuid, pk)
  email (string, unique)
  full_name (string)
  source (enum: form_8843, direct, referral, partner)
  created_at (datetime)
  updated_at (datetime)
  locale (enum: en, zh)

-- Products in the marketplace
products
  sku (string, pk)  -- e.g., "opt_execution"
  name (string)
  description (text)
  price_cents (integer)
  tier (enum: tier_0, tier_0_5_fulfillment, tier_1a_execution, tier_1b_advisory, tier_2, tier_3)
  requires_attorney (boolean)
  requires_questionnaire (boolean)
  stripe_price_id (string)
  active (boolean)
  created_at (datetime)

-- Qualifying questionnaire configs (YAML-loaded)
questionnaire_configs
  service_sku (string, pk)
  config_yaml (text)
  version (integer)
  active (boolean)
  updated_at (datetime)

-- User questionnaire responses
questionnaire_responses
  id (uuid, pk)
  user_id (uuid, fk -> users)
  service_sku (string, fk -> products)
  responses (json)  -- array of {item_id: bool}
  recommendation (enum: execution, advisory)
  user_choice (enum: execution, advisory)
  override (boolean)  -- true if user chose against recommendation
  created_at (datetime)

-- Orders / purchases
orders
  id (uuid, pk)
  user_id (uuid, fk -> users)
  product_sku (string, fk -> products)
  status (enum: pending, intake, processing, attorney_review, completed, flagged, refunded)
  stripe_session_id (string)
  stripe_payment_intent_id (string)
  amount_cents (integer)
  delivery_method (enum: download_only, user_mail, guardian_mail)
  filing_deadline (date, nullable)
  mailing_status (enum: not_required, needs_signature, ready_to_mail, mailed, delivered)
  mailed_at (datetime, nullable)
  tracking_number (string, nullable)
  intake_data (json)  -- user-submitted data for this order
  result_data (json)  -- output deliverables
  created_at (datetime)
  updated_at (datetime)
  completed_at (datetime, nullable)

-- Limited scope agreements (signed)
limited_scope_agreements
  id (uuid, pk)
  order_id (uuid, fk -> orders)
  user_id (uuid, fk -> users)
  attorney_id (uuid, fk -> attorneys, nullable)
  agreement_text (text)  -- snapshot of the agreement at signing
  user_signature (string)  -- typed name
  signed_at (datetime)
  user_ip (string)
  user_agent (string)

-- Attorneys on Guardian's panel
attorneys
  id (uuid, pk)
  full_name (string)
  email (string)
  bar_state (string)
  bar_number (string)
  bar_verified (boolean)
  bar_verified_at (datetime, nullable)
  specialties (json)  -- ["H-1B", "O-1", "OPT"]
  languages (json)  -- ["en", "zh", "hi"]
  location (string)  -- "Shanghai, China" or "New York, NY"
  photo_url (string, nullable)
  hourly_rate_usd (integer)
  flat_rate_structure (json)  -- {opt_execution: 80, h1b_execution: 100, ...}
  active (boolean)
  created_at (datetime)

-- Attorney assignments to orders
attorney_assignments
  id (uuid, pk)
  order_id (uuid, fk -> orders)
  attorney_id (uuid, fk -> attorneys)
  assigned_at (datetime)
  reviewed_at (datetime, nullable)
  decision (enum: pending, approved_filed, flagged_upgrade, cannot_proceed)
  checklist_responses (json)  -- the sign-off checklist answers
  attorney_notes (text, nullable)
  completed_at (datetime, nullable)

-- Email drip sequences
email_sequences
  id (uuid, pk)
  user_id (uuid, fk -> users)
  sequence_name (string)  -- "form_8843_welcome", "form_8843_mail_reminder", "opt_nurture"
  current_step (integer)
  next_send_at (datetime)
  completed (boolean)
  created_at (datetime)
```

### Existing Tables Used

- `checks` — Keep for existing document check flow; new orders can reference checks
- `documents_v2` — Reuse for order intake documents
- `extracted_fields` — Reuse for AI-extracted data

---

## API Endpoints

### Form 8843 Generator (Public, No Auth)

```
POST /api/form8843/generate
  Body: { email, full_name, visa_type, school, arrival_date, days_present, country, dependents }
  Response: { pdf_url, order_id, user_id, filing_instructions, filing_deadline }
  Side effects:
    - Creates user if not exists
    - Generates PDF
    - Sends email with PDF attached
    - Returns mailing instructions for the success screen
    - Enrolls in welcome drip sequence

GET /api/form8843/orders/{order_id}
  Response: { order_id, status, pdf_url, filing_deadline, mailing_status, filing_instructions }

POST /api/form8843/orders/{order_id}/mark-mailed
  Body: { mailed_at?, tracking_number? }
  Response: { order_id, mailing_status: "mailed" }

GET /api/form8843/orders/{order_id}/mailing-kit
  Response: { address_block, filing_notes, mailing_label_url?, envelope_template_url? }
```

### Marketplace (Authenticated)

```
GET /api/marketplace/products
  Response: { products: [...] }

GET /api/marketplace/products/{sku}
  Response: { sku, name, description, price_cents, tier, requires_questionnaire }

POST /api/marketplace/products/{sku}/questionnaire
  Body: { responses: [{item_id, checked}] }
  Response: { recommendation, advisory_reason, execution_reason }

POST /api/marketplace/checkout/{sku}
  Body: { questionnaire_response_id?, chosen_mode?: "execution"|"advisory" }
  Response: { stripe_checkout_url, order_id }

POST /api/marketplace/webhooks/stripe
  Body: Stripe webhook payload
  Handles: checkout.session.completed → create order, mark paid

GET /api/marketplace/orders
  Response: { orders: [...] }

GET /api/marketplace/orders/{order_id}
  Response: { order, status, result?, attorney_assignment? }

POST /api/marketplace/orders/{order_id}/intake
  Body: { intake data varies by product }
  Response: { order_id, status: "processing" }

POST /api/marketplace/orders/{order_id}/sign-agreement
  Body: { signature, agreement_text_snapshot }
  Response: { agreement_id, signed_at }

GET /api/marketplace/orders/{order_id}/result
  Response: { result_data, downloads }
```

### Attorney Portal (Authenticated, Attorney Role)

```
GET /api/attorney/dashboard
  Response: { pending_cases, completed_cases, stats }

GET /api/attorney/cases/{order_id}
  Response: { order, intake_data, ai_output, checklist, agreement }

POST /api/attorney/cases/{order_id}/review
  Body: { checklist_responses, decision, notes }
  Response: { decision_recorded, next_action }

POST /api/attorney/cases/{order_id}/file
  Body: { g28_signature, filing_confirmation }
  Response: { filed_at, receipt_number }

POST /api/attorney/cases/{order_id}/flag-upgrade
  Body: { flag_reason, notes }
  Response: { flagged, user_notified }
```

---

## Frontend Pages

### Public Pages (No Auth)

| Path | Purpose |
|------|---------|
| `/form-8843` | Landing + generator (Mandarin + English toggle) |
| `/form-8843/success` | Delivery + mailing checklist + "What's Next" reveal |
| `/services` | Marketplace catalog |
| `/services/{sku}` | Product detail page with pricing tiers |
| `/services/{sku}/questionnaire` | Qualifying questionnaire |
| `/services/{sku}/checkout` | Stripe Checkout redirect |

### Authenticated Pages

| Path | Purpose |
|------|---------|
| `/account/orders` | User's order history |
| `/account/orders/{order_id}` | Order detail with status |
| `/account/orders/{order_id}/intake` | Product-specific intake form |
| `/account/orders/{order_id}/agreement` | Limited scope agreement + signature |
| `/account/orders/{order_id}/result` | Deliverables download |

### Attorney Portal

| Path | Purpose |
|------|---------|
| `/attorney/dashboard` | Pending cases, stats |
| `/attorney/cases/{order_id}` | Case review with checklist |
| `/attorney/cases/{order_id}/file` | Filing workflow |

---

## Legal & Compliance

### Limited Scope Representation

Every Execution Mode order requires:
1. Written agreement displayed before payment (not after)
2. Typed-name signature with IP + timestamp capture
3. Agreement snapshot stored in database
4. "Stop and Flag" clause with upgrade path
5. Clear disclosure: Guardian is not a law firm

### Disclosures

Every page with attorney interaction shows:
```
ℹ Guardian is not a law firm. Legal services are provided
   by independent licensed attorneys who exercise independent
   professional judgment. [Learn more]
```

### Data Privacy

- All uploaded documents encrypted at rest
- PII (SSN, passport, etc.) only in encrypted fields
- Delete on request within 30 days
- Privacy policy + Terms of service required

### Mailing Fulfillment

- Guardian must not represent “PDF generated” as “filed”
- If Guardian offers mailing fulfillment, it is a clerical service, not legal representation
- Guardian must store proof of mailing and any tracking number returned to the user
- The paid mailing service should not launch until the signature workflow is validated and reviewed for compliance and chain-of-custody risk

### State Compliance

- Verify attorney's bar status per state for each case
- Attorney must be licensed in at least one US state (not necessarily the client's state — immigration is federal)
- Display attorney's bar number on signed agreements

---

## Out of Scope (Deferred)

- **Mandarin full localization** — Only Form 8843 page gets Mandarin; rest is English
- **Attorney panel with user choice** — Tier 3 deferred
- **H-1B Registration product** — deferred to Phase 4 (needs March 2027 timing)
- **CPA integration** — Tier 4 cross-domain services deferred
- **In-app messaging** — use email for attorney-user communication
- **Refund automation** — manual Stripe refund for Phase 1
- **Multi-attorney routing** — single panel attorney initially
- **Analytics dashboard** — basic only; use Stripe dashboard + logs
- **SEO-optimized marketing pages** — basic landing page only
- **83(b) mailing fulfillment service** — reuse the Form 8843 rail later if the signature + ops model proves workable

---

## Success Metrics

| Metric | Target (90 days) |
|--------|-----------------|
| Form 8843 users | 1,000+ |
| Form 8843 mailed-confirmation rate | 60%+ |
| Form 8843 → Tier 0 conversion | 5%+ |
| Form 8843 mailing-service take rate | 5-10% if launched |
| Tier 0 paid orders | 100+ |
| Tier 0 revenue | $5,000+ |
| OPT Execution orders | 10+ (manual attorney handling) |
| OPT Execution revenue | $2,000+ |
| Attorney sign-off completion rate | 90%+ within 48 hours |
| Stop-and-flag rate | 10-20% (healthy signal) |
| Agreement signature completion rate | 95%+ |

---

## Dependencies

- **Stripe account** with products + prices configured
- **Email provider** (Resend or Postmark) for transactional + drip emails
- **Form 8843 PDF template** from IRS.gov and the actual fill strategy validated (widget-based or overlay)
- **Form 8843 mailing instructions** verified, including current IRS mailing address and self-mail deadline copy
- **Signature policy for assisted mailing** validated before launching the $19 fulfillment upsell
- **Panel attorney** hired + onboarded with attorney portal access
- **Limited scope agreement** reviewed by legal counsel before launch
- **Terms of Service + Privacy Policy** updated to reflect marketplace model
- **Professional liability insurance** for Guardian (not the attorney)
