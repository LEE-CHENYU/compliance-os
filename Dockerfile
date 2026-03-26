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

# Install system deps + Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install Caddy binary directly
RUN curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=amd64" -o /usr/local/bin/caddy && \
    chmod +x /usr/local/bin/caddy

# Install Python deps
RUN pip install --no-cache-dir \
    fastapi uvicorn sqlalchemy python-multipart pymupdf openai \
    python-dotenv pydantic pydantic-settings pyyaml python-dateutil \
    rapidfuzz bcrypt pyjwt anthropic mistralai

# Copy application code
COPY compliance_os/ ./compliance_os/
COPY config/ ./config/

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
