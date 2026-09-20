# Multi-stage production container for Continuity (FastAPI + Gemini + Grafana Cloud MCP)
FROM grafana/mcp-grafana:1.5.1 AS grafana-mcp
FROM python:3.11-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    PYTHONPATH=/app/backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy official Grafana MCP binary from Grafana Labs official image
COPY --from=grafana-mcp /app/mcp-grafana /usr/local/bin/mcp-grafana
RUN chmod +x /usr/local/bin/mcp-grafana || true

# Install locked Python requirements for deterministic reproducible build
COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir -r /app/backend/requirements.lock

# Copy source code and configuration (frontend is deployed separately on Cloudflare Pages)
COPY backend /app/backend

# Create non-root system user for runtime isolation
RUN groupadd -r continuity && useradd -r -g continuity -d /app -s /sbin/nologin continuity \
    && chown -R continuity:continuity /app

USER continuity

# Expose standard Cloud Run port
EXPOSE 8080

# Healthcheck probe using dedicated /healthz
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/healthz || exit 1

# Start production ASGI server
CMD ["sh", "-c", "exec uvicorn main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8080}"]
