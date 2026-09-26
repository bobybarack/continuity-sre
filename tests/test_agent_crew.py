import sys
from pathlib import Path
import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.agent_crew import (
    continuity_crew,
    ContinuityAgentCrew,
    TriagePackage,
    EvidencePackage,
    RemediationIntent,
    VerificationVerdict,
    FIRST_AD_TOOLS,
    DIT_TOOLS,
    KEY_GRIP_TOOLS,
    CONTINUITY_TOOLS,
)

def test_continuity_crew_initialization():
    """Verifies that the 4 cinema SRE agents are initialized with explicit roles and boundaries."""
    crew = continuity_crew
    assert crew.first_ad.name == "first_ad_commander"
    assert crew.dit.name == "dit_signal_scout"
    assert crew.key_grip.name == "key_grip_rigger"
    assert crew.continuity.name == "continuity_quality_gate"

def test_agent_tool_scoping_boundaries():
    """Verifies that each agent holds strictly partitioned tool allowlists preventing scope creep."""
    specs = continuity_crew.get_agent_specs()
    assert len(specs) == 4
    
    spec_map = {s["role"]: s for s in specs}
    assert spec_map["1st AD"]["tools"] == FIRST_AD_TOOLS
    assert spec_map["DIT"]["tools"] == DIT_TOOLS
    assert spec_map["Key Grip"]["tools"] == KEY_GRIP_TOOLS
    assert spec_map["Continuity"]["tools"] == CONTINUITY_TOOLS
    
    # Verify no tool overlaps between DIT (observability) and Continuity (verification)
    assert not set(DIT_TOOLS).intersection(set(CONTINUITY_TOOLS))

def test_inter_agent_handover_models():
    """Verifies that structured handover data models validate cleanly between stages."""
    triage = TriagePackage(
        incident_id="INC-PREMIERE-401",
        stream_title="Continuity Premiere Night",
        initial_alert="VPF > 1.0%",
        severity="CRITICAL",
        affected_subsystems=["Primary CDN", "Edge Ingress"],
        hitl_required=False,
        executive_brief="Degradation detected on primary edge CDN."
    )
    assert triage.incident_id == "INC-PREMIERE-401"
    assert triage.severity == "CRITICAL"

    evidence = EvidencePackage(
        incident_id=triage.incident_id,
        promql_metrics={"vpf": 2.45, "latency_ms": 312.0},
        sanitized_logs=["[SECURITY_SHIELD_FLAGGED_CONTENT] filtered line"],
        flagged_security_injections=1,
        failure_hypothesis="Primary CDN egress saturated; failover required.",
        confidence=0.98,
        evidence_citations=["query_prometheus: vpf_rate", "query_loki_logs: timeout"]
    )
    assert evidence.flagged_security_injections == 1

    remediation = RemediationIntent(
        incident_id=triage.incident_id,
        action_name="SHIFT_TRAFFIC_TO_AKAMAI",
        target_subsystem="Edge CDN",
        transaction_id="TX-88219",
        idempotency_key="IDEMP-CDN-401",
        rollback_action="RESTORE_PRIMARY_CDN",
        execution_status="APPLIED",
        blast_radius="LOW"
    )
    assert remediation.action_name == "SHIFT_TRAFFIC_TO_AKAMAI"

    verdict = VerificationVerdict(
        incident_id=triage.incident_id,
        transaction_id=remediation.transaction_id,
        outcome="COMMITTED",
        health_gates={"vpf_rate": True, "buffer_health": True, "cdn_latency": True},
        authoritative=True,
        verification_source="remote_prometheus",
        verified_vpf_rate=0.18,
        verified_buffer_health_sec=24.2,
        recovery_proof_digest="a3f81e...912"
    )
    assert verdict.outcome == "COMMITTED"
    assert verdict.authoritative is True
