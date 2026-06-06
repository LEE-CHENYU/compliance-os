# Explicit Egress Consent — Design

**Date:** 2026-06-05
**Status:** Approved (brainstorming), pending spec review
**Goal:** No user data leaves the device/browser without an explicit, informed grant — and expose a consent-gated path for uploading the local SoT + documents to Guardian cloud, so future services (e.g. lawyer-matching with case context) can build on it.

---

## 1. Problem & current reality (verified)

A compliance product handling immigration/tax documents must never move user data off-device silently. Today:

| Surface | Today | Verified at |
|---|---|---|
| **A. Hosted web check** | File upload fires on `onChange` → POST to Fly server → document content sent to extraction LLM (OpenAI/Anthropic). **No consent.** | `frontend/src/app/check/*/upload/page.tsx` (`handleFile`→`uploadDocument`), `web/routers/extraction.py` ("Document upload, LLM extraction") |
| **B. `guardian_ask` (extension/local)** | Already returns `local_ask_grounding` (facts + chunks, **no model**); external LLM only in hosted mode. **No egress.** | `mcp_server.py` `guardian_ask` local-mode branch; `local_engine.local_ask_grounding` |
| **C. professional-search** | `build_search_plan` returns generic persona **prompts** for the user's Claude to web-search. **No network call from our code; no SoT embedded.** | `professional_search/personas.py` (only local SQLite `.fetchone()`; no `requests`/`httpx`; `build_search_plan` reads no `user_facts`) |
| Migration export | `export_user_data` builds a local zip the user downloads. **No auto-upload.** | `migration.py` |

**Conclusion:** the extension currently has **no** code path that sends the SoT/documents off-device. The only silent upload is **(A)**. We will (1) gate (A), and (2) **deliberately add** a consent-gated SoT/document egress path for future services.

---

## 2. Shared consent contract

Both runtimes honor one contract (a shared *semantics*, implemented per-runtime — a single code path can't span browser TS and extension Python).

```
ConsentRecord {
  egress_type:     "web_doc_upload" | "share_data_room"
  purpose:         string   # web: "extraction"; share: a named service, e.g. "lawyer-matching"
  destination:     string   # "guardian_server" | "extraction_llm" | "guardian_cloud"
  data_categories: string[] # e.g. ["raw_documents"] or ["sot_facts","documents"]
  scope:           "once" | "session" | "always"
  granted_at:      ISO-8601
}
```

**Decision set (agent-permission model, per the user's ask):** `Allow once` / `Allow this session` / `Always allow` / `Deny`.

**Granularity:** consent is keyed by **`purpose`**. "Always allow" grants exactly that purpose; a new purpose re-prompts. `scope: always` is persisted and revocable; `session` lives for the runtime/session lifetime; `once` is not stored.

---

## 3. Track 1 — Web consent gate (A) + landing copy

**Scope:** the hosted web check only. Ships via the Fly deploy (currently blocked on local Docker / network — see §7).

**Components:**
- `frontend/src/lib/consent.ts` — consent store over `localStorage` (key `guardian_consent`): `hasConsent(egress_type, purpose)`, `grant(record)`, `revoke(purpose)`. `session` grants held in an in-memory module variable; `always` in localStorage; `once` never stored.
- `frontend/src/components/EgressConsentModal.tsx` — modal stating **destination** (Guardian server + extraction AI) and **data categories** (the documents you're about to upload), with the four decision buttons. Returns the chosen scope or `deny`.
- **Gate point:** in each upload page's `handleFile`, before `uploadDocument(...)`: if no `always`/`session` grant for `("web_doc_upload","extraction")`, open the modal; proceed only on a non-deny choice; record the grant per scope. Applies to all four surfaces: `check/stem-opt/upload`, `check/entity/upload`, `check/student/upload`, and the batch upload path.

**Landing copy (already staged in `page.tsx`, deploys with this track):**
- Hero (l.318): "Your documents never leave your computer before you approve it — and with the local extension, never at all."
- How-it-works step 06 (l.412): "…kept in your data room, never shared without your approval…"
- Footer (l.624): "Local-first by design — your documents never leave your computer before you approve it."

These promises become **true** only once the gate exists, so copy + gate ship in the **same deploy**, never before.

---

## 4. Track 2 — Extension SoT egress path + consent primitive (PyPI 2.0.2)

**Scope:** the local extension. Ships as a `compliance-os` 2.0.2 release (built + uploaded + `.dxt` re-pinned, same flow as 2.0.1).

### 4.1 Consent store + management (extension)
- `compliance_os/consent.py` — `~/.guardian/consent.json` store:
  - `has_consent(purpose) -> bool` (true only for a persisted `always` grant or an in-process `session` grant).
  - `record_consent(purpose, scope, *, destination, data_categories)` — writes `always` to disk; keeps `session` in a module-level set; `once` not stored.
  - `revoke_consent(purpose)` / `list_consents() -> list`.
- MCP tools: `list_egress_consents()` and `revoke_egress_consent(purpose)` for visible, revocable management (the Cursor/Claude-Code feel).

### 4.2 The egress tool
- `share_data_room(purpose: str, confirm: bool = False, remember: str = "once") -> str` (local-mode only; `destructiveHint=False`, `readOnlyHint=False`):
  1. If `has_consent(purpose)` → proceed.
  2. Elif `not confirm` → return a structured **consent request**: what (`sot_facts` + N documents), where (`guardian_cloud`, the `POST /api/context/share` endpoint), why (`purpose`), and the instruction: "re-call with `confirm=True` and `remember` = `once`|`session`|`always`, or decline." (The user's Claude surfaces this; the user decides.)
  3. Elif `confirm` → `record_consent(purpose, remember, ...)`, build payload via **`export_user_data`** (reused), `POST /api/context/share` with the license token, return the server's reference id + a human summary.
- Deny path: the user simply doesn't re-call; nothing is sent. No partial upload.

### 4.3 guardian_ask regression (B)
- Test that `guardian_ask` in local mode calls `local_ask_grounding` and makes **zero** external-LLM calls (assert no `chat_completion`/provider invocation). Locks in the existing behavior so a refactor can't silently reintroduce egress.

### 4.4 professional-search transparency note
- Append one line to `build_search_plan`'s returned output / the `lawyer_search_plan` tool result: "Claude will search the web using generic persona queries; your personal facts are not included." No consent gate (it doesn't egress user data), just honest disclosure of what running the plan does.

### 4.5 Server endpoint
- `POST /api/context/share` in a new `web/routers/context.py`:
  - Auth: existing license/token (`decode_token` → user), same as other authed routes.
  - Body: multipart zip (the `export_user_data` output) + `purpose` form field.
  - Stores under `DATA_DIR/shared_context/<user_id>/<purpose>-<timestamp>.zip`; records a `SharedContextRow {id, user_id, purpose, path, created_at}` so future services can find it.
  - Returns `{reference_id, purpose, stored_at}`.
- **Security:** access is token-gated and per-user. Application-level encryption-at-rest of the stored blob is a recommended hardening; v1 stores on the access-controlled server volume and **defers** at-rest encryption to a follow-up task (called out, not silently skipped).

---

## 5. Data flow (SoT egress)

```
User → "share my case for lawyer-matching"
  → Claude calls share_data_room("lawyer-matching")
    → has_consent? no
    → returns ConsentRequest (what/where/why)
  → Claude shows it; user picks "Always allow"
  → Claude calls share_data_room("lawyer-matching", confirm=True, remember="always")
    → record_consent(...always...)
    → export_user_data(db, user_id)  →  zip bytes
    → POST /api/context/share (token, purpose)
    → server stores + SharedContextRow
    → returns reference_id
  → Claude confirms to user
Future: a lawyer-matching service reads SharedContextRow for the user.
```

Nothing leaves until step "confirm=True". A prior `always` grant for that purpose skips the prompt; a different purpose re-prompts.

---

## 6. Error handling & edges

- **Deny / no re-call:** action aborts; clear "not shared — you didn't approve" message; zero bytes sent.
- **Revoke:** `revoke_egress_consent(purpose)` removes the `always` grant; the next `share_data_room(purpose)` re-prompts.
- **Offline extension:** `export_user_data` still builds locally; the upload step reports it needs a connection. Consent itself is local (no network to check).
- **Web:** localStorage unavailable → fall back to per-action confirm (treat as `once`).
- **Idempotency:** re-sharing the same purpose creates a new timestamped blob (latest wins for a service); no overwrite races.

---

## 7. Testing

- **Consent store (extension):** grant/deny/session/always/revoke; `always` persists across a reload, `session` does not, `once` never persists.
- **`share_data_room`:** no-consent → returns a consent request and sends nothing; `confirm=True` → exactly one `POST /api/context/share` with the export bytes; existing `always` grant → proceeds without a request.
- **guardian_ask (B):** local mode makes zero external-LLM calls (grounding only).
- **Server:** `POST /api/context/share` stores the blob + row, is token-gated (401 without a valid token), and is scoped per-user.
- **Web (A):** no `uploadDocument` fires before a grant; each scope behaves (once re-prompts next file in a fresh session, session does not, always persists); all four upload surfaces gated.

---

## 8. Decomposition, sequencing & delivery

Two **independent** implementation plans (different ship channels, independently testable; they share only the §2 contract):

1. **Plan A — Web consent gate + landing copy.** Delivered by the Fly deploy. Blocker: the deploy is currently stuck (local Docker daemon wedged on a GUI prompt; Fly remote builder times out uploading the image over the current network). Resolve the deploy environment, then this plan + the already-staged copy + the already-built 2.0.1 `.dxt` go out together.
2. **Plan B — Extension SoT egress path + consent primitive + server endpoint.** Delivered as `compliance-os` **2.0.2** (build → twine upload → re-pin `.dxt` → deploy). Includes the server endpoint (also reaches prod via the same deploy).

Recommended order: **Plan A first** (resolves the live false-copy risk and is the only *current* silent egress), then **Plan B** (forward-looking infrastructure).

---

## 9. Out of scope (explicit)

- The actual lawyer-matching (or any) service that *consumes* the shared context — a later spec. We build the **path + storage + consent**, not the consumer.
- Cloud sync / multi-device of the SoT.
- Application-level encryption-at-rest of the shared blob (recommended hardening; deferred with a note, not silently dropped).
- A consent gate on professional-search (it does not egress user data from our code; instead we add a one-line transparency note in its plan output: "Claude will search the web using generic queries; your personal facts are not included").
