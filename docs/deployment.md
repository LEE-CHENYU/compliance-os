# Guardian — Deployment Guide

## Live URL

**https://guardian-compliance.fly.dev**

## Architecture

```
[Browser] → [Fly.io Machine]
                ↓
            [Caddy :8080]
            /api/* → FastAPI :8000
            /*     → Next.js :3000
```

Single Fly.io machine runs:
- **Caddy** reverse proxy on port 8080 (exposed to internet)
- **FastAPI** backend on port 8000 (Python + SQLAlchemy + SQLite)
- **Next.js** frontend on port 3000 (production mode)

## Infrastructure

| Component | Detail |
|---|---|
| App name | `guardian-compliance` |
| Region | `ewr` (Newark, US East) |
| VM | shared-cpu-1x, 512MB RAM |
| Volume | `guardian_data`, 1GB, mounted at `/data` |
| Database | SQLite at `/data/copilot.db` |
| Uploads | Stored at `/uploads/{check_id}/` |
| Auto-stop | Machine sleeps when idle, auto-starts on request |

## Secrets

Set via `flyctl secrets set`:

| Secret | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Sonnet 4.6 for document extraction (primary) |
| `OPENAI_API_KEY` | GPT-4.1-mini fallback for extraction |
| `JWT_SECRET` | JWT token signing for auth |

To view current secrets:
```bash
flyctl secrets list -a guardian-compliance
```

To update a secret:
```bash
flyctl secrets set KEY=value -a guardian-compliance
```

## Deploying

### Standard deploy (from project root):
```bash
flyctl deploy -a guardian-compliance
```

This builds the Docker image remotely on Fly's builders, pushes it, and deploys. Takes ~3-5 minutes.

### What happens during deploy:
1. Stage 1: Builds Next.js frontend (`npm run build`)
2. Stage 2: Installs Python deps, Node.js, Caddy
3. Copies built frontend + backend code into final image
4. Deploys to the machine, restarts services

### After deploy:
```bash
# Check status
flyctl status -a guardian-compliance

# Check logs
flyctl logs -a guardian-compliance

# SSH into the machine
flyctl ssh console -a guardian-compliance
```

## Key Files

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-stage build: Node.js frontend → Python backend |
| `Caddyfile` | Reverse proxy config: routes /api to backend, / to frontend |
| `start.sh` | Entrypoint: starts Next.js, FastAPI, then Caddy |
| `fly.toml` | Fly.io app config: region, VM size, volume mount |
| `.dockerignore` | Excludes dev files from Docker build |

## Environment Variables

| Var | Default | Description |
|---|---|---|
| `DATA_DIR` | `/data` (prod) or `./data` (dev) | SQLite database directory |
| `ANTHROPIC_API_KEY` | — | Claude API key for extraction |
| `OPENAI_API_KEY` | — | OpenAI fallback for extraction |
| `JWT_SECRET` | `guardian-dev-secret...` | JWT signing key |

## Local Development

```bash
# Backend (terminal 1)
conda activate compliance-os
uvicorn compliance_os.web.app:app --reload --port 8000

# Frontend (terminal 2)
cd frontend && npm run dev
```

Backend reads `.env` automatically via python-dotenv.
Frontend API client uses `localhost:8000` in dev, relative URLs in production.

## Volume & Data

The Fly volume persists across deploys. SQLite database and uploaded files survive redeployment.

```bash
# Check volume
flyctl volumes list -a guardian-compliance

# SSH in to inspect data
flyctl ssh console -a guardian-compliance
ls /data/
ls /uploads/
```

**Backup:** Fly takes automatic snapshots (5 retained). For manual backup:
```bash
flyctl ssh sftp get /data/copilot.db ./backup-copilot.db -a guardian-compliance
```

## Scaling

Current setup handles ~10-50 concurrent users. To scale:

1. **More RAM:** `flyctl scale memory 1024 -a guardian-compliance`
2. **More CPU:** Edit `fly.toml` → `size = "shared-cpu-2x"`
3. **Switch to Postgres:** When SQLite becomes a bottleneck, create a Fly Postgres cluster
4. **Multiple machines:** Add more machines for redundancy (requires Postgres, SQLite is single-writer)
5. **File storage:** Move uploads to S3/R2 when volume gets full

## Troubleshooting

**App not responding after deploy:**
```bash
flyctl logs -a guardian-compliance  # Check startup logs
flyctl ssh console -a guardian-compliance  # SSH in
ps aux  # Check if all 3 processes (caddy, uvicorn, next) are running
```

**Database migration needed:**
```bash
flyctl ssh console -a guardian-compliance
cd /app
python -c "
import sqlite3
conn = sqlite3.connect('/data/copilot.db')
conn.execute('ALTER TABLE checks ADD COLUMN new_column TEXT')
conn.commit()
"
```

**Machine won't start (auto-stop):**
The machine auto-stops after idle. First request may take 2-3 seconds as it cold-starts. This is normal for the free/low-cost tier.

## Cost

| Item | Monthly |
|---|---|
| shared-cpu-1x, 512MB | ~$3.19 (with auto-stop, less if idle) |
| 1GB volume | $0.15 |
| Outbound transfer | Free first 100GB |
| **Total** | **~$3-4/mo** |
