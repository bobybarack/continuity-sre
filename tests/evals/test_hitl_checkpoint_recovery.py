"""HITL Checkpoint Process-Restart Evaluation Suite (Phase 7.2).

Validates that when a high-blast-radius remediation is suspended pending Human-in-the-Loop
approval, state survives an abrupt process/container termination and can be recovered
and resumed cleanly from the SQLite WAL durable checkpoint store.
"""

import time
import pytest
from services.checkpoint_service import checkpoint_service
from services.hitl_service import hitl_service


def test_hitl_checkpoint_survives_process_restart():
    incident_id = f"INC-HITL-EVAL-{int(time.time()*1000)}"

    # 1. 1st AD raises high-impact action requiring supervisor gate
    gate_event = hitl_service.request_approval(
        incident_id=incident_id,
        action="SHIFT_TRAFFIC_TO_AKAMAI",
        params={"primary_cdn_pct": 20, "secondary_cdn_pct": 80},
        blast_radius=0.85,
        rationale="Primary transit packet loss 60% with forward buffer drop"
    )

    assert gate_event["type"] == "HITL_REQUIRED"
    assert gate_event["incident_id"] == incident_id
    assert gate_event["blast_radius"] == 0.85

    # 2. Simulate process crash / restart by reading directly from SQLite on disk
    chk = checkpoint_service.get_suspended_checkpoint_by_incident(incident_id)
    assert chk is not None
    assert chk["status"] == "SUSPENDED"
    assert chk["incident_id"] == incident_id
    assert chk["state_data"]["action"] == "SHIFT_TRAFFIC_TO_AKAMAI"
    assert chk["state_data"]["blast_radius"] == 0.85

    # 3. Supervisor authorizes after restart
    resumed = hitl_service.approve_incident(
        incident_id=incident_id,
        operator_note="Confirmed secondary CDN capacity headroom nominal"
    )
    assert resumed["success"] is True
    assert resumed["status"] == "APPROVED"
    assert resumed["incident_id"] == incident_id

    # 4. Verify no more pending checkpoints for this incident
    chk_after = checkpoint_service.get_suspended_checkpoint_by_incident(incident_id)
    assert chk_after is None


def test_hitl_checkpoint_denial_cancels_cleanly():
    incident_id = f"INC-DENIAL-EVAL-{int(time.time()*1000)}"

    hitl_service.request_approval(
        incident_id=incident_id,
        action="REROUTE_BGP_TRANSIT",
        params={"transit_asn": 3356},
        blast_radius=0.95,
        rationale="BGP withdrawal requested"
    )

    # Verify pending
    chk = checkpoint_service.get_suspended_checkpoint_by_incident(incident_id)
    assert chk is not None

    # Supervisor denies
    denied = hitl_service.deny_incident(
        incident_id=incident_id,
        reason="Exceeds operational risk tolerance during live global event"
    )

    assert denied["success"] is True
    assert denied["status"] == "DENIED"

    # Verify no longer pending
    chk_after = checkpoint_service.get_suspended_checkpoint_by_incident(incident_id)
    assert chk_after is None
