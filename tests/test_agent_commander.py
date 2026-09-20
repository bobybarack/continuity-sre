import pytest
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app
from services.agent_commander import agent_commander
from services.chaos import chaos_manager
from services.mcp_service import official_mcp_bridge

def test_agent_configuration():
    """Verifies that the Gemini Agent is initialized with the valid Google Cloud API key and model."""
    assert agent_commander.is_configured() is True
    assert agent_commander.model_name in ["models/gemini-3.6-flash", "models/gemini-3.7-flash", "models/gemini-2.5-flash"]

@pytest.mark.asyncio
async def test_official_grafana_mcp_bridge_discovery():
    """Verifies that the official mcp-grafana runtime server exposes the full tool catalog over stdio."""
    tools = await official_mcp_bridge.list_official_tools()
    assert len(tools) >= 50
    tool_names = [t["name"] for t in tools]
    assert "query_prometheus" in tool_names
    assert "query_loki_logs" in tool_names
    assert "create_annotation" in tool_names
    assert "create_incident" in tool_names

@pytest.mark.asyncio
async def test_agent_healthy_stream_evaluation():
    """Verifies that when metrics are nominal, the agent confirms healthy status without false alarms."""
    chaos_manager.reset_to_normal()
    result = await agent_commander.investigate_and_remediate()
    
    assert result.initial_anomaly_detected is False
    assert result.severity == "HEALTHY"
    assert result.vpf_rate < 0.5
    assert len(result.reasoning_trace) >= 2
    assert "HEALTHY" in result.reasoning_trace[-1]

@pytest.mark.asyncio
async def test_agent_autonomous_outage_remediation_live():
    """Verifies that upon detecting a live outage, Gemini diagnoses root cause and autonomously remediates."""
    # 1. Inject live CDN Outage
    chaos_manager.inject_cdn_outage()
    
    # 2. Trigger Autonomous SRE Investigation
    result = await agent_commander.investigate_and_remediate()
    
    # 3. Assert Autonomous Reasoning & Action
    assert result.initial_anomaly_detected is True
    assert result.severity in ["CRITICAL", "WARNING"]
    assert result.root_cause_analysis is not None
    assert len(result.root_cause_analysis) > 10
    assert result.autonomous_action_taken in ["SHIFT_TRAFFIC_TO_AKAMAI", "FAILOVER_DRM_KEY_CLUSTER", "REROUTE_BGP_TRANSIT"]
    assert result.traffic_shift_details["secondary_cdn_pct"] == 80
    assert result.mttr_seconds > 0.0
    assert "churn" in result.estimated_subscriber_loss_prevented.lower() or "$" in result.estimated_subscriber_loss_prevented
    assert len(result.reasoning_trace) >= 5
    
    # Assert Official Grafana MCP Tool Execution
    assert "grafana_query_prometheus" in result.mcp_tools_executed
    assert "grafana_query_loki" in result.mcp_tools_executed
    assert "continuity_execute_remediation" in result.mcp_tools_executed
    assert "grafana_create_annotation" in result.mcp_tools_executed
    assert "continuity_verify_closed_loop_recovery" in result.mcp_tools_executed
    
    # Assert Falsifiable Closed-Loop Recovery Verification
    assert result.closed_loop_verified is True
    assert result.verified_vpf_rate <= 0.5
    
    # 4. Verify system state recovered
    state = chaos_manager.get_state()
    assert state.lifecycle == "VERIFIED_RECOVERED"
    assert state.current_mode == "REMEDIATED"
    assert state.is_outage_active is False

@pytest.mark.asyncio
async def test_agent_api_endpoints():
    """Verifies REST endpoints for triggering investigations and retrieving audit history."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check Agent Status
        res_status = await client.get("/api/agent/status")
        assert res_status.status_code == 200
        data_status = res_status.json()
        assert data_status["configured"] is True
        assert "gemini" in data_status["model"]

        # Check Official MCP Tool Catalog
        res_mcp = await client.get("/api/agent/mcp-tools")
        assert res_mcp.status_code == 200
        data_mcp = res_mcp.json()
        assert data_mcp["status"] == "CONNECTED"
        assert data_mcp["total_tools"] >= 50
        
        # Trigger Investigation Endpoint (protected by demo key)
        from config import CONTINUITY_DEMO_KEY
        auth_headers = {"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY}
        res_inv = await client.post("/api/agent/investigate-and-remediate", headers=auth_headers)
        assert res_inv.status_code == 200
        data_inv = res_inv.json()
        assert "severity" in data_inv
        assert "root_cause_analysis" in data_inv
        assert "reasoning_trace" in data_inv
        
        # Retrieve Investigation History
        res_hist = await client.get("/api/agent/history")
        assert res_hist.status_code == 200
        data_hist = res_hist.json()
        assert isinstance(data_hist, list)
        assert len(data_hist) >= 1

@pytest.mark.asyncio
async def test_closed_loop_verifier_readback_and_pending_guard(monkeypatch):
    """Verifies that continuity_verify_closed_loop_recovery performs Prometheus read-back, and when PENDING, does not log 'Incident Resolved'."""
    from services.mcp_service import continuity_verify_closed_loop_recovery

    # 1. During an active un-remediated outage, verifier must return PENDING
    chaos_manager.inject_cdn_outage()
    verify_pending = await continuity_verify_closed_loop_recovery()
    assert verify_pending["status"] == "PENDING"
    assert verify_pending["verified"] is False
    assert verify_pending["prometheus_query"] == "ott_video_playback_failures_ratio"
    assert "prometheus_readback_status" in verify_pending

    # 2. When verification returns PENDING, agent must NOT log 'Incident Resolved'
    async def mock_pending_verify():
        return {
            "status": "PENDING",
            "verified": False,
            "prometheus_query": "ott_video_playback_failures_ratio",
            "prometheus_readback_status": "success",
            "prometheus_metric_value": 0.85,
            "current_vpf_pct": 2.4,
            "vpf_sla_target": 0.5,
            "forward_buffer_sec": 8.5,
            "buffer_target_sec": 20.0,
            "cdn_latency_ms": 310.0
        }

    monkeypatch.setattr("services.agent_commander.continuity_verify_closed_loop_recovery", mock_pending_verify)
    monkeypatch.setattr("services.mcp_service.continuity_verify_closed_loop_recovery", mock_pending_verify)
    result = await agent_commander.investigate_and_remediate()

    assert result.closed_loop_verified is False
    assert any("CLOSED-LOOP VERIFICATION PENDING" in line for line in result.reasoning_trace)
    assert not any("Incident Resolved" in line for line in result.reasoning_trace)
    assert "PENDING" in result.executive_summary

@pytest.mark.asyncio
async def test_verifier_fail_closed_on_unparseable_prometheus(monkeypatch):
    """Verifies that verification fails closed if authoritative Prometheus metrics cannot be parsed, even with nominal simulator telemetry."""
    from services.mcp_service import continuity_verify_closed_loop_recovery
    from services.telemetry import PREMIERE_REGISTRY

    # Ensure simulator is in healthy/normal mode
    chaos_manager.reset_to_normal()

    # Simulate unparseable Prometheus payload and empty registry collection
    async def mock_corrupt_prometheus(promql):
        return {"status": "error", "code": 500, "response": "unparseable_corrupt_metric_stream"}

    monkeypatch.setattr("services.mcp_service.grafana_query_prometheus", mock_corrupt_prometheus)
    monkeypatch.setattr(PREMIERE_REGISTRY, "collect", lambda: [])

    verify_res = await continuity_verify_closed_loop_recovery()
    assert verify_res["status"] == "PENDING"
    assert verify_res["verified"] is False
    assert verify_res["prometheus_value_available"] is False
    assert verify_res["prometheus_authoritative"] is False
    assert verify_res["verification_source_trusted"] is False
    assert verify_res["prometheus_metric_value"] is None

@pytest.mark.asyncio
async def test_verifier_metadata_source_differentiation():
    """Verifies that local registry read-back sets prometheus_value_available=True, verification_source_trusted=True, and prometheus_authoritative=False."""
    from services.mcp_service import continuity_verify_closed_loop_recovery

    chaos_manager.reset_to_normal()
    verify_res = await continuity_verify_closed_loop_recovery()

    assert verify_res["status"] == "PASSED"
    assert verify_res["verified"] is True
    assert verify_res["prometheus_value_available"] is True
    assert verify_res["verification_source_trusted"] is True
    # In local testing without remote Grafana Prometheus push, authoritative remote is False
    if verify_res["prometheus_source"] == "prometheus_collector_registry":
        assert verify_res["prometheus_authoritative"] is False
    elif verify_res["prometheus_source"] == "grafana_cloud_prometheus":
        assert verify_res["prometheus_authoritative"] is True



