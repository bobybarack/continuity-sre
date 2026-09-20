import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.telemetry import TelemetryEngine
from services.chaos import chaos_manager

def test_telemetry_normal_generation():
    chaos_manager.reset_to_normal()
    engine = TelemetryEngine()
    snap = engine.generate_current_snapshot()
    
    assert snap.chaos_mode == "NORMAL"
    assert snap.is_outage is False
    assert 0.10 <= snap.video_playback_failures_pct <= 0.35
    assert 30.0 <= snap.cdn_egress_latency_ms <= 70.0
    assert 80.0 <= snap.drm_handshake_ms <= 160.0
    assert snap.active_viewers > 4_000_000
    assert snap.status_label == "HEALTHY"
    assert snap.status_color == "green"

def test_telemetry_cdn_outage_spike():
    chaos_manager.inject_cdn_outage()
    engine = TelemetryEngine()
    snap = engine.generate_current_snapshot()
    
    assert snap.chaos_mode == "CDN_OUTAGE"
    assert snap.is_outage is True
    assert snap.video_playback_failures_pct >= 4.0
    assert snap.cdn_egress_latency_ms >= 350.0
    assert snap.buffer_health_sec < 6.0
    assert snap.status_label == "CRITICAL_OUTAGE"
    assert snap.status_color == "red"
    assert "502 Bad Gateway" in snap.latest_log

def test_telemetry_drm_timeout():
    chaos_manager.inject_drm_timeout()
    engine = TelemetryEngine()
    snap = engine.generate_current_snapshot()
    
    assert snap.chaos_mode == "DRM_TIMEOUT"
    assert snap.is_outage is True
    assert snap.drm_handshake_ms >= 2000.0
    assert snap.status_label == "CRITICAL_OUTAGE"
    assert "504 Gateway Timeout" in snap.latest_log

def test_telemetry_remediation_recovery():
    chaos_manager.inject_cdn_outage()
    chaos_manager.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    engine = TelemetryEngine()
    snap_recovering = engine.generate_current_snapshot()
    
    assert snap_recovering.chaos_mode == "RECOVERING"
    assert snap_recovering.is_outage is True
    assert snap_recovering.primary_traffic_pct == 20
    assert snap_recovering.secondary_traffic_pct == 80

    chaos_manager.mark_verified_recovered({"vpf": 0.19})
    snap_recovered = engine.generate_current_snapshot()
    assert snap_recovered.chaos_mode == "REMEDIATED"
    assert snap_recovered.is_outage is False
    assert snap_recovered.video_playback_failures_pct < 0.30
    assert snap_recovered.cdn_egress_latency_ms < 60.0
    assert snap_recovered.status_label == "RECOVERED"
    assert snap_recovered.status_color == "blue"

def test_telemetry_history_buffer():
    chaos_manager.reset_to_normal()
    engine = TelemetryEngine()
    for _ in range(75):
        engine.generate_current_snapshot()
    history = engine.get_history()
    assert len(history) <= 60

def test_prometheus_exposition_format():
    chaos_manager.reset_to_normal()
    engine = TelemetryEngine()
    exposition = engine.get_prometheus_exposition().decode("utf-8")
    
    assert "ott_video_playback_failures_ratio" in exposition
    assert "ott_cdn_egress_latency_ms" in exposition
    assert "ott_active_viewers_count" in exposition
    assert "ott_buffer_health_seconds" in exposition
    assert "ott_stream_bitrate_mbps" in exposition
    assert "ott_cdn_traffic_split_percentage" in exposition
    assert "ott_incident_active_status" in exposition
