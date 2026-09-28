import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app
from services.hitl_service import hitl_service
from services.checkpoint_service import checkpoint_service
from services.transaction_manager import transaction_manager
from services.chaos import chaos_manager
from config import CONTINUITY_DEMO_KEY

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean database and transaction ledger for each test."""
    transaction_manager.clear()
    checkpoint_service.clear()
    hitl_service.clear()
    chaos_manager.reset()
    yield
    transaction_manager.clear()
    checkpoint_service.clear()
    hitl_service.clear()
    chaos_manager.reset()

def test_hitl_blast_radius_evaluation():
    """Verifies that high-blast-radius actions trigger mandatory HITL policy."""
    req_bgp, radius_bgp, msg_bgp = hitl_service.evaluate_blast_radius("REROUTE_BGP_TRANSIT")
    assert req_bgp is True
    assert radius_bgp >= 0.90
    assert "critical blast radius" in msg_bgp

    req_drain, radius_drain, msg_drain = hitl_service.evaluate_blast_radius(
        "SHIFT_TRAFFIC_TO_AKAMAI", primary_cdn_pct=20
    )
    assert req_drain is True
    assert radius_drain >= 0.75

    req_nominal, radius_nominal, _ = hitl_service.evaluate_blast_radius(
        "SHIFT_TRAFFIC_TO_AKAMAI", primary_cdn_pct=50
    )
    assert req_nominal is False
    assert radius_nominal <= 0.30

def test_hitl_request_approval_suspends_and_audits():
    """Verifies that requesting approval suspends the workflow in SQLite and logs audit event."""
    inc_id = f"INC-HITL-{uuid.uuid4().hex[:6]}"
    req = hitl_service.request_approval(
        incident_id=inc_id,
        action="REROUTE_BGP_TRANSIT",
        params={"transit": "secondary"},
        rationale="Primary transit experiencing 90% packet loss"
    )

    assert req["type"] == "HITL_REQUIRED"
    assert req["incident_id"] == inc_id
    assert req["action"] == "REROUTE_BGP_TRANSIT"
    assert req["blast_radius"] >= 0.85

    # Check pending list
    pending = hitl_service.list_pending_approvals()
    assert len(pending) == 1
    assert pending[0]["incident_id"] == inc_id
    assert pending[0]["step_name"] == "HITL_SUPERVISOR_APPROVAL"

def test_hitl_supervisor_approve_flow():
    """Verifies that approving resumes the checkpoint, applies the remediation transaction, and audits."""
    inc_id = f"INC-HITL-{uuid.uuid4().hex[:6]}"
    hitl_service.request_approval(
        incident_id=inc_id,
        action="REROUTE_BGP_TRANSIT",
        params={"transit": "secondary"},
        rationale="Primary transit outage"
    )

    res = hitl_service.approve_incident(
        incident_id=inc_id,
        operator_note="Approved by Lead SRE"
    )

    assert res["success"] is True
    assert res["status"] == "APPROVED"
    assert res["action"] == "REROUTE_BGP_TRANSIT"
    assert "transaction_id" in res

    # Verify transaction was executed
    tx = transaction_manager.get_transaction(res["transaction_id"])
    assert tx is not None
    assert tx.status == "APPLIED"

    # Verify checkpoint is no longer active
    pending = hitl_service.list_pending_approvals()
    assert len(pending) == 0

def test_hitl_supervisor_deny_flow():
    """Verifies that denying resumes the checkpoint, halts remediation, and creates an escalation package."""
    inc_id = f"INC-HITL-{uuid.uuid4().hex[:6]}"
    hitl_service.request_approval(
        incident_id=inc_id,
        action="REROUTE_BGP_TRANSIT",
        params={"transit": "secondary"},
        rationale="Primary transit outage"
    )

    res = hitl_service.deny_incident(
        incident_id=inc_id,
        reason="Upstream ISP reported fiber maintenance window; hold BGP failover"
    )

    assert res["success"] is True
    assert res["status"] == "DENIED"
    assert "escalation_package" in res
    assert res["escalation_package"]["incident_id"] == inc_id

    # Verify escalation package in transaction manager
    esc = transaction_manager.get_escalation(inc_id)
    assert esc is not None
    assert "fiber maintenance window" in esc.diagnosis

    # Verify no pending checkpoints
    assert len(hitl_service.list_pending_approvals()) == 0

def test_hitl_fastapi_rest_endpoints():
    """Verifies REST endpoints: GET /api/incidents/checkpoints, POST approve, POST deny."""
    inc_id = f"INC-HITL-{uuid.uuid4().hex[:6]}"
    hitl_service.request_approval(
        incident_id=inc_id,
        action="SHIFT_TRAFFIC_TO_AKAMAI",
        params={"primary_cdn_pct": 20, "secondary_cdn_pct": 80},
        rationale="Cloudflare primary edge 502 rate spike"
    )

    # 1. GET /api/incidents/checkpoints
    resp = client.get("/api/incidents/checkpoints")
    assert resp.status_code == 200
    checkpoints = resp.json()
    assert any(c["incident_id"] == inc_id for c in checkpoints)

    # 2. GET /api/incidents/{incident_id}/checkpoint
    resp_chk = client.get(f"/api/incidents/{inc_id}/checkpoint")
    assert resp_chk.status_code == 200
    assert resp_chk.json()["incident_id"] == inc_id

    # 3. POST /api/incidents/{incident_id}/approve without auth header fails with 401
    resp_unauth = client.post(
        f"/api/incidents/{inc_id}/approve",
        json={"operator_note": "Unauthorized attempt"}
    )
    assert resp_unauth.status_code == 401

    # 4. POST /api/incidents/{incident_id}/approve with valid auth header succeeds
    resp_app = client.post(
        f"/api/incidents/{inc_id}/approve",
        headers={"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY},
        json={"operator_note": "Operator authorized 80% secondary shift"}
    )
    assert resp_app.status_code == 200
    data = resp_app.json()
    assert data["status"] == "APPROVED"
    assert data["incident_id"] == inc_id

    # 5. Checkpoints list should now be empty
    resp_after = client.get("/api/incidents/checkpoints")
    assert len(resp_after.json()) == 0
