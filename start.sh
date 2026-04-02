#!/bin/sh
set -eu

# Use /data volume for SQLite database
export DATA_DIR=/data

# Start Next.js frontend (production mode)
cd /app/frontend && PORT=3000 node_modules/.bin/next start &

# Start FastAPI backend
cd /app && uvicorn compliance_os.web.app:app --host 0.0.0.0 --port 8000 &

wait_for_http() {
    url="$1"
    label="$2"
    attempts="${3:-60}"
    delay="${4:-1}"

    i=0
    while [ "$i" -lt "$attempts" ]; do
        if curl -fsS "$url" >/dev/null 2>&1; then
            return 0
        fi
        i=$((i + 1))
        sleep "$delay"
    done

    echo "Timed out waiting for $label at $url" >&2
    return 1
}

# Only start the public proxy after both app servers are actually ready.
wait_for_http "http://127.0.0.1:3000/" "Next.js frontend"
wait_for_http "http://127.0.0.1:8000/healthz" "FastAPI backend"

# Start Caddy reverse proxy on port 8080
caddy run --config /app/Caddyfile --adapter caddyfile
