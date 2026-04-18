# Guardian — Anthropic Connector Directory submission package

This doc assembles the material Anthropic's Connector Directory
submission form typically asks for. When Anthropic opens applications
(or for direct outreach), paste from here.

---

## Identity

- **Connector name:** Guardian
- **Publisher:** Guardian (Chenyu Li)
- **Contact:** fretin13@gmail.com
- **Homepage:** https://guardiancompliance.app
- **Docs:** https://guardiancompliance.app/docs/install
- **Source:** https://github.com/LEE-CHENYU/compliance-os
- **Package:** `compliance-os[agent]` on PyPI (pending publish)
- **DXT:** https://guardiancompliance.app/guardian.dxt

## Short description (tagline, <120 chars)

> Cross-check immigration + tax docs before USCIS or the IRS does. Form 8843, H-1B packages, Form 5472, FBAR.

## Full description (~300 words)

Guardian is a compliance copilot for nonresidents, STEM OPT / H-1B
workers, international students, and foreign-owned US entities.
Connected to Claude (Code or Desktop) or Codex, Guardian gives the
assistant direct access to the user's personal compliance data room:
uploaded documents (I-20, I-983, I-94, W-2, 1042-S, EADs, tax
returns), active findings, deadlines, and entity status.

Users can ask their coding agent to scan a local folder against a case
template (H-1B petition with 59 required slots across 7 sections,
CPA tax engagement with 27 slots for Form 5472 + pro forma 1120
scope) and receive a gap report — exactly which documents are
missing, which are misplaced, where the I-20 lineage has gaps.

Beyond reporting, Guardian generates filings locally via the
assistant: Form 8843 (free, standalone or packaged with 1040-NR),
FBAR aggregation check, I-983 STEM OPT review, 83(b) election
readiness. Filed documents are produced as PDFs ready to mail or
attach to the tax return.

Guardian also wraps Gmail: the assistant can surface IRS notices,
read compliance-related correspondence, and draft replies with the
user's filings attached.

Once a case is ready, users issue tokenized read-only share links
for their immigration attorney or CPA — A–G section tree with
coverage percentages, inline PDF preview, and a download-all zip.

## Authentication

- Bearer token (`gdn_oc_` prefix), generated at
  https://guardiancompliance.app/connect after sign-in.
- Scoped to the user's own data room. Revocable from the same page.
- No OAuth flow required (kept simple for MCP clients).

## Tools exposed (23)

See `tools` array in `frontend/public/guardian.dxt` manifest. Grouped:

- **Compliance context (5):** status, deadlines, risks, documents, ask
- **Case templates (3):** case_active_search, h1b, cpa
- **Documents (6):** parse, classify, upload, batch_upload, query, index
- **Forms (3):** generate_form_8843, run_compliance_check, filing_guidance
- **Gmail (6):** search, read, draft, send, reply, download_attachment

## Data handling

- **At rest:** SOC 2 Type II infrastructure (Fly.io + Neon Postgres).
  Volumes encrypted at rest.
- **In transit:** TLS 1.3 to `guardiancompliance.app`.
- **Scope:** a user's token only reads/writes their own data room.
  Cross-tenant access is impossible.
- **Local processing:** PDF parsing + classification runs on the
  user's machine (PyMuPDF), not Guardian servers — sensitive docs
  don't have to leave the device.
- **Compliance posture:** see https://guardiancompliance.app/#privacy
  (TODO: add dedicated privacy page at /privacy).

## Security notes

- MCP server is a Python package with no bundled native binaries
  other than standard pip deps (fastapi, pymupdf, anthropic, …).
- The dev-mode auto-JWT flow (empty token + loopback host) is
  documented and disabled for non-loopback hosts.
- Token-scoped share links use HMAC-SHA256 signed JWTs with
  configurable expiry (default 14 days).

## Screenshots to include

- Landing page hero                        → share-page-prod.png (existing)
- /connect page                            → connect-brand-icons.png
- Data room share page (desktop)           → share-page-full.png
- Data room share page (mobile)            → mobile-after.png
- Docs/install page                        → (capture before submit)
- DXT install prompt in Claude Desktop     → (capture after Claude Desktop adds DXT support)

## Reviewer test instructions

1. Install: `pip install "compliance-os[agent]"`
2. Get token: https://guardiancompliance.app/connect (use
   fretin13+reviewer@gmail.com — seeded test data)
3. Configure: `GUARDIAN_TOKEN="..." guardian-mcp install --auto`
4. Restart host, call `guardian_status` — should return seeded
   findings including one critical (I-983 missing) and two warnings.
5. Try: `case_active_search(template="h1b", folder="/tmp")` — should
   return a gap report with A–G coverage.

## What we're asking for

1. Listing in the Claude Desktop Connector Directory.
2. Reviewing the DXT at https://guardiancompliance.app/guardian.dxt
   for any manifest gaps.
3. Feedback on whether anything in the 23-tool surface should be
   split into separate connectors (e.g. Guardian Gmail vs Guardian
   Compliance — currently bundled).

## Status

- [x] DXT package published at /guardian.dxt
- [x] AGENTS.md self-install published at /AGENTS.md
- [x] Docs page at /docs/install
- [x] Zero-fetch CLI path documented
- [ ] PyPI publish (currently local-only; plan: publish after DXT
      testing with 3-5 beta users confirms stable tool surface)
- [ ] Privacy policy page at /privacy
- [ ] 60-sec demo video
- [ ] Submitted to Anthropic Connector Directory
