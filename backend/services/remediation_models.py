import time
import hashlib
import json
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field

class HealthSnapshot(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    vpf_pct: Optional[float] = None
    cdn_latency_ms: Optional[float] = None
    drm_latency_ms: Optional[float] = None
    buffer_sec: Optional[float] = None
    bitrate_mbps: Optional[float] = None
    source: Optional[str] = "canonical_telemetry"

class RecoveryGateResult(BaseModel):
    name: str
    observed_value: Optional[Any] = None
    operator: str
    required_value: Optional[Any] = None
    passed: bool

class RecoveryProof(BaseModel):
    incident_id: str
    remediation_transaction_id: str
    pre_action: HealthSnapshot
    post_action: HealthSnapshot
    verification_source: str
    authoritative: bool
    gates: List[RecoveryGateResult] = Field(default_factory=list)
    verified_at: Optional[float] = None
    outcome: Literal["PASSED", "PENDING", "ROLLED_BACK", "ESCALATED"]
    evidence_hash: Optional[str] = None

    def calculate_evidence_hash(self) -> str:
        payload = {
            "incident_id": self.incident_id,
            "remediation_transaction_id": self.remediation_transaction_id,
            "pre_action": self.pre_action.model_dump(),
            "post_action": self.post_action.model_dump(),
            "gates": [g.model_dump() for g in self.gates],
            "outcome": self.outcome
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class RemediationTransaction(BaseModel):
    transaction_id: str
    incident_id: str
    action: str
    previous_state: Dict[str, Any] = Field(default_factory=dict)
    intended_state: Optional[Dict[str, Any]] = None
    applied_at: float = Field(default_factory=time.time)
    idempotency_key: str
    rollback_action: Optional[str] = None
    failure_mode: Optional[str] = None
    status: Literal[
        "PENDING",
        "APPLIED",
        "VERIFYING",
        "COMMITTED",
        "ROLLBACK_REQUIRED",
        "ROLLED_BACK",
        "FAILED"
    ] = "PENDING"
    error: Optional[str] = None
    proof: Optional[RecoveryProof] = None

class EscalationPackage(BaseModel):
    incident_id: str
    failure_mode: str
    severity: str
    diagnosis: str
    affected_subsystems: List[str] = Field(default_factory=list)
    evidence_summary: Dict[str, Any] = Field(default_factory=dict)
    prometheus_queries: List[str] = Field(default_factory=list)
    loki_queries: List[str] = Field(default_factory=list)
    actions_attempted: List[str] = Field(default_factory=list)
    remediation_transactions: List[str] = Field(default_factory=list)
    verification_failures: List[str] = Field(default_factory=list)
    rollback_status: Optional[str] = None
    recommended_next_step: str
    generated_at: float = Field(default_factory=time.time)

class EvidenceReference(BaseModel):
    query_type: str  # "promql" or "logql"
    query: str
    target_metric: str
    observed_value: Any
    threshold: Optional[str] = None
    status: str = "BREACHED"  # "BREACHED" or "NORMAL"
    timestamp: float = Field(default_factory=time.time)

class DiagnosisClaim(BaseModel):
    subsystem: str
    claim: str
    evidence: List[EvidenceReference] = Field(default_factory=list)
    confidence: float = 1.0

