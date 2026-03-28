# Agent Instructions

This file mirrors the active Claude guidance that should also apply to agents working in this repository.

## Source Coverage

- User-level source merged from `/Users/lichenyu/.claude/CLAUDE.md`
- Project-level `CLAUDE.md` in this repository: not present at the time this file was created

## Python Environment Policy

When initializing any new Python project, always create a dedicated conda environment before installing dependencies:

1. Name the environment after the project, lowercased and hyphenated.
2. Default to Python `3.11` unless the project has a specific version requirement.
3. Create and activate the environment before any `pip install`.
4. Record the environment by installing from `requirements.txt` or `pyproject.toml` when present, or by creating a `requirements.txt` before finishing if dependencies were added ad hoc.
5. Never install project packages into `base`.

### Existing environments

- `python310` for general-purpose work
- `browser-use` for browser automation
- `opencausality` for causal inference
- `scraping` for web scraping

Before creating a new environment, check whether an existing one already covers the project with `conda env list` and `conda list -n <env>`.

## Document Handling Policy

When any document is provided as input, save a copy into the relevant project folder such as `data/`, `docs/`, or another context-appropriate subdirectory before processing it.

## Git Commit and Push Policy

When asked to `commit and push`, break changes into logical feature-based commits and push without asking for confirmation.

## Global Skills

Available across projects via `~/.claude/skills/`:

- `red-green-tdd`: use for testable code changes with a failing-test-first workflow
- `linear-walkthrough`: use for execution tracing and danger-zone walkthroughs
- `numerical-cross-check`: use for financial or numerical consistency checks
- `brev-cli`: use for GPU and CPU cloud instance management

## Memory Policy

Every project should have a memory file. At the end of a session, or when asked to save memory, persist key facts, decisions, contacts, action items, and conventions to the project memory file and keep it concise and organized by topic.
