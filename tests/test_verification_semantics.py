import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.mcp_service import continuity_verify_closed_loop_recovery, _evaluate_single_recovery_sample
from services.agent_commander import agent_commander
from services.chaos import chaos_manager
from services.telemetry import telemetry_engine

@pytest.mark.asyncio
async def test_remote_source_success():
    """Remote Grafana Prometheus provides healthy metric: authoritative and trusted."""
    chaos_manager.reset_to_normal()
    telemetry_engine._tick()
    mock_prom = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"__name__": "ott_video_playback_failures_ratio"},
                    "value": [1789900000.0, "0.002"] # 0.2% VPF
                }
            ]
        }
    }
    with patch("services.mcp_service.grafana_query_prometheus", new=AsyncMock(return_value=mock_prom)):
        with patch("config.VERIFICATION_POLICY", "remote_preferred"):
            evidence = await _evaluate_single_recovery_sample()
            assert evidence["status"] == "PASSED"
            assert evidence["verified"] is True
            assert evidence["prometheus_source"] == "grafana_cloud_prometheus"
            assert evidence["prometheus_authoritative"] is True
            assert evidence["verification_source_trusted"] is True
            assert evidence["prometheus_metric_value"] == 0.2

@pytest.mark.asyncio
async def test_local_fallback_success():
    """Remote Prometheus unavailable, policy allows local fallback: trusted but not authoritative."""
    chaos_manager.reset_to_normal()
    telemetry_engine._tick()
    # Remote query fails or returns empty
    with patch("services.mcp_service.grafana_query_prometheus", new=AsyncMock(return_value={"status": "error"})):
        with patch("config.VERIFICATION_POLICY", "remote_preferred"):
            evidence = await _evaluate_single_recovery_sample()
            assert evidence["status"] == "PASSED"
            assert evidence["verified"] is True
            assert evidence["prometheus_source"] == "prometheus_collector_registry"
            assert evidence["prometheus_authoritative"] is False
            assert evidence["verification_source_trusted"] is True
            assert evidence["prometheus_value_available"] is True

@pytest.mark.asyncio
async def test_remote_required_fails_when_remote_unavailable():
    """Policy 'remote_required' fails closed when remote Grafana Prometheus is unavailable."""
    chaos_manager.reset_to_normal()
    with patch("services.mcp_service.grafana_query_prometheus", new=AsyncMock(return_value=None)):
        with patch("config.VERIFICATION_POLICY", "remote_required"):
            evidence = await _evaluate_single_recovery_sample()
            assert evidence["status"] == "PENDING"
            assert evidence["verified"] is False
            assert evidence["prometheus_source"] == "none"
            assert evidence["prometheus_value_available"] is False
            assert evidence["verification_source_trusted"] is False
            assert evidence["prometheus_authoritative"] is False

@pytest.mark.asyncio
async def test_remote_value_unhealthy_returns_pending():
    """Remote value exceeds 0.5% SLA threshold: verification returns PENDING."""
    chaos_manager.reset_to_normal()
    mock_prom = {
        "status": "success",
        "data": {
            "result": [
                {
                    "metric": {},
                    "value": [1789900000.0, "0.048"] # 4.8% VPF > 0.5% SLA
                }
            ]
        }
    }
    with patch("services.mcp_service.grafana_query_prometheus", new=AsyncMock(return_value=mock_prom)):
        evidence = await _evaluate_single_recovery_sample()
        assert evidence["status"] == "PENDING"
        assert evidence["verified"] is False
        assert evidence["prometheus_source"] == "grafana_cloud_prometheus"
        assert evidence["prometheus_metric_value"] == 4.8

@pytest.mark.asyncio
async def test_agent_investigation_stores_verifier_evidence_directly():
    """InvestigationResult matches the exact evidence produced by the verifier."""
    chaos_manager.inject_cdn_outage()
    mock_verify = {
        "status": "PASSED",
        "verified": True,
        "current_vpf_pct": 0.22,
        "forward_buffer_sec": 26.4,
        "cdn_latency_ms": 68.5,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_authoritative": True,
        "verification_source_trusted": True
    }
    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value={"status": "success"})), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=[])), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value={"id": "INC-TEST-123"})), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value={"id": 456})), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        assert res.closed_loop_verified is True
        assert res.verified_vpf_rate == 0.22
        assert res.verified_buffer_health_sec == 26.4
        assert res.verified_latency_ms == 68.5
        assert res.verification_source == "grafana_cloud_prometheus"
        assert res.verification_authoritative is True
        assert res.verification_status == "PASSED"
