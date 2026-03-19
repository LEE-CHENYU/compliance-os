# Compliance OS MVP Engineering Doc

## Purpose

This document defines the smallest runnable MVP we should engineer now.

It is intentionally narrower than the full product vision in `docs/product_master.md`.
The goal is to ship a real working system quickly, using the logic already present in this repository.

## MVP Thesis

The MVP should not be a generic chat app.

It should be a private compliance workbench with a chat box as the control surface.

The mental model is:

- document system of record,
- concern tracker,
- live Gmail context,
- deterministic deadline and risk engine,
- action queue,
- expert escalation when needed.

The chat box should feel like **Claude co-work**, not like a simple consumer chatbot.

That means the user is not only "asking questions." The user is:

- inspecting evidence,
- exploring risks,
- discovering missing facts,
- drafting actions,
- reviewing email context,
- approving outbound work.

## What The Founder Found Useful

The founder's actual working pattern is the blueprint for the MVP:

- put documents and key concerns in one workspace,
- interactively discover issues and solutions in a co-work environment,
- use live Gmail inbox context,
- inspect email threads line by line,
- draft and send emails with approval,
- keep the conversation anchored in the user's actual evidence.

That pattern is much more useful than a detached chat interface.

## Minimal Product Shape

The MVP should center on a single **workspace per user**.

Each workspace contains:

- documents,
- concerns,
- Gmail threads and attachments,
- extracted facts,
- events,
- deadlines,
- risks,
- action items,
- draft outbound emails.

## MVP User Promise

The first version should make only three strong promises:

- never lose the document trail,
- never miss the issue hiding in the inbox,
- never send the wrong follow-up without review.

## UX Model

### Core interaction model

The product should have a chat box, but the chat box is not the product.

The chat box is the operator console for the workspace.

The user should be able to say things like:

- "What am I missing for my 1040-NR correction?"
- "Read this Wolf Group thread and tell me whether they actually answered the fee question."
- "Check whether any Gmail thread changes my H-1B or CPT timeline."
- "Draft a follow-up to Fan Chen."
- "Show me every document and email related to Form 3520."
- "Why is this risk flagged?"

### Recommended layout

For v1, the interface can be simple:

- left panel:
  - concerns
  - inbox threads
  - documents
- center panel:
  - Claude co-work style thread
  - agent responses
  - draft actions
- right panel:
  - deadlines
  - risks
  - extracted facts
  - cited evidence

This gives the user a working environment instead of a single chat transcript.

## MVP Components

### 1. Authenticated web app

Minimum needs:

- user login,
- one workspace,
- document upload,
- Gmail connect,
- concerns list,
- co-work thread,
- deadlines/risk side panel.

### 2. Encrypted document storage

Store originals as the evidence layer.

Need:

- object storage,
- per-user scoping,
- basic metadata,
- upload timestamps,
- delete support.

### 3. Structured profile and concern store

Use Postgres for durable application state.

Minimum entities:

- `users`
- `workspaces`
- `concerns`
- `documents`
- `document_chunks`
- `gmail_threads`
- `gmail_messages`
- `extracted_facts`
- `events`
- `deadlines`
- `risks`
- `draft_actions`
- `citations`

### 4. Deterministic compliance engine

This repository already contains the kernel:

- `compliance_os/compliance/rules.py`
- `compliance_os/compliance/deadlines.py`
- `config/compliance_rules.yaml`

For the MVP:

- reuse this logic,
- keep it deterministic,
- expose results through the app,
- do not let the agent override it.

### 5. Retrieval and explanation layer

The current index/query stack is useful for:

- finding relevant documents,
- grounding explanations,
- surfacing supporting evidence,
- explaining "why this risk exists."

It is not the primary truth store.

### 6. Gmail integration

This is one of the highest-value MVP pieces.

Minimum Gmail capabilities:

- sync threads,
- sync message bodies,
- sync attachments metadata,
- search threads,
- read thread content,
- link threads to concerns,
- draft email replies,
- send email only after explicit user approval.

High-value Gmail use cases:

- inbox triage,
- missed-reply detection,
- follow-up reminders,
- attachment capture,
- expert communication history,
- issue discovery from live email flow.

### 7. Concern tracker

Concerns should be first-class objects, not just prompt text.

Each concern should support:

- title,
- status,
- category,
- linked documents,
- linked Gmail threads,
- linked deadlines,
- linked risks,
- notes,
- last update,
- owner,
- next action.

Example concerns:

- `1040 vs 1040-NR correction`
- `Form 3520 foreign gifts`
- `SEVIS cleanup before H-1B`
- `passport renewal before petition`
- `CPT at family-owned company`

### 8. Action queue

The system should create explicit actions, not just text suggestions.

Minimum action types:

- draft email
- follow up
- upload missing document
- verify fact
- review risk
- schedule expert consult
- mark complete

## Minimal End-to-End Flow

The smallest useful end-to-end flow is:

1. user creates workspace
2. user uploads core documents
3. user connects Gmail
4. user adds or imports concerns
5. extractor creates structured facts
6. deterministic engine computes deadlines and risks
7. co-work interface lets user inspect evidence and ask targeted questions
8. agent drafts follow-up emails and action items
9. user approves outbound email
10. workspace updates concern state and deadlines

If we can do this reliably, we have a real MVP.

## What The Agent Should Do In MVP

The agent should handle:

- concern summarization,
- missing-fact questioning,
- document retrieval,
- Gmail thread reading,
- issue spotting,
- risk explanation,
- follow-up draft generation,
- weekly summary generation,
- action extraction from email or document context.

## What The Agent Should Not Do In MVP

The agent should not:

- decide legal outcomes,
- give definitive legal or tax advice in ambiguous cases,
- file forms automatically,
- send emails without approval,
- classify a user as noncompliant based only on weak signals,
- operate as the source of truth for deadlines or obligations.

## Runtime Split

### Recommended split

Use the existing repo logic for:

- rules,
- deadlines,
- profile state,
- retrieval.

Use the co-work agent runtime for:

- orchestration,
- workspace memory,
- concern-thread continuity,
- Gmail reading and drafting,
- summarization and issue discovery,
- user-facing conversation.

### Important principle

The **Claude co-work** style interface is the front-end experience.
It is not the legal or tax engine.

The legal and tax engine remains deterministic and source-backed.

## Smallest Technical Stack

For immediate delivery, keep the stack conventional.

Recommended v1 stack:

- frontend: Next.js or similar
- backend API: FastAPI
- database: Postgres
- object storage: S3-compatible storage
- background jobs: one worker queue
- vector store: Chroma or Postgres extension if needed
- Gmail integration: Gmail API
- auth: simple hosted auth or standard OAuth/email auth

This repo already supports FastAPI-adjacent Python usage and deterministic engine logic, so Python backend is the path of least resistance.

## Hosting Recommendation

### Recommendation

Do not make the MVP depend on a specialized persistent sandbox provider.

Run the first version on a standard cloud or PaaS where we can ship fastest.

Reasons:

- lower infrastructure risk,
- easier debugging,
- less vendor coupling,
- simpler security review,
- we do not yet know the real workload shape.

### What to use first

Use:

- ordinary app hosting,
- Postgres,
- object storage,
- background worker,
- one agent worker process.

### Where Blaxel may fit later

Blaxel appears to be persistent sandbox / agent hosting / MCP hosting infrastructure.

That may become useful later if we need:

- long-lived isolated agent workers,
- persistent per-workspace tool state,
- sandboxed connector execution,
- low-latency resume for many active workspaces.

It is not required for the first MVP.

### Decision

- v1: standard cloud first
- later: evaluate Blaxel only if persistent sandbox workers become an actual bottleneck or product advantage

## Should We Use OpenClaw In MVP?

Yes, but in a narrow role.

Good use of OpenClaw in MVP:

- orchestrating workspace tasks,
- holding short-lived operational context,
- running Gmail + document co-work flows,
- generating summaries and drafts,
- maintaining concern-thread continuity.

Bad use of OpenClaw in MVP:

- primary legal logic,
- deadline truth,
- tax-residency determination by free-form reasoning alone,
- autonomous outbound actions without approval.

## Data Model For v1

Minimum durable objects:

### `workspace`

- id
- user_id
- title
- created_at
- updated_at

### `concern`

- id
- workspace_id
- title
- type
- status
- priority
- summary
- next_action
- created_at
- updated_at

### `document`

- id
- workspace_id
- name
- source
- storage_path
- mime_type
- uploaded_at
- parsed_at

### `gmail_thread`

- id
- workspace_id
- external_thread_id
- subject
- participants
- last_message_at
- linked_concern_id

### `gmail_message`

- id
- thread_id
- external_message_id
- sender
- recipients
- sent_at
- body_text
- direction

### `extracted_fact`

- id
- workspace_id
- concern_id
- fact_type
- fact_value
- confidence
- source_kind
- source_id
- created_at

### `event`

- id
- workspace_id
- concern_id
- event_type
- event_date
- payload

### `deadline`

- id
- workspace_id
- concern_id
- title
- due_date
- category
- status
- rationale

### `risk`

- id
- workspace_id
- concern_id
- risk_type
- severity
- message
- rationale
- requires_escalation

### `draft_action`

- id
- workspace_id
- concern_id
- action_type
- payload
- approval_status
- created_at

## First Screens To Build

1. workspace home
   - concerns
   - upcoming deadlines
   - top risks
   - recent Gmail activity

2. concern detail
   - summary
   - linked documents
   - linked Gmail threads
   - extracted facts
   - deadlines
   - risk list
   - co-work thread

3. inbox thread detail
   - line-by-line email content
   - attachments
   - linked concern
   - draft reply box

4. document detail
   - preview
   - extracted facts
   - linked concerns
   - citations

## Out Of Scope For Immediate MVP

Do not build these first:

- bank connectors
- corporate cross-border compliance
- meeting recording as a default workflow
- free-form expert marketplace
- autonomous filing
- multi-channel parity across iMessage/WhatsApp/SMS
- outcome prediction
- enterprise compliance features
- specialized sandbox infrastructure dependency

## 7-Day Build Order

If we are optimizing for speed, the build order should be:

1. workspace + auth + Postgres schema
2. document upload + storage + parser pipeline
3. concern model + concern UI
4. deterministic deadlines/risks API
5. Gmail connect + thread sync + thread viewer
6. co-work thread with citations and draft-email actions
7. outbound email approval + send flow

That is enough to produce a real working prototype.

## Summary Decision

The immediate MVP should be:

- a document-backed,
- Gmail-aware,
- concern-centric,
- deterministic compliance workbench,
- with a chat box that feels like Claude co-work.

The workbench is the product.
The chat box is the interface.
The rules engine is the truth layer.
The agent is the operator, not the judge.
