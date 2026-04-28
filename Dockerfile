# === Stage 1: Build Next.js frontend ===
# Pin to bookworm — node:20-slim is a rolling tag that recently moved to
# trixie, where some Debian package names changed (see stage 2 below).
FROM node:20-bookworm-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
RUN npm install --no-save @next/swc-linux-x64-gnu@14.2.33
COPY frontend/ ./
RUN npm run build

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

# Install Python deps
RUN pip install --no-cache-dir \
    fastapi uvicorn sqlalchemy python-multipart pymupdf openai \
    "psycopg[binary]" \
    python-dotenv pydantic pydantic-settings pyyaml python-dateutil \
    rapidfuzz bcrypt pyjwt anthropic mistralai google-generativeai \
    weasyprint stripe

# Copy application code
COPY compliance_os/ ./compliance_os/
COPY config/ ./config/
COPY templates/ ./templates/
COPY scripts/ ./scripts/

# Copy built frontend
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package*.json ./frontend/
COPY --from=frontend-build /app/frontend/node_modules ./frontend/node_modules
COPY --from=frontend-build /app/frontend/next.config.mjs ./frontend/

# Create directories
RUN mkdir -p /data /uploads

# Config files
COPY Caddyfile ./
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 8080
CMD ["./start.sh"]
