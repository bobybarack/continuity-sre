import time
import uuid
import logging
from typing import Dict, Any, Optional, Tuple, List
from services.checkpoint_service import checkpoint_service
from services.transaction_manager import transaction_manager
from services.chaos import chaos_manager

logger = logging.getLogger("continuity.hitl")

# High Blast Radius thresholds and action taxonomy
HIGH_BLAST_RADIUS_ACTIONS: Dict[str, float] = {
    "REROUTE_BGP_TRANSIT": 0.95,
    "DRAIN_PRIMARY_CDN": 0.85,
}

class HITLService:
    """Orchestrates Human-in-the-Loop (HITL) supervisor gates for high-blast-radius mitigations."""

    def __init__(self):
        self._pending_events: List[Dict[str, Any]] = []

    def evaluate_blast_radius(
        self,
        action: str,
        primary_cdn_pct: Optional[int] = None,
        severity: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """Evaluates whether an action requires mandatory human supervisor authorization."""
        if action in HIGH_BLAST_RADIUS_ACTIONS:
            radius = HIGH_BLAST_RADIUS_ACTIONS[action]
            return True, radius, f"Mandatory HITL policy: '{action}' carries critical blast radius ({radius:.2f})."

        # Draining primary CDN below 25% traffic
        if action in ("SHIFT_TRAFFIC_TO_AKAMAI", "SHIFT_CDN_TRAFFIC") and primary_cdn_pct is not None and primary_cdn_pct <= 20:
            return True, 0.80, "Mandatory HITL policy: Throttling primary CDN to <= 20% requires operator authorization."

        if severity == "CRITICAL" and action == "FAILOVER_DRM_KEY_CLUSTER":
            # For DRM failover in critical severity, evaluate blast radius
            return False, 0.45, "Autonomous failover permitted under SLA emergency protocol."

        return False, 0.20, "Low blast radius: safe for autonomous execution."

    def request_approval(
        self,
        incident_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        rationale: str = "",
        blast_radius: Optional[float] = None
    ) -> Dict[str, Any]:
        """Suspends workflow execution and creates a durable checkpoint pending human authorization."""
        params = params or {}
        checkpoint_id = f"chk-hitl-{uuid.uuid4().hex[:10]}"
        calculated_radius = blast_radius if blast_radius is not None else 0.85

        state_data = {
            "incident_id": incident_id,
            "action": action,
            "params": params,
            "rationale": rationale,
            "blast_radius": calculated_radius,
            "requested_at": time.time(),
            "timeout_seconds": 60,
            "rollback_plan": transaction_manager.get_rollback_action(action)
        }

        # 1. Durable SQLite checkpoint
        checkpoint_service.save_checkpoint(
            checkpoint_id=checkpoint_id,
            incident_id=incident_id,
            step_name="HITL_SUPERVISOR_APPROVAL",
            state_data=state_data
        )

        # 2. Immutable audit log
        checkpoint_service.log_audit_event(
            incident_id=incident_id,
            role="1st AD Commander",
            event_type="HITL_APPROVAL_REQUESTED",
            details={
                "checkpoint_id": checkpoint_id,
                "action": action,
                "blast_radius": calculated_radius,
                "rationale": rationale
            }
        )

        payload = {
            "type": "HITL_REQUIRED",
            "checkpoint_id": checkpoint_id,
            "incident_id": incident_id,
            "action": action,
            "params": params,
            "rationale": rationale,
            "blast_radius": calculated_radius,
            "requested_at": state_data["requested_at"],
            "timeout_seconds": 60,
            "rollback_plan": state_data["rollback_plan"]
        }
        self._pending_events.append(payload)
        if len(self._pending_events) > 50:
            self._pending_events.pop(0)

        logger.info(
            f"[HITL] Approval requested for incident {incident_id}: action={action}, blast_radius={calculated_radius}"
        )
        return payload

    def approve_incident(
        self,
        incident_id: str,
        operator_note: str = ""
    ) -> Dict[str, Any]:
        """Resumes the suspended checkpoint, executes the remediation transaction, and logs approval."""
        chk = checkpoint_service.get_suspended_checkpoint_by_incident(incident_id)
        if not chk:
            return {
                "success": False,
                "error": f"No suspended checkpoint found for incident '{incident_id}'."
            }

        checkpoint_id = chk["checkpoint_id"]
        state_data = chk["state_data"]
        action = state_data.get("action", "SHIFT_TRAFFIC_TO_AKAMAI")
        params = state_data.get("params", {})
        primary_cdn_pct = params.get("primary_cdn_pct", 20)
        secondary_cdn_pct = params.get("secondary_cdn_pct", 80)

        resolution = {
            "decision": "APPROVED",
            "operator_note": operator_note or "Authorized by broadcast supervisor",
            "resolved_at": time.time()
        }

        # 1. Update checkpoint state in SQLite
        checkpoint_service.resume_checkpoint(checkpoint_id, resolution)

        # 2. Log immutable audit log
        checkpoint_service.log_audit_event(
            incident_id=incident_id,
            role="Human Supervisor",
            event_type="HITL_APPROVED",
            details=resolution
        )

        # 3. Execute approved remediation via transaction manager
        tx, was_new = transaction_manager.execute_transaction(
            incident_id=incident_id,
            action=action,
            primary_cdn_pct=primary_cdn_pct,
            secondary_cdn_pct=secondary_cdn_pct
        )

        # 4. Resolve notification
        self._pending_events = [e for e in self._pending_events if e.get("incident_id") != incident_id]

        logger.info(f"[HITL] Incident {incident_id} approved. Executed transaction {tx.transaction_id}")
        return {
            "success": True,
            "status": "APPROVED",
            "incident_id": incident_id,
            "checkpoint_id": checkpoint_id,
            "transaction_id": tx.transaction_id,
            "action": action,
            "operator_note": operator_note,
            "transaction_status": tx.status
        }

    def deny_incident(
        self,
        incident_id: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Denies the requested action, halts the transaction, and generates an EscalationPackage."""
        chk = checkpoint_service.get_suspended_checkpoint_by_incident(incident_id)
        if not chk:
            return {
                "success": False,
                "error": f"No suspended checkpoint found for incident '{incident_id}'."
            }

        checkpoint_id = chk["checkpoint_id"]
        state_data = chk["state_data"]
        action = state_data.get("action", "UNKNOWN")

        resolution = {
            "decision": "DENIED",
            "reason": reason or "Action rejected by supervisor due to operational constraints",
            "resolved_at": time.time()
        }

        # 1. Update checkpoint in SQLite
        checkpoint_service.resume_checkpoint(checkpoint_id, resolution)

        # 2. Log immutable audit log
        checkpoint_service.log_audit_event(
            incident_id=incident_id,
            role="Human Supervisor",
            event_type="HITL_DENIED",
            details=resolution
        )

        # 3. Create escalation package
        pkg = transaction_manager.create_escalation_package(
            incident_id=incident_id,
            diagnosis=f"Supervisor rejected proposed action '{action}': {resolution['reason']}",
            failed_gates=["supervisor_approval"]
        )

        # 4. Remove pending notification
        self._pending_events = [e for e in self._pending_events if e.get("incident_id") != incident_id]

        logger.info(f"[HITL] Incident {incident_id} denied. Escalation package recorded.")
        return {
            "success": True,
            "status": "DENIED",
            "incident_id": incident_id,
            "checkpoint_id": checkpoint_id,
            "action": action,
            "reason": resolution["reason"],
            "escalation_package": pkg.model_dump()
        }

    def list_pending_approvals(self) -> List[Dict[str, Any]]:
        """Returns all suspended checkpoints currently waiting for supervisor decision."""
        return checkpoint_service.list_suspended_checkpoints()

    def get_pending_events(self) -> List[Dict[str, Any]]:
        """Returns pending notifications for SSE stream broadcast."""
        return list(self._pending_events)

    def clear(self):
        """Clears in-memory events for clean testing."""
        self._pending_events.clear()


# Global singleton instance
hitl_service = HITLService()
