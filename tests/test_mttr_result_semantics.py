import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.agent_commander import agent_commander
from services.chaos import chaos_manager
from services.telemetry import telemetry_engine

@pytest.mark.asyncio
async def test_healthy_workflow_has_null_mttr_and_not_required():
    """Healthy investigation: verification is NOT_REQUIRED and mttr_seconds is None."""
    chaos_manager.reset_to_normal()
    telemetry_engine._tick()
    
    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value={"status": "success"})), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        
        assert res.workflow_status == "HEALTHY"
        assert res.verification_status == "NOT_REQUIRED"
        assert res.mttr_seconds is None
        assert res.closed_loop_verified is False
        assert res.workflow_elapsed_seconds >= 0.0
        assert res.failure_mode == "NONE"

@pytest.mark.asyncio
async def test_passed_verification_has_mttr_equal_to_elapsed():
    """Verified recovery: MTTR is populated and matches workflow_elapsed_seconds."""
    chaos_manager.inject_cdn_outage()
    
    mock_verify = {
        "status": "PASSED",
        "verified": True,
        "current_vpf_pct": 0.18,
        "forward_buffer_sec": 27.2,
        "cdn_latency_ms": 62.0,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_authoritative": True,
        "verification_source_trusted": True
    }
    
    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value={"status": "success"})), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=[])), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value={"id": "INC-TEST-456"})), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value={"id": 789})), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        
        assert res.workflow_status == "RESOLVED"
        assert res.remediation_status == "SUCCESS"
        assert res.closed_loop_verified is True
        assert res.verification_status == "PASSED"
        assert res.mttr_seconds is not None
        assert res.mttr_seconds == res.workflow_elapsed_seconds
        assert res.failure_mode == "CDN_OUTAGE"

@pytest.mark.asyncio
async def test_pending_verification_has_null_mttr():
    """Unresolved/pending recovery: MTTR is None and workflow is PENDING_VERIFICATION."""
    chaos_manager.inject_cdn_outage()
    
    mock_verify = {
        "status": "PENDING",
        "verified": False,
        "current_vpf_pct": 2.45,
        "forward_buffer_sec": 8.0,
        "cdn_latency_ms": 280.0,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_authoritative": True,
        "verification_source_trusted": True
    }
    
    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value={"status": "success"})), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=[])), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value={"id": "INC-TEST-999"})), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value={"id": 101})), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        
        assert res.workflow_status == "PENDING_VERIFICATION"
        assert res.remediation_status == "PENDING_CONVERGENCE"
        assert res.closed_loop_verified is False
        assert res.verification_status == "PENDING"
        assert res.mttr_seconds is None
        assert res.workflow_elapsed_seconds >= 0.0
