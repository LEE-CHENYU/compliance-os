# ADR 001 — Defer OAuth 2.0 for Anthropic Connector Directory submission

- **Status:** Accepted
- **Date:** 2026-04-17
- **Context:** Anthropic's Connector Directory submission requires
  OAuth 2.0 for authenticated services. Guardian currently ships
  Bearer tokens (`gdn_oc_` prefix) scoped per user.

## Decision

Do not build OAuth 2.0 now. Ship submission prep work (privacy
policy, tool annotations, screenshots, test account) and use the
DXT + AGENTS.md + `/docs/install` install paths in the meantime.

## Why defer

1. **Cost-to-benefit is lopsided at current stage.** Minimum-viable
   OAuth (Auth Code + PKCE only, single scope, no dynamic client
   registration) is ~3-4 days of focused work. Full spec is ~2
   weeks. Directory listing is one discovery channel; DXT one-click
   + AGENTS.md agent-install + SEO cover the rest.
2. **Spec churn.** MCP's OAuth standard is still settling in early
   2026. Building against today's spec risks a refactor in 6 months.
3. **Permanent attack surface.** OAuth endpoints add a class of
   bugs (redirect_uri validation, PKCE verifier mismatches, token
   confusion) that require ongoing monitoring.
4. **Current users don't need it.** Power users install via DXT or
   CLI — copy-paste of a Bearer token is acceptable friction for
   this audience.

## Triggers for revisiting

Revisit when ANY of these happens:

- **Directory listing becomes a priority GTM channel** — e.g. after
  one ICP conversation where a customer says "I'd use this if it
  were in Claude's directory."
- **Anthropic's OAuth requirements stabilize** — specifically when
  they publish a formal MCP-OAuth RFC or version-stamped spec.
- **A non-technical user (lawyer, CPA, student) struggles with the
  token paste step** during real onboarding — friction signal.
- **We add multi-user features** (team accounts, shared data rooms)
  where Bearer-per-user doesn't scale.

## Scope when we do build

Minimum viable, **not** full spec:

- `GET /oauth/authorize` + consent screen
- `POST /oauth/token` (Auth Code + PKCE → access + refresh)
- `POST /oauth/revoke`
- `GET /.well-known/oauth-authorization-server`
- ONE scope (`guardian:read_write`) — no scope taxonomy yet
- Keep Bearer tokens (`gdn_oc_*`) working in parallel — zero
  regression for existing users

Explicitly excluded from v1: dynamic client registration, scope
splits, refresh-token rotation, token binding. Add if/when Anthropic
or production traffic demands them.

## What we're shipping instead

- `/privacy` page (required by directory anyway + good hygiene)
- MCP tool annotations (`title`, `readOnlyHint`, `destructiveHint`)
  — improves Claude Desktop tool UI regardless of directory status
- DXT one-click install at `/guardian.dxt`
- AGENTS.md self-install + zero-fetch CLI fallback
- Promotional screenshots + logo assets
- Seeded reviewer test account

## Revisit date

2026-07-17 (90 days from this ADR). If none of the triggers have
fired by then, re-evaluate cost-benefit with fresh data.
