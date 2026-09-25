import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from services.chaos import chaos_manager, FailureMode, IncidentLifecycle, ChaosState
from services.telemetry import telemetry_engine
from services.remediation_models import (
    RemediationTransaction,
    HealthSnapshot,
    RecoveryGateResult,
    RecoveryProof,
    EscalationPackage
)

logger = logging.getLogger("continuity.transaction")

class TransactionManager:
    """Transactional incident remediation controller ensuring idempotency, recovery verification, and rollback."""

    def __init__(self):
        self.ledger: Dict[str, RemediationTransaction] = {}
        self.idempotency_index: Dict[str, str] = {}
        self.proofs: Dict[str, RecoveryProof] = {}
        self.escalations: Dict[str, EscalationPackage] = {}

    def get_transaction(self, transaction_id: str) -> Optional[RemediationTransaction]:
        return self.ledger.get(transaction_id)

    def get_active_transaction(self, incident_id: Optional[str] = None) -> Optional[RemediationTransaction]:
        """Finds an in-flight transaction (APPLIED or VERIFYING) for the active incident."""
        target_inc = incident_id or chaos_manager.get_state().active_incident_id
        if not target_inc:
            return None
        for tx in reversed(list(self.ledger.values())):
            if tx.incident_id == target_inc and tx.status in ("APPLIED", "VERIFYING"):
                return tx
        return None

    def clear(self):
        """Resets ledger state for clean testing."""
        self.ledger.clear()
        self.idempotency_index.clear()
        self.proofs.clear()
        self.escalations.clear()

    def get_proof(self, transaction_id: str) -> Optional[RecoveryProof]:
        return self.proofs.get(transaction_id)

    def get_escalation(self, incident_id: str) -> Optional[EscalationPackage]:
        return self.escalations.get(incident_id)

    def get_rollback_action(self, action: str) -> str:
        if action in ("SHIFT_TRAFFIC_TO_AKAMAI", "SHIFT_TRAFFIC_TO_SECONDARY"):
            return "RESTORE_PREVIOUS_TRAFFIC_SPLIT"
        elif action == "FAILOVER_DRM_KEY_CLUSTER":
            return "RESTORE_PREVIOUS_DRM_CLUSTER"
        elif action == "REROUTE_BGP_TRANSIT":
            return "RESTORE_PREVIOUS_TRANSIT_ROUTE"
        return "RESTORE_PREVIOUS_STATE"

    def execute_transaction(
        self,
        incident_id: str,
        action: str,
        primary_cdn_pct: Optional[int] = None,
        secondary_cdn_pct: Optional[int] = None,
        version: str = "v1"
    ) -> Tuple[RemediationTransaction, bool]:
        """Creates or reuses an idempotent remediation transaction and applies infrastructure mutation.
        
        Returns:
            Tuple[RemediationTransaction, bool]: (transaction, was_newly_applied)
        """
        idempotency_key = f"{incident_id}:{action}:{version}"

        # Phase 6: Idempotent Remediation check
        if idempotency_key in self.idempotency_index:
            existing_tx_id = self.idempotency_index[idempotency_key]
            existing_tx = self.ledger[existing_tx_id]
            logger.info(f"[Remediation Transaction] Idempotency hit for {idempotency_key} -> Reusing {existing_tx_id}")
            return existing_tx, False

        current_chaos = chaos_manager.get_state()
        previous_state = {
            "primary_cdn_traffic_pct": current_chaos.primary_cdn_traffic_pct,
            "secondary_cdn_traffic_pct": current_chaos.secondary_cdn_traffic_pct,
            "edge_route_status": current_chaos.edge_route_status,
            "active_drm_cluster": current_chaos.active_drm_cluster,
            "primary_drm_cluster_status": current_chaos.primary_drm_cluster_status,
            "secondary_drm_cluster_status": current_chaos.secondary_drm_cluster_status,
            "active_transit_route": current_chaos.active_transit_route,
            "primary_transit_status": current_chaos.primary_transit_status,
            "secondary_transit_status": current_chaos.secondary_transit_status,
            "packet_loss_pct": current_chaos.packet_loss_pct,
        }

        rollback_action = self.get_rollback_action(action)
        tx_id = f"tx-{uuid.uuid4().hex[:12]}"

        tx = RemediationTransaction(
            transaction_id=tx_id,
            incident_id=incident_id,
            action=action,
            previous_state=previous_state,
            intended_state={
                "action": action,
                "primary_cdn_pct": primary_cdn_pct or 20,
                "secondary_cdn_pct": secondary_cdn_pct or 80
            },
            applied_at=time.time(),
            idempotency_key=idempotency_key,
            rollback_action=rollback_action,
            status="APPLIED"
        )

        self.ledger[tx_id] = tx
        self.idempotency_index[idempotency_key] = tx_id

        # Mutate simulator state
        chaos_manager.apply_autonomous_remediation(
            action=action,
            primary_cdn_pct=primary_cdn_pct,
            secondary_cdn_pct=secondary_cdn_pct
        )

        logger.info(f"[Remediation Transaction] Created {tx_id} ({action}) for incident {incident_id}")
        return tx, True

    def build_health_snapshot(self, source: str = "canonical_telemetry") -> HealthSnapshot:
        snap = telemetry_engine.get_current_snapshot()
        return HealthSnapshot(
            timestamp=time.time(),
            vpf_pct=snap.video_playback_failures_pct,
            cdn_latency_ms=snap.cdn_egress_latency_ms,
            drm_latency_ms=snap.drm_handshake_ms,
            buffer_sec=snap.buffer_health_sec,
            bitrate_mbps=snap.avg_bitrate_mbps,
            source=source
        )

    def evaluate_recovery_gates(
        self,
        failure_mode: FailureMode,
        snapshot: HealthSnapshot
    ) -> List[RecoveryGateResult]:
        """Evaluates scenario-tailored recovery gates against live telemetry."""
        gates: List[RecoveryGateResult] = []

        # Universal streaming QoS gates
        vpf_val = snapshot.vpf_pct or 0.0
        buf_val = snapshot.buffer_sec or 0.0

        vpf_passed = vpf_val <= 0.5
        gates.append(RecoveryGateResult(
            name="Video Playback Failures (VPF)",
            observed_value=f"{vpf_val:.2f}%",
            operator="<=",
            required_value="0.50%",
            passed=vpf_passed
        ))

        buf_passed = buf_val >= 20.0
        gates.append(RecoveryGateResult(
            name="Forward Playback Buffer",
            observed_value=f"{buf_val:.1f}s",
            operator=">=",
            required_value="20.0s",
            passed=buf_passed
        ))

        # Scenario-specific gate
        if failure_mode == FailureMode.CDN_OUTAGE:
            lat_val = snapshot.cdn_latency_ms or 0.0
            lat_passed = lat_val <= 150.0
            gates.append(RecoveryGateResult(
                name="CDN Egress Latency",
                observed_value=f"{lat_val:.1f}ms",
                operator="<=",
                required_value="150.0ms",
                passed=lat_passed
            ))
        elif failure_mode == FailureMode.DRM_TIMEOUT:
            drm_val = snapshot.drm_latency_ms or 0.0
            drm_passed = drm_val <= 250.0
            gates.append(RecoveryGateResult(
                name="DRM License Handshake",
                observed_value=f"{drm_val:.1f}ms",
                operator="<=",
                required_value="250.0ms",
                passed=drm_passed
            ))
        elif failure_mode == FailureMode.ISP_PEERING_DROP:
            bit_val = snapshot.bitrate_mbps or 0.0
            bit_passed = bit_val >= 10.0
            gates.append(RecoveryGateResult(
                name="Delivered Bitrate",
                observed_value=f"{bit_val:.1f} Mbps",
                operator=">=",
                required_value="10.0 Mbps",
                passed=bit_passed
            ))

        return gates

    def verify_and_commit(
        self,
        transaction_id: str,
        pre_action_snapshot: HealthSnapshot,
        verification_source: str = "Grafana Cloud Prometheus",
        authoritative: bool = True
    ) -> RecoveryProof:
        """Evaluates health gates to either COMMIT the transaction or trigger ROLLBACK and ESCALATION."""
        tx = self.ledger.get(transaction_id)
        if not tx:
            raise ValueError(f"Unknown transaction {transaction_id}")

        tx.status = "VERIFYING"
        state = chaos_manager.get_state()
        post_snapshot = self.build_health_snapshot(source=verification_source)

        gates = self.evaluate_recovery_gates(state.failure_mode, post_snapshot)
        all_passed = all(g.passed for g in gates) and not state.force_recovery_failure

        if all_passed:
            tx.status = "COMMITTED"
            outcome = "PASSED"
            chaos_manager.mark_verified_recovered({
                "transaction_id": transaction_id,
                "verified_at": time.time(),
                "gates": [g.model_dump() for g in gates]
            })
            logger.info(f"[Remediation Transaction] {transaction_id} COMMITTED: All recovery gates passed.")
        else:
            tx.status = "ROLLBACK_REQUIRED"
            outcome = "ROLLED_BACK"
            logger.warning(f"[Remediation Transaction] {transaction_id} FAILED gates. Initiating rollback...")
            
            # Execute Rollback
            self.rollback_transaction(transaction_id)
            
            # Create Escalation Package
            self.create_escalation_package(
                incident_id=tx.incident_id,
                diagnosis=f"Remediation '{tx.action}' executed but recovery gates failed validation.",
                failed_gates=[g.name for g in gates if not g.passed]
            )

        proof = RecoveryProof(
            incident_id=tx.incident_id,
            remediation_transaction_id=transaction_id,
            pre_action=pre_action_snapshot,
            post_action=post_snapshot,
            verification_source=verification_source,
            authoritative=authoritative,
            gates=gates,
            verified_at=time.time(),
            outcome=outcome
        )
        proof.evidence_hash = proof.calculate_evidence_hash()
        tx.proof = proof
        self.proofs[transaction_id] = proof
        return proof

    def rollback_transaction(self, transaction_id: str) -> RemediationTransaction:
        """Restores infrastructure from transaction previous_state snapshot and marks ROLLED_BACK."""
        tx = self.ledger.get(transaction_id)
        if not tx:
            raise ValueError(f"Unknown transaction {transaction_id}")

        action_name = tx.rollback_action or "RESTORE_PREVIOUS_STATE"
        chaos_manager.apply_rollback(previous_state=tx.previous_state, action=action_name)
        tx.status = "ROLLED_BACK"
        logger.warning(f"[Remediation Transaction] {transaction_id} ROLLED_BACK to safe baseline snapshot.")
        return tx

    def create_escalation_package(
        self,
        incident_id: str,
        diagnosis: str,
        failed_gates: List[str],
        prometheus_queries: Optional[List[str]] = None,
        loki_queries: Optional[List[str]] = None
    ) -> EscalationPackage:
        """Assembles comprehensive escalation dossier for human operator handoff."""
        state = chaos_manager.get_state()
        tx_list = [tx.transaction_id for tx in self.ledger.values() if tx.incident_id == incident_id]
        actions = [tx.action for tx in self.ledger.values() if tx.incident_id == incident_id]

        pkg = EscalationPackage(
            incident_id=incident_id,
            failure_mode=state.failure_mode.value if state.failure_mode else "UNKNOWN",
            severity="CRITICAL",
            diagnosis=diagnosis,
            affected_subsystems=[state.primary_cdn, state.active_drm_cluster, state.active_transit_route],
            evidence_summary={
                "failed_gates": failed_gates,
                "current_mode": state.current_mode,
                "lifecycle": state.lifecycle.value,
                "edge_route": state.edge_route_status
            },
            prometheus_queries=prometheus_queries or ["ott_video_playback_failures_ratio", "ott_cdn_egress_latency_ms"],
            loki_queries=loki_queries or ['{service="ott-edge-router"} |= "502 Bad Gateway"'],
            actions_attempted=actions,
            remediation_transactions=tx_list,
            verification_failures=failed_gates,
            rollback_status="EXECUTED",
            recommended_next_step="Human SRE intervention required: Manual peering reroute or upstream edge provider ticket."
        )
        self.escalations[incident_id] = pkg
        logger.error(f"[Escalation Contract] Incident {incident_id} ESCALATED to human operator.")
        return pkg

transaction_manager = TransactionManager()
