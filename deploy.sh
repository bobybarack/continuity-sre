#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Continuity: Google Cloud Run Automated Deployment Script
# ==============================================================================

PROJECT_ID="premiereshield-cinema"
REGION="us-central1"
SERVICE_NAME="continuity-api"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "=== Step 1: Validating Environment Configuration ==="
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found. Create .env before deploying."
    exit 1
fi

source .env

if [ -z "${GEMINI_API_KEY:-}" ] || [ -z "${GRAFANA_TOKEN:-}" ]; then
    echo "ERROR: GEMINI_API_KEY or GRAFANA_TOKEN missing from .env."
    exit 1
fi

echo "=== Step 2: Running Automated Pre-flight Test Suite ==="
.venv/bin/pytest -v tests/

echo "=== Step 3: Setting Google Cloud Project Configuration ==="
gcloud config set project "${PROJECT_ID}"

echo "=== Step 4: Submitting Container Build to Google Cloud Build ==="
gcloud builds submit --tag "${IMAGE_TAG}" .

echo "=== Step 5: Deploying Container to Google Cloud Run ==="
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_TAG}" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 10 \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars GEMINI_API_KEY="${GEMINI_API_KEY}",GEMINI_MODEL="${GEMINI_MODEL:-models/gemini-3.6-flash}",GRAFANA_INSTANCE_URL="${GRAFANA_INSTANCE_URL}",GRAFANA_TOKEN="${GRAFANA_TOKEN}",GRAFANA_PROM_UID="${GRAFANA_PROM_UID:-grafanacloud-prom}",GRAFANA_LOKI_UID="${GRAFANA_LOKI_UID:-grafanacloud-logs}",GOOGLE_CLOUD_PROJECT="${PROJECT_ID}"

echo "=== Deployment Complete: Public Live URL Generated ==="
gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)'
