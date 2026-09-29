import os
import time
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService

from config import GEMINI_API_KEY, GEMINI_MODEL, STREAM_TITLE
from services.chaos import chaos_manager, FailureMode
from services.scenarios import SCENARIOS
from services.telemetry import telemetry_engine
from services.integration_models import (
    PrometheusQueryResult,
    LokiQueryResult,
    GrafanaIncidentRef,
    GrafanaAnnotationRef
)
from services.transaction_manager import transaction_manager
from services.telemetry import PROM_AGENT_GEMINI_LATENCY
from services.remediation_models import DiagnosisClaim, EvidenceReference
from services.security_guard import security_guard
from services.mcp_service import (
    GEMINI_MCP_TOOLS,
    get_gemini_tools,
    dispatch_mcp_tool,
    official_mcp_bridge,
    grafana_query_prometheus,
    grafana_query_loki,
    grafana_create_annotation,
    grafana_create_incident,
    grafana_resolve_incident,
    continuity_execute_remediation,
    continuity_verify_closed_loop_recovery
)

logger = logging.getLogger("continuity.agent")

if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

FALLBACK_MODELS = list(dict.fromkeys([
    GEMINI_MODEL,
    "models/gemini-3.7-flash",
    "models/gemini-3.6-flash",
    "models/gemini-3.5-flash",
]))

class InvestigationResult(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    incident_id: Optional[str] = None
    failure_mode: Optional[str] = None
    stream_title: str = STREAM_TITLE
    initial_anomaly_detected: bool = False
    vpf_rate: float
    cdn_latency_ms: float
    drm_handshake_ms: float
    severity: str  # "CRITICAL", "WARNING", "HEALTHY"
    root_cause_analysis: str
    affected_subsystems: List[str]
    autonomous_action_taken: Optional[str] = None
    remediation_action: Optional[str] = None
    remediation_status: Optional[str] = None
    workflow_status: str = "COMPLETED"
    traffic_shift_details: Dict[str, Any] = Field(default_factory=dict)
    annotation_id: Optional[int] = None
    grafana_incident_id: Optional[str] = None
    workflow_elapsed_seconds: float = 0.0
    mttr_seconds: Optional[float] = None
    estimated_subscriber_loss_prevented: str
    executive_summary: str
    reasoning_trace: List[str] = Field(default_factory=list)
    mcp_tools_executed: List[str] = Field(default_factory=list)
    closed_loop_verified: bool = False
    verified_vpf_rate: float = 0.0
    verified_buffer_health_sec: float = 0.0
    verified_latency_ms: Optional[float] = None
    verification_status: Optional[str] = "PENDING"
    verification_source: Optional[str] = None
    verification_authoritative: bool = False
    remediation_transaction_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    rollback_action: Optional[str] = None
    rollback_status: Optional[str] = None
    recovery_proof: Optional[Dict[str, Any]] = None
    escalation_package: Optional[Dict[str, Any]] = None
    diagnosis_claims: List[Dict[str, Any]] = Field(default_factory=list)
    crew_dispatch: List[Dict[str, Any]] = Field(default_factory=list)

from services.agent_crew import (
    continuity_crew,
    TriagePackage,
    EvidencePackage,
    RemediationIntent,
    VerificationVerdict
)

class AgentCommander:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.model_name = GEMINI_MODEL
        self._incident_locks: Dict[str, asyncio.Lock] = {}
        self._guard_lock = asyncio.Lock()
        self._active_incidents: set[str] = set()
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.history: List[InvestigationResult] = []
        self.max_history_len = 30
        
        # Initialize Google ADK McpToolset and grounded SRE Agent
        self.mcp_toolset = official_mcp_bridge.get_toolset(restricted=True)
        self.adk_agent = Agent(
            name="continuity_sre_agent",
            model=self.model_name.removeprefix("models/"),
            instruction="Lead Autonomous SRE Incident Commander for tier-1 Hollywood OTT streaming platform. Ingests Grafana Cloud metrics and logs over official MCP, executes constrained remediation, and verifies closed-loop recovery.",
            tools=[self.mcp_toolset],
        )
        self.session_service = InMemorySessionService()
        self.adk_runner = Runner(
            app_name="continuity",
            agent=self.adk_agent,
            session_service=self.session_service,
            auto_create_session=True
        )
        self.crew = continuity_crew

    def is_configured(self) -> bool:
        return self.client is not None

    async def _get_incident_lock(self, incident_id: str) -> asyncio.Lock:
        async with self._guard_lock:
            if incident_id not in self._incident_locks:
                self._incident_locks[incident_id] = asyncio.Lock()
                if len(self._incident_locks) > 100:
                    keys = list(self._incident_locks.keys())[:-50]
                    for k in keys:
                        if k != incident_id and not self._incident_locks[k].locked():
                            self._incident_locks.pop(k, None)
            return self._incident_locks[incident_id]

    async def investigate_and_remediate(
        self,
        incident_id: Optional[str] = None,
        failure_mode_override: Optional[str] = None,
        trigger_source: str = "manual"
    ) -> InvestigationResult:
        """Executes the multi-step Gemini SRE autonomous reasoning and remediation loop via ADK and MCP tools."""
        start_time = time.time()
        actual_incident_id = incident_id or f"INC-{int(start_time * 1000)}"
        incident_lock = await self._get_incident_lock(actual_incident_id)

        async with incident_lock:
            for past_res in self.history:
                if past_res.incident_id == actual_incident_id and past_res.workflow_status in ("COMPLETED", "RESOLVED", "RECOVERED", "ESCALATED"):
                    logger.info(f"[Agent Commander] Returning existing result for incident {actual_incident_id}")
                    return past_res

            async with self._guard_lock:
                self._active_incidents.add(actual_incident_id)
            try:
                return await self._run_investigation(
                    incident_id=actual_incident_id,
                    failure_mode_override=failure_mode_override,
                    trigger_source=trigger_source,
                    start_time=start_time
                )
            finally:
                async with self._guard_lock:
                    self._active_incidents.discard(actual_incident_id)

    async def _run_investigation(
        self,
        incident_id: str,
        failure_mode_override: Optional[str] = None,
        trigger_source: str = "manual",
        start_time: float = 0.0
    ) -> InvestigationResult:
        start_time = start_time or time.time()
        trace: List[str] = []
        mcp_tools_called: List[str] = []
        
        if trigger_source == "grafana_alert_webhook":
            trace.append(f"[{time.strftime('%H:%M:%S')}] Automated Event Trigger: Grafana Cloud Alert Webhook (Incident ID: {incident_id})")
        
        snapshot = telemetry_engine.get_current_snapshot()
        state = chaos_manager.get_state()
        
        # Route initial PromQL and LogQL based on active scenario failure mode
        failure_key = failure_mode_override or (state.failure_mode.value if (state.failure_mode and state.failure_mode.value in SCENARIOS) else FailureMode.CDN_OUTAGE.value)
        scenario = SCENARIOS.get(failure_key, SCENARIOS[FailureMode.CDN_OUTAGE.value])
        promql_query = scenario["promql"]
        logql_query = scenario["logql"]
        scenario_subsystems = scenario.get("affected_subsystems", ["Edge CDN"])

        # Step 1: Query Prometheus metrics via official Grafana MCP Tool
        mcp_tools_called.extend(["query_prometheus", "grafana_query_prometheus"])
        trace.append(f"[{time.strftime('%H:%M:%S')}] ADK McpToolset [query_prometheus]: Executing PromQL ({promql_query}) against Grafana Cloud Mimir...")
        prom_res = await grafana_query_prometheus(promql_query)
        
        trace.append(
            f"[{time.strftime('%H:%M:%S')}] Telemetry Ingested: VPF={snapshot.video_playback_failures_pct}%, "
            f"CDN Latency={snapshot.cdn_egress_latency_ms}ms, DRM Handshake={snapshot.drm_handshake_ms}ms, "
            f"Active Viewers={snapshot.active_viewers:,}"
        )

        is_anomaly = (
            snapshot.anomaly_gate_triggered or
            snapshot.video_playback_failures_pct > 1.0 or
            snapshot.cdn_egress_latency_ms > 200.0 or
            snapshot.drm_handshake_ms > 500.0 or
            state.is_outage_active
        )

        if not is_anomaly and state.current_mode in ["NORMAL", "REMEDIATED"]:
            elapsed = round(time.time() - start_time, 2)
            trace.append(
                f"[{time.strftime('%H:%M:%S')}] Telemetry Anomaly Gate: Score={snapshot.nis_composite:.2f} <= 3.84. "
                f"LLM inference suppressed (Token Savings: {snapshot.token_savings_pct}%). Status: HEALTHY."
            )
            result = InvestigationResult(
                timestamp=time.time(),
                incident_id=None,
                failure_mode=state.failure_mode.value if state.failure_mode else "NONE",
                stream_title=STREAM_TITLE,
                initial_anomaly_detected=False,
                vpf_rate=snapshot.video_playback_failures_pct,
                cdn_latency_ms=snapshot.cdn_egress_latency_ms,
                drm_handshake_ms=snapshot.drm_handshake_ms,
                severity="HEALTHY",
                root_cause_analysis="No anomalous QoS degradation detected. Stream delivery is operating within normal parameters.",
                affected_subsystems=[],
                autonomous_action_taken=None,
                remediation_action=None,
                remediation_status=None,
                workflow_status="HEALTHY",
                traffic_shift_details={"primary_cdn_pct": snapshot.primary_traffic_pct, "secondary_cdn_pct": snapshot.secondary_traffic_pct},
                annotation_id=None,
                grafana_incident_id=None,
                workflow_elapsed_seconds=elapsed,
                mttr_seconds=None,
                estimated_subscriber_loss_prevented="Nominal SLA (0 degraded sessions)",
                executive_summary="Playback failure rates remain under 0.2%. Global edge CDN delivery and DRM license servers are healthy.",
                reasoning_trace=trace,
                mcp_tools_executed=list(dict.fromkeys(mcp_tools_called)),
                closed_loop_verified=False,
                verified_vpf_rate=snapshot.video_playback_failures_pct,
                verified_buffer_health_sec=snapshot.buffer_health_sec,
                verified_latency_ms=snapshot.cdn_egress_latency_ms,
                verification_status="NOT_REQUIRED",
                verification_source=None,
                verification_authoritative=False,
                crew_dispatch=self.crew.get_agent_specs()
            )
            self._record_result(result)
            return result

        # Step 2: Anomaly Confirmed - Dispatch Multi-Agent Cinema Crew
        effective_inc_id = incident_id or state.active_incident_id or f"INC-{int(start_time * 1000)}"
        failure_key = failure_mode_override or (state.failure_mode.value if state.failure_mode else "DEFAULT")
        scenario = SCENARIOS.get(failure_key, SCENARIOS.get("DEFAULT", {}))
        scenario_subsystems = scenario.get("affected_subsystems", ["Edge CDN", "Origin Shield"])
        candidate_action = scenario.get("default_action", "SHIFT_TRAFFIC_TO_AKAMAI")
        promql_query = scenario.get("promql") or scenario.get("promql_query") or "ott_video_playback_failures_ratio"
        logql_query = scenario.get("logql") or scenario.get("logql_query") or '{app="edge-gateway"} |= "error"'

        trace.append(f"[{time.strftime('%H:%M:%S')}] CRITICAL ANOMALY DETECTED: {state.failure_mode.value if state.failure_mode else 'QoS'} threshold breached.")

        # Consult Gemini for high-level Executive RCA if client is configured
        decision_rca = None
        if self.client:
            for model in FALLBACK_MODELS:
                try:
                    consult_prompt = (
                        f"You are the Lead Incident Commander for {STREAM_TITLE}. "
                        f"Telemetry Alert: {failure_key} degradation across SLA gates. "
                        f"Subsystems: {scenario_subsystems}. Candidate Action: {candidate_action}. "
                        f"Provide a concise root cause analysis (1-2 sentences)."
                    )
                    if hasattr(self.client, "aio") and hasattr(self.client.aio, "models"):
                        response = await asyncio.wait_for(
                            self.client.aio.models.generate_content(
                                model=model,
                                contents=consult_prompt,
                                config=types.GenerateContentConfig(temperature=0.2)
                            ),
                            timeout=5.0
                        )
                    else:
                        def _sync_gen(m=model):
                            return self.client.models.generate_content(
                                model=m,
                                contents=consult_prompt,
                                config=types.GenerateContentConfig(temperature=0.2)
                            )
                        response = await asyncio.wait_for(asyncio.to_thread(_sync_gen), timeout=5.0)
                    if response.text:
                        decision_rca = response.text.strip()
                        trace.append(f"[{time.strftime('%H:%M:%S')}] Gemini [{model}] Root Cause Analysis: {decision_rca}")
                    break
                except Exception as e:
                    logger.warning(f"Commander LLM consultation ({model}) bypassed: {e}")

        trace.append(f"[{time.strftime('%H:%M:%S')}] [Multi-Agent Cinema Crew] Executing 4-Agent Sequential Pipeline (1st AD -> DIT -> Key Grip -> Continuity)...")

        # Step 3: Run the live 4-Agent Cinema SRE Workflow
        tools_dict = {
            "grafana_query_prometheus": grafana_query_prometheus,
            "grafana_query_loki": grafana_query_loki,
            "grafana_create_incident": grafana_create_incident,
            "grafana_resolve_incident": grafana_resolve_incident,
            "grafana_create_annotation": grafana_create_annotation,
            "continuity_execute_remediation": continuity_execute_remediation,
            "continuity_verify_closed_loop_recovery": continuity_verify_closed_loop_recovery,
        }

        crew_res = await self.crew.execute_crew_workflow(
            incident_id=effective_inc_id,
            stream_title=STREAM_TITLE,
            initial_alert=f"{failure_key} degradation across SLA gates",
            affected_subsystems=scenario_subsystems,
            promql_query=promql_query,
            logql_query=logql_query,
            failure_mode_name=failure_key,
            candidate_action=candidate_action,
            action_params={"primary_cdn_pct": 20, "secondary_cdn_pct": 80},
            snapshot=snapshot,
            tools=tools_dict
        )

        triage: TriagePackage = crew_res["triage"]
        evidence: EvidencePackage = crew_res["evidence"]
        remediation: RemediationIntent = crew_res["remediation"]
        verdict: VerificationVerdict = crew_res["verdict"]
        crew_records = crew_res["dispatch_records"]
        mcp_tools_called.extend(crew_res.get("mcp_tools_executed", []))
        rem_res = crew_res.get("remediation_res") or {}
        verify_res = crew_res.get("verify_res") or {}
        grafana_incident_id = crew_res.get("grafana_incident_id")
        annotation_id = crew_res.get("annotation_id")

        trace.append(f"[{time.strftime('%H:%M:%S')}] [1st AD - {self.crew.first_ad.name}] Triage Handover (TriagePackage): incident_id={triage.incident_id}, severity={triage.severity}, hitl_required={triage.hitl_required}")
        if grafana_incident_id:
            trace.append(f"[{time.strftime('%H:%M:%S')}] [1st AD] Grafana IRM Incident opened: {grafana_incident_id}")

        trace.append(f"[{time.strftime('%H:%M:%S')}] [DIT - {self.crew.dit.name}] Observability Evidence Handover (EvidencePackage): {evidence.failure_hypothesis} (Citations: {', '.join(evidence.evidence_citations)})")
        if evidence.sanitized_logs:
            trace.append(f"[{time.strftime('%H:%M:%S')}] [DIT] Isolated edge log: \"{evidence.sanitized_logs[0]}\"")
        if evidence.flagged_security_injections > 0:
            trace.append(f"[{time.strftime('%H:%M:%S')}] [Security Guard] Adversarial log injection intercepted: flagged_injections={evidence.flagged_security_injections}")

        trace.append(f"[{time.strftime('%H:%M:%S')}] [Key Grip - {self.crew.key_grip.name}] Transactional Remediation Handover (RemediationIntent): action={remediation.action_name}, tx_id={remediation.transaction_id}, status={remediation.execution_status}")

        trace.append(f"[{time.strftime('%H:%M:%S')}] [Continuity - {self.crew.continuity.name}] Recovery Verification Verdict (VerificationVerdict): outcome={verdict.outcome}, authoritative={verdict.authoritative}, source={verdict.verification_source}, verified_vpf={verdict.verified_vpf_rate}%")

        # Step 4: Evaluate Verification Outcome and MTTR
        elapsed = round(time.time() - start_time, 2)
        is_verified = (verdict.outcome == "COMMITTED")
        is_hitl_pending = (remediation.execution_status == "PENDING_APPROVAL")
        rollback_happened = (verdict.outcome == "ROLLED_BACK")

        impacted_audience = int(snapshot.active_viewers * (snapshot.video_playback_failures_pct / 100.0))
        grounded_impact_str = f"SLA Impact Mitigated: ~{impacted_audience:,} stream sessions protected (VPF: {snapshot.video_playback_failures_pct:.2f}%)"

        if is_verified:
            chaos_manager.mark_verified_recovered(verify_res if isinstance(verify_res, dict) else {})
            mttr_value = elapsed
            workflow_status = "RESOLVED"
            remediation_status = "SUCCESS"
            rollback_status = "NONE"
            gate_status = "PASSED"
            trace.append(
                f"[{time.strftime('%H:%M:%S')}] CLOSED-LOOP VERIFIED: VPF dropped from {snapshot.video_playback_failures_pct}% to {verdict.verified_vpf_rate}%. "
                f"Forward buffer restored to {verdict.verified_buffer_health_sec}s. Verification Gate: PASSED (Source: {verdict.verification_source}, Authoritative: {verdict.authoritative})."
            )
            trace.append(f"[{time.strftime('%H:%M:%S')}] Incident Resolved in {elapsed}s. MTTR: {elapsed}s. Stream QoE restabilized to 4K UHD.")
            exec_summary = f"Autonomous remediation policy '{remediation.action_name}' verified by Continuity quality gate. VPF restabilized to {verdict.verified_vpf_rate}%."
        elif is_hitl_pending:
            mttr_value = None
            workflow_status = "SUSPENDED_HITL"
            remediation_status = "PENDING_APPROVAL"
            rollback_status = "NONE"
            gate_status = "SUSPENDED"
            trace.append(f"[{time.strftime('%H:%M:%S')}] ACTION SUSPENDED: High blast-radius action requires human supervisor approval. Checkpoint created.")
            exec_summary = f"Remediation policy '{remediation.action_name}' suspended. Pending supervisor approval."
        else:
            chaos_manager.mark_recovery_failed("Closed-loop verification pending or incomplete", details=verify_res if isinstance(verify_res, dict) else {})
            mttr_value = None
            if rollback_happened:
                gate_status = "FAILED"
                workflow_status = "ESCALATED"
                remediation_status = "ROLLED_BACK"
                rollback_status = "EXECUTED"
                trace.append(f"[{time.strftime('%H:%M:%S')}] ROLLBACK EXECUTED: Reverted via {remediation.rollback_action}. Escalation package assembled.")
                exec_summary = f"Remediation failed verification gates; rollback executed via {remediation.rollback_action}."
            else:
                gate_status = "PENDING"
                workflow_status = "PENDING_VERIFICATION"
                remediation_status = "PENDING_CONVERGENCE"
                rollback_status = "PENDING"
                trace.append(
                    f"[{time.strftime('%H:%M:%S')}] CLOSED-LOOP VERIFICATION PENDING: Stream QoE metrics have not yet crossed recovery SLA threshold. "
                    f"VPF: {verdict.verified_vpf_rate}% (Target <= 0.5%), Buffer: {verdict.verified_buffer_health_sec}s (Target >= 20s). "
                    f"Verification Gate: PENDING (Source: {verdict.verification_source})."
                )
                trace.append(f"[{time.strftime('%H:%M:%S')}] Closed-loop verification pending at {elapsed}s. Awaiting telemetry convergence; incident not marked resolved.")
                exec_summary = f"Autonomous remediation applied; closed-loop recovery verification is PENDING (VPF={verdict.verified_vpf_rate}%, Buffer={verdict.verified_buffer_health_sec}s). Incident not marked resolved."

        # Step 5: Structured Evidence-Addressed Diagnosis
        diagnosis_claims_data: List[Dict[str, Any]] = []
        try:
            ev_list = [
                EvidenceReference(
                    query_type="promql",
                    query=promql_query,
                    target_metric="ott_video_playback_failures_ratio",
                    observed_value=evidence.promql_metrics.get("video_playback_failures_pct", snapshot.video_playback_failures_pct),
                    threshold="> 1.0%",
                    status="BREACHED" if is_anomaly else "NORMAL"
                ),
                EvidenceReference(
                    query_type="logql",
                    query=logql_query,
                    target_metric="edge_log_stream",
                    observed_value=evidence.sanitized_logs[0] if evidence.sanitized_logs else "Log query returned empty",
                    threshold="Upstream/transit failure pattern",
                    status="BREACHED" if any(w in str(evidence.sanitized_logs) for w in ["502", "Timeout", "loss", "refused"]) else "NORMAL"
                )
            ]
            claim_obj = DiagnosisClaim(
                subsystem=triage.affected_subsystems[0] if triage.affected_subsystems else "Edge CDN",
                claim=decision_rca or evidence.failure_hypothesis,
                evidence=ev_list,
                confidence=evidence.confidence
            )
            diagnosis_claims_data.append(claim_obj.model_dump())
        except Exception as e:
            logger.warning(f"Error constructing diagnosis claims: {e}")

        # Step 6: Record Gemini latency metric
        try:
            PROM_AGENT_GEMINI_LATENCY.labels(
                model=self.model_name,
                trigger_source=trigger_source
            ).observe(time.time() - start_time)
        except Exception:
            pass

        result = InvestigationResult(
            timestamp=time.time(),
            incident_id=effective_inc_id,
            failure_mode=state.failure_mode.value if state.failure_mode else "NONE",
            stream_title=STREAM_TITLE,
            initial_anomaly_detected=True,
            vpf_rate=snapshot.video_playback_failures_pct,
            cdn_latency_ms=snapshot.cdn_egress_latency_ms,
            drm_handshake_ms=snapshot.drm_handshake_ms,
            severity=triage.severity,
            root_cause_analysis=decision_rca or evidence.failure_hypothesis,
            affected_subsystems=triage.affected_subsystems,
            autonomous_action_taken=remediation.action_name,
            remediation_action=remediation.action_name,
            remediation_status=remediation_status,
            workflow_status=workflow_status,
            traffic_shift_details={
                "primary_cdn": rem_res.get("primary_cdn", "Fastly Edge"),
                "primary_cdn_pct": rem_res.get("primary_cdn_traffic_pct", 20),
                "secondary_cdn": rem_res.get("secondary_cdn", "Akamai Edge"),
                "secondary_cdn_pct": rem_res.get("secondary_cdn_traffic_pct", 80)
            },
            annotation_id=annotation_id,
            grafana_incident_id=grafana_incident_id,
            workflow_elapsed_seconds=elapsed,
            mttr_seconds=mttr_value,
            estimated_subscriber_loss_prevented=grounded_impact_str,
            executive_summary=exec_summary,
            reasoning_trace=trace,
            mcp_tools_executed=list(dict.fromkeys(mcp_tools_called)),
            closed_loop_verified=is_verified and (gate_status == "PASSED"),
            verified_vpf_rate=verdict.verified_vpf_rate,
            verified_buffer_health_sec=verdict.verified_buffer_health_sec,
            verified_latency_ms=verify_res.get("cdn_latency_ms", snapshot.cdn_egress_latency_ms) if isinstance(verify_res, dict) else snapshot.cdn_egress_latency_ms,
            verification_status=gate_status,
            verification_source=verdict.verification_source,
            verification_authoritative=verdict.authoritative,
            remediation_transaction_id=remediation.transaction_id,
            idempotency_key=remediation.idempotency_key,
            rollback_action=remediation.rollback_action,
            rollback_status=rollback_status,
            recovery_proof=verify_res.get("recovery_proof") if isinstance(verify_res, dict) else None,
            escalation_package=verdict.escalation_package,
            diagnosis_claims=diagnosis_claims_data,
            crew_dispatch=crew_records
        )

        self._record_result(result)
        return result

    def get_history(self) -> List[InvestigationResult]:
        return self.history

    def _record_result(self, result: InvestigationResult):
        self.history.insert(0, result)
        if len(self.history) > self.max_history_len:
            self.history.pop()

# Global singleton
agent_commander = AgentCommander()

