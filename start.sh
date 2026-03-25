#!/bin/sh
set -e

# Use /data volume for SQLite database
export DATA_DIR=/data

# Start Next.js frontend (production mode)
cd /app/frontend && PORT=3000 node_modules/.bin/next start &

# Start FastAPI backend
cd /app && uvicorn compliance_os.web.app:app --host 0.0.0.0 --port 8000 &

# Wait for services to start
sleep 2

# Start Caddy reverse proxy on port 8080
caddy run --config /app/Caddyfile --adapter caddyfile
