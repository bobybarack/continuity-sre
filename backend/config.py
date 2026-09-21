import os
from pathlib import Path
from dotenv import load_dotenv

# Locate and load .env file from project root or current dir
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)

# Google Cloud & Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-3.6-flash")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "premiereshield-cinema")
GOOGLE_CLOUD_PROJECT_NUMBER = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER", "121300560395")

# Grafana Cloud Settings
GRAFANA_INSTANCE_URL = os.getenv("GRAFANA_INSTANCE_URL", "https://joyfuljasmine1550.grafana.net").rstrip("/")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN", "")
GRAFANA_PROM_UID = os.getenv("GRAFANA_PROM_UID", "grafanacloud-prom")
GRAFANA_LOKI_UID = os.getenv("GRAFANA_LOKI_UID", "grafanacloud-logs")
GRAFANA_TEMPO_UID = os.getenv("GRAFANA_TEMPO_UID", "grafanacloud-traces")

# Stream Simulation Metadata
STREAM_TITLE = "Continuity Premiere: Global Broadcast (Live 4K UHD)"
TOTAL_ACTIVE_VIEWERS_BASE = 4_281_900
TARGET_BITRATE_MBPS = 14.8
TARGET_BUFFER_HEALTH_SEC = 28.5

# Verification Policy ('remote_required', 'remote_preferred', 'local_allowed')
VERIFICATION_POLICY = os.getenv("VERIFICATION_POLICY", "remote_preferred")

# API Mutation Protection & CORS Settings
CONTINUITY_DEMO_KEY = os.getenv("CONTINUITY_DEMO_KEY", "continuity-demo-secret-2026")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000,https://continuity-sre.pages.dev"
    ).split(",")
    if origin.strip()
]
