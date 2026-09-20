import pytest
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.agent_commander import agent_commander
from services.chaos import chaos_manager
from services.telemetry import telemetry_engine
from services.scenarios import SCENARIOS

@pytest.mark.asyncio
async def test_cdn_outage_selects_cdn_promql_and_logql():
    """CDN outage investigation queries edge-router PromQL and LogQL."""
    chaos_manager.inject_cdn_outage()
    
    mock_prom = AsyncMock(return_value={"status": "success"})
    mock_loki = AsyncMock(return_value=[])
    mock_verify = {
        "status": "PASSED",
        "verified": True,
        "current_vpf_pct": 0.18,
        "forward_buffer_sec": 25.0,
        "cdn_latency_ms": 60.0,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_authoritative": True,
        "verification_source_trusted": True
    }
    
    with patch("services.agent_commander.grafana_query_prometheus", mock_prom), \
         patch("services.agent_commander.grafana_query_loki", mock_loki), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value={"id": "INC-CDN-1"})), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value={"id": 1})), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        
        # Verify PromQL query
        mock_prom.assert_called_with("ott_video_playback_failures_ratio")
        # Verify LogQL query
        mock_loki.assert_called_with('{service="ott-edge-router"} |= "502 Bad Gateway"', limit=20)
        # Verify remediation action
        assert res.remediation_action == "SHIFT_TRAFFIC_TO_AKAMAI"
        assert res.failure_mode == "CDN_OUTAGE"

@pytest.mark.asyncio
async def test_drm_timeout_selects_drm_promql_and_logql():
    """DRM timeout investigation queries DRM handshake PromQL and auth-proxy LogQL."""
    chaos_manager.inject_drm_timeout()
    
    mock_prom = AsyncMock(return_value={"status": "success"})
    mock_loki = AsyncMock(return_value=[])
    mock_verify = {
        "status": "PASSED",
        "verified": True,
        "current_vpf_pct": 0.20,
        "forward_buffer_sec": 25.0,
        "cdn_latency_ms": 60.0,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_authoritative": True,
        "verification_source_trusted": True
    }
    
    with patch("services.agent_commander.grafana_query_prometheus", mock_prom), \
         patch("services.agent_commander.grafana_query_loki", mock_loki), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value={"id": "INC-DRM-1"})), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value={"id": 2})), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        
        # Verify PromQL query
        mock_prom.assert_called_with("ott_drm_handshake_ms")
        # Verify LogQL query
        mock_loki.assert_called_with('{service="drm-auth-proxy"} |= "504 Gateway Timeout"', limit=20)
        # Verify remediation action
        assert res.remediation_action == "FAILOVER_DRM_KEY_CLUSTER"
        assert res.failure_mode == "DRM_TIMEOUT"

@pytest.mark.asyncio
async def test_isp_peering_drop_selects_transit_promql_and_logql():
    """ISP peering drop investigation queries bitrate PromQL and transit monitor LogQL."""
    chaos_manager.inject_isp_peering_drop()
    
    mock_prom = AsyncMock(return_value={"status": "success"})
    mock_loki = AsyncMock(return_value=[])
    mock_verify = {
        "status": "PASSED",
        "verified": True,
        "current_vpf_pct": 0.22,
        "forward_buffer_sec": 25.0,
        "cdn_latency_ms": 60.0,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_authoritative": True,
        "verification_source_trusted": True
    }
    
    with patch("services.agent_commander.grafana_query_prometheus", mock_prom), \
         patch("services.agent_commander.grafana_query_loki", mock_loki), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value={"id": "INC-ISP-1"})), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value={"id": 3})), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch.object(agent_commander, "client", None):
        res = await agent_commander.investigate_and_remediate()
        
        # Verify PromQL query
        mock_prom.assert_called_with("ott_stream_bitrate_mbps")
        # Verify LogQL query
        mock_loki.assert_called_with('{service="transit-monitor"} |= "ASN 3356"', limit=20)
        # Verify remediation action
        assert res.remediation_action == "REROUTE_BGP_TRANSIT"
        assert res.failure_mode == "ISP_PEERING_DROP"
