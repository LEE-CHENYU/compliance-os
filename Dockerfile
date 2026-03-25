# === Stage 1: Build Next.js frontend ===
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# === Stage 2: Python backend + serve everything ===
FROM python:3.11-slim
WORKDIR /app

# Install system deps + Caddy for reverse proxy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev curl debian-keyring debian-archive-keyring apt-transport-https && \
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg && \
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list && \
    apt-get update && apt-get install -y caddy && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js for Next.js server
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    fastapi uvicorn sqlalchemy python-multipart pymupdf openai \
    python-dotenv pydantic pydantic-settings pyyaml python-dateutil \
    rapidfuzz bcrypt pyjwt

# Copy application code
COPY compliance_os/ ./compliance_os/
COPY config/ ./config/

# Copy built frontend
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package*.json ./frontend/
COPY --from=frontend-build /app/frontend/node_modules ./frontend/node_modules
COPY --from=frontend-build /app/frontend/next.config.mjs ./frontend/

# Create data and upload directories on the volume
RUN mkdir -p /data /uploads

# Caddy config
COPY Caddyfile ./

# Start script
COPY start.sh ./
RUN chmod +x start.sh

EXPOSE 8080

CMD ["./start.sh"]
