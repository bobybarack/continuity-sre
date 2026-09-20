import pytest
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app

@pytest.mark.asyncio
async def test_healthz_probe_operational():
    """Verifies that /healthz responds with 200 and healthy status for process liveness."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/healthz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "HEALTHY"
        assert data["service"] == "continuity-api"

@pytest.mark.asyncio
async def test_readyz_probe_reflects_configuration(monkeypatch):
    """Verifies that /readyz responds with 200 when configured, and 503 if critical config missing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Nominal readiness check
        res = await client.get("/readyz")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "READY"
        assert data["telemetry_ready"] is True
        
        # 2. Simulate missing critical configuration
        import main
        monkeypatch.setattr(main, "STREAM_TITLE", "")
        res_unready = await client.get("/readyz")
        assert res_unready.status_code == 503
        assert "Required service configuration missing" in res_unready.json()["detail"]
