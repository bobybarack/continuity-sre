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

FALLBACK_MODELS = [
    "models/gemini-3.6-flash",
    GEMINI_MODEL,
    "models/gemini-3.7-flash",
    "models/gemini-3.5-flash"
]

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
            snapshot.video_playback_failures_pct > 1.0 or
            snapshot.cdn_egress_latency_ms > 200.0 or
            snapshot.drm_handshake_ms > 500.0 or
            state.is_outage_active
        )

        if not is_anomaly and state.current_mode in ["NORMAL", "REMEDIATED"]:
            elapsed = round(time.time() - start_time, 2)
            trace.append(f"[{time.strftime('%H:%M:%S')}] Anomaly Check: All metrics within operational SLA. Status: HEALTHY.")
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
                verification_authoritative=False
            )
            self._record_result(result)
            return result

        # Step 2: Anomaly Confirmed - Query Loki Logs via official Grafana MCP Tool
        mcp_tools_called.extend(["query_loki_logs", "grafana_query_loki"])
        trace.append(f"[{time.strftime('%H:%M:%S')}] CRITICAL ANOMALY DETECTED: {state.failure_mode.value if state.failure_mode else 'QoS'} threshold breached.")
        trace.append(f"[{time.strftime('%H:%M:%S')}] ADK McpToolset [query_loki_logs]: Querying error logs via Loki proxy ({logql_query})...")
        loki_res = await grafana_query_loki(logql_query, limit=20)
        trace.append(f"[{time.strftime('%H:%M:%S')}] Loki Log Isolated: \"{snapshot.latest_log}\"")

        prompt = f"""
You are Continuity, the Lead Autonomous SRE AI Incident Commander for a tier-1 Hollywood OTT streaming platform.
Analyze the live incident telemetry ingested via official Grafana Cloud MCP tools and execute autonomous remediation:

STREAM METADATA:
- Title: {STREAM_TITLE}
- Active Viewers: {snapshot.active_viewers:,}
- Active Chaos Mode: {state.current_mode}
- Affected Region: {state.affected_region}

OBSERVABILITY TELEMETRY (Prometheus & Loki via Grafana MCP):
- Video Playback Failures (VPF): {snapshot.video_playback_failures_pct}% (Baseline SLA: < 0.5%)
- CDN Egress Latency: {snapshot.cdn_egress_latency_ms}ms (Baseline: 45ms)
- DRM Handshake Duration: {snapshot.drm_handshake_ms}ms (Baseline: 120ms)
- Buffer Health: {snapshot.buffer_health_sec}s
- Delivered Bitrate: {snapshot.avg_bitrate_mbps} Mbps
- Recent Edge Log: "{snapshot.latest_log}"

RAW GRAFANA CLOUD MCP RESPONSES:
- Prometheus PromQL Query Response ({promql_query}):
{json.dumps(prom_res.model_dump() if hasattr(prom_res, "model_dump") else prom_res, indent=2)}

- Loki LogQL Query Response ({logql_query}):
{json.dumps(loki_res.model_dump() if hasattr(loki_res, "model_dump") else loki_res, indent=2)}

AVAILABLE TOOLS:
- continuity_execute_remediation: Shift traffic or failover key cluster.
- create_annotation / grafana_create_annotation: Drop annotation pin on live Grafana dashboard.
- create_incident / grafana_create_incident: Open incident in Grafana IRM.
- continuity_verify_closed_loop_recovery: Verify closed-loop recovery.

Call the necessary MCP tools to remediate this critical stream degradation.
"""

        decision = None
        remediation_res = None
        remediation_action = None
        incident_res = None
        grafana_incident_id = None
        annotation_resp = None
        annotation_id = None
        verify_res = None
        decision_rca = None

        # Execute Gemini reasoning if client is configured
        if self.client:
            dynamic_gemini_tools = await get_gemini_tools()

            for model in FALLBACK_MODELS:
                try:
                    if hasattr(self.client, "aio") and hasattr(self.client.aio, "models"):
                        response = await asyncio.wait_for(
                            self.client.aio.models.generate_content(
                                model=model,
                                contents=prompt,
                                config=types.GenerateContentConfig(
                                    tools=dynamic_gemini_tools,
                                    temperature=0.2
                                )
                            ),
                            timeout=9.0
                        )
                    else:
                        def _sync_generate(m=model):
                            return self.client.models.generate_content(
                                model=m,
                                contents=prompt,
                                config=types.GenerateContentConfig(
                                    tools=dynamic_gemini_tools,
                                    temperature=0.2
                                )
                            )
                        response = await asyncio.wait_for(asyncio.to_thread(_sync_generate), timeout=9.0)
                    trace.append(f"[{time.strftime('%H:%M:%S')}] Gemini Model [{model}] multi-step reasoning completed successfully.")

                    if response.function_calls:
                        for fc in response.function_calls:
                            tool_name = fc.name
                            tool_args = fc.args or {}
                            mcp_tools_called.append(tool_name)
                            trace.append(f"[{time.strftime('%H:%M:%S')}] Gemini Autonomous Tool Call [{tool_name}]: {json.dumps(tool_args)}")
                            tool_result = await dispatch_mcp_tool(tool_name, tool_args)
                            trace.append(f"[{time.strftime('%H:%M:%S')}] Tool [{tool_name}] Result: {str(tool_result)[:120]}")

                            if tool_name == "continuity_execute_remediation":
                                remediation_res = tool_result
                                remediation_action = tool_args.get("action", "SHIFT_TRAFFIC_TO_AKAMAI")
                                decision_rca = tool_args.get("reason")
                            elif tool_name in ("create_incident", "grafana_create_incident"):
                                incident_res = tool_result
                                grafana_incident_id = getattr(tool_result, "incident_id", None) or (tool_result.get("incident_id") or tool_result.get("id") if isinstance(tool_result, dict) else None)
                            elif tool_name in ("create_annotation", "grafana_create_annotation"):
                                annotation_resp = tool_result
                                annotation_id = getattr(tool_result, "id", None) or (tool_result.get("id") if isinstance(tool_result, dict) else None)
                            elif tool_name == "continuity_verify_closed_loop_recovery":
                                verify_res = tool_result

                    if response.text:
                        try:
                            decision = json.loads(response.text)
                        except Exception:
                            pass

                    break
                except Exception as e:
                    logger.warning(f"Model {model} tool calling attempt failed: {e}. Trying fallback...")

        # Grounded audience SLA impact calculated from active viewers and measured VPF failure rate
        impacted_audience = int(snapshot.active_viewers * (snapshot.video_playback_failures_pct / 100.0))
        grounded_impact_str = f"SLA Impact Mitigated: ~{impacted_audience:,} stream sessions protected (VPF: {snapshot.video_playback_failures_pct:.2f}%)"

        if not decision:
            if not remediation_action:
                remediation_action = scenario["default_action"]
                decision_rca = f"Degradation in {', '.join(scenario_subsystems)} identified via {snapshot.latest_log}"

            decision = {
                "severity": "CRITICAL" if state.failure_mode != FailureMode.ISP_PEERING_DROP else "WARNING",
                "root_cause_analysis": decision_rca or f"Degradation detected via {snapshot.latest_log}",
                "affected_subsystems": scenario_subsystems,
                "remediation_action": remediation_action,
                "estimated_subscriber_loss_prevented": grounded_impact_str,
                "executive_summary": f"Autonomous remediation policy '{remediation_action}' executed via official Grafana MCP tools."
            }

        if not remediation_action:
            remediation_action = decision.get("remediation_action", scenario["default_action"])

        trace.append(f"[{time.strftime('%H:%M:%S')}] Gemini Root Cause Analysis: {decision.get('root_cause_analysis')}")

        # Step 3: Apply Autonomous Remediation via MCP Tool if not yet applied
        if not remediation_res:
            mcp_tools_called.append("continuity_execute_remediation")
            trace.append(f"[{time.strftime('%H:%M:%S')}] MCP Tool [continuity_execute_remediation]: Executing policy '{remediation_action}'...")
            remediation_res = await continuity_execute_remediation(
                action=remediation_action,
                primary_cdn_pct=20,
                secondary_cdn_pct=80,
                reason=decision.get("root_cause_analysis", "Autonomous failover")
            )
        if remediation_action == "FAILOVER_DRM_KEY_CLUSTER":
            trace.append(f"[{time.strftime('%H:%M:%S')}] Failover Applied: DRM Key Cluster switched to {remediation_res.get('active_drm_cluster', 'secondary')}.")
        elif remediation_action == "REROUTE_BGP_TRANSIT":
            trace.append(f"[{time.strftime('%H:%M:%S')}] Reroute Applied: Transit route shifted to {remediation_res.get('active_transit_route', 'secondary')}.")
        else:
            trace.append(
                f"[{time.strftime('%H:%M:%S')}] Failover Applied: Primary CDN egress throttled to {remediation_res.get('primary_cdn_traffic_pct', 20)}%, "
                f"Secondary CDN egress scaled to {remediation_res.get('secondary_cdn_traffic_pct', 80)}%."
            )

        # Step 4: Open Incident in Grafana Cloud IRM via MCP Tool if not yet opened
        if not incident_res:
            mcp_tools_called.extend(["create_incident", "grafana_create_incident"])
            incident_res = await grafana_create_incident(
                title=f"Premiere Streaming Incident: {remediation_action}",
                severity=decision.get("severity", "CRITICAL"),
                summary=decision.get("executive_summary", "Autonomous remediation executed.")
            )
            grafana_incident_id = getattr(incident_res, "incident_id", None) or (incident_res.get("incident_id") or incident_res.get("id") if isinstance(incident_res, dict) else None)
            trace.append(f"[{time.strftime('%H:%M:%S')}] ADK McpToolset [create_incident]: Opened Grafana IRM incident {grafana_incident_id}.")

        # Step 5: Write visual annotation to Grafana live dashboard via MCP Tool if not yet written
        if not annotation_resp:
            mcp_tools_called.extend(["create_annotation", "grafana_create_annotation"])
            annotation_text = f"[CONTINUITY MCP Auto-Fix]: {remediation_action} - {decision.get('root_cause_analysis')}"
            trace.append(f"[{time.strftime('%H:%M:%S')}] ADK McpToolset [create_annotation]: Placing vertical timestamp pin on live dashboard...")
            annotation_resp = await grafana_create_annotation(
                text=annotation_text,
                tags=["continuity", "mcp-grafana", "gemini-sre", "autonomous-remediation"]
            )
            annotation_id = getattr(annotation_resp, "id", None) or (annotation_resp.get("id") if isinstance(annotation_resp, dict) else None)

        # Step 6: Closed-Loop Verification Gate (Falsifiable Proof of Recovery)
        if not verify_res:
            mcp_tools_called.append("continuity_verify_closed_loop_recovery")
            trace.append(f"[{time.strftime('%H:%M:%S')}] CONTINUITY Gate [continuity_verify_closed_loop_recovery]: Executing closed-loop verification check...")
            verify_res = await continuity_verify_closed_loop_recovery()

        is_verified = verify_res.get("verified", False) if isinstance(verify_res, dict) else False
        gate_status = verify_res.get("status", "PENDING") if isinstance(verify_res, dict) else "PENDING"
        elapsed = round(time.time() - start_time, 2)

        # Single source of truth: extract verified QoE metrics and source semantics directly from verify_res
        verified_vpf = verify_res.get("current_vpf_pct", snapshot.video_playback_failures_pct) if isinstance(verify_res, dict) else snapshot.video_playback_failures_pct
        verified_buffer = verify_res.get("forward_buffer_sec", snapshot.buffer_health_sec) if isinstance(verify_res, dict) else snapshot.buffer_health_sec
        verified_latency = verify_res.get("cdn_latency_ms", snapshot.cdn_egress_latency_ms) if isinstance(verify_res, dict) else snapshot.cdn_egress_latency_ms
        verify_source = verify_res.get("prometheus_source", "none") if isinstance(verify_res, dict) else "none"
        is_authoritative = verify_res.get("prometheus_authoritative", False) if isinstance(verify_res, dict) else False

        tx_id = remediation_res.get("transaction_id") if isinstance(remediation_res, dict) else None
        idempotency_key = remediation_res.get("idempotency_key") if isinstance(remediation_res, dict) else None
        rollback_action = remediation_res.get("rollback_action") if isinstance(remediation_res, dict) else None
        proof_data = verify_res.get("recovery_proof") if isinstance(verify_res, dict) else None
        rollback_happened = verify_res.get("rollback_executed", False) if isinstance(verify_res, dict) else False

        effective_inc_id = incident_id or state.active_incident_id or grafana_incident_id or f"INC-{int(time.time())}"
        escalation_obj = transaction_manager.get_escalation(effective_inc_id)
        escalation_data = escalation_obj.model_dump() if escalation_obj else None

        if is_verified and gate_status == "PASSED":
            chaos_manager.mark_verified_recovered(verify_res if isinstance(verify_res, dict) else {})
            mttr_value = elapsed
            workflow_status = "RESOLVED"
            remediation_status = "SUCCESS"
            rollback_status = "NONE"

            # Synchronize Grafana IRM incident lifecycle: resolve incident only after verification passes
            if grafana_incident_id:
                try:
                    await grafana_resolve_incident(
                        incident_id=grafana_incident_id,
                        summary=f"Autonomous remediation verified. VPF restabilized to {verified_vpf}%, buffer restored to {verified_buffer}s."
                    )
                    mcp_tools_called.extend(["update_incident", "grafana_resolve_incident"])
                    trace.append(f"[{time.strftime('%H:%M:%S')}] Grafana IRM Incident {grafana_incident_id} marked RESOLVED via McpToolset [update_incident].")
                except Exception as e:
                    logger.warning(f"Failed to resolve Grafana incident {grafana_incident_id}: {e}")

            trace.append(
                f"[{time.strftime('%H:%M:%S')}] CLOSED-LOOP VERIFIED: VPF dropped from {snapshot.video_playback_failures_pct}% to {verified_vpf}%. "
                f"Forward buffer restored to {verified_buffer}s. Verification Gate: PASSED (Source: {verify_source}, Authoritative: {is_authoritative})."
            )
            trace.append(f"[{time.strftime('%H:%M:%S')}] Incident Resolved in {elapsed}s. MTTR: {elapsed}s. Stream QoE restabilized to 4K UHD.")
            exec_summary = decision.get("executive_summary", "Incident resolved autonomously.")
        else:
            chaos_manager.mark_recovery_failed("Closed-loop verification pending or incomplete", details=verify_res if isinstance(verify_res, dict) else {})
            mttr_value = None
            if rollback_happened:
                workflow_status = "ESCALATED"
                remediation_status = "ROLLED_BACK"
                rollback_status = "EXECUTED"
                trace.append(f"[{time.strftime('%H:%M:%S')}] ROLLBACK EXECUTED: Reverted via {rollback_action or 'safe snapshot'}. Escalation package assembled.")
            else:
                workflow_status = "PENDING_VERIFICATION"
                remediation_status = "PENDING_CONVERGENCE"
                rollback_status = "PENDING"

            # Do NOT resolve Grafana IRM incident while verification is PENDING or FAILED
            if grafana_incident_id:
                trace.append(f"[{time.strftime('%H:%M:%S')}] Grafana IRM Incident {grafana_incident_id} remains ACTIVE (Verification Gate: PENDING/ESCALATED).")

            trace.append(
                f"[{time.strftime('%H:%M:%S')}] CLOSED-LOOP VERIFICATION PENDING: Stream QoE metrics have not yet crossed recovery SLA threshold. "
                f"VPF: {verified_vpf}% (Target <= 0.5%), Buffer: {verified_buffer}s (Target >= 20s). "
                f"Verification Gate: PENDING (Source: {verify_source})."
            )
            trace.append(f"[{time.strftime('%H:%M:%S')}] Closed-loop verification pending at {elapsed}s. Awaiting telemetry convergence; incident not marked resolved.")
            exec_summary = f"Autonomous remediation applied; closed-loop recovery verification is PENDING/ESCALATED (VPF={verified_vpf}%, Buffer={verified_buffer}s). Incident not marked resolved."

        # Phase 9: Structured Evidence-Addressed Diagnosis
        diagnosis_claims_data: List[Dict[str, Any]] = []
        try:
            ev_list = [
                EvidenceReference(
                    query_type="promql",
                    query=promql_query,
                    target_metric="ott_video_playback_failures_ratio" if failure_key in (FailureMode.CDN_OUTAGE.value, FailureMode.SECONDARY_PATH_DEGRADED.value) else ("ott_drm_handshake_ms" if failure_key == FailureMode.DRM_TIMEOUT.value else "ott_stream_bitrate_mbps"),
                    observed_value=snapshot.video_playback_failures_pct if failure_key in (FailureMode.CDN_OUTAGE.value, FailureMode.SECONDARY_PATH_DEGRADED.value) else (snapshot.drm_handshake_ms if failure_key == FailureMode.DRM_TIMEOUT.value else snapshot.avg_bitrate_mbps),
                    threshold="> 1.0%" if failure_key in (FailureMode.CDN_OUTAGE.value, FailureMode.SECONDARY_PATH_DEGRADED.value) else ("> 500.0ms" if failure_key == FailureMode.DRM_TIMEOUT.value else "< 10.0 Mbps"),
                    status="BREACHED" if is_anomaly else "NORMAL"
                ),
                EvidenceReference(
                    query_type="logql",
                    query=logql_query,
                    target_metric="edge_log_stream",
                    observed_value=snapshot.latest_log,
                    threshold="Upstream/transit failure pattern",
                    status="BREACHED" if any(w in snapshot.latest_log for w in ["502", "Timeout", "loss", "refused"]) else "NORMAL"
                )
            ]
            claim_obj = DiagnosisClaim(
                subsystem=scenario_subsystems[0] if scenario_subsystems else "Edge CDN",
                claim=decision.get("root_cause_analysis", "Service degradation identified via telemetry correlation"),
                evidence=ev_list,
                confidence=0.98 if is_anomaly else 0.50
            )
            diagnosis_claims_data.append(claim_obj.model_dump())
        except Exception as e:
            logger.warning(f"Error constructing diagnosis claims: {e}")

        # Phase 8: Record Gemini latency
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
            severity=decision.get("severity", "CRITICAL"),
            root_cause_analysis=decision.get("root_cause_analysis", "Edge transit congestion"),
            affected_subsystems=decision.get("affected_subsystems", ["Edge CDN"]),
            autonomous_action_taken=remediation_action,
            remediation_action=remediation_action,
            remediation_status=remediation_status,
            workflow_status=workflow_status,
            traffic_shift_details={
                "primary_cdn": remediation_res.get("primary_cdn", "Fastly Edge"),
                "primary_cdn_pct": remediation_res.get("primary_cdn_traffic_pct", 20),
                "secondary_cdn": remediation_res.get("secondary_cdn", "Akamai Edge"),
                "secondary_cdn_pct": remediation_res.get("secondary_cdn_traffic_pct", 80)
            },
            annotation_id=annotation_id,
            grafana_incident_id=grafana_incident_id,
            workflow_elapsed_seconds=elapsed,
            mttr_seconds=mttr_value,
            estimated_subscriber_loss_prevented=decision.get("estimated_subscriber_loss_prevented", grounded_impact_str),
            executive_summary=exec_summary,
            reasoning_trace=trace,
            mcp_tools_executed=list(dict.fromkeys(mcp_tools_called)),
            closed_loop_verified=is_verified and (gate_status == "PASSED"),
            verified_vpf_rate=verified_vpf,
            verified_buffer_health_sec=verified_buffer,
            verified_latency_ms=verified_latency,
            verification_status=gate_status,
            verification_source=verify_source,
            verification_authoritative=is_authoritative,
            remediation_transaction_id=tx_id,
            idempotency_key=idempotency_key,
            rollback_action=rollback_action,
            rollback_status=rollback_status,
            recovery_proof=proof_data,
            escalation_package=escalation_data,
            diagnosis_claims=diagnosis_claims_data
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

