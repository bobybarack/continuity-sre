import pytest
import asyncio
from services.telemetry import (
    telemetry_engine,
    PROM_AGENT_GEMINI_LATENCY,
    PROM_AGENT_MCP_TOOL_CALLS,
    PROM_AGENT_REMEDIATIONS,
    PROM_AGENT_ROLLBACKS,
    PROM_AGENT_ESCALATIONS,
    PROM_AGENT_VERIFICATION_GATE_OUTCOME
)
from services.mcp_service import dispatch_mcp_tool
from services.chaos import chaos_manager, FailureMode
from services.transaction_manager import transaction_manager
from services.agent_commander import agent_commander

@pytest.mark.asyncio
async def test_agent_observability_metrics_in_prometheus_exposition():
    """Verifies that all agent self-observability metrics are exported in Prometheus format."""
    exposition = telemetry_engine.get_prometheus_exposition().decode("utf-8")
    assert "continuity_agent_gemini_latency_seconds" in exposition
    assert "continuity_agent_mcp_tool_calls_total" in exposition
    assert "continuity_agent_remediations_total" in exposition
    assert "continuity_agent_rollbacks_total" in exposition
    assert "continuity_agent_escalations_total" in exposition
    assert "continuity_agent_verification_gate_total" in exposition

@pytest.mark.asyncio
async def test_mcp_dispatcher_increments_tool_call_metrics():
    """Verifies that dispatching MCP tools updates Prometheus tool call counters."""
    initial_exp = telemetry_engine.get_prometheus_exposition().decode("utf-8")
    
    # Dispatch an MCP query
    res = await dispatch_mcp_tool("query_prometheus", {"expr": "ott_video_playback_failures_ratio"})
    assert res is not None
    
    updated_exp = telemetry_engine.get_prometheus_exposition().decode("utf-8")
    assert 'continuity_agent_mcp_tool_calls_total{status="success",tool_name="query_prometheus"}' in updated_exp

@pytest.mark.asyncio
async def test_transaction_remediation_metrics_recorded():
    """Verifies that transaction commit and rollback record metrics."""
    transaction_manager.clear()
    chaos_manager.reset()
    chaos_manager.inject_cdn_outage()
    
    # Execute transaction
    tx, is_new = transaction_manager.execute_transaction(
        incident_id="INC-METRIC-TEST",
        action="SHIFT_TRAFFIC_TO_AKAMAI",
        primary_cdn_pct=20,
        secondary_cdn_pct=80
    )
    assert is_new
    assert tx.status == "APPLIED"
    
    pre_snap = transaction_manager.build_health_snapshot()
    
    # Simulate convergence time so metrics reflect healthy recovered state
    import time
    chaos_manager.state.remediation_applied_at = time.time() - 5.0
    telemetry_engine._tick()

    # Verify and commit
    proof = transaction_manager.verify_and_commit(tx.transaction_id, pre_snap)
    assert proof.outcome == "PASSED"
    
    exposition = telemetry_engine.get_prometheus_exposition().decode("utf-8")
    assert 'continuity_agent_remediations_total{action="SHIFT_TRAFFIC_TO_AKAMAI",failure_mode="CDN_OUTAGE",status="COMMITTED"}' in exposition
    assert 'continuity_agent_verification_gate_total{failure_mode="CDN_OUTAGE",gate_name="Video Playback Failures (VPF)",outcome="PASSED"}' in exposition
