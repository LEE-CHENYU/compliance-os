# Egress Consent — Plan A: Web Consent Gate + Landing Copy

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No document uploads from the hosted web check until the user explicitly approves (Allow once / this session / Always / Deny), and ship the already-staged landing copy that promises this in the same change.

**Architecture:** A pure-logic consent store (`localStorage` for `always`, in-memory for `session`) + a modal component + a small hook. Each of the three upload pages awaits a consent decision in `handleFile` before calling `uploadDocument`. Tested with a new minimal vitest setup (store logic) and a Playwright spec (the gate behavior).

**Tech Stack:** Next.js 14 / React / TypeScript, Playwright (existing), vitest (added — no JS unit runner exists today).

**Reference (read before starting):**
- Spec: `docs/superpowers/specs/2026-06-05-egress-consent-design.md` (§2 contract, §3 Track 1)
- `frontend/src/app/check/stem-opt/upload/page.tsx` — `handleFile` (l.112) calls `uploadDocument(checkId, file, slot.docType)` on file select. Same pattern in `check/entity/upload/page.tsx` and `check/student/upload/page.tsx`.
- `frontend/src/lib/api-v2.ts` — `uploadDocument(checkId, file, docType)` POSTs to `${API}/checks/${checkId}/documents`.
- Landing copy already staged (uncommitted) in `frontend/src/app/page.tsx` lines ~318, ~412, ~624.

**Consent contract (from spec §2):** key by `(egress_type, purpose)`. For the web check: `egress_type="web_doc_upload"`, `purpose="extraction"`, `destination="Guardian server + extraction AI"`, `data_categories=["the documents you upload"]`. Decisions: `once` | `session` | `always` | `deny`.

---

## Task 1: Consent store (`consent.ts`) with vitest

**Files:**
- Create: `frontend/src/lib/consent.ts`
- Create: `frontend/vitest.config.ts`
- Test: `frontend/src/lib/consent.test.ts`
- Modify: `frontend/package.json` (devDeps + `test:unit` script)

- [ ] **Step 1: Add vitest + script**

Run:
```bash
cd frontend && npm install -D vitest@^2.1.0 jsdom@^25.0.0
```
Then add to `frontend/package.json` `"scripts"` (after the `test:e2e` line):
```json
    "test:unit": "vitest run",
```

- [ ] **Step 2: Add vitest config**

Create `frontend/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
```

- [ ] **Step 3: Write the failing test**

Create `frontend/src/lib/consent.test.ts`:
```ts
import { beforeEach, describe, expect, it } from "vitest";
import { hasConsent, grant, revoke, _resetSessionForTest } from "./consent";

const KEY = { egressType: "web_doc_upload", purpose: "extraction" } as const;

beforeEach(() => {
  localStorage.clear();
  _resetSessionForTest();
});

describe("consent store", () => {
  it("has no consent initially", () => {
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(false);
  });

  it("once does not persist", () => {
    grant({ egressType: KEY.egressType, purpose: KEY.purpose, destination: "d", dataCategories: ["x"], scope: "once" });
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(false);
  });

  it("session persists in-memory but not in localStorage", () => {
    grant({ egressType: KEY.egressType, purpose: KEY.purpose, destination: "d", dataCategories: ["x"], scope: "session" });
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(true);
    expect(localStorage.getItem("guardian_consent")).toBeNull();
  });

  it("always persists in localStorage and survives a session reset", () => {
    grant({ egressType: KEY.egressType, purpose: KEY.purpose, destination: "d", dataCategories: ["x"], scope: "always" });
    _resetSessionForTest(); // simulate reload (memory cleared, localStorage kept)
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(true);
  });

  it("revoke clears an always grant", () => {
    grant({ egressType: KEY.egressType, purpose: KEY.purpose, destination: "d", dataCategories: ["x"], scope: "always" });
    revoke(KEY.egressType, KEY.purpose);
    expect(hasConsent(KEY.egressType, KEY.purpose)).toBe(false);
  });
});
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd frontend && npm run test:unit`
Expected: FAIL — `Cannot find module './consent'`.

- [ ] **Step 5: Implement `consent.ts`**

Create `frontend/src/lib/consent.ts`:
```ts
// Egress consent store. `always` → localStorage; `session` → in-memory; `once` → not stored.
// Keyed by `${egressType}:${purpose}`.

export type EgressType = "web_doc_upload" | "share_data_room";
export type ConsentScope = "once" | "session" | "always" | "deny";

export interface ConsentRecord {
  egressType: EgressType;
  purpose: string;
  destination: string;
  dataCategories: string[];
  scope: ConsentScope;
}

const STORE_KEY = "guardian_consent";
const sessionGrants = new Set<string>();

function k(egressType: string, purpose: string): string {
  return `${egressType}:${purpose}`;
}

function loadAlways(): Record<string, true> {
  if (typeof localStorage === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(STORE_KEY) || "{}");
  } catch {
    return {};
  }
}

export function hasConsent(egressType: string, purpose: string): boolean {
  if (sessionGrants.has(k(egressType, purpose))) return true;
  return loadAlways()[k(egressType, purpose)] === true;
}

export function grant(record: ConsentRecord): void {
  if (record.scope === "always") {
    const all = loadAlways();
    all[k(record.egressType, record.purpose)] = true;
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(all));
    } catch {
      sessionGrants.add(k(record.egressType, record.purpose)); // fallback: treat as session
    }
  } else if (record.scope === "session") {
    sessionGrants.add(k(record.egressType, record.purpose));
  }
  // "once" and "deny": nothing stored.
}

export function revoke(egressType: string, purpose: string): void {
  sessionGrants.delete(k(egressType, purpose));
  const all = loadAlways();
  delete all[k(egressType, purpose)];
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

// Test-only: clear in-memory session grants (simulates a page reload).
export function _resetSessionForTest(): void {
  sessionGrants.clear();
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npm run test:unit`
Expected: PASS (5 tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/consent.ts frontend/src/lib/consent.test.ts frontend/vitest.config.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(web-consent): consent store + vitest"
```

---

## Task 2: Consent modal component

**Files:**
- Create: `frontend/src/components/EgressConsentModal.tsx`
- Test: covered by the Playwright spec in Task 5 (presentational; no separate unit test).

- [ ] **Step 1: Implement the modal**

Create `frontend/src/components/EgressConsentModal.tsx`:
```tsx
"use client";
import type { ConsentScope } from "@/lib/consent";

export interface EgressConsentModalProps {
  open: boolean;
  destination: string;
  dataCategories: string[];
  onDecide: (scope: ConsentScope) => void;
}

export function EgressConsentModal({ open, destination, dataCategories, onDecide }: EgressConsentModalProps) {
  if (!open) return null;
  return (
    <div
      data-testid="egress-consent-modal"
      style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(13,20,36,0.45)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}
    >
      <div style={{ background: "#fff", borderRadius: 16, maxWidth: 440, width: "100%", padding: 28, boxShadow: "0 20px 60px rgba(13,20,36,0.25)" }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: "#0d1424" }}>Approve upload?</h3>
        <p style={{ fontSize: 14, color: "#556480", lineHeight: 1.6, marginBottom: 8 }}>
          Your {dataCategories.join(", ")} will be uploaded to <strong>{destination}</strong> to extract fields. Nothing is sent until you approve.
        </p>
        <p style={{ fontSize: 12.5, color: "#8e9ab5", lineHeight: 1.6, marginBottom: 20 }}>
          Prefer your documents never leave your device? Use the local Guardian extension.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <button data-testid="consent-always" onClick={() => onDecide("always")} style={btnPrimary}>Always allow</button>
          <button data-testid="consent-session" onClick={() => onDecide("session")} style={btn}>Allow for this session</button>
          <button data-testid="consent-once" onClick={() => onDecide("once")} style={btn}>Allow once</button>
          <button data-testid="consent-deny" onClick={() => onDecide("deny")} style={btnGhost}>Deny</button>
        </div>
      </div>
    </div>
  );
}

const btnBase: React.CSSProperties = { padding: "10px 16px", borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer", border: "1px solid rgba(91,141,238,0.2)" };
const btnPrimary: React.CSSProperties = { ...btnBase, background: "#5b8dee", color: "#fff", border: "none" };
const btn: React.CSSProperties = { ...btnBase, background: "rgba(91,141,238,0.06)", color: "#3a5a8c" };
const btnGhost: React.CSSProperties = { ...btnBase, background: "transparent", color: "#8e9ab5" };
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors from this file.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/EgressConsentModal.tsx
git commit -m "feat(web-consent): egress consent modal component"
```

---

## Task 3: `useEgressConsent` hook

**Files:**
- Create: `frontend/src/lib/useEgressConsent.tsx`
- Test: exercised via Task 5 Playwright spec.

- [ ] **Step 1: Implement the hook**

Create `frontend/src/lib/useEgressConsent.tsx`:
```tsx
"use client";
import { useCallback, useRef, useState } from "react";
import { EgressConsentModal } from "@/components/EgressConsentModal";
import { grant, hasConsent, type ConsentScope, type EgressType } from "@/lib/consent";

interface Args {
  egressType: EgressType;
  purpose: string;
  destination: string;
  dataCategories: string[];
}

// Returns `ensure()` — resolves true if upload may proceed (consent already held
// or just granted), false if denied — plus the modal element to render.
export function useEgressConsent({ egressType, purpose, destination, dataCategories }: Args) {
  const [open, setOpen] = useState(false);
  const resolver = useRef<((ok: boolean) => void) | null>(null);

  const ensure = useCallback((): Promise<boolean> => {
    if (hasConsent(egressType, purpose)) return Promise.resolve(true);
    setOpen(true);
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
    });
  }, [egressType, purpose]);

  const onDecide = useCallback((scope: ConsentScope) => {
    setOpen(false);
    if (scope !== "deny") grant({ egressType, purpose, destination, dataCategories, scope });
    resolver.current?.(scope !== "deny");
    resolver.current = null;
  }, [egressType, purpose, destination, dataCategories]);

  const modal = (
    <EgressConsentModal open={open} destination={destination} dataCategories={dataCategories} onDecide={onDecide} />
  );

  return { ensure, modal };
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/useEgressConsent.tsx
git commit -m "feat(web-consent): useEgressConsent hook"
```

---

## Task 4: Gate the three upload pages

**Files:**
- Modify: `frontend/src/app/check/stem-opt/upload/page.tsx`
- Modify: `frontend/src/app/check/entity/upload/page.tsx`
- Modify: `frontend/src/app/check/student/upload/page.tsx`

Do the **same three edits** in each of the three files.

- [ ] **Step 1: Import the hook** (add near the other `@/lib` imports at the top of each file)

```tsx
import { useEgressConsent } from "@/lib/useEgressConsent";
```

- [ ] **Step 2: Instantiate the hook** (inside the component, near the top with the other hooks)

```tsx
  const consent = useEgressConsent({
    egressType: "web_doc_upload",
    purpose: "extraction",
    destination: "Guardian's server",
    dataCategories: ["documents"],
  });
```

- [ ] **Step 3: Gate `handleFile`** — add the guard as the first line inside `handleFile`, before any `setSlots`/`uploadDocument`:

```tsx
  const handleFile = useCallback(async (index: number, file: File) => {
    if (!(await consent.ensure())) return; // <-- gate: no upload without approval
    const slot = slots[index];
    setError(null);
    // ...unchanged below...
```
Update the `useCallback` dependency array for `handleFile` to include `consent` (append `consent` to the existing deps).

- [ ] **Step 4: Render the modal** — add `{consent.modal}` just inside the top-level returned JSX fragment of each page (e.g. right after the opening `<>` or root `<div>`).

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/check/stem-opt/upload/page.tsx frontend/src/app/check/entity/upload/page.tsx frontend/src/app/check/student/upload/page.tsx
git commit -m "feat(web-consent): gate uploads on all three check pages"
```

---

## Task 5: Playwright gate spec

**Files:**
- Create: `frontend/tests/consent/upload-gate.spec.ts`

- [ ] **Step 1: Write the spec** — assert no POST to `.../documents` before consent, and one after "Allow once".

Create `frontend/tests/consent/upload-gate.spec.ts`:
```ts
import { test, expect } from "@playwright/test";

// Drives the stem-opt upload page; stubs the API so no real backend is needed.
test("no document upload fires until the user approves", async ({ page }) => {
  const uploadCalls: string[] = [];

  // Stub check creation + fetch so the page reaches the upload UI.
  await page.route("**/api/checks/**", async (route) => {
    const url = route.request().url();
    if (/\/documents$/.test(url) && route.request().method() === "POST") {
      uploadCalls.push(url);
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "test-check", track: "stem_opt", documents: [] }) });
  });

  await page.goto("/check/stem-opt/upload?check=test-check");

  // Select a file into the first slot.
  const input = page.getByTestId(/stem-upload-input-/).first();
  await input.setInputFiles({ name: "i20.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 test") });

  // The consent modal must appear, and NO upload may have fired yet.
  await expect(page.getByTestId("egress-consent-modal")).toBeVisible();
  expect(uploadCalls).toHaveLength(0);

  // Approve once → exactly one upload fires.
  await page.getByTestId("consent-once").click();
  await expect.poll(() => uploadCalls.length).toBe(1);
});
```

- [ ] **Step 2: Run the spec**

Run: `cd frontend && npx playwright test tests/consent/upload-gate.spec.ts`
Expected: PASS. (If the page requires a running dev server, start `npm run dev` in another shell first, or rely on the existing `playwright.config.ts` webServer block; confirm the base URL resolves `/check/stem-opt/upload`.)

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/consent/upload-gate.spec.ts
git commit -m "test(web-consent): playwright gate spec"
```

---

## Task 6: Commit the staged landing copy + final check

**Files:**
- Modify (already staged, uncommitted): `frontend/src/app/page.tsx` (hero l.318, step-06 l.412, footer l.624)

- [ ] **Step 1: Verify the staged copy** is the approval-gated wording.

Run: `cd /Users/lichenyu/compliance-os && git diff frontend/src/app/page.tsx | grep -E "never leave your computer before you approve|never shared without your approval"`
Expected: shows the three changed lines.

- [ ] **Step 2: Production build sanity**

Run: `cd frontend && npm run build`
Expected: build succeeds (the gate + copy compile).

- [ ] **Step 3: Commit the copy**

```bash
git add frontend/src/app/page.tsx
git commit -m "landing: approval-gated privacy copy (ships with the web consent gate)"
```

- [ ] **Step 4: Full unit + typecheck sweep**

Run: `cd frontend && npm run test:unit && npx tsc --noEmit`
Expected: unit tests PASS, no type errors.

**Deploy note:** This plan's changes go live only via the Fly deploy (currently blocked on the Docker/network environment). The landing copy promise becomes true exactly when this gate ships — deploy them together, never the copy alone.

---

## Self-Review Notes

**Spec coverage (§3):** consent store (Task 1) ✅; modal with the four decisions + destination/categories (Task 2) ✅; gate before `uploadDocument` on every web upload surface — the three check pages, corrected from the spec's "four" which conflated the MCP `batch_upload` (Task 4) ✅; landing copy ships with the gate (Task 6) ✅; tests: no upload pre-consent + scope persistence (Tasks 1, 5) ✅.

**Type consistency:** `ConsentRecord {egressType, purpose, destination, dataCategories, scope}`, `EgressType`, `ConsentScope` defined in Task 1 and used identically in Tasks 2–4. `hasConsent(egressType, purpose)`, `grant(record)`, `revoke(egressType, purpose)` consistent throughout. Hook returns `{ensure, modal}`; pages call `await consent.ensure()` and render `{consent.modal}`.

**Known risks:** the Playwright spec assumes the upload page is reachable with a stubbed `/api/checks/**`; if the page's check-bootstrap differs, adjust the stub. vitest is a new devDep — if the team prefers no new runner, the store can instead be covered only by the Playwright flow, but unit tests are cleaner for the scope/persistence logic.
