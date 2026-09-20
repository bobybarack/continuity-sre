import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.chaos import ChaosStateManager, IncidentLifecycle, FailureMode

def test_remediation_enters_recovering_not_verified_recovered():
    """Test 1: After remediation, lifecycle must be RECOVERING, not VERIFIED_RECOVERED."""
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    state = mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    
    assert state.lifecycle == IncidentLifecycle.RECOVERING
    assert state.lifecycle != IncidentLifecycle.VERIFIED_RECOVERED
    assert state.remediation_action == "SHIFT_TRAFFIC_TO_AKAMAI"

def test_incident_remains_unresolved_after_remediation_before_verification():
    """Test 2: After remediation but before verification, incident remains unresolved."""
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    state = mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    
    assert state.is_outage_active is True
    assert state.active_incident_id is not None
    assert state.verified_recovered_at is None

def test_verification_failure_leaves_unresolved():
    """Test 3: A verification failure leaves lifecycle != VERIFIED_RECOVERED and incident active."""
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    failed_state = mgr.mark_recovery_failed("Metrics exceeded SLA threshold", {"vpf": 2.4})
    
    assert failed_state.lifecycle == IncidentLifecycle.ESCALATED
    assert failed_state.lifecycle != IncidentLifecycle.VERIFIED_RECOVERED
    assert failed_state.is_outage_active is True

def test_only_successful_verification_produces_verified_recovered():
    """Test 4: Only a successful verification can transition state to VERIFIED_RECOVERED."""
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    recovered_state = mgr.mark_verified_recovered({"vpf": 0.19, "buffer": 26.5})
    
    assert recovered_state.lifecycle == IncidentLifecycle.VERIFIED_RECOVERED
    assert recovered_state.is_outage_active is False
    assert recovered_state.verified_recovered_at is not None

def test_no_resolved_event_emitted_before_verification_passes():
    """Test 5: A RESOLVED event is not emitted before verification passes."""
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    state_after_remediation = mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
    
    # Verify no recent event has severity "RESOLVED"
    remediation_event = state_after_remediation.recent_events[0]
    assert remediation_event.event_type == "AGENT_REMEDIATION_APPLIED"
    assert remediation_event.severity != "RESOLVED"
    assert all(event.severity != "RESOLVED" for event in state_after_remediation.recent_events if event.event_type == "AGENT_REMEDIATION_APPLIED")
    
    # Now verify recovery and check that RESOLVED event is emitted only then
    state_after_verification = mgr.mark_verified_recovered({"source": "grafana_cloud_prometheus"})
    verified_event = state_after_verification.recent_events[0]
    assert verified_event.event_type == "CLOSED_LOOP_RECOVERY_VERIFIED"
    assert verified_event.severity == "RESOLVED"
