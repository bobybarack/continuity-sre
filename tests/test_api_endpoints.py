import pytest
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app
from services.chaos import chaos_manager

@pytest.mark.asyncio
async def test_root_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "OPERATIONAL"
        assert "Continuity" in data["project"]
        assert "joyfuljasmine1550" in data["grafana_instance"]
        assert data["google_cloud_project"] == "premiereshield-cinema"

@pytest.mark.asyncio
async def test_telemetry_current_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/telemetry/current")
        assert res.status_code == 200
        data = res.json()
        assert "video_playback_failures_pct" in data
        assert "cdn_egress_latency_ms" in data
        assert "active_viewers" in data

@pytest.mark.asyncio
async def test_telemetry_history_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/telemetry/history")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/telemetry/metrics")
        assert res.status_code == 200
        assert "text/plain" in res.headers["content-type"] or "version=0.0.4" in res.headers["content-type"]
        text = res.text
        assert "ott_video_playback_failures_ratio" in text

@pytest.mark.asyncio
async def test_chaos_lifecycle_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Reset
        res_reset = await client.post("/api/chaos/reset")
        assert res_reset.status_code == 200
        assert res_reset.json()["current_mode"] == "NORMAL"
        
        # Inject Outage
        res_inject = await client.post("/api/chaos/inject-cdn-outage")
        assert res_inject.status_code == 200
        assert res_inject.json()["current_mode"] == "CDN_OUTAGE"
        assert res_inject.json()["is_outage_active"] is True
        
        # Verify Telemetry shows outage
        res_tel = await client.get("/api/telemetry/current")
        assert res_tel.json()["status_label"] == "CRITICAL_OUTAGE"
        
        # Remediate
        res_rem = await client.post("/api/chaos/remediate", json={"action": "SHIFT_TRAFFIC_TO_AKAMAI"})
        assert res_rem.status_code == 200
        assert res_rem.json()["lifecycle"] == "RECOVERING"
        assert res_rem.json()["is_outage_active"] is True
        assert res_rem.json()["secondary_cdn_traffic_pct"] == 80
        
        # Reset back
        res_reset2 = await client.post("/api/chaos/reset")
        assert res_reset2.status_code == 200
        assert res_reset2.json()["current_mode"] == "NORMAL"
        assert res_reset2.json()["lifecycle"] == "NORMAL"
        assert res_reset2.json()["is_outage_active"] is False
