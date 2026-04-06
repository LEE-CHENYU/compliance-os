# Compliance OS Memory

Last updated: 2026-04-06

This file is implementation-specific working memory for the repo. It should stay short, factual, and revision-friendly. Use `docs/product_master.md` for the durable product definition.

## Current Repo Reality

- Repo started as an extracted prototype from the accounting workflow and is now a live FastAPI + Next.js web app.
- Current product surface includes auth, dashboard/timeline views, document intake and review, grounded chat, and form-fill APIs.
- Fly deployment exists for the combined app at `guardian-compliance.fly.dev`.
- Current codebase already contains real domain logic, especially:
  - deterministic compliance rules,
  - deadline status computation,
  - event-triggered deadline creation,
  - document classification,
  - retrieval with source-grounded answers.

## Files That Matter Most

- `compliance_os/compliance/schemas.py`
- `compliance_os/compliance/rules.py`
- `compliance_os/compliance/deadlines.py`
- `config/compliance_rules.yaml`
- `compliance_os/indexer/index.py`
- `compliance_os/indexer/classifier.py`
- `config/document_types.yaml`
- `compliance_os/query/engine.py`
- `compliance_os/web/app.py`
- `compliance_os/web/routers/dashboard.py`
- `docs/product_master.md`

## Extracted Product Truths

- Deterministic compliance logic is the critical path.
- The main product object is the compliance profile, not the chat transcript.
- Events trigger obligations.
- Deadlines are first-class product objects with lifecycle.
- Documents are evidence and provenance, not just retrieval context.
- LLM outputs must stay grounded and secondary to rules.

## First-Party Use Cases Confirmed From `/Users/lichenyu/accounting`

- attorney / CPA sourcing and credential-fit evaluation is a real workflow problem
- 1040 vs 1040-NR correction is a real product-driving issue
- Form 8843 / 3520 / FBAR / 8938 / 5472 confusion is not theoretical
- SEVIS / OPT / STEM OPT / CPT / H-1B timing needs explicit state tracking
- passport-renewal timing versus petition timing is a real trigger
- W-2 retrieval, paystub reconciliation, and employer correction letters are recurring operational work
- international family wires and LLC/personal account boundaries create threshold-monitoring and documentation needs
- the actual user need is continuous compliance state management, not one-off Q&A

## Decisions From This Session

- Create a master product doc and a separate repo memory file.
- Treat the current repo as a live MVP workbench, not yet a complete multi-tenant product.
- Narrow the day-to-day operating surface to four canonical artifacts:
  - `README.md`
  - `docs/product_master.md`
  - `docs/mvp_engineering.md`
  - `docs/roadmap.md`
- Keep backlog execution in GitHub Issues and PRs instead of adding placeholder planning templates.
- Make the authenticated app the future system of record.
- Use messaging as a companion interface, not the primary source of truth.
- Do not commit to iMessage-first.
- Prefer web app plus SMS/email initially; evaluate WhatsApp later.
- Use hybrid privacy architecture:
  - encrypted raw document storage,
  - minimal structured extraction,
  - minimized retrieval embeddings.
- Use OpenCLO, if adopted, as orchestration/runtime memory rather than as the source of legal logic.
- Keep negative-compliance monitoring in scope, but express outputs as risk alerts, not legal conclusions.
- Enforce legal/tax boundaries in workflow and architecture, not only in disclaimer text.
- Founder execution sequence is:
  - bring the product online,
  - get initial real users,
  - then do investor outreach.
- Before the H-1B full petition stage, the company should have:
  - a live product surface,
  - two employees onboarded,
  - and a coherent operational story.
- By the October H-1B activation/start-date milestone, the company should have one of:
  - external funding,
  - initial cash flow,
  - or founder payroll in place.
- Narrow the product wedge hard:
  - not "AI lawyer/CPA for immigrants"
  - yes to "continuous compliance OS for immigrants"
- Preferred initial segment is F-1 / OPT / STEM OPT / early-career immigrant compliance.
- Expert layer should start as structured triage plus verified routing, not a free-form marketplace.
- Positioning to preserve:
  - "system of record and risk engine for immigrant compliance, with humans at the advice boundary"
- Add an engineering MVP doc.
- The intended chat-box metaphor is `Claude co-work`, not generic chat and not "cloud co-work".
- MVP should be a private compliance workbench:
  - documents
  - concerns
  - Gmail context
  - deterministic risks/deadlines
  - action queue
- Gmail is a high-value v1 connector because it enables:
  - live issue discovery
  - thread inspection
  - attachment capture
  - draft/send follow-up workflows
- OpenClaw should be used for orchestration and co-work memory, not as the truth layer.
- Standard cloud first; do not make Blaxel or any specialized sandbox platform a hard v1 dependency.
- Founder timing constraints are tracked in `docs/founder_execution_timeline.md`.

## What Is Missing In Code

- persistent profile store
- durable event store
- multi-tenant isolation model
- consent and privacy settings
- audit logging
- connector framework
- expert escalation workflow
- policy gating for high-risk outputs
- negative-compliance detection beyond placeholders

## Recommended Next Build Steps

1. Harden intake and evidence handling:
   - duplicate visibility
   - extraction issue visibility
   - canonical-document selection
2. Tighten the authenticated workspace:
   - cited risk and chat explanations
   - fewer demo-only assumptions
   - consistent session failure handling
3. Finish reviewed action flows:
   - form-fill proposal review
   - filled PDF generation
   - approval gates before action execution
4. Add privacy surfaces:
   - data map
   - connector permissions
   - audit log
   - delete/export
5. Add Gmail and expert-escalation flows only after the workspace state model is stable.

## Product Risks To Keep In Mind

- turning the product into generic chat instead of stateful compliance software
- overclaiming legal/tax certainty
- relying on embeddings as the primary truth store
- collecting more private data than is operationally necessary
- shipping too many channels before the dashboard and state model are stable
- producing false-positive "violations" from bank or transaction monitoring

## Operating Rule

When making future product decisions, ask:

1. Does this strengthen the regulatory state model?
2. Is this deterministic where it must be?
3. Can the user see why the system believes what it believes?
4. Does this reduce or increase trust burden?
5. Are we staying on the safe side of the legal/tax boundary?
