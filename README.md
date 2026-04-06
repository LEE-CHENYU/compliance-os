# Compliance OS

Compliance OS is a continuous compliance workbench for immigrants and international founders. This repository contains the live Guardian product surface: a FastAPI backend, a Next.js frontend, and the deterministic rules and evidence pipeline behind the workspace.

## What Exists In This Repo

- authenticated web app for document-driven compliance work
- document intake, extraction, review, and retrieval flows
- dashboard timeline with deadlines, risks, and integrity issues
- grounded chat and form-fill APIs
- Fly.io deployment for the combined app

## Canonical Docs

- [README.md](/Users/lichenyu/compliance-os/README.md): repo entry point and local setup
- [docs/product_master.md](/Users/lichenyu/compliance-os/docs/product_master.md): durable product truth
- [docs/mvp_engineering.md](/Users/lichenyu/compliance-os/docs/mvp_engineering.md): current MVP boundary
- [docs/roadmap.md](/Users/lichenyu/compliance-os/docs/roadmap.md): active roadmap, backlog rules, and execution model
- [docs/deployment.md](/Users/lichenyu/compliance-os/docs/deployment.md): production deploy path

`docs/superpowers/` contains design records and implementation notes. It is useful reference material, but it is not the day-to-day execution source of truth.

## Repo Shape

- `compliance_os/`: backend app, compliance engine, and services
- `frontend/`: Next.js app for the Guardian workspace
- `config/`: rules, manifests, and environment-facing config
- `tests/`: backend regression coverage
- `docs/`: product, engineering, roadmap, and deployment docs

## Local Development

The repo already has a `compliance-os` conda environment.

```bash
conda activate compliance-os
pip install -e ".[dev]"
cd frontend && npm install
```

Run the app in two terminals:

```bash
uvicorn compliance_os.web.app:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

Backend runs on `http://localhost:8000`. Frontend runs on `http://localhost:3000`.

## Working Rule

Keep planning lean: roadmap in [docs/roadmap.md](/Users/lichenyu/compliance-os/docs/roadmap.md), backlog in GitHub Issues, execution in small PRs.
