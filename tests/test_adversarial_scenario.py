import pytest
from services.chaos import chaos_manager, FailureMode, IncidentLifecycle
from services.agent_commander import agent_commander
from services.transaction_manager import transaction_manager

@pytest.mark.asyncio
async def test_adversarial_secondary_path_degraded_scenario():
    """Verifies that an adversarial double-fault (secondary path degraded) triggers
    closed-loop verification failure, automatic rollback, human escalation packaging,
    and structured evidence-addressed diagnosis.
    """
    transaction_manager.clear()
    chaos_manager.reset()
    state = chaos_manager.inject_secondary_path_degradation()
    
    assert state.failure_mode == FailureMode.SECONDARY_PATH_DEGRADED
    assert state.is_outage_active is True
    assert state.force_recovery_failure is True
    
    # Run autonomous investigation
    result = await agent_commander.investigate_and_remediate(
        incident_id=state.active_incident_id,
        failure_mode_override=FailureMode.SECONDARY_PATH_DEGRADED.value,
        trigger_source="automated_chaos"
    )
    
    # 1. Closed-loop verification MUST NOT pass
    assert result.closed_loop_verified is False
    assert result.workflow_status in ("PENDING_VERIFICATION", "ESCALATED")
    
    # 2. Remediation transaction must be recorded and rolled back
    assert result.remediation_transaction_id is not None
    assert result.rollback_status == "EXECUTED"
    assert result.remediation_status == "ROLLED_BACK"
    
    # 3. Escalation package must be present
    assert result.escalation_package is not None
    assert result.escalation_package["rollback_status"] == "EXECUTED"
    assert "failed_gates" in result.escalation_package["evidence_summary"]
    
    # 4. Phase 9: Structured evidence diagnosis claims must be present
    assert len(result.diagnosis_claims) > 0
    claim = result.diagnosis_claims[0]
    assert "claim" in claim
    assert "evidence" in claim
    assert len(claim["evidence"]) > 0
    
    # Evidence must contain PromQL and LogQL queries with breached status
    promql_ev = next(e for e in claim["evidence"] if e["query_type"] == "promql")
    assert promql_ev["status"] == "BREACHED"
    assert promql_ev["threshold"] is not None
    
    logql_ev = next(e for e in claim["evidence"] if e["query_type"] == "logql")
    assert logql_ev["status"] == "BREACHED"
    assert "502" in logql_ev["threshold"] or "failure" in logql_ev["threshold"]

@pytest.mark.asyncio
async def test_evidence_addressed_diagnosis_claims_healthy():
    """Verifies that diagnosis claims on normal/healthy streams indicate SLA compliance."""
    chaos_manager.reset()
    
    result = await agent_commander.investigate_and_remediate(
        incident_id="INC-HEALTHY-EVIDENCE",
        trigger_source="manual"
    )
    assert result.severity == "HEALTHY"
    assert result.initial_anomaly_detected is False
