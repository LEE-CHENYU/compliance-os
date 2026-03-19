# Compliance OS Master Product Doc

## Purpose

This document is the canonical product definition for Compliance OS.
It separates:

1. what the current codebase already implements,
2. what business logic we should preserve as product truth, and
3. what product and architecture decisions we should make next.

The current repository is a backend/CLI prototype extracted from an accounting workflow. The next step is to turn that logic into a consumer-facing compliance product with a trustworthy user interface, narrow legal boundaries, and strong privacy posture.

## Product Thesis

Compliance OS is not "chat for legal/tax questions."

It is a continuous compliance system for people with recurring, stateful obligations, especially immigrants and international founders. The product moat is the user's regulatory state model:

- immigration state,
- tax state,
- entity state,
- document inventory,
- deadline ledger,
- event ledger, and
- expert-routing history.

The assistant layer is useful, but it is not the product core. The product core is a deterministic system that detects obligations, watches for risky changes, and keeps the user in a compliant operating state over time.

## Who It Is For

Primary wedge:

- F-1 / OPT / STEM OPT / H-1B users
- immigrants with recurring status transitions
- international students with tax and work-authorization complexity
- founders or contractors with side entities, foreign gifts, foreign accounts, or cross-border issues

Why this wedge works:

- obligations recur,
- deadlines are periodic and consequential,
- users accumulate fragmented documents across many channels,
- negative compliance matters as much as positive compliance,
- stakes are high enough that users will pay for prevention.

## The Core User Problems

1. Users do not know their current compliance state.
2. Users miss recurring deadlines or do not understand which documents are needed.
3. Users do not realize when a new event changes their obligations.
4. Users often need preventive guidance, not just help after a problem appears.
5. Users do not trust generic AI with private documents or sensitive decisions.
6. Users need a product boundary that does not pretend to be a law firm or CPA firm.

## Founder-Origin Problem Statement

The original idea is grounded in a real first-party pain pattern:

- immigrant students and early-career immigrants face dense legal, tax, and documentation requirements,
- they usually do not have enough domain knowledge to self-manage the moving parts,
- lawyers and CPAs are hard to source and even harder to judge before spending time and money,
- the user often cannot tell whether a given issue is tax, immigration, corporate, school-policy, or multi-regime,
- there is real value in preventive warning before the user falls into a loophole.

Three starting pain points came from the founder's own experience:

1. expert sourcing and matching
   - lawyers and CPAs are difficult to evaluate,
   - initial consults can create deadweight loss if the professional later declines the matter,
   - the user usually cannot judge fit, specialization, or actual responsibility structure.
2. document and obligation tracking
   - the user needs one place to keep documents, deadlines, status facts, and updates,
   - the system should monitor those facts against tax and immigration rules over time.
3. agentic prevention with strong guardrails
   - the system should surface similar-case risks and missing-fact questions,
   - but safety, correctness, and evaluation matter more than automation theater.

Other founder concerns that should remain in scope:

- optional use of meeting recordings or structured recap as information sources, while recognizing many lawyers resist recording,
- privacy and trust design for a small startup handling sensitive personal documents,
- differentiation from generic workflow or agent-builder tools such as BubbleLab-style products,
- whether a narrow immigrant-compliance wedge can later expand into broader cross-border corporate compliance.

## Real First-Party Use Cases From The Accounting Repository

The `/Users/lichenyu/accounting` repository contains concrete examples of the product surface area. These are more important than abstract feature lists because they show the actual failure modes one user encountered.

### 1. Expert sourcing and quality verification

The user had to evaluate multiple immigration and tax providers, often without clear information about:

- who the attorney of record would be,
- who would handle the case day to day,
- whether the engagement was with a law firm or consulting entity,
- whether malpractice insurance existed,
- whether the work could be completed before a filing deadline.

This appears directly in the H-1B attorney vetting drafts and CPA outreach drafts. The product implication is that expert routing should expose structure and credentials, not just lead forms.

### 2. Cross-regime tax correction and filing-state confusion

One of the clearest use cases is the overlap between immigration status and tax reporting:

- F-1 arrival in Oct 2023,
- prior returns filed as Form 1040 instead of 1040-NR,
- need to determine whether amendments are required for 2023 and 2024,
- need to file 2025 correctly,
- need to determine treatment of Form 8843, Form 3520, FBAR, Form 8938, Form 5472, pro forma 1120, and state returns.

This is exactly the type of confusion users cannot safely resolve from memory alone. The system should make the dependency graph visible:

- immigration status facts,
- tax residency consequences,
- filing consequences,
- document evidence,
- escalation points.

### 3. Preventive warning on near-miss reporting logic

The founder's own near-miss is strategically important:

- almost missing Form 3520 because of confusion around student exemptions and related filings,
- uncertainty around whether exemption logic depended on timely filing of a different form,
- uncertainty created by filing history and changing tax-residency assumptions.

Whether the exact legal resolution is straightforward or not is less important than the product lesson:

- users regularly mis-map one rule system onto another,
- the product must catch these category mistakes before the filing deadline.

### 4. Immigration lifecycle tracking, not just document storage

The accounting repo shows a full state-tracking problem, not a single filing problem:

- OPT unemployment limits,
- STEM OPT cumulative unemployment logic,
- open-ended SEVIS employer records,
- transitions into CPT,
- H-1B registration and petition planning,
- passport renewal timing relative to petition filing,
- questions about self-employment, unpaid work, and family-owned employers.

This is why the product has to manage a regulatory timeline, not just a file cabinet.

### 5. Employment authorization gap detection and evidence building

The repo includes a concrete example where paystub timing and SEVIS/work-authorization periods had to be reconciled to address a potential unauthorized-employment concern.

That is a high-value product behavior:

- detect the inconsistency,
- identify the evidence gap,
- request correction from the employer,
- preserve the correction letter for future immigration use.

This is closer to compliance operations than to generic chat.

### 6. W-2 retrieval and fragmented communications

The accounting repo also shows how routine compliance work becomes operationally messy:

- W-2 mailed to an old address,
- bounced legacy email address,
- manual follow-up with employer and accountant,
- password-protected W-2 attachment handling,
- need to cross-check W-2 against paystubs and address history.

This is a practical argument for the document vault plus reminders plus communication memory layer.

### 7. Financial-event monitoring and related-party risk detection

The repo contains detailed tracking of:

- repeated international family wire transfers from China,
- possible Form 3520 threshold and related-party aggregation issues,
- personal versus business account boundaries,
- LLC distributions, contributions, and legal-fee tracking,
- unresolved transfer destinations and account mapping questions.

This is the strongest evidence that transaction-level monitoring can be valuable if handled carefully. It should produce:

- fact extraction,
- threshold tracking,
- audit-ready documentation,
- risk alerts,
- escalation prompts.

It should not jump straight to definitive legal conclusions.

### 8. Corporate and founder overlap

The founder's case is not purely "student immigration" and not purely "small business accounting." It includes both:

- immigration status transitions,
- personal tax residency questions,
- foreign gifts and foreign accounts,
- Wyoming SMLLC compliance,
- business account reconciliation,
- legal-fee and entity-governance records.

This overlap is strategically important because it suggests the long-term expansion path:

- individual immigrant compliance first,
- founder and self-employment edge cases second,
- employer-side or cross-border business compliance later.

### 9. Product lesson from the founder's actual workflow

The real use case is not "answer my question."

The real use case is:

- track my status,
- track my documents,
- track what changed,
- detect what that change may trigger,
- tell me what is missing,
- tell me when I need a professional,
- and preserve the evidence trail when I do.

That is the product to build.

## Business Logic Already Implemented In Code

The current codebase already contains several real product truths.

### 1. Deterministic compliance logic is the critical path

This is explicit in the rule engine and deadline engine:

- `compliance_os/compliance/rules.py`
- `compliance_os/compliance/deadlines.py`
- `config/compliance_rules.yaml`

Core principle:

- legal and tax obligations should be computed deterministically from verified rules,
- LLMs should not invent obligations,
- LLMs can help explain and retrieve, but not decide core compliance state.

This principle should remain non-negotiable in the product.

### 2. The real product object is a compliance profile

`ComplianceProfile` in `compliance_os/compliance/schemas.py` already captures the correct abstraction:

- identity,
- immigration state,
- tax residency state,
- corporate entities,
- deadlines,
- events,
- document requirements.

This should become the source of truth for the product UI and alert system.

### 3. Events trigger obligations

`ComplianceEvent` and `DeadlineEngine.process_event()` capture the right causal model:

- foreign gifts can trigger Form 3520,
- foreign balances can trigger FBAR,
- employment changes can trigger work-authorization reporting,
- status changes can trigger new obligations.

This event-driven model is more important than a chat log. The product should track state transitions and event history, not just messages.

### 4. Deadlines are first-class objects with lifecycle

`Deadline` and `DeadlineStatus` already model:

- overdue,
- urgent,
- upcoming,
- later,
- done,
- auto-extension logic.

This should directly power the consumer UI:

- dashboard,
- notifications,
- weekly summaries,
- expert escalation.

### 5. Documents are evidence, not just context

The indexer and classifier already treat documents as compliance artifacts:

- `compliance_os/indexer/index.py`
- `compliance_os/indexer/classifier.py`
- `config/document_types.yaml`

This means the product is not just an answer engine. It is a document-backed evidence system.

### 6. Querying should stay grounded and source-backed

`compliance_os/query/engine.py` enforces:

- answer only from retrieved context,
- cite source paths,
- say when evidence is missing,
- label legal/tax outputs as informational only.

That is the correct trust model for the assistant layer.

## What The Current Code Does Not Yet Implement

The repository is still a prototype. These gaps matter:

- no authenticated user interface,
- no persistent user profile store,
- no concern graph or memory model,
- no notification/channel layer,
- no connector framework for Gmail, bank data, payroll, or USCIS-style sources,
- no event ingestion pipeline,
- no tenant isolation or encryption model,
- no expert workflow or escalation queue,
- no durable audit log,
- no policy layer for legal/tax boundary enforcement in product behavior,
- no negative-compliance monitoring beyond placeholders.

## Product Direction

### Product Definition

Compliance OS should become a preventive compliance copilot with three layers:

1. State layer
   - user compliance profile
   - events
   - deadlines
   - documents
   - concerns

2. Policy layer
   - deterministic rules
   - threshold logic
   - date logic
   - missing-document logic
   - escalation thresholds

3. Experience layer
   - dashboard
   - message-based nudges
   - document intake
   - explanations
   - expert handoff

The product should feel like "an always-on compliance operating system," not "a better chatbot."

## Recommended Runtime Model

OpenCLO is a reasonable runtime candidate if we use it for orchestration, not as the source of legal truth.

Recommended use of OpenCLO:

- maintain a concern graph: what the user is worried about now,
- maintain a deadline stream: what is due and why,
- maintain a document-change stream: what was uploaded, changed, or is still missing,
- maintain user-facing conversation memory that stays tied to the underlying state model.

Do not let OpenCLO own the regulatory logic itself.

Recommended split:

- deterministic compliance engine = legal/tax state machine,
- OpenCLO runtime = orchestration and user-facing memory,
- document vault = source evidence,
- retrieval layer = explanation and document lookup.

## User Interface Strategy

The current implementation is CLI-first. Consumer-facing product should not be chat-only.

Recommended primary surfaces:

1. Authenticated web app
   - compliance dashboard
   - deadlines timeline
   - document vault
   - issue/risk feed
   - profile state editor
   - settings, privacy, and connected accounts

2. Messaging layer
   - reminders
   - missing-document nudges
   - short status summaries
   - approval requests
   - lightweight intake

3. Expert handoff layer
   - when risk is high,
   - when filings become complex,
   - when the product should stop and escalate.

The app should be the system of record. Messaging should be a companion channel, not the only interface.

## Channel Strategy

### Recommendation

Do not make iMessage the primary product channel.

Instead:

- primary control plane: authenticated web app,
- primary notification channels: SMS, WhatsApp, and email,
- optional future support: iMessage or Apple Business Messages if distribution and operations make sense.

### Why not iMessage-first

- too platform-constrained,
- weak cross-platform reach,
- business automation constraints,
- difficult to make it the operational backbone,
- product would inherit Apple-specific limitations too early.

### Why not "all channels equally" from day one

- too much operational complexity,
- fragmented trust model,
- hard to maintain consistent behavior and consent,
- slows down core product learning.

### Pragmatic channel rollout

Phase 1:

- web app + email + SMS

Phase 2:

- add WhatsApp if user base shows strong demand

Phase 3:

- evaluate iMessage only if it materially improves trust or conversion and can be supported cleanly

### Trust implication

iMessage may feel more trustworthy to some users, but trust will come more from product behavior than from channel brand:

- clear provenance,
- explicit permissions,
- visible state,
- transparent retention,
- consistent reminders,
- easy delete/export,
- strong incident posture.

## Privacy And Trust Architecture

This is one of the core product decisions.

### Recommendation

Use a hybrid architecture:

1. store the original documents in encrypted tenant-scoped storage,
2. extract a minimal structured compliance state model,
3. create a minimized retrieval index only for the chunks needed to answer or monitor compliance,
4. keep raw-document access narrow and auditable.

Do not choose between "embeddings only" and "store everything blindly." Both are the wrong extreme.

### Why embeddings-only is insufficient

- no reliable audit trail,
- hard to re-extract facts when rules change,
- hard to prove provenance,
- hard to debug errors,
- hard to support expert review.

### Why full raw-document storage without minimization is also wrong

- over-collects sensitive information,
- increases breach radius,
- weakens user trust,
- raises internal access risk,
- makes retention and deletion policy harder.

### Recommended privacy model

- encrypted document vault per tenant
- least-privilege access for services
- structured extraction for only the fields needed by compliance logic
- embeddings only for compliance-relevant chunks
- retention classes by document type
- auditable access log
- clear export and delete controls
- no model training on user data by default
- explicit consent per connector and per data class

### How to make users believe us

Trust cannot rely on a sentence in the footer. It needs product mechanics:

- show exactly what documents are stored,
- show exactly what facts were extracted,
- show why each fact matters,
- show which deadline or risk each fact feeds,
- show who or what accessed each document,
- allow users to revoke connectors and delete data,
- provide a clean "what we do not do" page,
- publish a narrow data-handling policy in plain language,
- give users a way to use the product with partial data instead of forcing maximum access.

### Suggested data layers

Layer 1: Original evidence

- encrypted files
- audit and expert review

Layer 2: Structured state

- visa dates
- filing status
- entity facts
- account thresholds
- employment facts
- recurring deadlines

Layer 3: Retrieval index

- only chunks needed for explanation and document search

Layer 4: Messaging memory

- concerns
- preferences
- reminder history
- escalation history

## Negative Compliance Monitoring

This is strategically important and easy to miss.

Examples:

- revenue activity that may conflict with current work authorization,
- side-project payments while on a restrictive status,
- entity or payroll activity inconsistent with the user's declared immigration or tax state,
- account or wire events that trigger filings the user does not realize they now owe.

### Product principle

The system should detect possible compliance conflicts early, but it should not overclaim.

For example:

- good: "New incoming business revenue may be inconsistent with your current work authorization. Review before continuing."
- bad: "You violated immigration law."

### Recommended implementation

- read-only bank and payment connectors
- user-mapped accounts and entities
- event normalization into the compliance event ledger
- deterministic rule checks for thresholds and conflict patterns
- confidence scoring and user confirmation requests
- high-risk routing to attorney/CPA review

### Important boundary

Financial monitoring should be framed as preventive risk detection, not as a definitive legal judgment engine.

## Legal And Tax Boundary

This product lives close to regulated advice. Boundary design is mandatory.

### What the product should do

- organize documents,
- compute deterministic deadlines and thresholds,
- detect possible risks,
- explain obligations with sources,
- ask clarifying questions,
- recommend escalation when uncertainty or consequence is high,
- generate checklists and preparation steps.

### What the product should not do

- represent itself as a law firm or CPA firm,
- claim definitive legal or tax advice for ambiguous situations,
- auto-file sensitive forms without guardrails,
- tell users to take aggressive filing positions without human review,
- present uncertain inferences as facts.

### Required product controls

- source-backed outputs,
- explicit confidence and uncertainty language,
- escalation triggers for high-risk cases,
- expert-review mode for sensitive recommendations,
- domain-specific prompt policy,
- approval checkpoints before high-consequence actions,
- clear separation between information, workflow support, and professional advice.

Disclaimers alone are not enough. The boundary must be enforced in system behavior.

## Business Model Direction

Recommended model:

### Base subscription

Recurring consumer subscription for continuous monitoring:

- deadline tracking,
- document vault,
- reminders,
- document change detection,
- risk alerts,
- channel notifications,
- compliance dashboard.

### Add-on modules

- STEM OPT module
- H-1B transition module
- international tax module
- founder / LLC module
- foreign accounts and gifts module

### Premium layer

- expert routing,
- document review,
- attorney/CPA handoff,
- guided filing preparation,
- white-glove onboarding.

This aligns well with the recurring nature of immigration and cross-border compliance.

## What We Should Build Next

### Product priorities

1. persistent compliance profile and event store
2. authenticated user dashboard
3. document intake and extraction pipeline
4. deadline and risk feed in UI
5. notification service with SMS/email first
6. privacy and consent controls
7. expert escalation workflow

### Engineering priorities

1. separate deterministic engine from retrieval system more cleanly
2. add a durable database for users, profiles, events, deadlines, and documents
3. add tenant-aware storage and access controls
4. implement structured extraction from documents into profile facts
5. implement event ingestion interfaces for manual entry and connectors
6. add policy gates for high-risk advice
7. build a dashboard before expanding channels

## Engineering MVP Direction

There is now a separate engineering-focused MVP document at `docs/mvp_engineering.md`.

The key engineering decision is:

- build a private compliance workbench with a chat box as the control surface,
- not a chat-first consumer assistant.

The intended interaction style is **Claude co-work**:

- documents and concerns live in one workspace,
- Gmail provides real-time communication context,
- the user can inspect email content, attachments, risks, and deadlines in one place,
- the agent can draft actions and emails,
- deterministic logic remains the truth layer.

For v1:

- use a standard cloud stack,
- keep OpenClaw narrow and orchestration-focused,
- do not make specialized sandbox infrastructure a dependency,
- and do not rely on the model for legal or tax conclusions.

## Product Decision Summary

These are the default decisions this repo should now assume:

- Compliance OS is a preventive compliance operating system, not a generic chat app.
- Deterministic rules and deadlines are the product core.
- The app is the system of record; messaging is a companion channel.
- Do not go iMessage-first.
- Start with web app plus SMS/email, then evaluate WhatsApp.
- Store original documents in encrypted tenant storage.
- Extract minimal structured facts for the rule engine.
- Build minimized embeddings for retrieval, not for primary truth.
- Use OpenCLO as orchestration/memory runtime, not as the legal logic engine.
- Negative compliance monitoring is in scope, but must produce risk flags rather than legal conclusions.
- Legal/tax boundary must be enforced in product behavior, not just disclaimer text.

## Open Questions

- Which initial user segment should be the launch wedge: STEM OPT, H-1B transitions, or international tax?
- How much of the intake should be self-serve versus concierge?
- Which connectors are worth launching first: Gmail, bank, payroll, calendar, or cloud drive?
- What degree of local-first or client-side encryption is required for trust and distribution?
- Should premium expert partners be integrated operationally from day one or only after the monitoring product is stable?

## Strategic Addendum: Narrow The Wedge Hard

This section captures the stronger market framing that should guide product scope.

### Company framing

This is worth exploring, but only if it is narrowed hard.

The buildable company is not "AI lawyer/CPA for immigrants." The buildable company is a continuous compliance OS for immigrants:

- document system of record,
- deadline and risk engine,
- credentialed expert routing when the user crosses into legal or tax advice territory.

Adjacent markets already prove people and institutions pay for slices of this problem:

- consumer immigration workflows: Boundless, SimpleCitizen
- nonresident tax prep: Sprintax, Glacier
- immigration professional workflow: Docketwise, eimmigration, INSZoom
- international-student career and immigration support: Interstride
- employer-side immigration and mobility: Envoy, Fragomen, BAL, Deel, Gale

The underbuilt gap is the user-centric layer that keeps one person's status, documents, dates, and expert escalation synchronized over time.

### Why the pain is real

Immigrant compliance is genuinely multi-regime and easy to confuse.

Examples:

- a student excluding days of presence as an exempt individual may need Form 8843,
- Form 3520 is a separate regime for certain foreign trusts and certain large foreign gifts by U.S. persons,
- Form 3520-A applies to a foreign trust with a U.S. owner,
- OPT and STEM OPT create separate timing and reporting obligations tied to immigration status and Form I-765 workflows.

Users routinely blend together tax residency rules, information returns, and immigration-status rules even though they come from different legal systems. The product should be designed to catch these category errors early.

### Non-negotiable advice boundary

The biggest failure mode is drifting into unauthorized practice.

The safe product boundary is:

- organize,
- monitor,
- warn,
- educate with sources,
- escalate.

The unsafe boundary is: "let the agent decide your case."

This has direct product implications:

- immigration advice must be routed to licensed attorneys or accredited representatives where required,
- lawyer referral flows must be structured so they do not accidentally become noncompliant referral-service operations,
- tax escalation should anchor on CPAs, EAs, or attorneys with the right practice rights.

### Expert sourcing should be structured, not marketplace-first

Do not start with a free-form marketplace.

Start with structured triage plus verified routing.

For immigration, relevant signals include:

- bar status,
- jurisdiction,
- practice area,
- language capability,
- whether the relationship is a certified referral path or a simple directory listing.

For tax, relevant signals include:

- CPA / EA / attorney status,
- IRS preparer-directory verification where applicable,
- relevant specialty area.

Directories should be treated as verification inputs, not shortcuts around referral-service rules.

### Product shape for v1

The tighter product to build first is:

1. a document vault and timeline that knows what the user has, what is missing, what expires, and what changed
2. a deterministic compliance engine for dates, thresholds, and event triggers
3. a risk detector that says "this change may affect your status or tax filing; here is why; here are the sources"
4. credentialed escalation to the right lawyer, EA, or CPA when advice is needed
5. a post-consult action layer that turns advice into reminders, checklists, and tracked obligations

This is more defensible than a generic agent demo because the moat is the regulatory state model, not the workflow automation by itself.

### Differentiation

Generic workflow and agent builders can automate tasks, but they do not inherently provide:

- regulatory correctness,
- privilege boundaries,
- source accountability,
- trustworthy expert routing.

The unique value here must be:

"We maintain your compliance state over time."

The core asset is a domain graph of:

- visa status,
- entry and exit history,
- school and employment events,
- tax-residency logic,
- document dependencies,
- filing windows,
- escalation rules.

### Agentic design rule

Keep the model off the critical path for legal conclusions.

Use:

- rules and code for deterministic obligations,
- retrieval from official or verified sources for explanations,
- human review for high-risk or ambiguous matters.

Similar-case search can be useful, but mainly to:

- generate missing-fact questions,
- surface adjacent risks,
- help with issue spotting.

It should not be used to promise approval odds or outcome predictions.

NIST AI RMF style governance is the right operating model:

- map the use case,
- measure failure modes,
- manage them with documentation, testing, and escalation.

### Meeting recording should be optional

Meeting recording should not be a core assumption.

Lawyer resistance is rational because confidentiality, supervision, and privilege boundaries matter. The safer default workflow is:

- user-uploaded documents,
- structured intake,
- optional and consent-based recording,
- structured post-call recap,
- explicit controls around storage and access.

### Privacy and trust architecture

A small startup wins trust more through architecture than branding.

Baseline expectations:

- collect the minimum data necessary,
- do not train models on customer documents by default,
- encrypt in transit and at rest,
- require MFA and role-based access,
- keep audit logs,
- give users export and delete controls,
- publish retention windows,
- maintain a breach playbook.

If the product sells to institutions or employers, SOC 2 becomes an important trust signal.

### Legal and data-compliance layers

Think about legal compliance in layers.

First layer:

- general privacy and security duties,
- FTC unfairness and deception risk,
- state breach-notification laws,
- CCPA / CPRA if threshold conditions are met.

Second layer:

- if functioning as a tax-prep provider or as a service provider to tax professionals, GLBA Safeguards Rule implications become much more important,
- IRS taxpayer-data restrictions and preparer-specific obligations may also become important.

The operating principle is simple:

- do not collect more regulated data than the product actually needs,
- and do not take on regulated workflow responsibility accidentally.

### GTM wedge

Copy the good part of narrow-wedge startup logic:

- start with one sharp wedge, not a broad platform pitch.

Preferred first wedge:

- F-1 / OPT / STEM OPT / first-job immigrants who need ongoing immigration and tax-compliance tracking and do not know when to escalate to a professional.

Why this segment works:

- repeated deadlines,
- recurring document needs,
- clear anxiety,
- concentrated distribution,
- strong need for preventive monitoring.

Pure B2C subscription is likely not enough by itself. A plausible path is B2B2C through:

- universities,
- international student offices,
- employers,
- mobility or HR partners.

### Competitor map

Useful market summary:

- consumer immigration: Boundless, SimpleCitizen
- tax for nonresidents / international students: Sprintax, Glacier
- law-firm and nonprofit workflow: Docketwise, eimmigration, INSZoom, LawLogix
- university and student enablement: Interstride
- corporate immigration and mobility: Envoy, Fragomen, BAL, Deel, Gale

The opening is the gap between these categories:

- continuous compliance tracking for the individual,
- with trustworthy handoff when the issue becomes legal or tax advice.

### Expansion path

Corporate cross-border compliance for foreign firms entering the U.S. may be a later expansion, but it should not be v1.

That is a different:

- buyer,
- sales motion,
- implementation scope,
- regulatory surface area.

The sensible sequencing is:

1. nail a narrow immigrant lifecycle
2. extend into employer-side immigration compliance
3. only later expand into broader cross-border corporate compliance

### Bottom line

Yes, this is a serious idea.

No, it should not be built first as a broad "AI compliance assistant for all immigrants and all businesses."

The right first product is a trusted compliance OS for one narrow immigrant lifecycle, probably F-1 / OPT / STEM-to-early-career, with three promises:

- never miss a deadline
- never lose the document trail
- never talk to the wrong expert

If that wedge works, employer-side immigration compliance is the next sensible move. Broader cross-border corporate compliance comes later.

### Positioning line

"We are the system of record and risk engine for immigrant compliance, with humans at the advice boundary."
