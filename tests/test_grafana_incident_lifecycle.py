import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.mcp_service import normalize_incident_result, normalize_annotation_result, grafana_resolve_incident
from services.agent_commander import agent_commander
from services.chaos import chaos_manager

def test_normalize_incident_result_mcp_format():
    """Normalizes incident from MCP format with id and status."""
    raw = {"id": "INC-MCP-001", "title": "Outage", "severity": "CRITICAL", "status": "active"}
    norm = normalize_incident_result(raw)
    assert norm["incident_id"] == "INC-MCP-001"
    assert norm["title"] == "Outage"
    assert norm["severity"] == "CRITICAL"
    assert norm["lifecycle_status"] == "active"

def test_normalize_incident_result_nested_format():
    """Normalizes incident from nested API format."""
    raw = {
        "status": "success",
        "incident": {
            "id": "INC-NESTED-002",
            "title": "Degraded Stream",
            "severity": "WARNING",
            "status": "investigating"
        }
    }
    norm = normalize_incident_result(raw)
    assert norm["incident_id"] == "INC-NESTED-002"
    assert norm["title"] == "Degraded Stream"
    assert norm["severity"] == "WARNING"
    assert norm["lifecycle_status"] == "investigating"

def test_normalize_annotation_result_formats():
    """Normalizes annotation results from direct and MCP payload formats."""
    raw_mcp = {"Payload": {"id": 101, "message": "Annotation added"}}
    norm_mcp = normalize_annotation_result(raw_mcp)
    assert norm_mcp["id"] == 101

    raw_direct = {"id": 202, "text": "Pin added"}
    norm_direct = normalize_annotation_result(raw_direct)
    assert norm_direct["id"] == 202

@pytest.mark.asyncio
async def test_passed_verification_resolves_grafana_incident():
    """When verification passes, the Grafana incident is resolved."""
    chaos_manager.inject_cdn_outage()
    
    mock_verify = {
        "status": "PASSED",
        "verified": True,
        "current_vpf_pct": 0.2,
        "forward_buffer_sec": 26.0,
        "cdn_latency_ms": 65.0,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_authoritative": True,
        "verification_source_trusted": True
    }
    mock_create_inc = AsyncMock(return_value={"incident_id": "INC-RESOLVE-100", "status": "success"})
    mock_resolve_inc = AsyncMock(return_value={"incident_id": "INC-RESOLVE-100", "lifecycle_status": "resolved"})
    
    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value={"status": "success"})), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=[])), \
         patch("services.agent_commander.grafana_create_incident", mock_create_inc), \
         patch("services.agent_commander.grafana_resolve_incident", mock_resolve_inc), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value={"id": 1})), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        
        assert res.closed_loop_verified is True
        assert res.grafana_incident_id == "INC-RESOLVE-100"
        mock_resolve_inc.assert_called_once()
        assert mock_resolve_inc.call_args[1]["incident_id"] == "INC-RESOLVE-100"

@pytest.mark.asyncio
async def test_pending_verification_does_not_resolve_grafana_incident():
    """When verification is PENDING, the Grafana incident remains ACTIVE and resolve is NOT called."""
    chaos_manager.inject_cdn_outage()
    
    mock_verify = {
        "status": "PENDING",
        "verified": False,
        "current_vpf_pct": 2.5,
        "forward_buffer_sec": 10.0,
        "cdn_latency_ms": 250.0,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_authoritative": True,
        "verification_source_trusted": True
    }
    mock_create_inc = AsyncMock(return_value={"incident_id": "INC-STAYS-ACTIVE-200", "status": "success"})
    mock_resolve_inc = AsyncMock()
    
    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value={"status": "success"})), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=[])), \
         patch("services.agent_commander.grafana_create_incident", mock_create_inc), \
         patch("services.agent_commander.grafana_resolve_incident", mock_resolve_inc), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value={"id": 2})), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        
        assert res.closed_loop_verified is False
        assert res.verification_status == "PENDING"
        assert res.grafana_incident_id == "INC-STAYS-ACTIVE-200"
        # Must NOT have resolved the incident
        mock_resolve_inc.assert_not_called()

@pytest.mark.asyncio
async def test_grafana_resolve_incident_calls_official_update_incident():
    """Verifies that grafana_resolve_incident invokes official MCP tool update_incident with incidentId and resolved status."""
    from services.mcp_service import official_mcp_bridge
    mock_mcp_call = AsyncMock(return_value={
        "status": "resolved",
        "incident": {
            "id": "INC-MCP-999",
            "title": "Edge CDN Latency Spike",
            "status": "resolved"
        }
    })
    
    with patch.object(official_mcp_bridge, "call_official_tool", mock_mcp_call):
        res = await grafana_resolve_incident("INC-MCP-999", "Closed loop verification passed.")
        
        mock_mcp_call.assert_called_once_with("update_incident", {
            "incidentId": "INC-MCP-999",
            "status": "resolved"
        })
        assert res.source == "official_mcp"
        assert res.incident_id == "INC-MCP-999"
        assert res.lifecycle_status == "resolved"
        assert res.status == "success"

@pytest.mark.asyncio
async def test_grafana_resolve_incident_falls_back_to_direct_client():
    """Verifies that when official MCP update_incident fails, fallback to direct REST resolve_incident occurs."""
    from services.mcp_service import official_mcp_bridge, grafana_client
    mock_mcp_call = AsyncMock(return_value=None)
    mock_direct_resolve = AsyncMock(return_value={
        "status": "success",
        "incident_id": "INC-REST-888",
        "lifecycle_status": "resolved"
    })
    
    with patch.object(official_mcp_bridge, "call_official_tool", mock_mcp_call), \
         patch.object(grafana_client, "resolve_incident", mock_direct_resolve):
        res = await grafana_resolve_incident("INC-REST-888", "Closed loop verification passed.")
        
        mock_mcp_call.assert_called_once_with("update_incident", {
            "incidentId": "INC-REST-888",
            "status": "resolved"
        })
        mock_direct_resolve.assert_called_once_with("INC-REST-888", "Closed loop verification passed.")
        assert res.source == "direct_rest"
        assert res.incident_id == "INC-REST-888"
        assert res.lifecycle_status == "resolved"
