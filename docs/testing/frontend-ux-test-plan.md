# Guardian Frontend & UX Test Plan

**Date:** 2026-04-13
**App:** https://guardiancompliance.app
**Method:** Each test is a copy-paste-ready prompt for a Claude agent with browser access (Claude Code + Playwright MCP, Claude.ai computer use, or Codex CLI with Playwright).

## Priority Order

| Priority | Test | What it covers | Why |
|---|---|---|---|
| 1 | Test 2: Auth Flow | Signup, login, guards, errors | Gates everything else |
| 2 | Test 1: Form 8843 | Free wedge product end-to-end | Primary acquisition funnel |
| 3 | Test 3: Student Check | Core verification product | The main product |
| 4 | Test 5: Dashboard | Upload, timeline, chat | Retention surface |
| 5 | Test 4: Marketplace | Browse, order, intake | Monetization path |
| 6 | Test 8: Error States | 404s, invalid input, crashes | Catches issues before users |
| 7 | Test 6: Conversion Funnel | Form 8843 → Check flow | Conversion optimization |
| 8 | Test 7: Mobile | Responsive layouts | Likely 50%+ of traffic |
| 9 | Test 10: Other Tracks | STEM OPT + Entity checks | Secondary products |
| 10 | Test 9: Attorney Portal | Role-based internal tool | Internal, lower priority |

## Test Accounts

| Email | Password | Role | Notes |
|---|---|---|---|
| `test@123.com` | `test123` | user | Existing test account with documents |
| `fretin13@gmail.com` | (use Google OAuth) | admin | Primary admin account |

---

## Test 1: Form 8843 Generator — Happy Path

**What it tests:** The free Form 8843 generator wizard end-to-end — the primary user acquisition funnel.

**Prompt:**
```
Go to https://guardiancompliance.app/form-8843 and complete the Form 8843 generator as an F-1 student.

Fill in:
- Full name: "Test Student"
- Visa type: F-1
- School name: "Columbia University"
- School address: "116th and Broadway, New York, NY 10027"
- School contact phone: "212-854-1754"
- Program director: "Dr. Smith"
- Current nonimmigrant status: F-1
- Date of arrival: 2023-08-15
- Country of citizenship: China
- Country of passport: China
- Passport number: E12345678
- US taxpayer ID: leave blank
- Address: 500 W 120th St, New York, NY 10027
- Days present current year: 200
- Days present 1 year ago: 300
- Days present 2 years ago: 100
- Check "exempt individual" status

Submit the form. Verify:
1. The form submits without errors
2. You're redirected to the /form-8843/success page
3. A download link for the PDF appears
4. The filing checklist card shows mailing instructions
5. There's a "What's Next" section with recommended next steps

Screenshot the success page.
```

**Expected result:** PDF generated, success page with download link + filing checklist + upsell CTAs.

**Routes covered:** `/form-8843`, `/form-8843/success`

**API endpoints exercised:** `POST /api/form8843/generate`, `GET /api/form8843/{order_id}/mailing-kit`

---

## Test 2: Auth Flow — Signup + Login + Guards

**What it tests:** Registration, login, auth guards on protected routes, error handling for bad credentials.

**Prompt:**
```
Test the authentication flow on https://guardiancompliance.app:

Part A — Registration:
1. Go to /login
2. Toggle to "Register" mode (there should be a toggle or link)
3. Enter email: testrunner-{timestamp}@example.com, password: TestPass123!
4. Submit the registration form
5. Verify you're logged in (redirected to dashboard or previous page)
6. Screenshot the logged-in state

Part B — Auth guard:
1. Open a new incognito/private window
2. Try to navigate directly to /dashboard
3. Verify you're redirected to /login with a ?next=/dashboard parameter
4. Log in with the credentials from Part A
5. Verify you're redirected back to /dashboard after login

Part C — Logout and login:
1. Log out (find the logout mechanism)
2. Navigate to /login
3. Log in with the credentials from Part A
4. Verify successful login

Part D — Error handling:
1. Try logging in with wrong password
2. Verify an error message appears (not a crash)
3. Try registering with an already-used email
4. Verify appropriate error message

Report: which parts passed, which failed, screenshots of any errors.
```

**Expected result:** All 4 parts pass — registration works, guards redirect correctly, errors display cleanly.

**Routes covered:** `/login`, `/dashboard` (guard), any protected route

**API endpoints exercised:** `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`

---

## Test 3: Student Check — Full Verification Flow

**What it tests:** The core product — document upload, AI extraction, cross-document comparison, followup questions, rule engine evaluation, and findings display.

**Prompt:**
```
Test the student document verification flow on https://guardiancompliance.app.

Step 1 — Track selection:
1. Go to /check
2. Click the "Student" card
3. Verify you land on /check/student

Step 2 — Questionnaire:
1. Fill in the student context questions:
   - Currently enrolled: Yes
   - Has CPT: Yes
   - No gap periods
   - No visa changes
   - Tax residency: Nonresident alien
2. Submit and verify navigation to the upload page

Step 3 — Document upload:
1. You should see upload slots (I-20 required, employment letter optional, I-94 optional)
2. Upload a test PDF for the I-20 slot (use any small PDF you can generate or find)
3. Verify the upload shows progress and then "uploaded" state
4. If there's an employment letter slot, upload another test PDF there
5. Continue to the review page

Step 4 — Review:
1. Verify the review page shows extraction progress (Phase 1: extracting)
2. Wait for extraction to complete
3. Verify comparison results appear (Phase 2: comparing)
4. If followup questions appear, answer them
5. Verify the final snapshot shows findings with severity levels (critical/warning/info)

Screenshot each phase transition. Report any errors, loading states that hang, or unexpected UI behavior.
```

**Expected result:** Full 4-phase flow completes — extraction, comparison, followups, findings snapshot with severity indicators.

**Routes covered:** `/check`, `/check/student`, `/check/student/upload`, `/check/student/review`

**API endpoints exercised:** `POST /api/checks`, `POST /api/checks/{id}/documents`, `POST /api/checks/{id}/extract`, `POST /api/checks/{id}/compare`, `POST /api/checks/{id}/followups`, `POST /api/checks/{id}/evaluate`, `GET /api/checks/{id}/snapshot`

---

## Test 4: Marketplace — Browse + Questionnaire + Order

**What it tests:** Product catalog display, questionnaire intake, mode selection (execution vs advisory), order creation, and the orders list.

**Prompt:**
```
Test the marketplace flow on https://guardiancompliance.app.

Step 1 — Browse products:
1. Go to /services
2. Verify the product catalog displays multiple products
3. Check that each product card shows: name, price (Free or $XX), category badge, description
4. Screenshot the catalog page

Step 2 — Product detail:
1. Click on the "H-1B Document Check" product (or similar paid product)
2. Verify the detail page shows product info, pricing, and a CTA
3. If there's a questionnaire step, click to start it

Step 3 — Questionnaire (if applicable):
1. Answer the questionnaire questions (check yes/no boxes in each section)
2. Submit the questionnaire
3. Verify the result shows a recommended product/mode
4. If prompted to choose between "execution" and "advisory" mode, select one

Step 4 — Order creation:
1. Click to create the order (you may need to log in first)
2. Verify the order is created and you're redirected to /account/orders/{id}
3. Verify the order page shows the correct product, status, and any intake form

Step 5 — Orders list:
1. Go to /account/orders
2. Verify your order appears in the list
3. Verify the status badge and CTA button are correct

Screenshot each step. Report: product count visible, any broken cards, any order creation failures.
```

**Expected result:** Products display correctly, questionnaire evaluates and recommends a mode, order created successfully, visible in orders list.

**Routes covered:** `/services`, `/services/[sku]`, `/services/[sku]/questionnaire`, `/account/orders`, `/account/orders/[id]`

**API endpoints exercised:** `GET /api/marketplace/products`, `GET /api/marketplace/questionnaire/{sku}`, `POST /api/marketplace/questionnaire/{sku}/submit`, `POST /api/marketplace/orders`, `GET /api/marketplace/orders`

---

## Test 5: Dashboard — Upload + Timeline + Chat

**What it tests:** The logged-in user workspace — document upload with duplicate detection, timeline rendering, and the AI chat interface.

**Prompt:**
```
Test the dashboard experience on https://guardiancompliance.app/dashboard.

Prerequisites: Log in first (use test@123.com / test123 or create a new account).

Step 1 — Initial state:
1. Navigate to /dashboard
2. Verify the page loads without errors
3. Note what's shown: timeline, upload prompts, document library
4. Screenshot the initial dashboard state

Step 2 — Document upload:
1. Find the upload area (should be drag-drop or click to upload)
2. Upload a small test PDF
3. Verify the upload shows progress
4. After upload, verify the document appears in the document list
5. Check if the timeline updates with a new entry for the upload

Step 3 — Chat interface:
1. Find the chat panel (might be "Document Reader" or "Compliance Assistant" mode)
2. Type a message like "What documents do I need for my F-1 status?"
3. Verify the assistant responds (not an error)
4. Try switching modes (Document Reader vs Compliance Assistant) if available
5. Verify the mode switch works and the chat context changes

Step 4 — Duplicate detection (if testable):
1. Upload the same PDF again
2. Verify the system detects the duplicate
3. Check for options like "Ask me", "Keep both", "Skip"
4. Screenshot the duplicate detection dialog

Report: load time, any errors, chat response quality, upload behavior.
```

**Expected result:** Dashboard loads with timeline, upload works with progress indicator, chat responds meaningfully, duplicate detection triggers on re-upload.

**Routes covered:** `/dashboard`

**API endpoints exercised:** `POST /api/dashboard/upload`, `GET /api/dashboard/timeline`, `GET /api/dashboard/stats`, `POST /api/dashboard/chat`

---

## Test 6: Form 8843 → Check Funnel (Conversion Path)

**What it tests:** The primary conversion funnel — does the free Form 8843 product successfully hand off to the paid compliance check?

**Prompt:**
```
Test the Form 8843 to compliance check conversion funnel on https://guardiancompliance.app.

This tests the primary user journey: free Form 8843 → paid compliance check.

1. Go to /form-8843
2. Complete the Form 8843 wizard (use F-1 student data):
   - Name: Test Funnel User
   - Visa: F-1
   - School: NYU
   - Fill in remaining required fields with plausible data
3. Submit and reach the success page
4. On the success page, look for "What's Next" cards or CTAs that link to the compliance check
5. Click the CTA that leads to /check (should auto-detect the F-1/student context)
6. Verify the check page opens with the correct track pre-selected (student)
7. If the questionnaire pre-fills any answers from the Form 8843 data, verify they match
8. Screenshot: the success page CTAs, the check page with any pre-filled context

Report: Does the funnel flow smoothly? Is context carried between Form 8843 and the check? Any broken links or missing CTAs?
```

**Expected result:** Smooth handoff from Form 8843 success → check page with student track auto-selected and any available context pre-filled.

**Routes covered:** `/form-8843`, `/form-8843/success`, `/check`, `/check/student`

**Analytics events to verify:** `form_8843_gtm_generate_succeeded`, `form_8843_gtm_check_path_inferred`

---

## Test 7: Mobile Responsiveness

**What it tests:** Whether the app is usable on a phone-sized viewport (375x812, iPhone 14 Pro).

**Prompt:**
```
Test mobile responsiveness on https://guardiancompliance.app using a mobile viewport (375x812, iPhone 14 Pro).

Test these pages in mobile viewport:

1. / (landing page)
   - Does the hero section display correctly?
   - Is text readable (not overflowing)?
   - Are buttons tappable (not too small)?

2. /login
   - Does the login form fit the screen?
   - Are input fields full-width?
   - Is the Google OAuth button visible?

3. /form-8843
   - Does the wizard fit the mobile screen?
   - Are step labels readable?
   - Can you navigate forward/back?
   - Are input fields usable on mobile?

4. /services
   - Do product cards stack vertically?
   - Are prices and CTAs visible?

5. /dashboard (logged in)
   - Does the layout adapt?
   - Is the chat panel accessible?
   - Can you upload a file?

For each page: screenshot the mobile view, note any overflow issues, unreadable text, or untappable buttons.
```

**Expected result:** All pages render cleanly at 375px width — cards stack, text is readable, forms are usable, no horizontal scrolling.

**Routes covered:** `/`, `/login`, `/form-8843`, `/services`, `/dashboard`

---

## Test 8: Error States + Edge Cases

**What it tests:** How the app handles bad input, missing data, expired sessions, and invalid navigation.

**Prompt:**
```
Test error handling across https://guardiancompliance.app:

1. 404 — Navigate to /nonexistent-page. Does a 404 page appear, or do you get a blank screen?

2. Expired token — Log in, then manually clear localStorage (or wait). Try accessing /dashboard. Verify you're redirected to login, not shown a broken page.

3. Invalid check ID — Navigate to /check/student/review?id=fake-uuid-12345. Verify error handling (not a crash).

4. Upload invalid file — Go to any upload page and try uploading a .txt file or a very large file (>50MB if possible). Verify the upload is rejected with a clear message.

5. Empty form submission — On /form-8843, try clicking submit without filling required fields. Verify validation messages appear for each missing field.

6. Rapid double-click — On any form submission button, click it twice rapidly. Verify only one submission happens (check for duplicate orders, double uploads, etc.).

7. Attorney access without role — Log in as a regular user and navigate to /attorney/dashboard. Verify you get a 401/403 error, not a blank page or crash.

8. Back button during wizard — Start the Form 8843 wizard, fill a few steps, then click the browser back button. Verify the wizard handles it gracefully (returns to previous step or shows a confirmation).

For each test: note whether the error is handled gracefully (clear message) or crashes (blank screen, console error, unhandled exception). Screenshot any crashes.
```

**Expected result:** All 8 edge cases handled gracefully — clear error messages, no blank screens, no unhandled exceptions.

---

## Test 9: Attorney Portal (Role-Based)

**What it tests:** The internal attorney workflow — case assignment, checklist completion, decision recording, filing confirmation.

**Prompt:**
```
Test the attorney portal on https://guardiancompliance.app. You'll need an attorney-role user.

Prerequisites: Check the database for a user with role='attorney'. If none exists, you may need to create one via API or database update.

Step 1 — Attorney dashboard:
1. Log in as the attorney user
2. Navigate to /attorney/dashboard
3. Verify the page shows a list of assigned cases (or an empty "No cases" message)
4. Screenshot the dashboard

Step 2 — Case review (if cases exist):
1. Click on a case
2. Verify the case detail page shows:
   - Client information
   - Agreement text (if not signed, a signing prompt)
   - Checklist with yes/no questions
   - Decision radio (approve/flag)
   - Notes textarea
3. Try completing the checklist
4. Select a decision (approve)
5. Submit the review
6. Verify the status updates

Step 3 — Filing confirmation (if case approved):
1. After approval, find the filing confirmation section
2. Enter a receipt number (e.g., "WAC0000000001")
3. Submit
4. Verify the case status updates to "filed"

Report: whether each step works, any missing UI elements, any access control issues.
```

**Expected result:** Attorney dashboard loads, case detail shows all required fields, checklist + decision + filing flow works end-to-end.

**Routes covered:** `/attorney/dashboard`, `/attorney/cases/[id]`

**API endpoints exercised:** `GET /api/attorney/dashboard`, `GET /api/attorney/cases/{id}`, `POST /api/attorney/cases/{id}/review`, `POST /api/attorney/cases/{id}/filing`

---

## Test 10: STEM OPT + Entity Check Tracks

**What it tests:** The non-student check tracks — verifying track-specific questionnaires, upload slots, and findings.

**Prompt:**
```
Test the non-student check tracks on https://guardiancompliance.app.

Part A — STEM OPT:
1. Go to /check → click "Young Professional" (STEM OPT track)
2. Fill the context questions:
   - Stage: STEM OPT
   - Employer changed: No
   - Employment status: Employed
   - Has foreign accounts: No
3. Proceed to upload page
4. Verify upload slots show I-983 (required) and employment letter
5. Upload test documents
6. Proceed to review
7. Verify extraction + comparison + findings flow works

Part B — Entity:
1. Go to /check → click "Entrepreneur" (Entity track)
2. Fill context:
   - Entity type: SMLLC
   - Owner residency: outside_us
   - Formation age: 3+ years
   - Separate bank account: No
3. Proceed to upload
4. Verify upload shows entity-specific document slots (tax return)
5. Upload a test document
6. Proceed to review
7. Verify entity-specific findings appear (expect: corporate_veil_risk for separate_bank_account=no)

For each track: screenshot the questionnaire, upload page, and final findings. Report any track-specific bugs.
```

**Expected result:** Both tracks complete end-to-end. Entity track should surface `corporate_veil_risk` finding for `separate_bank_account=no`.

**Routes covered:** `/check/stem-opt/*`, `/check/entity/*`

---

## Appendix: Route Map

| Route | Auth | Purpose |
|---|---|---|
| `/` | No | Landing page |
| `/login` | No | Auth (signup/login toggle + Google OAuth) |
| `/form-8843` | No | Form 8843 wizard |
| `/form-8843/success` | No | Form 8843 success + filing checklist |
| `/check` | No | Track selector (Student / STEM OPT / Entity) |
| `/check/student` | No | Student context questionnaire |
| `/check/student/upload` | No | Student document upload |
| `/check/student/review` | Conditional | Student extraction + findings |
| `/check/stem-opt` | No | STEM OPT context questionnaire |
| `/check/stem-opt/upload` | No | STEM OPT document upload |
| `/check/stem-opt/review` | Conditional | STEM OPT extraction + findings |
| `/check/entity` | No | Entity context questionnaire |
| `/check/entity/upload` | No | Entity document upload |
| `/check/entity/review` | Conditional | Entity extraction + findings |
| `/dashboard` | **Yes** | User workspace (timeline, upload, chat) |
| `/services` | No | Product catalog |
| `/services/[sku]` | No | Product detail |
| `/services/[sku]/questionnaire` | **Yes** | Intake questionnaire |
| `/account/orders` | **Yes** | Orders list |
| `/account/orders/[id]` | **Yes** | Order workspace |
| `/account/orders/[id]/agreement` | **Yes** | Agreement signing |
| `/case/new` | **Yes** | Create case |
| `/case/[id]` | **Yes** | Case overview |
| `/case/[id]/discovery` | **Yes** | Case discovery |
| `/case/[id]/documents` | **Yes** | Case documents |
| `/attorney/dashboard` | **Yes (attorney)** | Attorney case list |
| `/attorney/cases/[id]` | **Yes (attorney)** | Attorney case review |

## Appendix: Key API Endpoints

### Auth
- `POST /api/auth/register` — create account
- `POST /api/auth/login` — authenticate
- `GET /api/auth/me` — current user
- `GET /api/auth/google` — Google OAuth start
- `POST /api/auth/logout` — revoke session

### Form 8843
- `POST /api/form8843/generate` — generate PDF
- `GET /api/form8843/{order_id}/mailing-kit` — filing context
- `POST /api/form8843/{order_id}/mark-mailed` — record mailing

### Checks
- `POST /api/checks` — create check
- `GET /api/checks/{id}` — get check
- `PATCH /api/checks/{id}` — update answers
- `POST /api/checks/{id}/documents` — upload document
- `POST /api/checks/{id}/extract` — extract fields
- `POST /api/checks/{id}/compare` — compare documents
- `POST /api/checks/{id}/followups` — generate followups
- `POST /api/checks/{id}/evaluate` — run rule engine
- `GET /api/checks/{id}/snapshot` — get all results

### Dashboard
- `POST /api/dashboard/upload` — upload document
- `GET /api/dashboard/timeline` — timeline events
- `GET /api/dashboard/stats` — user stats
- `POST /api/dashboard/chat` — chat message

### Marketplace
- `GET /api/marketplace/products` — list products
- `GET /api/marketplace/questionnaire/{sku}` — get questionnaire
- `POST /api/marketplace/questionnaire/{sku}/submit` — evaluate responses
- `POST /api/marketplace/orders` — create order
- `GET /api/marketplace/orders` — list orders
- `GET /api/marketplace/orders/{id}` — order details
- `POST /api/marketplace/orders/{id}/agreements` — sign agreement

### Attorney
- `GET /api/attorney/dashboard` — list assigned cases
- `GET /api/attorney/cases/{id}` — case details
- `POST /api/attorney/cases/{id}/review` — record decision
- `POST /api/attorney/cases/{id}/filing` — record filing
