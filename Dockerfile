# === Stage 1: Install Next.js production dependencies ===
# We DON'T run `next build` inside this stage anymore — Next's compile
# step hangs 25+ minutes under QEMU amd64-on-arm64 emulation on Apple
# Silicon. Instead, the developer runs `cd frontend && npm run build`
# on the host (arm64 native, ~5 min), and we copy the prebuilt
# .next/ + public/ into the runtime stage. .next contains portable JS
# only — no native binaries — so an arm64-built bundle runs on amd64.
#
# This stage exists solely to install the linux/amd64 node_modules
# (which DO have native binaries: SWC, sharp, esbuild, etc.) that
# `next start` needs at runtime.
FROM node:20-bookworm-slim AS frontend-deps
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --omit=dev
RUN npm install --no-save @next/swc-linux-x64-gnu@14.2.33

# === Stage 2: Python backend + serve everything ===
# Pin to bookworm — python:3.11-slim recently rolled to trixie, where
# libgdk-pixbuf-2.0-0, libharfbuzz0b, shared-mime-info, fonts-liberation
# were renamed/restructured. The package names below are bookworm-correct
# and have shipped successfully many times. When ready to upgrade, also
# update the names (libgdk-pixbuf2.0-0, etc.) in one coordinated change.
FROM python:3.11-slim-bookworm
WORKDIR /app

# Install system deps + Node.js
# WeasyPrint needs cairo, pango, and gdk-pixbuf for HTML→PDF rendering;
# fonts-liberation gives it a serif/sans set so reports render even without
# any user-supplied fonts.
RUN printf 'Acquire::Retries "5";\nAcquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n' > /etc/apt/apt.conf.d/80-retries && \
    find /etc/apt -type f \( -name '*.sources' -o -name '*.list' \) -print0 | \
      xargs -0 -r sed -i 's|http://deb.debian.org|https://deb.debian.org|g' && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev curl \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libharfbuzz0b shared-mime-info fonts-liberation && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Caddy binary directly
RUN curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=amd64" -o /usr/local/bin/caddy && \
    chmod +x /usr/local/bin/caddy

# Install Python deps. Fly remote/local builders can have brief PyPI stalls;
# use longer pip timeouts so deploys do not fail on a single slow wheel.
RUN pip install --no-cache-dir --timeout 120 --retries 10 \
    fastapi uvicorn sqlalchemy python-multipart pymupdf openai \
    "psycopg[binary]" \
    python-dotenv pydantic pydantic-settings pyyaml python-dateutil \
    rapidfuzz bcrypt pyjwt anthropic mistralai google-generativeai \
    weasyprint stripe

# Copy application code. templates/ moved into compliance_os/templates/
# in commit 18ec873 so it ships inside the wheel; no separate COPY needed.
COPY compliance_os/ ./compliance_os/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Copy frontend artifacts. .next and public come from the host-prebuilt
# directory (build context); node_modules + linux/amd64 SWC come from
# the frontend-deps stage above.
COPY frontend/.next ./frontend/.next
COPY frontend/public ./frontend/public
COPY frontend/package*.json ./frontend/
COPY frontend/next.config.mjs ./frontend/
COPY --from=frontend-deps /app/frontend/node_modules ./frontend/node_modules

# Create directories
RUN mkdir -p /data /uploads

# Config files
COPY Caddyfile ./
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 8080
CMD ["./start.sh"]
