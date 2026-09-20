from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from services.chaos import chaos_manager, ChaosState

router = APIRouter(prefix="/api/chaos", tags=["Chaos Simulator"])

class RemediationRequest(BaseModel):
    action: Optional[str] = None

@router.get("/state", response_model=ChaosState)
async def get_chaos_state():
    """Returns the current active chaos state, outage flags, and recent event audit trail."""
    return chaos_manager.get_state()

@router.post("/inject-cdn-outage", response_model=ChaosState)
async def inject_cdn_outage():
    """Simulates primary edge CDN transit collapse (502 storm, VPF spikes to 4.85%)."""
    return chaos_manager.inject_cdn_outage()

@router.post("/inject-drm-timeout", response_model=ChaosState)
async def inject_drm_timeout():
    """Simulates DRM licensing authentication timeout (Widevine key server 2450ms)."""
    return chaos_manager.inject_drm_timeout()

@router.post("/inject-isp-drop", response_model=ChaosState)
async def inject_isp_drop():
    """Simulates major Tier-1 ISP peering congestion (packet loss, bitrate drops to 3.2 Mbps)."""
    return chaos_manager.inject_isp_peering_drop()

@router.post("/remediate", response_model=ChaosState)
async def remediate_outage(payload: RemediationRequest):
    """Applies autonomous traffic shift or failover to heal the active incident."""
    action = payload.action
    if not action:
        state = chaos_manager.get_state()
        from services.scenarios import SCENARIOS
        if state.failure_mode.value in SCENARIOS:
            action = SCENARIOS[state.failure_mode.value]["default_action"]
        else:
            action = "SHIFT_TRAFFIC_TO_AKAMAI"
    return chaos_manager.apply_autonomous_remediation(action)

@router.post("/reset", response_model=ChaosState)
async def reset_chaos():
    """Restores baseline normal operations (0.18% VPF, 48ms latency, Fastly 100%)."""
    return chaos_manager.reset_to_normal()
