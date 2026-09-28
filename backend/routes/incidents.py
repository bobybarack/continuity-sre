import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel
from services.hitl_service import hitl_service
from services.checkpoint_service import checkpoint_service
from services.auth import verify_demo_key

logger = logging.getLogger("continuity.routes.incidents")

router = APIRouter(prefix="/api/incidents", tags=["Incident HITL Governance"])


class ApprovalPayload(BaseModel):
    operator_note: Optional[str] = "Approved via Command Center HITL Gate"


class DenialPayload(BaseModel):
    reason: Optional[str] = "Rejected by broadcast supervisor due to operational constraints"


@router.get("/checkpoints")
async def list_pending_checkpoints() -> List[Dict[str, Any]]:
    """Lists all incidents currently suspended waiting for human supervisor approval."""
    return hitl_service.list_pending_approvals()


@router.get("/{incident_id}/checkpoint")
async def get_incident_checkpoint(incident_id: str) -> Dict[str, Any]:
    """Retrieves the active suspended checkpoint for a given incident."""
    chk = checkpoint_service.get_suspended_checkpoint_by_incident(incident_id)
    if not chk:
        raise HTTPException(
            status_code=404,
            detail=f"No active suspended checkpoint found for incident '{incident_id}'."
        )
    return chk


@router.post("/{incident_id}/approve", dependencies=[Depends(verify_demo_key)])
async def approve_incident(
    incident_id: str,
    payload: Optional[ApprovalPayload] = Body(default=None)
) -> Dict[str, Any]:
    """Approves the proposed high-blast-radius remediation and resumes execution."""
    note = payload.operator_note if payload and payload.operator_note else "Approved by broadcast supervisor"
    result = hitl_service.approve_incident(incident_id, operator_note=note)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Approval failed"))
    return result


@router.post("/{incident_id}/deny", dependencies=[Depends(verify_demo_key)])
async def deny_incident(
    incident_id: str,
    payload: Optional[DenialPayload] = Body(default=None)
) -> Dict[str, Any]:
    """Denies the proposed remediation, suspends the action, and triggers an escalation package."""
    reason = payload.reason if payload and payload.reason else "Rejected by supervisor"
    result = hitl_service.deny_incident(incident_id, reason=reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Denial failed"))
    return result
