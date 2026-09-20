import asyncio
import json
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST
from services.telemetry import telemetry_engine, TelemetrySnapshot
from services.grafana_client import grafana_client
from typing import List, Dict, Any

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry Stream"])

@router.get("/current", response_model=TelemetrySnapshot)
async def get_current_telemetry():
    """Returns the latest real-time snapshot of OTT streaming QoS metrics."""
    return telemetry_engine.get_current_snapshot()

@router.get("/history", response_model=List[TelemetrySnapshot])
async def get_telemetry_history():
    """Returns historical metric data points (last 60 seconds) for frontend charts."""
    return telemetry_engine.get_history()

@router.get("/grafana-health")
async def get_grafana_health():
    """Checks live connection status with Grafana Cloud Prometheus and Loki datasources."""
    return await grafana_client.check_health()

@router.get("/metrics")
async def prometheus_metrics():
    """Exposes standard OpenMetrics / Prometheus scrape endpoint for Grafana Agent."""
    metrics_data = telemetry_engine.get_prometheus_exposition()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

@router.get("/stream")
async def stream_telemetry_sse():
    """Server-Sent Events (SSE) endpoint providing a continuous 1Hz real-time telemetry feed."""
    async def event_generator():
        last_timestamp = None
        while True:
            snapshot = telemetry_engine.get_current_snapshot()
            if snapshot.timestamp != last_timestamp:
                last_timestamp = snapshot.timestamp
                data_json = json.dumps(snapshot.model_dump())
                yield f"data: {data_json}\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
