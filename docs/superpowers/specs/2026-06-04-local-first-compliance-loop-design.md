# Local-First Compliance Loop: Zero-Marginal-Cost Privacy Architecture

**Date:** 2026-06-04
**Status:** Draft — pending user review
**Author:** Cheney Li + Claude
**Related:**
- `compliance_os/mcp_server.py` (the extension / tool surface — currently a thin HTTP client to the hosted API)
- `compliance_os/web/services/*` (extraction, retrieval, model routing — the engine to be made transport-agnostic)
- `compliance_os/facts/extraction_map.py`, `compliance_os/facts/vocabulary.py` (the deterministic facts SoT mapping)
- `compliance_os/web/models/auth.py` (existing `subscriptions` table + `is_pro()` entitlement to reuse)
- `compliance_os/settings.py` (`GUARDIAN_HOME` / `~/.guardian` on-device state dir)
- `frontend/public/guardian.dxt` + `compliance_os/mcp_install.py` (existing distribution rail)

---

## Overview

Re-architect Guardian so the **entire compliance loop — document extraction, source-of-truth (SoT) formation, retrieval/chat, rules, and tools — runs locally on the user's machine at $0 marginal cost to us**, eliminating the privacy concern that currently blocks adoption (a user's immigration/tax documents leave their device and hit our servers).

The mechanism: **move the LLM reasoning out of our backend and into the user's own Claude.** The MCP extension becomes a set of **deterministic local primitives** (parse text, classify, embed, store, retrieve, run rules, fill forms, read/write facts). The user's Claude — which they already pay for — supplies all the intelligence by orchestrating those primitives. Nothing about a user's documents touches Guardian servers.

We retain **control over the extension via a Guardian-issued license key**: no valid key → the extension does nothing. The key gates activation and (later) paid tiers, reusing the `subscriptions`/`is_pro()` entitlement infrastructure that already exists.

This is a **distribution-first** move: ship a maximally useful, free, private product to drive adoption; monetize later via a server-reserved deliverable, with the entitlement hooks already in place so no client re-ship is needed.

### Strategic framing

- **Distribute first, profit later.** The free local loop has no per-user cost, so we can give it away to maximize reach. Monetization is a *licensing lever*, decoupled from compute cost.
- **Privacy is the wedge.** "Your immigration and tax documents never leave your computer" is a concrete, defensible claim most competitors can't make. Lead the relaunch with it.

---

## Goals

- **$0 marginal cost per user** for the full loop (extraction, SoT, retrieval/chat, rules, forms, professional-search, Gmail).
- **No user document data leaves the device** through Guardian. The only outbound Guardian call is a license check carrying the key + extension version — no personal data.
- **Frontier-quality extraction** by using the user's own Claude as the reasoning engine (better than a bundled local model).
- **Control over the extension**: a Guardian license key is required to operate; we can flip any user active/inactive and gate features server-side.
- **One shared engine** behind both the hosted trial app and the local extension, so they never diverge.
- **Graceful degradation** across MCP hosts (Claude Desktop, Claude Code, Codex, others) and capability levels.

## Non-Goals

- **No bundled local LLM** (Ollama/llama.cpp). Rejected: heavy install, mediocre extraction, support burden. The user's Claude is the brain.
- **No payment/paywall implementation in this phase.** We build the entitlement *hook* (so we can flip later); we do not build checkout flows now (YAGNI).
- **No Guardian-owned Gmail OAuth** on the free critical path (it would trigger Google's restricted-scope CASA verification). Deferred to a possible Pro/server feature.
- **No hard DRM.** Client-side gating is acknowledged as *soft*; hard monetization is handled by a server-reserved deliverable, not by trying to make local code un-bypassable.

---

## The Local / Cloud Boundary

**Principle:** the MCP extension is a self-contained local engine doing only deterministic work in-process; the user's Claude is the reasoning layer; the server shrinks to a license endpoint plus one reserved paid deliverable.

| Step | Where it runs | Mechanism | Status |
|------|---------------|-----------|--------|
| Document text extraction | local, in-process | PyMuPDF / python-docx | ✅ already local (`parse_document`) |
| Classification | local, in-process | regex/pattern matcher, 40+ types | ✅ already local (`classify_document`) |
| Fact extraction (text → structured facts) | **user's Claude** | reads parsed text + schema → `record_extracted_facts` | 🔨 re-home from backend LLM |
| Scanned PDFs / images (no text layer) | **user's Claude** | multimodal vision reads the page image | 🔨 new path, no OCR dependency |
| Facts SoT (source of truth) | local, in-process | SQLite under `~/.guardian` | 🔨 de-couple from hosted API |
| Embeddings + vector store | local, in-process | fastembed `bge-small` + ChromaDB | ✅ already local-capable |
| Retrieval / chat grounding | local retrieval + **user's Claude answers** | `query_documents` returns chunks; Claude composes | 🔨 retrieval stays, answer moves to Claude |
| Rules, deadlines, risks, form-fill (8843, etc.) | local, in-process | deterministic config/rules | ✅ already local logic |
| Professional-search | **user's Claude + its web search** | tool ships persona/rubric/diligence scaffolding | 🔨 re-home; optional cloud fallback (paid) |
| Gmail (intake + act) | user's own connector/plugin/OAuth | detected ambient capability | ✅ never Guardian's cost |
| License / entitlements check | tiny Guardian endpoint | `POST /api/license/validate` | 🔨 new (small) |
| Stripe + reserved server-side paid deliverable | server | only when charging | ✅ Stripe exists |

**Net marginal cost per user ≈ $0.** The server is a license-validate endpoint plus the (already-built) Stripe webhooks, plus one optional reserved paid deliverable.

---

## Architecture: One Engine, Two Transports

Today the MCP tools call the hosted backend over HTTP (`_api_get` / `_api_post`, gated by `_is_hosted()` / `_resolve_token()` in `mcp_server.py`), so storage + reasoning live on the server. Approach A makes the tools run against on-device storage, in-process, with no network.

**Shared service facade (the backbone):** extract the logic in `compliance_os/web/services/*` into a transport-agnostic **service layer** that both surfaces call:

- the **hosted trial web app** wraps the facade in HTTP (the Approach-C funnel tier), and
- the **MCP extension** calls the facade **directly via Python imports** — no localhost server, no HTTP hop.

One engine, two transports → the trial app and the local extension never drift.

**Mode switch:** `GUARDIAN_MODE=local|hosted`.
- `local` (extension default): embeddings force the local provider; the service facade is called in-process; data path uses local SQLite with no auth (single local user).
- `hosted` (trial app): current behavior — cloud LLM, server storage.

### On-device layout

Under `GUARDIAN_HOME` (already resolves to `~/.guardian` in `settings.py`):

- `uploads/` — raw documents *(exists)*
- `chroma_db/` — local vector store *(exists)*
- `guardian.db` — SQLite: facts SoT, document metadata, deadlines/risks cache (precedent: `diligence.db` + `sessionmaker` in `tables_v2`)
- `license.json` — cached entitlements (see License Control Plane)
- `gmail_token.json` — only if a Guardian-owned Gmail path is ever enabled (not in v1)

---

## Extraction-Loop Redesign

**The core idea — division of labor:** split each step into *perception* (reading values out of a document → needs intelligence → the user's Claude) vs *bookkeeping* (mapping, provenance, supersession, conflict detection → deterministic → the local engine). Claude reads; the engine records and reconciles. Neither side needs a model on our payroll.

### Unchanged (already local)

`parse_document` (text), `classify_document` (regex doc-type), `get_user_facts`, `set_user_fact` (user-*locked* facts), `resolve_fact_conflict`. The deterministic mapping pieces — `EXTRACTION_TO_FACT_KEY`, `CANONICAL_FACTS`, supersession, conflict detection — move in-process, unchanged.

### New / changed tools

| Tool | Type | Contract |
|------|------|----------|
| `get_extraction_schema(doc_type)` | **new**, deterministic | Returns the target fields for a doc type, by reverse-filtering `EXTRACTION_TO_FACT_KEY` + `CANONICAL_FACTS`: `[{source_field, fact_key, label, shape}]`. Tells Claude exactly what to look for, with human labels and value shapes. Zero model. v1 returns the SoT-tracked fields per doc type; extending to each doc type's full raw field list is a later enhancement. |
| `upload_document(file_path, doc_type)` | **changed** | Now **local-only**: store file in `~/.guardian/uploads`, register metadata + a `doc_id` in local SQLite, index into ChromaDB. **No server extraction.** Returns `{doc_id, doc_type}`. |
| `record_extracted_facts(doc_id, facts[])` | **new** | Claude submits what it read: `[{fact_key, value, source_field, confidence}]`. Engine writes `user_facts` rows with **provenance = doc_id**, runs deterministic supersession + conflict detection, returns any `detected_conflicts` for Claude to surface. This is exactly what `_upsert_extracted_field` does today — driven by Claude's read instead of the server LLM. |

**Critical boundary:** `record_extracted_facts` is **distinct from `set_user_fact`**. Document-sourced facts carry provenance and are subject to supersession; `set_user_fact` stays reserved for user-*locked* decisions ("my salary is $135K now"). Claude's reads must not masquerade as user-locked truth.

### The end-to-end local loop (orchestrated by the user's Claude)

```
parse_document ─▶ classify_document ─▶ get_extraction_schema
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
        (Claude reads values from text + schema)   ◀── the only "intelligence" step
                       ▼
        upload_document (store + index, get doc_id)
                       ▼
        record_extracted_facts(doc_id, facts)
                       ▼
        engine runs supersession + conflict detection
                       ▼
        conflicts? ─▶ Claude surfaces ─▶ resolve_fact_conflict
```

### Chat redesign — same split

Today `guardian_ask` proxies to the server's RAG+LLM. New behavior:
- `query_documents` does **local retrieval only** (local embeddings + ChromaDB → ranked chunks with citations).
- The user's **Claude composes the grounded answer** from those chunks + `get_user_facts`.
- `guardian_ask` is kept as a thin convenience that **bundles grounding** (relevant chunks + relevant facts in one call) but **calls no model** — "ask" becomes "gather grounding," not "answer."

### Edge cases designed for now

- **Scanned PDFs / images (no text layer):** `parse_document` returns a signal ("no text layer — read the image at `<path>`"); the user's Claude reads the page image directly via vision. No server OCR dependency.
- **Low-confidence / unmapped fields:** Claude passes `confidence`; the engine stores low-confidence facts flagged `needs_review`. Values outside the schema use `custom:<slug>` (already supported).

---

## License / Entitlements Control Plane

Reuses existing infrastructure: the `subscriptions` table mirroring Stripe, the derived `tier` (`pro_trial`/`pro`), and `is_pro()` in `auth.py`. The MCP config already has a token slot.

### The key

A Guardian-issued, long-lived license key (e.g. `gdn_live_…`), bound to the user's account, issued at web signup. The user pastes it **once** into the MCP config as `GUARDIAN_LICENSE_KEY` (a new slot, distinct from the old per-request JWT — in local mode the data path is local SQLite with no auth, so the key's only job is activation + entitlements). **No valid key → the extension does nothing.**

### The one server touchpoint

`POST /api/license/validate { license_key, ext_version }` → looks up the key → user → reads existing `subscriptions`/`is_pro()` state → returns:

```json
{ "valid": true, "status": "active", "tier": "free",
  "features": ["extraction", "chat", "prof_search", "gmail_draft"],
  "grace_until": "2026-06-18T00:00:00Z", "message": null }
```

Read-only, tiny, carries **no user data** — only the key + extension version go out. This is the entire server surface for the free product (plus the existing Stripe webhooks).

### Validation cadence + offline grace

Validate on startup and every ~24h; cache entitlements in `~/.guardian/license.json` with a `grace_until` (default 7 days); background-refresh when online.

| State | Condition | Tool behavior |
|-------|-----------|---------------|
| `unconfigured` | no key | "Configure your Guardian license key to activate." |
| `active` | valid, fresh | runs normally |
| `grace` | offline, within `grace_until`, last-known-good | runs normally (offline-first privacy) |
| `expired_offline` | offline past grace | "Reconnect to reactivate (offline grace expired)." |
| `inactive` / `revoked` | server says so | "Your Guardian license is inactive — reactivate at `<url>`." |

Flipping a user active↔inactive server-side takes effect within a day (or instantly on next launch), while a traveler offline for a week still works.

### Two enforcement levels (decorators on the MCP tools)

- `@requires_activation` — global gate on every tool (the active/inactive switch).
- `@requires_feature("prof_search")` — per-tool gate read from `entitlements.features`. **Ship the free tier with all features on** (distribute-first); later, flipping a feature to `requires: pro` is a **server-side change in the validate response — no client re-ship.**

Both return a **structured `activation_required` message, not an exception**, so the user's Claude relays it conversationally instead of erroring.

### The soft-gate rule (design constraint)

Because the loop runs locally and the client is inspectable, the gate is **soft** — a determined user can patch it out. That is acceptable for a generous free tier. The **hard** monetization lever is a **server-side deliverable** held in reserve (cloud prof-search report / data-room sync / verified-Gmail auto-pull).

> **Rule:** anything we ever want to *hard*-gate must keep a server-side component; everything client-only is soft-gated and belongs in the free tier.

### Privacy invariant

The validate call transmits only the license key + extension version. No documents, facts, email, or query text ever leave the device through Guardian. Any usage telemetry is separate, anonymous, and opt-in — never bundled into validation.

---

## Gmail as a Detected Ambient Capability

Gmail availability is determined by **what connector/plugin is enabled**, not by the host. Guardian ships **no Gmail OAuth of its own** in v1 and probes for an available Gmail capability at startup, orchestrating through whatever is present.

| Capability source | Available on | Read / draft | Attachments / send |
|---|---|:---:|:---:|
| claude.ai Gmail connector (`mcp__claude_ai_Gmail__*`) | Claude Code, Desktop, web (signed-in Claude account + connector on) | ✅ `search_threads`, `get_thread`, `create_draft`, full label CRUD | ❌ |
| Gmail MCP plugin (user-installed) | any MCP host that loads it | ✅ | ✅ (its own OAuth) |
| none enabled | any host | — | — → **file-drop fallback** |

**"Useful" = wiring Gmail into the loop**, not just exposing tools:

- **Intake:** "scan my inbox for immigration/tax mail" → find USCIS notices (I-797, RFE), employer letters, tax forms → read text via the connector → into the extraction loop → facts SoT / data room. The inbox becomes a document feed (the "continuous compliance" vision).
- **Act:** draft RFE responses, attorney/employer emails, reminders — grounded in local facts; the user reviews and sends in Gmail (safer than auto-send, and sidesteps the send scope entirely).
- **Triage:** the connector's full label CRUD lets Guardian mark `Guardian/processed` / `Guardian/needs-action` on the user's own account.

**Attachment gap:** the claude.ai connector exposes no attachment-byte download or programmatic send. v1 handles attachments via **watched-folder / manual drop** plus **Claude's Drive connector** (`Google_Drive__download_file_content`) when the doc is in Drive. For users who want attachment auto-pull, recommend a **Gmail MCP plugin** rather than Guardian taking on Google's restricted-scope CASA verification (tradeoff: a third-party dependency we vet). A Guardian-owned verified Gmail OAuth, if ever built, is a Pro/server-reserved feature.

**Gmail is $0 to us in every case** — always the user's connector/plugin/OAuth, never Guardian's.

---

## Packaging, Distribution & Migration

The distribution rail already exists: `guardian.dxt` (v1.0.6) installs into Claude Desktop via `uv`; `mcp_install.py` configures Claude Desktop / Claude Code / Codex. Approach A is largely a **manifest + mode flip**.

### Manifest changes (`guardian.dxt` → v2.0.0)

User-config shrinks from three fields to one — a major onboarding win:

| Today | Approach A |
|-------|-----------|
| `token` (`gdn_oc_…`, required) | `license_key` (`gdn_live_…`, required) |
| `api_url` (defaults to hosted) | dropped from default (advanced/hidden field kept for hosted-trial fallback) |
| `openai_api_key` (required) | **dropped** — local `bge-small` embeddings, no key |
| — | `GUARDIAN_MODE=local` env |

Entire user setup becomes: **install the .dxt, paste one license key, done.**

### First-run weight

`uv run` resolves engine deps (`chromadb`, `fastembed`, `pymupdf`); `fastembed` downloads the `bge-small` ONNX model (~130 MB) on first embed. Already handled gracefully — `mcp_server.py` has `_prewarm_embedding_model_bg()` and an "embeddings still downloading" status path; non-search tools work immediately. Communicate the one-time ~130 MB download in onboarding.

### Two surfaces, one engine (the funnel)

- **Hosted trial app** (current Fly deploy) stays as the zero-setup "try it" tier — cloud LLM, the small cost we knowingly accept for trial conversion.
- **Local extension** (.dxt) is the privacy/power tier — $0 to us.
- Same `compliance_os` engine behind both (the service facade) → no drift.

### Migration for existing cloud users

Provide a one-time **hosted export → local import**: an export endpoint zips the user's data room + facts SoT; `guardian-mcp import <export.zip>` lands it in `~/.guardian`. New users start local.

---

## Host Capability Matrix

| Host | Local engine | Gmail (if connector/plugin enabled) | Notes |
|------|:---:|:---:|------|
| Claude Desktop | ✅ | ✅ connector or plugin | full experience |
| Claude Code | ✅ | ✅ connector or plugin | connectors surface here when signed in with a Claude account |
| Codex / other MCP | ✅ | ⚠️ plugin only | degrade to file-drop if no Gmail capability |
| any host, no Gmail enabled | ✅ | ❌ → file-drop | loop still runs fully |

Degrade, never break: the compliance loop runs on any MCP host; Gmail is an additive capability.

---

## Testing Strategy

- **Deterministic engine** (parse, classify, map, store, index, supersede, detect conflicts, rules, forms): unit + integration tests. Straightforward.
- **Claude-as-brain contracts** (not ours to test, but their interfaces are): fixture-based tests feed golden documents → assert `get_extraction_schema` returns the right targets → feed a simulated extraction → assert `record_extracted_facts` produces the correct SoT rows, supersession, and conflict flags. Seed an eval harness from existing `dev_dataset/` and `sample_data/`.
- **License/activation state machine:** unit tests for each state → expected tool behavior; offline-grace expiry; revoked-key lockout.
- **Mode parity:** the service facade is exercised through both transports (in-process and HTTP) to prove the trial app and the extension behave identically.

---

## Cost Model Summary

| Component | Cost to Guardian |
|-----------|------------------|
| Extraction, chat, prof-search reasoning | $0 (user's Claude) |
| Embeddings + vector store | $0 (local) |
| Facts SoT, rules, forms, retrieval | $0 (local) |
| Gmail | $0 (user's connector/plugin/OAuth) |
| License validate endpoint | ~$0 (tiny, read-only) |
| Stripe + reserved paid deliverable | only when charging |

**Per-user marginal cost ≈ $0.** Monetization is a licensing lever, not cost recovery.

---

## Open Questions / Decisions Deferred

1. **Validate endpoint hosting** — a FastAPI route on the existing app vs a separate lightweight worker. Default: a route on the existing app (near-zero cost) unless load justifies splitting.
2. **Grace window length** — 7 days proposed; tune after observing real offline patterns. Server-controlled via `grace_until`.
3. **First reserved paid deliverable** — which of {cloud prof-search report, data-room sync, verified-Gmail auto-pull} ships first as the hard-gated Pro feature. Not built this phase; named so the soft-gate rule has a target.
4. **`get_extraction_schema` depth** — v1 returns SoT-tracked fields only; decide when to extend to full per-doc-type raw schemas.
5. **Telemetry** — whether to ship opt-in anonymous usage counts alongside (never inside) the validate call.

---

## Build Sequence (high level — detailed plan to follow)

1. **Service facade** — extract `compliance_os/web/services/*` into a transport-agnostic engine; prove parity through both transports.
2. **In-process local mode** — `GUARDIAN_MODE=local`; `~/.guardian/guardian.db` SoT; route `_api_*` to in-process facade; force local embeddings.
3. **Extraction-loop re-home** — `get_extraction_schema`, local-only `upload_document`, `record_extracted_facts`; chat → retrieval + Claude answers; scanned-image vision path.
4. **License control plane** — `/api/license/validate`, `license.json` cache, state machine, `@requires_activation` / `@requires_feature` decorators.
5. **Gmail detection** — probe for ambient Gmail capability; intake + act + label workflows; file-drop fallback.
6. **Packaging** — `guardian.dxt` v2.0.0 manifest (single `license_key`, `GUARDIAN_MODE=local`); update `mcp_install.py`; migration export/import.
7. **Tests + eval harness** — engine units, contract fixtures, state-machine tests, mode-parity.

The detailed implementation plan is produced separately (writing-plans).
