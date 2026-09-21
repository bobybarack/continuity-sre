import pytest
import asyncio
import sys
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app
from services.telemetry import TelemetryEngine, telemetry_engine
from services.chaos import chaos_manager
from services.mcp_service import continuity_verify_closed_loop_recovery

def test_same_snapshot_between_ticks():
    """Test 1: Two immediate calls to get_current_snapshot() return identical snapshot and timestamp."""
    engine = TelemetryEngine()
    snap1 = engine.get_current_snapshot()
    snap2 = engine.get_current_snapshot()
    
    assert snap1.timestamp == snap2.timestamp
    assert snap1.video_playback_failures_pct == snap2.video_playback_failures_pct
    assert snap1.cdn_egress_latency_ms == snap2.cdn_egress_latency_ms
    assert snap1.active_viewers == snap2.active_viewers

@pytest.mark.asyncio
async def test_sse_observers_do_not_accelerate_telemetry():
    """Test 2: Multiple callers reading /current and SSE do not increase history or generate new ticks."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Record initial history length
        initial_history_len = len(telemetry_engine.get_history())
        
        # Make 15 immediate requests to /api/telemetry/current
        for _ in range(15):
            res = await client.get("/api/telemetry/current")
            assert res.status_code == 200
            
        final_history_len = len(telemetry_engine.get_history())
        # History length must NOT increase from read requests
        assert final_history_len == initial_history_len

@pytest.mark.asyncio
async def test_prometheus_scraping_is_side_effect_free():
    """Test 3: Scraping /metrics does not append history or mutate current telemetry."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        initial_history_len = len(telemetry_engine.get_history())
        snap_before = telemetry_engine.get_current_snapshot()
        
        # Scrape /metrics 5 times
        for _ in range(5):
            res = await client.get("/api/telemetry/metrics")
            assert res.status_code == 200
            assert "ott_video_playback_failures_ratio" in res.text
            
        final_history_len = len(telemetry_engine.get_history())
        snap_after = telemetry_engine.get_current_snapshot()
        
        assert final_history_len == initial_history_len
        assert snap_before.timestamp == snap_after.timestamp

def test_history_is_time_based_not_read_based():
    """Test 4: After 5 controlled ticks, history has exactly 5 new samples regardless of reads."""
    engine = TelemetryEngine()
    initial_len = len(engine.get_history())
    
    for i in range(5):
        # 10 reads between each tick
        for _ in range(10):
            _ = engine.get_current_snapshot()
        engine._tick()
        
    final_len = len(engine.get_history())
    assert final_len == initial_len + 5

@pytest.mark.asyncio
async def test_agent_and_api_observe_same_canonical_snapshot():
    """Test 5: The agent receives the same canonical snapshot visible through /current during that tick."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/telemetry/current")
        assert res.status_code == 200
        api_snap = res.json()
        
        canonical_snap = telemetry_engine.get_current_snapshot()
        
        assert api_snap["timestamp"] == canonical_snap.timestamp
        assert api_snap["video_playback_failures_pct"] == canonical_snap.video_playback_failures_pct
        assert api_snap["cdn_egress_latency_ms"] == canonical_snap.cdn_egress_latency_ms
        assert api_snap["active_viewers"] == canonical_snap.active_viewers

@pytest.mark.asyncio
async def test_verification_corresponds_to_canonical_snapshot():
    """Test 6: Verification output uses canonical snapshot values rather than a second random sample."""
    chaos_manager.reset_to_normal()
    
    verify_res = await continuity_verify_closed_loop_recovery(timeout_sec=0.2, poll_interval_sec=0.1)
    canonical_snap = telemetry_engine.get_current_snapshot()
    
    assert verify_res["current_vpf_pct"] == canonical_snap.video_playback_failures_pct
    assert verify_res["forward_buffer_sec"] == canonical_snap.buffer_health_sec
    assert verify_res["cdn_latency_ms"] == canonical_snap.cdn_egress_latency_ms

@pytest.mark.asyncio
async def test_verification_polling_does_not_advance_telemetry_clock():
    """Test 7: Verification polling does not invoke _tick() or append to telemetry history."""
    chaos_manager.reset_to_normal()
    telemetry_engine._tick()
    initial_history_len = len(telemetry_engine.get_history())
    snap_before = telemetry_engine.get_current_snapshot()
    
    # Run closed-loop verification across multiple poll cycles without background ticker
    verify_res = await continuity_verify_closed_loop_recovery(timeout_sec=0.2, poll_interval_sec=0.05)
    assert verify_res["status"] == "PASSED"
    
    snap_after = telemetry_engine.get_current_snapshot()
    final_history_len = len(telemetry_engine.get_history())
    
    # Telemetry history and snapshot timestamp must be completely unmodified by verification polling
    assert final_history_len == initial_history_len
    assert snap_after.timestamp == snap_before.timestamp
