import pytest
import asyncio
import time
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.chaos import chaos_manager, IncidentLifecycle
from services.telemetry import telemetry_engine
from services.mcp_service import continuity_verify_closed_loop_recovery

from contextlib import asynccontextmanager

@pytest.fixture(autouse=True)
def mock_remote_prometheus(monkeypatch):
    """Bypasses slow stdio process spawning during deterministic convergence unit tests, falling back to authoritative local registry."""
    async def _mock_remote(promql):
        return None
    monkeypatch.setattr("services.mcp_service.grafana_query_prometheus", _mock_remote)

@asynccontextmanager
async def running_ticker(interval_sec: float = 0.05):
    """Runs the canonical background ticker naturally at high frequency during convergence tests."""
    telemetry_engine.tick_interval_sec = interval_sec
    await telemetry_engine.start()
    await asyncio.sleep(0.01)
    try:
        yield
    finally:
        await telemetry_engine.stop()
        telemetry_engine.tick_interval_sec = 1.0

@pytest.mark.asyncio
async def test_successful_convergence_recovery():
    """Test 1: Successful convergence - recovery evolves and passes verification, transitioning to VERIFIED_RECOVERED."""
    chaos_manager.reset_to_normal()
    chaos_manager.inject_cdn_outage()
    chaos_manager.state.convergence_duration_sec = 0.3  # Fast convergence for test
    chaos_manager.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    
    # Run closed-loop verification with polling while canonical ticker runs in background
    async with running_ticker(0.05):
        verify_res = await continuity_verify_closed_loop_recovery(timeout_sec=2.0, poll_interval_sec=0.05)
    
    assert verify_res["status"] == "PASSED"
    assert verify_res["verified"] is True
    assert verify_res["current_vpf_pct"] <= 0.5
    
    # Mark verified recovered
    recovered_state = chaos_manager.mark_verified_recovered(verify_res)
    assert recovered_state.lifecycle == IncidentLifecycle.VERIFIED_RECOVERED
    assert recovered_state.is_outage_active is False

@pytest.mark.asyncio
async def test_failed_convergence_falsifiable():
    """Test 2: Failed convergence - when force_recovery_failure is True, verification remains PENDING and incident is ESCALATED."""
    chaos_manager.reset_to_normal()
    chaos_manager.inject_cdn_outage()
    chaos_manager.set_force_recovery_failure(True)
    chaos_manager.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    
    async with running_ticker(0.05):
        verify_res = await continuity_verify_closed_loop_recovery(timeout_sec=0.3, poll_interval_sec=0.05)
    
    assert verify_res["status"] == "PENDING"
    assert verify_res["verified"] is False
    assert verify_res["current_vpf_pct"] > 0.5  # Exceeds SLA threshold!
    
    # Verification failure escalates and leaves incident unresolved
    escalated_state = chaos_manager.mark_recovery_failed("Convergence stalled", verify_res)
    assert escalated_state.lifecycle == IncidentLifecycle.ESCALATED
    assert escalated_state.is_outage_active is True

@pytest.mark.asyncio
async def test_slow_convergence_verifier_waits():
    """Test 3: Slow convergence - verifier waits through intermediate unhealthy samples until convergence completes."""
    chaos_manager.reset_to_normal()
    chaos_manager.inject_cdn_outage()
    chaos_manager.state.convergence_duration_sec = 0.3
    chaos_manager.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    
    # Immediately check tick at t=0
    snap_early = telemetry_engine._tick()
    # At t=0, VPF is still high (not recovered yet)
    assert snap_early.video_playback_failures_pct > 1.0
    
    # Polling verifier waits until convergence completes
    async with running_ticker(0.05):
        verify_res = await continuity_verify_closed_loop_recovery(timeout_sec=2.0, poll_interval_sec=0.05)
    assert verify_res["status"] == "PASSED"
    assert verify_res["verified"] is True

@pytest.mark.asyncio
async def test_verifier_stops_at_configured_deadline():
    """Test 4: Verifier stops polling at configured deadline when timeout is reached."""
    chaos_manager.reset_to_normal()
    chaos_manager.inject_cdn_outage()
    # Slow convergence of 10s with short timeout of 0.25s
    chaos_manager.state.convergence_duration_sec = 10.0
    chaos_manager.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    
    start_time = time.time()
    async with running_ticker(0.05):
        verify_res = await continuity_verify_closed_loop_recovery(timeout_sec=0.25, poll_interval_sec=0.05)
    elapsed = time.time() - start_time
    
    assert elapsed < 0.8  # Stopped promptly at deadline
    assert verify_res["status"] == "PENDING"
    assert verify_res["verified"] is False
