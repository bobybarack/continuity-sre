import pytest
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app
from config import CONTINUITY_DEMO_KEY

@pytest.mark.asyncio
async def test_public_get_endpoints_work_unauthenticated():
    """Public read-only endpoints are accessible without demo key."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Current telemetry
        res_current = await client.get("/api/telemetry/current")
        assert res_current.status_code == 200
        
        # Chaos state
        res_chaos = await client.get("/api/chaos/state")
        assert res_chaos.status_code == 200
        
        # Agent status
        res_status = await client.get("/api/agent/status")
        assert res_status.status_code == 200

@pytest.mark.asyncio
async def test_mutation_endpoint_fails_without_key():
    """Mutation endpoints reject unauthenticated requests with 401 Unauthorized."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_inject = await client.post("/api/chaos/inject-cdn-outage")
        assert res_inject.status_code == 401
        assert "Missing required X-Continuity-Demo-Key" in res_inject.json()["detail"]

        res_reset = await client.post("/api/chaos/reset")
        assert res_reset.status_code == 401

        res_investigate = await client.post("/api/agent/investigate-and-remediate")
        assert res_investigate.status_code == 401

@pytest.mark.asyncio
async def test_mutation_endpoint_fails_with_invalid_key():
    """Mutation endpoints reject invalid keys with 403 Forbidden."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/chaos/inject-cdn-outage",
            headers={"X-Continuity-Demo-Key": "unauthorized-fraudulent-key"}
        )
        assert res.status_code == 403
        assert "Invalid X-Continuity-Demo-Key" in res.json()["detail"]

@pytest.mark.asyncio
async def test_mutation_endpoint_succeeds_with_valid_key():
    """Mutation endpoints succeed when the authentic demo key is provided."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/chaos/inject-cdn-outage",
            headers={"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["is_outage_active"] is True
        
        # Reset with key
        res_reset = await client.post(
            "/api/chaos/reset",
            headers={"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY}
        )
        assert res_reset.status_code == 200
        assert res_reset.json()["is_outage_active"] is False
