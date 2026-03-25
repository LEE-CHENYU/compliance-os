# Data Room, Track B & Auth — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Track B (Entity Check), email/password auth with account wall, and a timeline-centered personal data room — completing the Guardian MVP.

**Architecture:** Track B reuses all Track A infrastructure (extractor, comparator, rule engine, review router) with entity-specific rules and a single-document comparison flow. Auth adds a users table, JWT tokens, and a register/login API. The data room adds timeline events, upload prompts, and a dashboard page that auto-re-evaluates on new uploads.

**Tech Stack:** FastAPI + SQLAlchemy + SQLite (backend), Next.js + Tailwind (frontend), PyJWT + bcrypt (auth), existing OpenAI extractor + YAML rule engine

**Spec:** `docs/superpowers/specs/2026-03-24-dataroom-entity-auth-design.md`

---

## File Structure

### Track B — New Files
| File | Responsibility |
|---|---|
| `config/rules/entity.yaml` | All entity rules (6 logic + 6 advisory) |
| `frontend/src/app/check/entity/page.tsx` | Entity info questions (B1) |
| `frontend/src/app/check/entity/upload/page.tsx` | Tax return upload (B2) |
| `frontend/src/app/check/entity/review/page.tsx` | Entity review flow (B3-B5) |

### Track B — Modified Files
| File | Change |
|---|---|
| `compliance_os/web/routers/review.py` | Add entity field mapping for answers-vs-extraction comparison |

### Auth — New Files
| File | Responsibility |
|---|---|
| `compliance_os/web/models/auth.py` | User SQLAlchemy model + Pydantic schemas |
| `compliance_os/web/routers/auth.py` | Register, login, me endpoints |
| `compliance_os/web/services/auth_service.py` | Password hashing, JWT creation/validation |
| `frontend/src/app/login/page.tsx` | Login page |
| `frontend/src/components/auth/AuthModal.tsx` | Glass modal for "Save as my case" account creation |
| `frontend/src/lib/auth.ts` | JWT storage, auth headers, useAuth hook |
| `tests/test_auth.py` | Auth endpoint tests |

### Auth — Modified Files
| File | Change |
|---|---|
| `compliance_os/web/models/tables_v2.py` | Add `user_id` column to CheckRow |
| `compliance_os/web/app.py` | Mount auth router |
| `frontend/src/app/page.tsx` | Add "Sign in" link to nav |
| `frontend/src/app/check/stem-opt/review/page.tsx` | Replace save button with AuthModal |
| `frontend/src/app/check/entity/review/page.tsx` | Same AuthModal integration |

### Data Room — New Files
| File | Responsibility |
|---|---|
| `compliance_os/web/models/timeline.py` | TimelineEvent, UploadPrompt, DocumentEvent models |
| `compliance_os/web/routers/dashboard.py` | Dashboard API: timeline, stats, upload, documents |
| `compliance_os/web/services/timeline_builder.py` | Build timeline events from extractions + rules |
| `frontend/src/app/dashboard/page.tsx` | Data room main page |
| `frontend/src/components/dashboard/Timeline.tsx` | Timeline component with events, docs, prompts |
| `frontend/src/components/dashboard/Sidebar.tsx` | Category/risk/check sidebar |
| `frontend/src/components/dashboard/StatsBar.tsx` | Stats cards |
| `tests/test_dashboard.py` | Dashboard API tests |

---

## Task 1: Track B — Entity Rules + Backend

**Files:**
- Create: `config/rules/entity.yaml`
- Modify: `compliance_os/web/routers/review.py`
- Test: existing `tests/test_rule_engine.py` (add entity tests)

- [ ] **Step 1: Create entity.yaml with all rules from spec**

All 12 rules: nra_scorp_invalid, missing_5472, schedule_c_on_opt, foreign_capital_undocumented, corporate_veil_risk, wrong_form_type, advisory_state_annual_report, advisory_registered_agent, advisory_entity_fbar, advisory_dividend_withholding, advisory_form_3520, advisory_boi_foreign.

- [ ] **Step 2: Add entity field mapping to review.py**

Track B compares answers vs tax return extraction (not two documents). Add a second mapping dict `ENTITY_FIELD_MAP` and branch in the compare endpoint based on `check.track`.

- [ ] **Step 3: Write tests for entity rules**

Add tests to `test_rule_engine.py`: test NRA + S-Corp fires critical, test missing 5472, test advisory gating on residency.

- [ ] **Step 4: Run all tests**

Run: `conda run -n compliance-os pytest tests/ -v`

- [ ] **Step 5: Commit**

```
git commit -m "feat: add entity rules and Track B comparison logic"
```

---

## Task 2: Track B — Frontend Pages

**Files:**
- Create: `frontend/src/app/check/entity/page.tsx`
- Create: `frontend/src/app/check/entity/upload/page.tsx`
- Create: `frontend/src/app/check/entity/review/page.tsx`

- [ ] **Step 1: Create entity info page (B1)**

Six questions with chip selectors. Q6 (visa type) conditionally shown when Q2 = "on_visa". On submit, creates check with `track: "entity"` and navigates to upload.

- [ ] **Step 2: Create entity upload page (B2)**

Single upload slot for tax return. Same component pattern as Track A upload but one zone instead of two.

- [ ] **Step 3: Create entity review page (B3-B5)**

Copy Track A review page structure. Change:
- Grid header: "Your Answers" / "Tax Return" instead of "I-983" / "Employment Letter"
- Snapshot title: "Your Entity Check" instead of "Your STEM OPT Check"
- Timeline: show entity-relevant dates (tax year, filing deadlines)

- [ ] **Step 4: Build frontend**

Run: `cd frontend && npm run build`

- [ ] **Step 5: Commit**

```
git commit -m "feat: add Track B entity check frontend pages"
```

---

## Task 3: Auth — Backend

**Files:**
- Create: `compliance_os/web/models/auth.py`
- Create: `compliance_os/web/services/auth_service.py`
- Create: `compliance_os/web/routers/auth.py`
- Modify: `compliance_os/web/models/tables_v2.py`
- Modify: `compliance_os/web/app.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write auth tests**

```python
def test_register_creates_user(client):
    resp = client.post("/api/auth/register", json={"email": "test@example.com", "password": "secure123"})
    assert resp.status_code == 200
    assert "token" in resp.json()

def test_register_duplicate_email(client):
    client.post("/api/auth/register", json={"email": "dup@example.com", "password": "pass123"})
    resp = client.post("/api/auth/register", json={"email": "dup@example.com", "password": "pass456"})
    assert resp.status_code == 409

def test_login_success(client):
    client.post("/api/auth/register", json={"email": "login@example.com", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": "pass123"})
    assert resp.status_code == 200
    assert "token" in resp.json()

def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"email": "wrong@example.com", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"email": "wrong@example.com", "password": "badpass"})
    assert resp.status_code == 401

def test_me_with_token(client):
    resp = client.post("/api/auth/register", json={"email": "me@example.com", "password": "pass123"})
    token = resp.json()["token"]
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"
```

- [ ] **Step 2: Implement User model and auth schemas**

`compliance_os/web/models/auth.py`: UserRow (id, email, password_hash, created_at), RegisterRequest, LoginRequest, AuthResponse, UserOut.

- [ ] **Step 3: Implement auth service**

`compliance_os/web/services/auth_service.py`: hash_password, verify_password (bcrypt), create_token, decode_token (PyJWT), get_current_user (FastAPI dependency).

- [ ] **Step 4: Implement auth router**

`compliance_os/web/routers/auth.py`: POST /register, POST /login, GET /me.

- [ ] **Step 5: Add user_id to CheckRow**

Add nullable `user_id` column. Add `link_check_to_user(check_id, user_id)` helper.

- [ ] **Step 6: Mount router, install deps**

Add `bcrypt` and `pyjwt` to pyproject.toml. Mount auth router in app.py. Add `JWT_SECRET` to `.env`.

- [ ] **Step 7: Run tests**

Run: `conda run -n compliance-os pytest tests/test_auth.py -v`

- [ ] **Step 8: Commit**

```
git commit -m "feat: add email/password auth with JWT tokens"
```

---

## Task 4: Auth — Frontend

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/components/auth/AuthModal.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/check/stem-opt/review/page.tsx`
- Modify: `frontend/src/app/check/entity/review/page.tsx`

- [ ] **Step 1: Create auth client library**

`frontend/src/lib/auth.ts`: `register(email, password)`, `login(email, password)`, `getToken()`, `logout()`, `isLoggedIn()`, `authHeaders()`. JWT stored in localStorage.

- [ ] **Step 2: Create login page**

`/login` — email + password form, glass panel, "Sign in" button. On success, redirect to `/dashboard`. Link to register.

- [ ] **Step 3: Create AuthModal component**

Glass modal that appears over the snapshot. "Create your account to save this case." Email + password inputs. On submit: register → link check to user → redirect to `/dashboard`.

- [ ] **Step 4: Replace "Save as my case" with AuthModal**

In both `stem-opt/review/page.tsx` and `entity/review/page.tsx`, the save button now opens AuthModal instead of calling updateCheck directly. If already logged in, skip modal and save directly.

- [ ] **Step 5: Add "Sign in" to landing page nav**

Show "Sign in" link in nav when not logged in. Show email + "Dashboard" when logged in.

- [ ] **Step 6: Build frontend**

Run: `cd frontend && npm run build`

- [ ] **Step 7: Commit**

```
git commit -m "feat: add auth UI — login page, register modal, protected nav"
```

---

## Task 5: Data Room — Backend

**Files:**
- Create: `compliance_os/web/models/timeline.py`
- Create: `compliance_os/web/services/timeline_builder.py`
- Create: `compliance_os/web/routers/dashboard.py`
- Modify: `compliance_os/web/app.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write dashboard API tests**

Test `/api/dashboard/timeline` returns events with documents and prompts. Test `/api/dashboard/stats` returns counts. Test `/api/dashboard/upload` triggers extraction + re-evaluation.

- [ ] **Step 2: Create timeline models**

`TimelineEventRow`, `DocumentEventRow`, `UploadPromptRow` — as defined in spec.

- [ ] **Step 3: Create timeline builder service**

`build_timeline(user_id)`:
- Query all checks + documents + extracted fields for user
- Generate events from extracted dates (start_date, end_date, tax_year)
- Generate computed events (12-month eval anniversary, grace period end)
- Generate upload prompts based on missing documents and upcoming deadlines
- Sort by date
- Return structured timeline

- [ ] **Step 4: Create dashboard router**

Endpoints:
- `GET /api/dashboard/timeline` — returns timeline events with docs, risks, prompts
- `GET /api/dashboard/stats` — returns aggregate stats
- `POST /api/dashboard/upload` — upload doc → extract → re-evaluate → return updated timeline
- `GET /api/dashboard/documents` — list all user documents

All endpoints require auth (use `get_current_user` dependency).

- [ ] **Step 5: Mount router, run tests**

- [ ] **Step 6: Commit**

```
git commit -m "feat: add data room backend — timeline builder, dashboard API"
```

---

## Task 6: Data Room — Frontend

**Files:**
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/components/dashboard/Timeline.tsx`
- Create: `frontend/src/components/dashboard/Sidebar.tsx`
- Create: `frontend/src/components/dashboard/StatsBar.tsx`

- [ ] **Step 1: Create Sidebar component**

Views (Timeline / All Documents), Categories with counts, Risks with counts, past Checks with status, "+ Run new check" button.

- [ ] **Step 2: Create StatsBar component**

Four glass cards: documents count, risks count, verified fields, days to next deadline.

- [ ] **Step 3: Create Timeline component**

Vertical timeline with:
- Date + title + dot (color by type: past/now/future/alert)
- Document pills attached to events (glass cards, category tags)
- Risk cards inline (glass panels, vibrancy severity tags)
- Upload prompts inline (dashed border, icon + text + why)
- Click prompt → file picker → auto-upload

- [ ] **Step 4: Create dashboard page**

`/dashboard` — requires auth (redirect to `/login` if no token). Three-column layout: sidebar + stats + timeline. Fetches from dashboard API on load.

- [ ] **Step 5: Add auth guard**

If user navigates to `/dashboard` without a valid JWT, redirect to `/login`.

- [ ] **Step 6: Build and test**

Run: `cd frontend && npm run build`
Manual test: login → dashboard → see timeline → upload from prompt → see re-evaluation.

- [ ] **Step 7: Commit**

```
git commit -m "feat: add data room UI — timeline, sidebar, stats, upload prompts"
```

---

## Task 7: Integration + Polish

- [ ] **Step 1: Run all backend tests**
- [ ] **Step 2: Run frontend build**
- [ ] **Step 3: Full E2E test**

Flow: Landing → Track A → upload → review → "Save as my case" → register → dashboard → upload from prompt → see new findings.

- [ ] **Step 4: Fix issues**
- [ ] **Step 5: Commit and push**

```
git push origin feat/discovery-dataroom
```
