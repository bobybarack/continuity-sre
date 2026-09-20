from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.chaos import router as chaos_router
from routes.telemetry import router as telemetry_router
from routes.agent import router as agent_router
from services.telemetry import telemetry_engine
from config import (
    STREAM_TITLE,
    GOOGLE_CLOUD_PROJECT,
    GRAFANA_INSTANCE_URL,
    GEMINI_MODEL
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await telemetry_engine.start()
    yield
    await telemetry_engine.stop()

app = FastAPI(
    title="Continuity API",
    description="Autonomous Stream Continuity Incident Commander (Grafana Cloud MCP & Gemini)",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local dev and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(chaos_router)
app.include_router(telemetry_router)
app.include_router(agent_router)

@app.get("/")
async def root_info():
    return {
        "project": "Continuity: Autonomous Stream Continuity Incident Commander",
        "stream": STREAM_TITLE,
        "google_cloud_project": GOOGLE_CLOUD_PROJECT,
        "grafana_instance": GRAFANA_INSTANCE_URL,
        "gemini_model": GEMINI_MODEL,
        "status": "OPERATIONAL",
        "endpoints": {
            "agent_status": "/api/agent/status",
            "agent_mcp_tools": "/api/agent/mcp-tools",
            "agent_investigate_and_remediate": "/api/agent/investigate-and-remediate",
            "agent_history": "/api/agent/history",
            "telemetry_current": "/api/telemetry/current",
            "telemetry_stream_sse": "/api/telemetry/stream",
            "telemetry_history": "/api/telemetry/history",
            "telemetry_metrics_prometheus": "/api/telemetry/metrics",
            "grafana_health": "/api/telemetry/grafana-health",
            "chaos_state": "/api/chaos/state",
            "inject_cdn_outage": "/api/chaos/inject-cdn-outage",
            "inject_drm_timeout": "/api/chaos/inject-drm-timeout",
            "inject_isp_drop": "/api/chaos/inject-isp-drop",
            "remediate_outage": "/api/chaos/remediate",
            "reset_chaos": "/api/chaos/reset"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
