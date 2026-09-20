import pytest
import concurrent.futures
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.chaos import ChaosStateManager

def test_initial_state():
    mgr = ChaosStateManager()
    state = mgr.get_state()
    assert state.current_mode == "NORMAL"
    assert state.is_outage_active is False
    assert state.primary_cdn_traffic_pct == 100
    assert state.secondary_cdn_traffic_pct == 0
    assert len(state.recent_events) >= 1

def test_inject_cdn_outage():
    mgr = ChaosStateManager()
    state = mgr.inject_cdn_outage()
    assert state.current_mode == "CDN_OUTAGE"
    assert state.is_outage_active is True
    assert state.active_incident_id is not None
    assert state.injected_at is not None
    assert state.primary_cdn_traffic_pct == 100
    assert state.recent_events[0].event_type == "CHAOS_INJECT_CDN_OUTAGE"

def test_inject_drm_timeout():
    mgr = ChaosStateManager()
    state = mgr.inject_drm_timeout()
    assert state.current_mode == "DRM_TIMEOUT"
    assert state.is_outage_active is True
    assert "DRM" in state.active_incident_id
    assert state.recent_events[0].event_type == "CHAOS_INJECT_DRM_TIMEOUT"

def test_inject_isp_peering_drop():
    mgr = ChaosStateManager()
    state = mgr.inject_isp_peering_drop()
    assert state.current_mode == "ISP_PEERING_DROP"
    assert state.is_outage_active is True
    assert state.recent_events[0].event_type == "CHAOS_INJECT_ISP_DROP"

def test_apply_remediation():
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    state = mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    assert state.lifecycle == "RECOVERING"
    assert state.current_mode == "RECOVERING"
    assert state.is_outage_active is True
    assert state.primary_cdn_traffic_pct == 20
    assert state.secondary_cdn_traffic_pct == 80
    assert state.remediation_action_applied == "SHIFT_TRAFFIC_TO_AKAMAI"
    assert state.recent_events[0].severity != "RESOLVED"

    # Verification gate passes -> verified recovered
    recovered = mgr.mark_verified_recovered({"vpf": 0.19})
    assert recovered.lifecycle == "VERIFIED_RECOVERED"
    assert recovered.current_mode == "REMEDIATED"
    assert recovered.is_outage_active is False
    assert recovered.recent_events[0].severity == "RESOLVED"

def test_reset_to_normal():
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    mgr.apply_autonomous_remediation()
    state = mgr.reset_to_normal()
    assert state.current_mode == "NORMAL"
    assert state.is_outage_active is False
    assert state.primary_cdn_traffic_pct == 100
    assert state.secondary_cdn_traffic_pct == 0
    assert state.active_incident_id is None

def test_event_history_bounded():
    mgr = ChaosStateManager()
    for i in range(70):
        mgr.inject_cdn_outage()
        mgr.reset_to_normal()
    state = mgr.get_state()
    assert len(state.recent_events) <= 50

def test_thread_safety_concurrent_mutations():
    mgr = ChaosStateManager()
    
    def mutate(idx):
        if idx % 3 == 0:
            mgr.inject_cdn_outage()
        elif idx % 3 == 1:
            mgr.apply_autonomous_remediation()
        else:
            mgr.reset_to_normal()
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(mutate, i) for i in range(100)]
        for f in futures:
            f.result()
            
    state = mgr.get_state()
    assert state.current_mode in ["NORMAL", "CDN_OUTAGE", "RECOVERING", "REMEDIATED"]
    assert len(state.recent_events) <= 50
