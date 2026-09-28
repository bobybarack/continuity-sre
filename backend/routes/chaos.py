import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.chaos import chaos_manager, ChaosState
from services.auth import verify_demo_key

router = APIRouter(prefix="/api/chaos", tags=["Chaos Simulator"])

class RemediationRequest(BaseModel):
    action: Optional[str] = None
    primary_cdn_pct: Optional[int] = None
    secondary_cdn_pct: Optional[int] = None

@router.get("/state", response_model=ChaosState)
async def get_chaos_state():
    """Returns the current active chaos state, outage flags, and recent event audit trail."""
    return chaos_manager.get_state()

@router.post("/inject-cdn-outage", response_model=ChaosState, dependencies=[Depends(verify_demo_key)])
async def inject_cdn_outage():
    """Simulates primary edge CDN transit collapse (502 storm, VPF spikes to 4.85%)."""
    return chaos_manager.inject_cdn_outage()

@router.post("/inject-drm-timeout", response_model=ChaosState, dependencies=[Depends(verify_demo_key)])
async def inject_drm_timeout():
    """Simulates DRM licensing authentication timeout (Widevine key server 2450ms)."""
    return chaos_manager.inject_drm_timeout()

@router.post("/inject-isp-drop", response_model=ChaosState, dependencies=[Depends(verify_demo_key)])
async def inject_isp_drop():
    """Simulates major Tier-1 ISP peering congestion (packet loss, bitrate drops to 3.2 Mbps)."""
    return chaos_manager.inject_isp_peering_drop()

@router.post("/remediate", response_model=ChaosState, dependencies=[Depends(verify_demo_key)])
async def remediate_outage(payload: RemediationRequest):
    """Applies autonomous traffic shift or failover to heal the active incident, enforcing HITL policy."""
    action = payload.action
    state = chaos_manager.get_state()
    if not action:
        from services.scenarios import SCENARIOS
        if state.failure_mode and state.failure_mode.value in SCENARIOS:
            action = SCENARIOS[state.failure_mode.value]["default_action"]
        else:
            action = "SHIFT_TRAFFIC_TO_AKAMAI"

    from services.hitl_service import hitl_service
    from services.checkpoint_service import checkpoint_service
    
    requires_approval, blast_radius, policy_reason = hitl_service.evaluate_blast_radius(
        action=action,
        primary_cdn_pct=payload.primary_cdn_pct or 20,
        severity="CRITICAL" if state.is_outage_active else None
    )

    inc_id = state.active_incident_id or f"INC-{uuid.uuid4().hex[:8]}"
    latest_chk = checkpoint_service.get_latest_checkpoint_by_incident(inc_id)
    is_already_approved = False
    if latest_chk and latest_chk.get("status") == "RESUMED":
        res_data = latest_chk.get("resolution_data") or {}
        if res_data.get("decision") == "APPROVED":
            is_already_approved = True

    if requires_approval and not is_already_approved:
        chk_payload = hitl_service.request_approval(
            incident_id=inc_id,
            action=action,
            params={"primary_cdn_pct": payload.primary_cdn_pct, "secondary_cdn_pct": payload.secondary_cdn_pct},
            rationale=policy_reason,
            blast_radius=blast_radius
        )
        raise HTTPException(
            status_code=403,
            detail=f"Remediation action '{action}' requires human supervisor approval (blast_radius={blast_radius}). Checkpoint created."
        )

    return chaos_manager.apply_autonomous_remediation(
        action,
        primary_cdn_pct=payload.primary_cdn_pct,
        secondary_cdn_pct=payload.secondary_cdn_pct
    )

@router.post("/reset", response_model=ChaosState, dependencies=[Depends(verify_demo_key)])
async def reset_chaos():
    """Restores baseline normal operations (0.18% VPF, 48ms latency, Fastly 100%)."""
    return chaos_manager.reset_to_normal()
