import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.grafana_client import grafana_client

@pytest.mark.asyncio
async def test_grafana_cloud_live_connection():
    """Verifies live connection and datasource discovery on joyfuljasmine1550.grafana.net."""
    health = await grafana_client.check_health()
    assert health["connected"] is True
    assert health["status"] == "HEALTHY"
    assert health["datasources_count"] >= 5

@pytest.mark.asyncio
async def test_grafana_dashboard_annotation_live():
    """Verifies that the agent can programmatically write annotations to the live Grafana Cloud dashboard."""
    result = await grafana_client.create_annotation(
        text="[Continuity Pytest Verification]: Automated SRE Health Check Succeeded",
        tags=["continuity", "pytest", "automated-check", "sre-agent"]
    )
    assert result is not None
    assert "id" in result or result.get("message") == "Annotation added" or "status" in result

@pytest.mark.asyncio
async def test_grafana_dashboard_discovery_live():
    """Verifies that the provisioned CONTINUITY dashboard exists and is discoverable on Grafana Cloud."""
    search_res = await grafana_client.search_dashboards("CONTINUITY")
    assert search_res["status"] == "success"
    dashboards = search_res.get("dashboards", [])
    continuity_dashboards = [d for d in dashboards if "continuity" in d.get("uid", "").lower() or "continuity" in d.get("title", "").lower()]
    assert len(continuity_dashboards) >= 1
    assert any(d["uid"] == "continuity-premiere-hud" for d in continuity_dashboards)

@pytest.mark.asyncio
async def test_grafana_irm_incident_live():
    """Verifies programmatic creation of structured incident records in Grafana Cloud."""
    incident = await grafana_client.create_incident(
        title="Pytest SRE Health Verification",
        severity="CRITICAL",
        summary="Automated verification of Grafana Cloud incident lifecycle."
    )
    assert incident["status"] == "success"
    assert "incident_id" in incident or "incident" in incident

