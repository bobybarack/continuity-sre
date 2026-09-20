import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.chaos import ChaosStateManager, FailureMode
from services.scenarios import SCENARIOS, SCENARIO_ACTIONS

def test_cdn_remediation_affects_only_cdn():
    """CDN test: After CDN remediation, CDN traffic changes, DRM active cluster does not change, transit route does not change."""
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    
    initial_drm = mgr.get_state().active_drm_cluster
    initial_transit = mgr.get_state().active_transit_route
    
    state = mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI", primary_cdn_pct=25, secondary_cdn_pct=75)
    
    assert state.primary_cdn_traffic_pct == 25
    assert state.secondary_cdn_traffic_pct == 75
    assert state.edge_route_status == "REROUTED"
    
    # Assert DRM and transit route did not change
    assert state.active_drm_cluster == initial_drm
    assert state.active_transit_route == initial_transit

def test_drm_remediation_affects_only_drm():
    """DRM test: After DRM remediation, DRM cluster changes, CDN traffic remains unchanged."""
    mgr = ChaosStateManager()
    mgr.inject_drm_timeout()
    
    initial_cdn_primary = mgr.get_state().primary_cdn_traffic_pct
    initial_cdn_secondary = mgr.get_state().secondary_cdn_traffic_pct
    initial_transit = mgr.get_state().active_transit_route
    
    state = mgr.apply_autonomous_remediation("FAILOVER_DRM_KEY_CLUSTER")
    
    assert state.active_drm_cluster == "drm-key-cluster-failover"
    assert state.secondary_drm_cluster_status == "ACTIVE"
    assert state.primary_drm_cluster_status == "FAILED"
    
    # Assert CDN traffic and transit route remained unchanged
    assert state.primary_cdn_traffic_pct == initial_cdn_primary
    assert state.secondary_cdn_traffic_pct == initial_cdn_secondary
    assert state.active_transit_route == initial_transit

def test_isp_remediation_affects_only_transit():
    """ISP test: After ISP remediation, transit route changes, CDN traffic does not falsely represent the remediation."""
    mgr = ChaosStateManager()
    mgr.inject_isp_peering_drop()
    
    initial_cdn_primary = mgr.get_state().primary_cdn_traffic_pct
    initial_cdn_secondary = mgr.get_state().secondary_cdn_traffic_pct
    initial_drm = mgr.get_state().active_drm_cluster
    
    state = mgr.apply_autonomous_remediation("REROUTE_BGP_TRANSIT")
    
    assert state.active_transit_route == "ASN-2914-Backup"
    assert state.secondary_transit_status == "ACTIVE"
    assert state.primary_transit_status == "BYPASSED"
    assert state.packet_loss_pct == 0.2
    
    # Assert CDN traffic and DRM cluster remained unchanged
    assert state.primary_cdn_traffic_pct == initial_cdn_primary
    assert state.secondary_cdn_traffic_pct == initial_cdn_secondary
    assert state.active_drm_cluster == initial_drm

def test_invalid_action_fails_explicitly():
    """Invalid action test: Unknown action must fail explicitly with ValueError."""
    mgr = ChaosStateManager()
    mgr.inject_cdn_outage()
    
    with pytest.raises(ValueError, match="Unknown remediation action"):
        mgr.apply_autonomous_remediation("INVALID_ACTION_NAME")

def test_wrong_scenario_action_fails_explicitly():
    """Wrong-scenario action test: Inappropriate action for active failure mode must fail explicitly."""
    mgr = ChaosStateManager()
    mgr.inject_drm_timeout()
    
    # Attempting CDN shift during DRM outage must fail
    with pytest.raises(ValueError, match="is invalid for active failure mode"):
        mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")

    # Attempting BGP reroute during DRM outage must fail
    with pytest.raises(ValueError, match="is invalid for active failure mode"):
        mgr.apply_autonomous_remediation("REROUTE_BGP_TRANSIT")
