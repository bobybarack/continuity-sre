import sys
import tempfile
import uuid
from pathlib import Path
import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.checkpoint_service import CheckpointService
from services.remediation_models import RemediationTransaction, HealthSnapshot, RecoveryProof
from services.transaction_manager import transaction_manager

def test_checkpoint_service_transaction_roundtrip():
    """Verifies that ACID remediation transactions persist and restore cleanly from SQLite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_checkpoint.db"
        svc = CheckpointService(db_path=db_path)

        tx = RemediationTransaction(
            transaction_id="tx-test-persistence-01",
            incident_id="INC-PREMIERE-TEST",
            action="SHIFT_TRAFFIC_TO_AKAMAI",
            previous_state={"primary_cdn_traffic_pct": 100, "secondary_cdn_traffic_pct": 0},
            intended_state={"primary_cdn_pct": 20, "secondary_cdn_pct": 80},
            applied_at=1700000000.0,
            idempotency_key="INC-PREMIERE-TEST:SHIFT_TRAFFIC_TO_AKAMAI:v1",
            rollback_action="RESTORE_PREVIOUS_TRAFFIC_SPLIT",
            status="APPLIED"
        )
        svc.save_transaction(tx)

        # Restore from database
        restored = svc.get_transaction("tx-test-persistence-01")
        assert restored is not None
        assert restored.transaction_id == "tx-test-persistence-01"
        assert restored.action == "SHIFT_TRAFFIC_TO_AKAMAI"
        assert restored.previous_state["primary_cdn_traffic_pct"] == 100
        assert restored.status == "APPLIED"

        # Update status to COMMITTED with proof
        proof = RecoveryProof(
            incident_id="INC-PREMIERE-TEST",
            remediation_transaction_id="tx-test-persistence-01",
            pre_action=HealthSnapshot(vpf_pct=2.4),
            post_action=HealthSnapshot(vpf_pct=0.2),
            verification_source="remote_prometheus",
            authoritative=True,
            gates=[],
            outcome="PASSED",
            evidence_hash="test-hash-12345"
        )
        tx.status = "COMMITTED"
        tx.proof = proof
        svc.save_transaction(tx)

        restored_updated = svc.get_transaction("tx-test-persistence-01")
        assert restored_updated.status == "COMMITTED"
        assert restored_updated.proof is not None
        assert restored_updated.proof.evidence_hash == "test-hash-12345"

def test_checkpoint_hitl_suspension_and_resumption():
    """Verifies that suspended HITL graph state persists across simulated container restart."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_checkpoint.db"
        svc = CheckpointService(db_path=db_path)

        state_data = {
            "incident_id": "INC-HIGH-BLAST-999",
            "proposed_action": "REROUTE_BGP_TRANSIT",
            "target": "Comcast AS7922",
            "reason": "14% packet loss on direct transpacific peering"
        }
        svc.save_checkpoint(
            checkpoint_id="chk-bgp-999",
            incident_id="INC-HIGH-BLAST-999",
            step_name="await_supervisor_bgp_approval",
            state_data=state_data
        )

        # Verify listed as suspended
        active = svc.list_suspended_checkpoints()
        assert len(active) == 1
        assert active[0]["checkpoint_id"] == "chk-bgp-999"
        assert active[0]["state_data"]["proposed_action"] == "REROUTE_BGP_TRANSIT"

        # Simulate operator approval resolution
        resumed = svc.resume_checkpoint("chk-bgp-999", {"decision": "APPROVED", "operator": "lead-sre-alice"})
        assert resumed is not None
        assert resumed["status"] == "RESUMED"
        assert resumed["resolution_data"]["decision"] == "APPROVED"

        # Verify no longer active
        assert len(svc.list_suspended_checkpoints()) == 0

def test_transaction_manager_durable_rehydration():
    """Verifies that transaction_manager can rehydrate transactions from persistent storage after memory clear."""
    test_inc_id = f"INC-REHYDRATE-{uuid.uuid4().hex[:6]}"
    tx, _ = transaction_manager.execute_transaction(
        incident_id=test_inc_id,
        action="FAILOVER_DRM_KEY_CLUSTER"
    )
    tx_id = tx.transaction_id
    assert tx_id in transaction_manager.ledger

    # Clear in-memory ledger to simulate process restart
    transaction_manager.ledger.clear()
    transaction_manager.idempotency_index.clear()
    assert tx_id not in transaction_manager.ledger

    # Re-retrieve: should rehydrate from SQLite
    rehydrated = transaction_manager.get_transaction(tx_id)
    assert rehydrated is not None
    assert rehydrated.transaction_id == tx_id
    assert rehydrated.action == "FAILOVER_DRM_KEY_CLUSTER"
    assert tx_id in transaction_manager.ledger
