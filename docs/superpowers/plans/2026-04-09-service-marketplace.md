# Service Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Guardian's service marketplace with Form 8843 generator (free wedge), filing instructions + mailing reminders, 4 Tier 0 paid products ($29-99), an optional $19 Form 8843 mailing upsell, and the first Execution Mode product (OPT Application at $199) with attorney review workflow.

**Spec:** `docs/superpowers/specs/2026-04-09-service-marketplace-design.md`

**Architecture:** Marketplace is a new module that reuses existing `form_filler.py`, `extractor.py`, `rule_engine.py`, and `llm_runtime.py` services. New tables sit alongside existing check/document tables. Stripe Checkout handles payments. Emails via Resend or similar transactional provider. Mail-only products share a filing-instructions and reminder layer. Attorney portal is a gated route under `/attorney/*` requiring role-based auth.

**Tech Stack:** Next.js 14, FastAPI, SQLAlchemy, PyMuPDF, Stripe Python SDK, Resend API, Claude Haiku, Tailwind CSS.

**Build order:** Ship in 4 vertical slices, each independently shippable:
1. **Slice 1:** Form 8843 generator + mailing checklist (public, no auth)
2. **Slice 2:** User accounts + marketplace catalog + Stripe checkout
3. **Slice 3:** Tier 0 products (H-1B doc check, FBAR, 83(b), student tax)
4. **Slice 4:** Execution Mode (OPT Application) + attorney portal

Each slice should be demo-able and shippable before starting the next.

---

## File Structure

### New Backend Files

| File | Responsibility |
|------|---------------|
| `compliance_os/web/models/marketplace.py` | New SQLAlchemy tables (users, products, orders, etc.) |
| `compliance_os/web/services/form_8843.py` | Form 8843 PDF generation using template |
| `compliance_os/web/services/email_service.py` | Email sending + drip sequence management |
| `compliance_os/web/services/mailing_service.py` | Filing instructions, mailing label generation, reminder scheduling |
| `compliance_os/web/services/stripe_service.py` | Stripe Checkout session creation + webhook handling |
| `compliance_os/web/services/questionnaire.py` | Questionnaire evaluation engine |
| `compliance_os/web/services/attorney_workflow.py` | Attorney assignment + sign-off logic |
| `compliance_os/web/routers/form8843.py` | `POST /api/form8843/generate` |
| `compliance_os/web/routers/marketplace.py` | Marketplace catalog + orders + checkout |
| `compliance_os/web/routers/attorney.py` | Attorney portal endpoints |
| `config/products.yaml` | Product catalog config (prices, SKUs, descriptions) |
| `config/questionnaires/opt_execution.yaml` | OPT questionnaire config |
| `config/attorney_checklists/opt_execution.yaml` | Attorney sign-off checklist |
| `templates/pdfs/form_8843_template.pdf` | IRS Form 8843 source template for overlay/widget fill |
| `templates/agreements/opt_execution_agreement.md` | Limited scope agreement template |
| `templates/emails/form_8843_welcome.html` | Welcome email with PDF attachment |
| `templates/emails/form_8843_mail_reminder.html` | Reminder email asking user to confirm they mailed the form |
| `templates/emails/form_8843_drip_*.html` | Drip sequence emails (4 steps) |
| `tests/test_form_8843.py` | Form 8843 generation tests |
| `tests/test_marketplace.py` | Marketplace flow tests |
| `tests/test_questionnaire.py` | Questionnaire evaluation tests |
| `tests/test_attorney_workflow.py` | Attorney workflow tests |

### New Frontend Files

| File | Responsibility |
|------|---------------|
| `frontend/src/app/form-8843/page.tsx` | Landing page for Form 8843 generator |
| `frontend/src/app/form-8843/success/page.tsx` | Delivery + mailing checklist + upsell page |
| `frontend/src/components/form8843/OnboardingWizard.tsx` | 6-question conversational onboarding |
| `frontend/src/components/form8843/FilingChecklistCard.tsx` | Mailing instructions, address copy, and mark-as-mailed UI |
| `frontend/src/components/form8843/WhatsNextCards.tsx` | Upsell reveal cards |
| `frontend/src/app/services/page.tsx` | Marketplace catalog |
| `frontend/src/app/services/[sku]/page.tsx` | Product detail page |
| `frontend/src/app/services/[sku]/questionnaire/page.tsx` | Qualifying questionnaire |
| `frontend/src/components/marketplace/TierSelector.tsx` | Execution vs. Advisory selector |
| `frontend/src/components/marketplace/QualifyingChecklist.tsx` | Questionnaire UI |
| `frontend/src/components/marketplace/ComplianceBanner.tsx` | "Guardian is not a law firm" banner |
| `frontend/src/components/marketplace/PriceComparison.tsx` | Execution vs Advisory pricing card |
| `frontend/src/app/account/orders/page.tsx` | User orders list |
| `frontend/src/app/account/orders/[id]/page.tsx` | Order detail |
| `frontend/src/app/account/orders/[id]/intake/page.tsx` | Product intake form |
| `frontend/src/app/account/orders/[id]/agreement/page.tsx` | Limited scope agreement signing |
| `frontend/src/app/attorney/dashboard/page.tsx` | Attorney portal dashboard |
| `frontend/src/app/attorney/cases/[id]/page.tsx` | Attorney case review |
| `frontend/src/components/attorney/SignOffChecklist.tsx` | Attorney sign-off checklist |

### Modified Files

| File | Changes |
|------|---------|
| `compliance_os/web/app.py` | Add new router includes: form8843, marketplace, attorney |
| `compliance_os/web/models/tables_v2.py` | Import new marketplace models |
| `compliance_os/web/models/auth.py` | Add `role` column (user, attorney, admin) |
| `requirements.txt` | Add `stripe`, `resend` (or chosen email SDK) |
| `frontend/package.json` | Add `@stripe/stripe-js` for redirect to checkout |
| `frontend/src/lib/api.ts` | Add marketplace API client functions |
| `.env.example` | Add STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, RESEND_API_KEY |

---

## Slice 1: Form 8843 Generator (Week 1-2)

**Goal:** Public-facing Form 8843 generator that captures emails, generates a filled PDF, explains how to actually file it, and tracks whether the user mailed it. No auth required. No payment for the base flow.

**Success criteria:** A user can land on `/form-8843`, complete 6 questions, get a filled Form 8843 PDF in their inbox within 1 minute, see clear filing instructions on the success screen, and mark the order as mailed.

### Task 1.1: Database Foundation

- [ ] **Step 1.1.1: Write failing test for `users` table creation**

```python
# tests/test_marketplace.py
from compliance_os.web.models.marketplace import User

def test_create_user(db_session):
    user = User(email="test@example.com", full_name="Test User", source="form_8843")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    assert user.email == "test@example.com"
```

- [ ] **Step 1.1.2: Create `compliance_os/web/models/marketplace.py`**

```python
"""Marketplace-related tables."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from compliance_os.web.models.tables_v2 import Base  # reuse Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "mp_users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    source = Column(String, default="direct")  # form_8843, direct, referral, partner
    locale = Column(String, default="en")  # en, zh
    role = Column(String, default="user")  # user, attorney, admin
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
```

- [ ] **Step 1.1.3: Run migration, verify test passes**

- [ ] **Step 1.1.4: Write tests for `Product`, `Order`, `Form8843Response` tables**

- [ ] **Step 1.1.5: Implement all marketplace models from spec**

### Task 1.2: Form 8843 Service

- [ ] **Step 1.2.1: Write failing test for PDF generation**

```python
# tests/test_form_8843.py
def test_generate_form_8843_pdf():
    from compliance_os.web.services.form_8843 import generate_form_8843
    inputs = {
        "full_name": "Jessica Chen",
        "visa_type": "F-1",
        "country_citizenship": "China",
        "school_name": "Columbia University",
        "days_present_current": 340,
        "days_present_year_1_ago": 280,
        "days_present_year_2_ago": 0,
    }
    pdf_bytes = generate_form_8843(inputs)
    assert len(pdf_bytes) > 1000  # Non-empty PDF
    assert pdf_bytes[:4] == b"%PDF"  # PDF magic bytes
```

- [ ] **Step 1.2.2: Download Form 8843 PDF from IRS.gov**
  - Save to `templates/pdfs/form_8843_template.pdf`
  - Inspect the actual template format; do not assume AcroForm widgets
  - If widget fill is not viable, use deterministic text overlay and preserve a searchable text layer

- [ ] **Step 1.2.3: Create `compliance_os/web/services/form_8843.py`**

```python
"""Form 8843 PDF generation."""
from pathlib import Path
import pymupdf

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "templates/pdfs/form_8843_template.pdf"

FIELD_MAP = {
    "full_name": "f1_01",  # exact field names from the actual template
    "us_taxpayer_id": "f1_02",
    "country_citizenship": "f1_03",
    "country_passport": "f1_04",
    "passport_number": "f1_05",
    "visa_type": "f1_06",
    "school_name": "f1_07",
    "days_present_current": "f1_08",
    "days_present_year_1_ago": "f1_09",
    "days_present_year_2_ago": "f1_10",
    # ... map all fields
}


def generate_form_8843(inputs: dict) -> bytes:
    """Generate a filled Form 8843 PDF from user inputs."""
    doc = pymupdf.open(TEMPLATE_PATH)
    for page in doc:
        for widget in page.widgets():
            field_key = _find_key_for_widget(widget.field_name)
            if field_key and field_key in inputs:
                widget.field_value = str(inputs[field_key])
                widget.update()
    out = doc.tobytes()
    doc.close()
    return out
```

- [ ] **Step 1.2.4: Verify test passes, PDF opens correctly**

### Task 1.3: Delivery Email + Mailing Reminder Service

- [ ] **Step 1.3.1: Sign up for Resend (or Postmark) and get API key**

- [ ] **Step 1.3.2: Add `resend` to requirements.txt**

- [ ] **Step 1.3.3: Write failing test for email sending (mock)**

```python
def test_send_form_8843_welcome(mock_resend):
    from compliance_os.web.services.email_service import send_form_8843_welcome
    send_form_8843_welcome(
        to_email="test@example.com",
        full_name="Test User",
        pdf_bytes=b"fake pdf bytes",
    )
    mock_resend.emails.send.assert_called_once()
```

- [ ] **Step 1.3.4: Create `compliance_os/web/services/email_service.py`**

```python
"""Transactional and drip email sending."""
import os
import resend

resend.api_key = os.environ.get("RESEND_API_KEY")


def send_form_8843_welcome(to_email: str, full_name: str, pdf_bytes: bytes):
    """Send Form 8843 with the PDF attached."""
    resend.Emails.send({
        "from": "Guardian <hello@guardian.ai>",
        "to": to_email,
        "subject": "Your Form 8843 is ready",
        "html": _render_welcome_html(full_name),
        "attachments": [{
            "filename": "Form_8843.pdf",
            "content": list(pdf_bytes),
        }],
    })
```

- [ ] **Step 1.3.5: Create email HTML templates in `templates/emails/`**

- [ ] **Step 1.3.6: Create `compliance_os/web/services/mailing_service.py`**
  - Return filing instructions for:
    - Form 8843-only filers (mail to Austin, TX; June 15 default)
    - Users who appear to need 1040-NR packaging instead
  - Generate a mailing-address block and printable label payload
  - Schedule reminder cadence for “did you mail it?”

- [ ] **Step 1.3.7: Add reminder email sequence logic**
  - Welcome email includes filing instructions
  - 2-week and 4-week reminders until user marks the order as mailed
  - 30-day pre-deadline reminder for self-mail Form 8843 users

### Task 1.4: Form 8843 API Endpoint

- [ ] **Step 1.4.1: Write failing test for `POST /api/form8843/generate`**

```python
def test_form8843_generate_endpoint(client):
    response = client.post("/api/form8843/generate", json={
        "email": "test@example.com",
        "full_name": "Test User",
        "visa_type": "F-1",
        "school_name": "Columbia University",
        "country_citizenship": "China",
        "days_present_current": 340,
    })
    assert response.status_code == 200
    assert "order_id" in response.json()
```

- [ ] **Step 1.4.2: Create `compliance_os/web/routers/form8843.py`**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from compliance_os.web.services.form_8843 import generate_form_8843
from compliance_os.web.services.email_service import send_form_8843_welcome
from compliance_os.web.models.marketplace import User, Form8843Response
# ... imports

router = APIRouter(prefix="/api/form8843", tags=["form8843"])


class Form8843Request(BaseModel):
    email: EmailStr
    full_name: str
    visa_type: str  # F-1, J-1, M-1, Q-1
    school_name: str
    country_citizenship: str
    days_present_current: int
    days_present_year_1_ago: int = 0
    days_present_year_2_ago: int = 0


@router.post("/generate")
async def generate(req: Form8843Request, db=Depends(get_db)):
    # 1. Create or find user
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        user = User(email=req.email, full_name=req.full_name, source="form_8843")
        db.add(user)
        db.commit()

    # 2. Generate PDF
    pdf_bytes = generate_form_8843(req.dict())

    # 3. Store response record
    response = Form8843Response(user_id=user.id, inputs=req.dict())
    db.add(response)
    db.commit()

    # 4. Email with PDF attached
    send_form_8843_welcome(req.email, req.full_name, pdf_bytes)

    # 5. Return success
    return {"order_id": response.id, "user_id": user.id}
```

- [ ] **Step 1.4.3: Wire router into `compliance_os/web/app.py`**

- [ ] **Step 1.4.4: Verify test passes**

- [ ] **Step 1.4.5: Add `GET /api/form8843/orders/{order_id}`**
  - Return `pdf_url`, `filing_deadline`, `mailing_status`, and mailing instructions

- [ ] **Step 1.4.6: Add `POST /api/form8843/orders/{order_id}/mark-mailed`**
  - Store `mailed_at` and optional tracking number
  - Stop pending reminder sequence

- [ ] **Step 1.4.7: Add `GET /api/form8843/orders/{order_id}/mailing-kit`**
  - Return mailing address block and any generated label/envelope assets

### Task 1.5: Frontend Form 8843 Page

- [ ] **Step 1.5.1: Create `frontend/src/app/form-8843/page.tsx`**
  - Landing page with Mandarin primary + English secondary
  - "Get my Form 8843 — Free" CTA button
  - Brief explainer: "Required for all F-1 students, even with $0 income"

- [ ] **Step 1.5.2: Create `OnboardingWizard.tsx` component**
  - 6 animated screens, one question at a time
  - Progress dots (● ● ○ ○ ○ ○)
  - "Next" button disabled until valid input
  - State managed with `useState` hook

- [ ] **Step 1.5.3: Wire up form submission**
  - `POST /api/form8843/generate`
  - Show loading state
  - On success: redirect to `/form-8843/success?order_id=...`

- [ ] **Step 1.5.4: Create `/form-8843/success/page.tsx`**
  - Confirmation: "Your Form 8843 is ready"
  - Inline PDF preview or strong download CTA
  - Filing checklist:
    - Form 8843 cannot be e-filed by itself
    - IRS Austin mailing address
    - Default deadline copy
    - Certified mail recommendation
    - `Mark as mailed` action
    - `Copy mailing address` action
  - `WhatsNextCards` component with 3 upsell cards
  - Prominent "Just the 8843, thanks" exit

- [ ] **Step 1.5.5: Manual E2E test**
  - Fill form with test data
  - Verify email arrives within 30s
  - Verify PDF opens correctly in Preview
  - Verify all fields are filled
  - Verify mailing instructions match the expected filing scenario
  - Verify `Mark as mailed` suppresses reminders

- [ ] **Step 1.5.6: Add optional $19 mailing upsell behind a feature flag or ops toggle**
  - CTA copy: “Let Guardian mail this for me”
  - Only expose when signature workflow and certified-mail ops are validated
  - If not launch-ready, show waitlist or hide entirely

### Task 1.6: Deploy + Distribution

- [ ] **Step 1.6.1: Deploy to Fly.io**

- [ ] **Step 1.6.1a: Configure reminder job for unmailed Form 8843 orders**

- [ ] **Step 1.6.1b: Create manual ops checklist for paid mailing service beta**
  - print
  - signature verification
  - certified mail purchase
  - tracking capture
  - user notification

- [ ] **Step 1.6.2: Write first 小红书 post in Mandarin**

- [ ] **Step 1.6.3: Post to Reddit r/f1visa, r/OPT**

- [ ] **Step 1.6.4: Measure: first 50 users within 7 days**

---

## Slice 2: User Accounts + Marketplace + Stripe (Week 3-4)

**Goal:** User authentication, product catalog browsing, and working Stripe checkout for at least one Tier 0 product (start with student tax $29).

**Success criteria:** A user can sign up, browse services, buy student tax filing for $29 via Stripe, and see the order in their dashboard.

### Task 2.1: User Auth Extension

- [ ] **Step 2.1.1: Write test: user signs up with email/password**

- [ ] **Step 2.1.2: Add `role` column to users table (migration)**

- [ ] **Step 2.1.3: Extend existing auth to support marketplace users**
  - Reuse `auth.py` and `auth_service.py` if present
  - Add `/api/auth/signup`, `/api/auth/login`, `/api/auth/me`

- [ ] **Step 2.1.4: Frontend: signup/login pages**

### Task 2.2: Product Catalog

- [ ] **Step 2.2.1: Create `config/products.yaml`**

```yaml
products:
  - sku: form_8843_free
    name: "Form 8843 (Free)"
    description: "For F-1/J-1/M-1/Q-1 students, even with zero income"
    price_cents: 0
    tier: tier_0
    requires_attorney: false
    requires_questionnaire: false
    active: true

  - sku: form_8843_mailing_service
    name: "Form 8843 Mailing Service"
    description: "Guardian prints and mails your completed packet with tracking proof"
    price_cents: 1900
    tier: tier_0_5_fulfillment
    requires_attorney: false
    requires_questionnaire: false
    active: false  # enable only after signature + ops validation

  - sku: student_tax_1040nr
    name: "Student Tax Filing (1040-NR + 8843)"
    description: "For international students with W-2 income"
    price_cents: 2900
    tier: tier_0
    requires_attorney: false
    requires_questionnaire: false
    active: true

  - sku: h1b_doc_check
    name: "H-1B Document Check"
    description: "AI-powered review of your H-1B petition for errors"
    price_cents: 4900
    tier: tier_0
    requires_attorney: false
    requires_questionnaire: false
    active: true

  - sku: fbar_check
    name: "FBAR Compliance Check"
    description: "Check your FBAR filing obligation + generate FinCEN 114"
    price_cents: 4900
    tier: tier_0
    requires_attorney: false
    requires_questionnaire: false
    active: true

  - sku: election_83b
    name: "83(b) Election Filing"
    description: "File your 83(b) election before the 30-day deadline"
    price_cents: 9900
    tier: tier_0
    requires_attorney: false
    requires_questionnaire: false
    active: true

  - sku: opt_execution
    name: "OPT Application — Execution Mode"
    description: "For self-directed users: attorney verifies and files. $199."
    price_cents: 19900
    tier: tier_1a_execution
    requires_attorney: true
    requires_questionnaire: true
    active: false  # Enable in Slice 4

  - sku: opt_advisory
    name: "OPT Application — Advisory Mode"
    description: "For uncertain users: 30-min consultation + strategy + filing. $499."
    price_cents: 49900
    tier: tier_1b_advisory
    requires_attorney: true
    requires_questionnaire: true
    active: false  # Enable in Slice 4
```

- [ ] **Step 2.2.2: Create product seeder script**
  - Reads YAML, creates Stripe products + prices via API
  - Stores `stripe_price_id` in database

- [ ] **Step 2.2.3: Build `GET /api/marketplace/products` endpoint**

- [ ] **Step 2.2.4: Frontend: `/services` catalog page**

### Task 2.3: Stripe Integration

- [ ] **Step 2.3.1: Set up Stripe test account, get keys**

- [ ] **Step 2.3.2: Add `stripe` to requirements.txt**

- [ ] **Step 2.3.3: Write failing test for checkout session creation**

- [ ] **Step 2.3.4: Create `compliance_os/web/services/stripe_service.py`**

```python
import stripe
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

def create_checkout_session(
    product_sku: str,
    user_email: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    product = get_product_by_sku(product_sku)
    session = stripe.checkout.Session.create(
        line_items=[{"price": product.stripe_price_id, "quantity": 1}],
        mode="payment",
        customer_email=user_email,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"product_sku": product_sku},
    )
    return {"url": session.url, "session_id": session.id}
```

- [ ] **Step 2.3.5: Build `POST /api/marketplace/checkout/{sku}` endpoint**

- [ ] **Step 2.3.6: Build Stripe webhook handler `POST /api/marketplace/webhooks/stripe`**
  - On `checkout.session.completed`: create Order, mark paid
  - Verify webhook signature

- [ ] **Step 2.3.7: Frontend: checkout flow**
  - User clicks "Buy" → redirect to Stripe Checkout
  - On return to success_url → show "Processing"
  - Poll until order is created via webhook

### Task 2.4: First Paid Product — Student Tax Filing

- [ ] **Step 2.4.1: Create `compliance_os/web/services/student_tax.py`**
  - Generate 1040-NR + 8843 + treaty claim form (8833)
  - Reuse `form_filler.py` for PDF generation

- [ ] **Step 2.4.2: Create intake form route `POST /api/marketplace/orders/{order_id}/intake`**
  - Accepts W-2 upload, personal info, scholarship data
  - Stores in order.intake_data

- [ ] **Step 2.4.3: Create processing route `POST /api/marketplace/orders/{order_id}/process`**
  - Generates all three forms
  - Stores PDFs in `uploads/`
  - Updates order.result_data

- [ ] **Step 2.4.4: Frontend: intake form + result page**

- [ ] **Step 2.4.5: E2E test: buy + intake + delivery**

### Task 2.5: Order Dashboard

- [ ] **Step 2.5.1: Build `/account/orders` page**

- [ ] **Step 2.5.2: Build `/account/orders/[id]` page**

- [ ] **Step 2.5.3: Email notifications on order status changes**

---

## Slice 3: Remaining Tier 0 Products (Week 5-6)

**Goal:** Ship H-1B doc check, FBAR check, and 83(b) election filing as paid Tier 0 products.

**Success criteria:** Users can buy any of the 4 paid Tier 0 products end-to-end.

### Task 3.1: H-1B Document Check ($49)

- [ ] **Step 3.1.1: Design intake (upload I-129, LCA, job description)**

- [ ] **Step 3.1.2: Reuse existing `extractor.py` + `rule_engine.py` for H-1B rules**

- [ ] **Step 3.1.3: Create `config/rules/h1b_doc_check.yaml`**
  - Common H-1B errors: wage level mismatch, SOC code alignment, LCA validity period, etc.

- [ ] **Step 3.1.4: Create service + route for processing**

- [ ] **Step 3.1.5: Deliver: report with findings + severity**

- [ ] **Step 3.1.6: Frontend: intake + results page**

### Task 3.2: FBAR Compliance Check ($49)

- [ ] **Step 3.2.1: Intake form: list of foreign accounts with balances**

- [ ] **Step 3.2.2: Rule: aggregate > $10K triggers FBAR requirement**

- [ ] **Step 3.2.3: Generate FinCEN 114 PDF (from template)**

- [ ] **Step 3.2.4: Include instructions for e-filing with FinCEN**

- [ ] **Step 3.2.5: Frontend flow**

### Task 3.3: 83(b) Election Filing ($99)

- [ ] **Step 3.3.1: Intake: stock grant details, grant date, vesting schedule**

- [ ] **Step 3.3.2: Calculate 30-day deadline from grant date**

- [ ] **Step 3.3.3: Generate 83(b) election letter + cover sheet**

- [ ] **Step 3.3.4: Include certified mail instructions**

- [ ] **Step 3.3.5: Send deadline alert email**

- [ ] **Step 3.3.6: Reuse the Form 8843 mailing rail for 83(b) only if the signature + ops model has been validated**

- [ ] **Step 3.3.6: Frontend flow**

### Task 3.4: Cross-Product Integration

- [ ] **Step 3.4.1: Add "What's Next" cards to each product's success page**

- [ ] **Step 3.4.2: Set up drip email sequences for each product**

- [ ] **Step 3.4.3: Add order history with consolidated view**

---

## Slice 4: Execution Mode — OPT Application + Attorney Portal (Week 7-10)

**Goal:** Ship the first attorney-involved product. Includes qualifying questionnaire, limited scope agreement, attorney portal, and sign-off workflow.

**Success criteria:** A user can buy OPT Execution Mode, complete intake, sign the agreement, have an attorney review and sign off, and receive the filed I-765 receipt.

### Task 4.1: Attorney Infrastructure

- [ ] **Step 4.1.1: Add `attorneys` and `attorney_assignments` tables**

- [ ] **Step 4.1.2: Add attorney role-based auth**

- [ ] **Step 4.1.3: Create seed script to add the first attorney**

- [ ] **Step 4.1.4: Build `/api/attorney/dashboard` endpoint**

- [ ] **Step 4.1.5: Build `/attorney/dashboard` frontend page**

### Task 4.2: Qualifying Questionnaire Engine

- [ ] **Step 4.2.1: Create `config/questionnaires/opt_execution.yaml`** (from spec)

- [ ] **Step 4.2.2: Write failing test for questionnaire evaluator**

```python
def test_questionnaire_routes_to_execution():
    from compliance_os.web.services.questionnaire import evaluate
    responses = {
        "f1_good_standing": True,
        "full_time_enrolled": True,
        "employment_plan": True,
        "school_confirmed_eligible": True,
        "has_i20": True,
        "has_passport": True,
        "has_photos": True,
        "denied_before": False,
        "prior_rfe": False,
        "unauthorized_employment": False,
        "late_application": False,
    }
    result = evaluate("opt_execution", responses)
    assert result.recommendation == "execution"
    assert result.advisory_reason is None


def test_questionnaire_routes_to_advisory_on_complexity_flag():
    responses = {
        # all required checked
        "f1_good_standing": True, "full_time_enrolled": True, "employment_plan": True,
        "school_confirmed_eligible": True, "has_i20": True, "has_passport": True, "has_photos": True,
        # but a complexity flag
        "denied_before": True,
        "prior_rfe": False, "unauthorized_employment": False, "late_application": False,
    }
    result = evaluate("opt_execution", responses)
    assert result.recommendation == "advisory"
    assert "denied before" in result.advisory_reason.lower()
```

- [ ] **Step 4.2.3: Implement `compliance_os/web/services/questionnaire.py`**

- [ ] **Step 4.2.4: Build `POST /api/marketplace/products/{sku}/questionnaire` endpoint**

- [ ] **Step 4.2.5: Frontend: `QualifyingChecklist.tsx` component**

- [ ] **Step 4.2.6: Integration: questionnaire → recommendation → user choice → checkout**

### Task 4.3: Limited Scope Agreement

- [ ] **Step 4.3.1: Create `templates/agreements/opt_execution_agreement.md`** (from spec)

- [ ] **Step 4.3.2: Write failing test for agreement snapshot**

- [ ] **Step 4.3.3: Create `limited_scope_agreements` table**

- [ ] **Step 4.3.4: Build `POST /api/marketplace/orders/{order_id}/sign-agreement` endpoint**
  - Store: agreement_text snapshot, user signature (typed name), IP, user-agent
  - Timestamp

- [ ] **Step 4.3.5: Frontend: `/account/orders/[id]/agreement` page**
  - Full agreement text displayed
  - Scroll-to-bottom required to enable signature field
  - Typed name = signature

### Task 4.4: OPT Application Intake

- [ ] **Step 4.4.1: Create intake form fields for OPT**
  - Passport upload, I-20 upload, photo upload
  - Employment plan (text or upload)
  - Desired start date

- [ ] **Step 4.4.2: AI pre-fills I-765**
  - Reuse `form_filler.py`
  - Extract data from uploads using `extractor.py`

- [ ] **Step 4.4.3: Store all pre-filled data in `order.intake_data`**

- [ ] **Step 4.4.4: Frontend intake page**

### Task 4.5: Attorney Assignment + Review

- [ ] **Step 4.5.1: On agreement signing: auto-assign to available attorney**

- [ ] **Step 4.5.2: Create `config/attorney_checklists/opt_execution.yaml`** (from spec)

- [ ] **Step 4.5.3: Build `GET /api/attorney/cases/{order_id}` endpoint**
  - Returns: intake data, AI pre-fill, checklist config, agreement

- [ ] **Step 4.5.4: Build `POST /api/attorney/cases/{order_id}/review` endpoint**
  - Accepts: checklist responses, decision, notes

- [ ] **Step 4.5.5: Build `/attorney/cases/[id]` frontend page**
  - Display all client-submitted data
  - `SignOffChecklist.tsx` component
  - Two decision buttons: "Approve & File" or "Flag for Upgrade"

- [ ] **Step 4.5.6: Email notifications**
  - Attorney on assignment
  - User on decision

### Task 4.6: Filing Workflow

- [ ] **Step 4.6.1: On approval: attorney signs G-28 (stored as signed PDF)**

- [ ] **Step 4.6.2: Manual filing step (attorney files externally, enters receipt number)**

- [ ] **Step 4.6.3: On filing: email user with confirmation + receipt**

- [ ] **Step 4.6.4: Update order status → completed**

### Task 4.7: "Stop and Flag" Upgrade Path

- [ ] **Step 4.7.1: On "Flag for Upgrade": send user email with explanation**

- [ ] **Step 4.7.2: Allow user to click through to Advisory Mode with credit applied**

- [ ] **Step 4.7.3: Stripe: create promotional coupon for the $199 credit**

- [ ] **Step 4.7.4: Frontend: upgrade acceptance flow**

### Task 4.8: End-to-End Testing

- [ ] **Step 4.8.1: E2E test: happy path (all green → filed)**

- [ ] **Step 4.8.2: E2E test: flag path (red flag → upgrade)**

- [ ] **Step 4.8.3: Legal review of the limited scope agreement**

- [ ] **Step 4.8.4: Dry run with panel attorney**

- [ ] **Step 4.8.5: Launch with 5 real users**

---

## Deferred / Post-Launch

- Form 8843 landing page Mandarin localization
- Long-form educational email drip beyond the core welcome + mailing reminder sequence
- Advisory Mode for OPT ($499) — stub for now, build after Execution Mode proves out
- Other Execution products (STEM OPT, H-1B extension, naturalization)
- Attorney panel with user choice (Tier 3)
- Cross-domain inconsistency check ($99)
- Referral/affiliate tracking
- User data room (persistent document storage across orders)
- Analytics dashboard for Cheney (use Stripe + logs for now)

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Form 8843 PDF template field names differ from expected | Medium | Inspect actual IRS template on Day 1, map fields manually |
| White-glove mailing blocked by signature or chain-of-custody issues | High | Keep base flow as self-mail, launch assisted mailing only after legal + ops validation |
| Stripe webhook flakiness in dev | Medium | Use Stripe CLI for local testing, log all webhook events |
| Attorney turnaround too slow | High | Set 48-hour SLA, email attorney + Cheney on new assignments |
| Limited scope agreement not enforceable | Medium | Have actual attorney review the template before launch |
| Users don't understand Execution vs. Advisory | Medium | A/B test the questionnaire copy, iterate |
| State bar complaints about UPL | Low | Keep disclosures prominent, never use "recommend" language |
| Email deliverability | Low | Use dedicated sending domain, warm up gradually |

---

## Success Metrics by Slice

| Slice | Ship Date (target) | Success Criteria |
|-------|-------------------|------------------|
| Slice 1: Form 8843 | Week 2 | 50+ users, PDF + filing instructions <60s, mailed confirmation flow working |
| Slice 2: Marketplace + 1 paid | Week 4 | 10+ paid orders, Stripe working |
| Slice 3: All Tier 0 | Week 6 | 50+ paid orders across products |
| Slice 4: OPT Execution | Week 10 | 5+ Execution orders filed, 0 attorney complaints |

---

## Dependencies to Resolve Before Starting

- [ ] Stripe account created + verified
- [ ] Resend (or alternative) account + API key
- [ ] Form 8843 PDF template downloaded from IRS.gov and actual fill strategy validated
- [ ] Form 8843 mailing instructions + Austin address verified
- [ ] Signature policy for assisted mailing reviewed before enabling the $19 upsell
- [ ] Panel attorney hired + onboarded (needed for Slice 4)
- [ ] Limited scope agreement reviewed by independent attorney
- [ ] Terms of Service + Privacy Policy drafted
- [ ] Professional liability insurance quote obtained
- [ ] Existing auth flow reviewed for extension (see `compliance_os/web/routers/auth.py`)

---

**End of Plan**
