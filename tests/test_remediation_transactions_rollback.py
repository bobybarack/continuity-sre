import time
import pytest
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from services.chaos import chaos_manager, FailureMode, IncidentLifecycle
from services.transaction_manager import transaction_manager
from services.telemetry import telemetry_engine
from services.remediation_models import RemediationTransaction, RecoveryProof, EscalationPackage

@pytest.fixture(autouse=True)
def reset_system():
    chaos_manager.reset_to_normal()
    transaction_manager.ledger.clear()
    transaction_manager.idempotency_index.clear()
    transaction_manager.proofs.clear()
    transaction_manager.escalations.clear()
    yield
    chaos_manager.reset_to_normal()

def test_successful_transaction_commit():
    """Validates: incident -> remediation transaction -> convergence -> verification PASS -> COMMITTED."""
    chaos_manager.inject_cdn_outage()
    inc_id = "inc-test-001"
    
    tx, was_new = transaction_manager.execute_transaction(
        incident_id=inc_id,
        action="SHIFT_TRAFFIC_TO_AKAMAI",
        primary_cdn_pct=20,
        secondary_cdn_pct=80
    )
    assert was_new is True
    assert tx.status == "APPLIED"
    assert tx.previous_state["primary_cdn_traffic_pct"] == 100
    assert tx.previous_state["secondary_cdn_traffic_pct"] == 0
    assert tx.rollback_action == "RESTORE_PREVIOUS_TRAFFIC_SPLIT"

    # Simulate full convergence
    chaos_manager.state.remediation_applied_at = time.time() - 5.0
    telemetry_engine._tick()
    pre_snap = transaction_manager.build_health_snapshot()

    proof = transaction_manager.verify_and_commit(
        transaction_id=tx.transaction_id,
        pre_action_snapshot=pre_snap,
        verification_source="Grafana Cloud Prometheus",
        authoritative=True
    )

    assert proof.outcome == "PASSED"
    assert tx.status == "COMMITTED"
    assert proof.evidence_hash is not None
    assert len(proof.gates) >= 2
    assert all(g.passed for g in proof.gates)
    assert chaos_manager.get_state().lifecycle == IncidentLifecycle.VERIFIED_RECOVERED

def test_failed_remediation_triggers_rollback_and_escalate():
    """Validates: incident -> remediation -> recovery fails -> ROLLBACK_REQUIRED -> ROLLED_BACK -> ESCALATED."""
    chaos_manager.inject_cdn_outage()
    chaos_manager.set_force_recovery_failure(True)
    inc_id = "inc-test-fail-002"

    tx, was_new = transaction_manager.execute_transaction(
        incident_id=inc_id,
        action="SHIFT_TRAFFIC_TO_AKAMAI",
        primary_cdn_pct=20,
        secondary_cdn_pct=80
    )
    assert tx.status == "APPLIED"
    # State was modified to 20/80
    assert chaos_manager.get_state().primary_cdn_traffic_pct == 20

    pre_snap = transaction_manager.build_health_snapshot()

    proof = transaction_manager.verify_and_commit(
        transaction_id=tx.transaction_id,
        pre_action_snapshot=pre_snap,
        verification_source="Grafana Cloud Prometheus",
        authoritative=True
    )

    assert proof.outcome == "ROLLED_BACK"
    assert tx.status == "ROLLED_BACK"
    
    # State was rolled back to previous snapshot (100/0)
    current_state = chaos_manager.get_state()
    assert current_state.primary_cdn_traffic_pct == 100
    assert current_state.secondary_cdn_traffic_pct == 0
    assert current_state.lifecycle == IncidentLifecycle.ESCALATED

    # Escalation package must exist
    escalation = transaction_manager.get_escalation(inc_id)
    assert escalation is not None
    assert escalation.incident_id == inc_id
    assert escalation.rollback_status == "EXECUTED"
    assert len(escalation.actions_attempted) >= 1
    assert "Human SRE intervention required" in escalation.recommended_next_step

def test_idempotent_remediation_ledger():
    """Validates that calling the same remediation with same idempotency key does not re-execute side effects."""
    chaos_manager.inject_drm_timeout()
    inc_id = "inc-drm-idempotent-003"

    tx1, was_new1 = transaction_manager.execute_transaction(
        incident_id=inc_id,
        action="FAILOVER_DRM_KEY_CLUSTER"
    )
    assert was_new1 is True
    assert tx1.status == "APPLIED"

    tx2, was_new2 = transaction_manager.execute_transaction(
        incident_id=inc_id,
        action="FAILOVER_DRM_KEY_CLUSTER"
    )
    assert was_new2 is False
    assert tx2.transaction_id == tx1.transaction_id
    assert tx2.idempotency_key == tx1.idempotency_key

def test_scenario_tailored_recovery_gates():
    """Validates that each failure mode evaluates relevant scenario gates."""
    # CDN outage evaluates VPF, buffer, and latency
    cdn_snap = transaction_manager.build_health_snapshot()
    cdn_snap.vpf_pct = 0.3
    cdn_snap.buffer_sec = 25.0
    cdn_snap.cdn_latency_ms = 95.0
    cdn_gates = transaction_manager.evaluate_recovery_gates(FailureMode.CDN_OUTAGE, cdn_snap)
    assert any(g.name == "CDN Egress Latency" for g in cdn_gates)

    # DRM timeout evaluates DRM Handshake
    drm_snap = transaction_manager.build_health_snapshot()
    drm_snap.drm_latency_ms = 110.0
    drm_gates = transaction_manager.evaluate_recovery_gates(FailureMode.DRM_TIMEOUT, drm_snap)
    assert any(g.name == "DRM License Handshake" for g in drm_gates)

    # ISP drop evaluates Delivered Bitrate
    isp_snap = transaction_manager.build_health_snapshot()
    isp_snap.bitrate_mbps = 14.5
    isp_gates = transaction_manager.evaluate_recovery_gates(FailureMode.ISP_PEERING_DROP, isp_snap)
    assert any(g.name == "Delivered Bitrate" for g in isp_gates)

def test_proof_evidence_hash_determinism():
    """Validates that RecoveryProof produces a cryptographic SHA-256 evidence hash."""
    pre = transaction_manager.build_health_snapshot()
    post = transaction_manager.build_health_snapshot()
    proof = RecoveryProof(
        incident_id="inc-hash-test",
        remediation_transaction_id="tx-123",
        pre_action=pre,
        post_action=post,
        verification_source="test_source",
        authoritative=True,
        gates=[],
        outcome="PASSED"
    )
    h1 = proof.calculate_evidence_hash()
    h2 = proof.calculate_evidence_hash()
    assert h1 == h2
    assert len(h1) == 64
