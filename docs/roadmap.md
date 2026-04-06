# Compliance OS Roadmap

This is the only planning doc the repo needs for day-to-day execution. Keep it tight, current, and tied to real product work.

## Canonical Operating Artifacts

- [docs/product_master.md](/Users/lichenyu/compliance-os/docs/product_master.md): long-lived product truth
- [docs/mvp_engineering.md](/Users/lichenyu/compliance-os/docs/mvp_engineering.md): MVP boundary and architecture direction
- [docs/roadmap.md](/Users/lichenyu/compliance-os/docs/roadmap.md): current roadmap and execution rules
- GitHub Issues: backlog and ownership
- GitHub PRs: implementation and review

## Do Not Add Right Now

- separate sprint docs
- placeholder epics or milestones
- story points
- issue or PR templates
- multiple project boards
- backlog items without a real owner or a concrete acceptance condition

## Minimal GitHub Setup

- labels: `roadmap`, `feature`, `bug`, `infra`, `urgent`
- board columns: `Backlog`, `In Progress`, `Review`, `Done`
- one issue owner at a time
- one issue should usually fit in 1 to 2 days
- one PR should usually map to one issue

## Current Roadmap

### 1. Trusted Intake To Evidence Graph

Outcome: a user can upload real documents and end up with a reviewable evidence set, not a pile of files.

Exit signals:

- uploads are classified or explicitly flagged
- duplicates and extraction failures are visible in the workspace
- timeline and integrity logic work from canonical documents, not ad hoc guesses

### 2. Deterministic Compliance Workspace

Outcome: the dashboard becomes the default operator console for understanding state, deadlines, and risk.

Exit signals:

- risks and deadlines are explainable with evidence
- timeline integrity issues are surfaced before the user gets a misleading answer
- chat stays grounded in the workspace state

### 3. Reviewed Action Execution

Outcome: the product helps the user complete the next action, but nothing high-risk happens without explicit review.

Exit signals:

- form-fill proposals are reviewable and editable
- generated outputs are downloadable after review
- outbound assistance stays in draft mode until the user approves it

## Active Backlog Now

Open only the issues that are truly active. Everything else stays out of the board until it becomes the bottleneck.

### Intake And Evidence

- `feature`: Surface duplicate-detection and ingestion-issue summaries directly on dashboard document views.
- `bug`: Add regression coverage for upload and extraction paths where document type resolution or OCR output is weak.
- `feature`: Make canonical-document selection explicit when multiple uploads map to the same evidence chain.

### Workspace

- `feature`: Link risk cards, integrity issues, and chat answers back to cited source documents.
- `bug`: Normalize auth and session-failure handling across frontend API calls and FastAPI auth routes.
- `feature`: Remove remaining demo-only dashboard assumptions in favor of authenticated user workspace state.

### Action Layer

- `feature`: Finish the form-fill round trip from PDF upload to editable field proposals to filled PDF download.
- `bug`: Keep `/api/form-fill/*` and `/api/dashboard/form-fill/*` behavior in lockstep until the legacy alias can be removed.
- `feature`: Gate action-oriented assistant flows behind explicit review instead of silent execution.

## Review Cadence

- Once per week: cut or reorder roadmap items based on the next demo bottleneck.
- Every few days: prune stale backlog items aggressively.
- Every PR: prefer smaller changes and fix forward instead of batching unrelated work together.
