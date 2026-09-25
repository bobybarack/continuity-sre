import os
import time
import json
import asyncio
import logging
import shutil
from pathlib import Path
from contextlib import AsyncExitStack
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google.genai import types

from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams

from config import (
    GRAFANA_INSTANCE_URL,
    GRAFANA_TOKEN,
    GRAFANA_PROM_UID,
    GRAFANA_LOKI_UID,
)
from services.grafana_client import grafana_client
from services.chaos import chaos_manager
from services.telemetry import telemetry_engine, PROM_AGENT_MCP_TOOL_CALLS
from services.transaction_manager import transaction_manager
from services.integration_models import (
    PrometheusQueryResult,
    LokiQueryResult,
    GrafanaIncidentRef,
    GrafanaAnnotationRef,
    normalize_prometheus_result,
    normalize_loki_result,
    normalize_incident_result,
    normalize_annotation_result,
)

logger = logging.getLogger("continuity.mcp")

ALLOWED_GRAFANA_TOOLS = [
    "query_prometheus",
    "query_loki_logs",
    "create_annotation",
    "create_incident",
    "update_incident",
]

def parse_mcp_tool_result(res: Any) -> Any:
    """Parses full MCP CallToolResult handling isError, multiple content items, structured content, and fallbacks."""
    if res is None:
        return None

    is_error = getattr(res, "isError", False) or getattr(res, "is_error", False)
    content = getattr(res, "content", None)

    if not content:
        if is_error:
            logger.warning("[Official MCP] Tool execution reported isError=True with empty content")
            return {"status": "error", "error": "Tool returned error state with empty content"}
        return {}

    parsed_items = []
    for item in content:
        text_val = getattr(item, "text", None)
        if text_val is not None:
            try:
                parsed_items.append(json.loads(text_val))
            except Exception:
                parsed_items.append(text_val)
            continue

        data_val = getattr(item, "data", None)
        if data_val is not None:
            parsed_items.append(data_val)
            continue

        resource_val = getattr(item, "resource", None)
        if resource_val is not None:
            parsed_items.append(resource_val)
            continue

        parsed_items.append(str(item))

    if not parsed_items:
        return {"status": "error" if is_error else "empty"}

    if is_error:
        err_msg = parsed_items[0] if len(parsed_items) == 1 else parsed_items
        logger.warning(f"[Official MCP] Tool reported isError: {err_msg}")
        return {"status": "error", "error": err_msg}

    if len(parsed_items) == 1:
        return parsed_items[0]

    return parsed_items

class OfficialGrafanaMCPBridge:
    """Manages stdio sessions to the official grafana/mcp-grafana runtime server via Google ADK McpToolset."""
    def __init__(self):
        self.cached_tools: List[Dict[str, Any]] = []
        self._cached_declarations: Optional[List[types.FunctionDeclaration]] = None
        self._session: Optional[ClientSession] = None
        self._toolset: Optional[McpToolset] = None
        self._full_toolset: Optional[McpToolset] = None
        self.init_timeout = float(os.getenv("MCP_INIT_TIMEOUT", "15.0"))
        self.call_timeout = float(os.getenv("MCP_CALL_TIMEOUT", "15.0"))

    def get_binary_path(self) -> Optional[str]:
        candidates = [
            Path(__file__).resolve().parent.parent / "bin" / "mcp-grafana",
            Path("/usr/local/bin/mcp-grafana"),
            Path("/tmp/mcp-grafana"),
            Path("/opt/homebrew/bin/mcp-grafana"),
        ]
        for c in candidates:
            if c.exists() and os.access(c, os.X_OK):
                return str(c)
        return shutil.which("mcp-grafana")

    def get_allowed_tools(self) -> List[str]:
        return list(ALLOWED_GRAFANA_TOOLS)

    def _create_toolset(self, tool_filter: Optional[List[str]] = None) -> McpToolset:
        bin_path = self.get_binary_path() or "mcp-grafana"
        env = {
            **os.environ,
            "GRAFANA_URL": GRAFANA_INSTANCE_URL,
            "GRAFANA_SERVICE_ACCOUNT_TOKEN": GRAFANA_TOKEN,
        }
        params = StdioServerParameters(
            command=bin_path,
            args=["-t", "stdio"],
            env=env,
        )
        return McpToolset(
            connection_params=StdioConnectionParams(
                server_params=params,
                timeout=self.init_timeout,
            ),
            tool_filter=tool_filter,
        )

    def get_toolset(self, restricted: bool = True) -> McpToolset:
        """Returns the Google ADK McpToolset instance. Restricted exposes only CONTINUITY required tools."""
        if restricted:
            if self._toolset is None:
                self._toolset = self._create_toolset(tool_filter=ALLOWED_GRAFANA_TOOLS)
            return self._toolset
        else:
            if self._full_toolset is None:
                self._full_toolset = self._create_toolset(tool_filter=None)
            return self._full_toolset

    def get_allowed_tools(self) -> List[str]:
        """Returns the bounded list of Grafana MCP tools exposed to the agent."""
        return list(ALLOWED_GRAFANA_TOOLS)

    async def close(self):
        """Explicitly resets session state and closes ADK McpToolset sessions on shutdown."""
        self._session = None
        self._cached_declarations = None
        if self._toolset is not None:
            try:
                await self._toolset.close()
            except Exception as e:
                logger.warning(f"[Official MCP] Error closing restricted McpToolset: {e}")
            self._toolset = None
        if self._full_toolset is not None:
            try:
                await self._full_toolset.close()
            except Exception as e:
                logger.warning(f"[Official MCP] Error closing full McpToolset: {e}")
            self._full_toolset = None

    async def list_official_tools(self, restricted: bool = False) -> List[Dict[str, Any]]:
        """Discovers tools exposed by the official mcp-grafana binary via ADK McpToolset or active mock session."""
        if self._session is not None:
            try:
                tools_resp = await asyncio.wait_for(
                    self._session.list_tools(),
                    timeout=self.call_timeout,
                )
                self.cached_tools = [
                    {"name": t.name, "description": t.description or ""}
                    for t in tools_resp.tools
                ]
                return self.cached_tools
            except Exception as e:
                logger.warning(f"[Official MCP] Session list_tools failed: {e}")
                self._session = None

        if self.cached_tools and not restricted:
            return self.cached_tools

        bin_path = self.get_binary_path()
        if not bin_path:
            logger.warning("[Official MCP] mcp-grafana binary not located.")
            return []

        try:
            toolset = self.get_toolset(restricted=restricted)
            tools = await asyncio.wait_for(
                toolset.get_tools(),
                timeout=self.init_timeout,
            )
            discovered = [
                {"name": t.name, "description": t.description or ""}
                for t in tools
            ]
            if not restricted:
                self.cached_tools = discovered
            logger.info(f"[Official MCP] Discovered {len(discovered)} tools via ADK McpToolset from {bin_path}")
            return discovered
        except Exception as e:
            logger.warning(f"[Official MCP] Tool enumeration via ADK McpToolset failed: {e}")
            return self.cached_tools

    async def call_official_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """Calls a tool on official mcp-grafana via ADK McpToolset or active mock session with timeout and error handling."""
        if self._session is not None:
            try:
                res = await asyncio.wait_for(
                    self._session.call_tool(tool_name, arguments),
                    timeout=self.call_timeout,
                )
                return parse_mcp_tool_result(res)
            except (asyncio.TimeoutError, TimeoutError) as te:
                logger.warning(f"[Official MCP] Tool {tool_name} timed out: {te}")
                self._session = None
                return None
            except Exception as e:
                logger.warning(f"[Official MCP] Tool {tool_name} failed: {e}")
                self._session = None
                return None

        bin_path = self.get_binary_path()
        if not bin_path:
            return None

        try:
            toolset = self.get_toolset(restricted=True)
            raw_res = await asyncio.wait_for(
                toolset._execute_with_session(
                    lambda session: session.call_tool(tool_name, arguments),
                    f"Failed to execute tool {tool_name}"
                ),
                timeout=self.call_timeout,
            )
            return parse_mcp_tool_result(raw_res)
        except (asyncio.TimeoutError, TimeoutError) as te:
            logger.warning(f"[Official MCP] Tool {tool_name} timed out after {self.call_timeout}s: {te}")
            return None
        except Exception as e:
            logger.warning(f"[Official MCP] Tool {tool_name} ADK McpToolset execution failed: {e}. Falling back to direct client.")
            return None

    async def get_gemini_declarations(self) -> List[types.FunctionDeclaration]:
        """Discovers official Grafana MCP tool schemas via Google ADK McpToolset and converts to Gemini FunctionDeclarations."""
        if self._cached_declarations is not None:
            return self._cached_declarations
        try:
            toolset = self.get_toolset(restricted=True)
            tools = await asyncio.wait_for(toolset.get_tools(), timeout=self.init_timeout)
            decls = []
            for t in tools:
                if hasattr(t, "_get_declaration"):
                    decls.append(t._get_declaration())
            if decls:
                self._cached_declarations = decls
            return decls
        except Exception as e:
            logger.warning(f"[Official MCP] Failed to retrieve ADK tool declarations: {e}")
            return []

official_mcp_bridge = OfficialGrafanaMCPBridge()


# Tool Functions implementing runtime Grafana Cloud MCP capabilities
async def grafana_query_prometheus(promql: str) -> PrometheusQueryResult:
    """Queries real-time OpenMetrics and Prometheus telemetry via official Grafana Cloud MCP Server or direct REST."""
    logger.info(f"[MCP Tool] Executing PromQL: {promql}")
    try:
        res = await official_mcp_bridge.call_official_tool("query_prometheus", {
            "datasourceUid": GRAFANA_PROM_UID,
            "expr": promql,
            "endTime": "now",
            "queryType": "instant"
        })
        if res is not None and isinstance(res, dict) and ("data" in res or "status" in res):
            return normalize_prometheus_result(res, query=promql, source="official_mcp")
    except Exception as e:
        logger.warning(f"[MCP Tool] Official MCP query_prometheus failed: {e}. Executing direct REST fallback...")
    direct_res = await grafana_client.query_prometheus(promql)
    return normalize_prometheus_result(direct_res, query=promql, source="direct_rest")

async def grafana_query_loki(logql: str, limit: int = 20) -> LokiQueryResult:
    """Queries distributed edge router and transcode logs via official Grafana Cloud MCP Server or direct REST."""
    logger.info(f"[MCP Tool] Executing LogQL: {logql} (limit={limit})")
    try:
        res = await official_mcp_bridge.call_official_tool("query_loki_logs", {
            "datasourceUid": GRAFANA_LOKI_UID,
            "logql": logql,
            "limit": limit
        })
        if res is not None and isinstance(res, (dict, list)):
            return normalize_loki_result(res, query=logql, source="official_mcp")
    except Exception as e:
        logger.warning(f"[MCP Tool] Official MCP query_loki_logs failed: {e}. Executing direct REST fallback...")
    direct_res = await grafana_client.query_loki_logs(logql, limit=limit)
    return normalize_loki_result(direct_res, query=logql, source="direct_rest")

async def grafana_create_annotation(text: str, tags: Optional[List[str]] = None) -> GrafanaAnnotationRef:
    """Drops a visible timestamped vertical annotation pin on live Grafana dashboard via official MCP Server."""
    logger.info(f"[MCP Tool] Creating dashboard annotation: {text}")
    try:
        res = await official_mcp_bridge.call_official_tool("create_annotation", {
            "text": text,
            "tags": tags or []
        })
        if res is not None and isinstance(res, dict):
            if "Payload" in res and isinstance(res["Payload"], dict) and "id" in res["Payload"]:
                return normalize_annotation_result({"id": res["Payload"]["id"], "text": text, "tags": tags or []}, source="official_mcp")
            if "id" in res:
                return normalize_annotation_result(res, source="official_mcp")
    except Exception as e:
        logger.warning(f"[MCP Tool] Official MCP create_annotation failed: {e}. Executing direct REST fallback...")
    direct_res = await grafana_client.create_annotation(text, tags)
    return normalize_annotation_result(direct_res, source="direct_rest")

async def grafana_create_incident(title: str, severity: str, summary: str) -> GrafanaIncidentRef:
    """Opens a structured P1/P2 incident record in Grafana Cloud IRM via official MCP Server."""
    logger.info(f"[MCP Tool] Opening Grafana IRM incident: {title} [{severity}]")
    try:
        res = await official_mcp_bridge.call_official_tool("create_incident", {
            "title": title,
            "severity": severity,
            "roomPrefix": "stream-incident"
        })
        if res is not None and isinstance(res, dict) and ("incident_id" in res or "id" in res or "incident" in res):
            return normalize_incident_result(res, default_title=title, default_severity=severity, source="official_mcp")
    except Exception as e:
        logger.warning(f"[MCP Tool] Official MCP create_incident failed: {e}. Executing direct REST fallback...")
    direct_res = await grafana_client.create_incident(title, severity, summary)
    return normalize_incident_result(direct_res, default_title=title, default_severity=severity, source="direct_rest")

async def grafana_resolve_incident(incident_id: str, summary: str = "Verified closed-loop recovery.") -> GrafanaIncidentRef:
    """Resolves an existing incident in Grafana Cloud IRM via official MCP Server or direct API."""
    logger.info(f"[MCP Tool] Resolving Grafana IRM incident: {incident_id}")
    try:
        res = await official_mcp_bridge.call_official_tool("update_incident", {
            "incidentId": incident_id,
            "status": "resolved"
        })
        if res is not None and isinstance(res, dict) and res.get("status") != "error":
            if "incident_id" not in res and "id" not in res:
                res["incident_id"] = incident_id
            if "lifecycle_status" not in res and res.get("status") != "resolved":
                res["lifecycle_status"] = "resolved"
            return normalize_incident_result(res, source="official_mcp")
    except Exception as e:
        logger.warning(f"[MCP Tool] Official MCP update_incident failed: {e}. Executing direct REST fallback...")
    direct_res = await grafana_client.resolve_incident(incident_id, summary)
    return normalize_incident_result(direct_res, source="direct_rest")

async def grafana_search_dashboards(query: str = "") -> Dict[str, Any]:
    """Searches active dashboards on the connected Grafana Cloud instance via official MCP Server."""
    logger.info(f"[MCP Tool] Searching dashboards: query='{query}'")
    res = await official_mcp_bridge.call_official_tool("search_dashboards", {"query": query})
    if res is not None:
        return res if isinstance(res, dict) else {"dashboards": res}
    return await grafana_client.search_dashboards(query)


async def continuity_execute_remediation(
    action: str,
    primary_cdn_pct: int = 20,
    secondary_cdn_pct: int = 80,
    reason: str = "",
    incident_id: Optional[str] = None
) -> Dict[str, Any]:
    """Executes autonomous multi-CDN egress traffic failover, DRM cluster switch, or BGP transit rerouting as an idempotent transaction."""
    logger.info(f"[MCP Tool] Executing autonomous remediation: {action} (Primary={primary_cdn_pct}%, Secondary={secondary_cdn_pct}%)")
    inc_id = incident_id or chaos_manager.get_state().active_incident_id or f"INC-{int(time.time())}"
    tx, was_newly_applied = transaction_manager.execute_transaction(
        incident_id=inc_id,
        action=action,
        primary_cdn_pct=primary_cdn_pct,
        secondary_cdn_pct=secondary_cdn_pct
    )
    updated_state = chaos_manager.get_state()
    return {
        "status": tx.status,
        "transaction_id": tx.transaction_id,
        "idempotency_key": tx.idempotency_key,
        "rollback_action": tx.rollback_action,
        "action": action,
        "primary_cdn": updated_state.primary_cdn,
        "primary_cdn_traffic_pct": updated_state.primary_cdn_traffic_pct,
        "secondary_cdn": updated_state.secondary_cdn,
        "secondary_cdn_traffic_pct": updated_state.secondary_cdn_traffic_pct,
        "active_drm_cluster": updated_state.active_drm_cluster,
        "active_transit_route": updated_state.active_transit_route,
        "reason": reason,
        "was_newly_applied": was_newly_applied,
        "previous_state": tx.previous_state,
        "timestamp": tx.applied_at
    }

async def _evaluate_single_recovery_sample() -> Dict[str, Any]:
    """Evaluates a single recovery sample against Grafana Prometheus and local telemetry."""
    from config import VERIFICATION_POLICY
    prom_readback = await grafana_query_prometheus("ott_video_playback_failures_ratio")
    snapshot = telemetry_engine.get_current_snapshot()

    # Parse Prometheus instant vector readback metric value if available
    prom_vpf_value = None
    prom_source = "none"
    if isinstance(prom_readback, PrometheusQueryResult):
        if prom_readback.status == "success" and prom_readback.metric_value is not None:
            prom_vpf_value = prom_readback.metric_value
            prom_source = "grafana_cloud_prometheus"
    elif isinstance(prom_readback, dict):
        data_field = prom_readback.get("data")
        result_list = []
        if isinstance(data_field, dict):
            result_list = data_field.get("result", [])
        elif isinstance(data_field, list):
            result_list = data_field
        if result_list and isinstance(result_list, list) and len(result_list) > 0:
            first_item = result_list[0]
            if isinstance(first_item, dict):
                first_val = first_item.get("value")
                if first_val and isinstance(first_val, (list, tuple)) and len(first_val) >= 2:
                    try:
                        raw_val = float(first_val[1])
                        # Normalize ratio (e.g. 0.0019 -> 0.19%) to match percentage SLA
                        prom_vpf_value = round(raw_val * 100.0, 2) if raw_val <= 1.0 else round(raw_val, 2)
                        prom_source = "grafana_cloud_prometheus"
                    except (ValueError, TypeError):
                        pass

    # Policy enforcement:
    # If remote value was not obtained, allow local fallback ONLY under 'remote_preferred' or 'local_allowed'
    if prom_vpf_value is None and VERIFICATION_POLICY in ("remote_preferred", "local_allowed"):
        try:
            from services.telemetry import PREMIERE_REGISTRY
            for metric in PREMIERE_REGISTRY.collect():
                if metric.name == "ott_video_playback_failures_ratio":
                    for sample in metric.samples:
                        if sample.name == "ott_video_playback_failures_ratio":
                            prom_vpf_value = round(float(sample.value) * 100.0, 2)
                            prom_source = "prometheus_collector_registry"
                            break
        except Exception as e:
            logger.warning(f"Authoritative Prometheus CollectorRegistry sample read failed: {e}")

    # Semantics per Issue 6:
    if prom_source == "grafana_cloud_prometheus":
        is_remote_authoritative = True
        is_value_available = (prom_vpf_value is not None)
        is_source_trusted = True
    elif prom_source == "prometheus_collector_registry":
        is_remote_authoritative = False
        is_value_available = (prom_vpf_value is not None)
        is_source_trusted = True
    else:
        prom_source = "none"
        prom_vpf_value = None
        is_remote_authoritative = False
        is_value_available = False
        is_source_trusted = False

    # Fail closed: if an authoritative/trusted Prometheus value is not available, verification fails
    prom_healthy = (prom_vpf_value <= 0.5) if (prom_vpf_value is not None and is_source_trusted) else False
    telemetry_healthy = (
        snapshot.video_playback_failures_pct <= 0.5 and
        snapshot.cdn_egress_latency_ms <= 150.0 and
        snapshot.buffer_health_sec >= 20.0
    )
    chaos_state = chaos_manager.get_state()
    from services.chaos import IncidentLifecycle
    if chaos_state.force_recovery_failure:
        is_recovered = False
    elif chaos_state.is_outage_active and (chaos_state.lifecycle == IncidentLifecycle.INCIDENT_ACTIVE or chaos_state.remediation_applied_at is None):
        is_recovered = False
    else:
        is_recovered = prom_healthy and telemetry_healthy

    return {
        "status": "PASSED" if is_recovered else "PENDING",
        "verified": is_recovered,
        "prometheus_query": "ott_video_playback_failures_ratio",
        "prometheus_readback_status": getattr(prom_readback, "status", None) or (prom_readback.get("status", "success") if isinstance(prom_readback, dict) else "ok"),
        "prometheus_metric_value": prom_vpf_value,
        "prometheus_source": prom_source,
        "prometheus_value_available": is_value_available,
        "prometheus_authoritative": is_remote_authoritative,
        "verification_source_trusted": is_source_trusted,
        "verification_policy": VERIFICATION_POLICY,
        "prometheus_raw_readback": prom_readback.model_dump() if hasattr(prom_readback, "model_dump") else prom_readback,
        "current_vpf_pct": snapshot.video_playback_failures_pct,
        "vpf_sla_target": 0.5,
        "forward_buffer_sec": snapshot.buffer_health_sec,
        "buffer_target_sec": 20.0,
        "cdn_latency_ms": snapshot.cdn_egress_latency_ms,
        "timestamp": time.time()
    }

async def continuity_verify_closed_loop_recovery(
    timeout_sec: Optional[float] = None,
    poll_interval_sec: Optional[float] = None,
    transaction_id: Optional[str] = None
) -> Dict[str, Any]:
    """Executes a closed-loop falsifiable recovery verification query against Prometheus and client telemetry with convergence polling."""
    eff_timeout = timeout_sec if timeout_sec is not None else float(os.getenv("CONTINUITY_VERIFY_TIMEOUT_SEC", "5.0"))
    eff_poll = poll_interval_sec if poll_interval_sec is not None else float(os.getenv("CONTINUITY_VERIFY_POLL_INTERVAL_SEC", "0.25"))
    logger.info(f"[MCP Tool] Verifying closed-loop recovery (timeout={eff_timeout}s, poll={eff_poll}s)...")
    loop = asyncio.get_event_loop()
    deadline = loop.time() + eff_timeout
    last_evidence: Dict[str, Any] = {}

    pre_snapshot = transaction_manager.build_health_snapshot()

    while True:
        evidence = await _evaluate_single_recovery_sample()
        last_evidence = evidence
        
        if evidence.get("verified", False) and evidence.get("status") == "PASSED":
            active_tx = transaction_manager.get_transaction(transaction_id) if transaction_id else transaction_manager.get_active_transaction()
            if active_tx:
                proof = transaction_manager.verify_and_commit(
                    transaction_id=active_tx.transaction_id,
                    pre_action_snapshot=pre_snapshot,
                    verification_source=evidence.get("prometheus_source", "Grafana Cloud Prometheus"),
                    authoritative=evidence.get("prometheus_authoritative", True)
                )
                evidence["recovery_proof"] = proof.model_dump()
                evidence["transaction_status"] = "COMMITTED"
                evidence["remediation_transaction_id"] = active_tx.transaction_id
            return evidence
            
        if loop.time() + eff_poll > deadline:
            break
            
        await asyncio.sleep(eff_poll)

    active_tx = transaction_manager.get_transaction(transaction_id) if transaction_id else transaction_manager.get_active_transaction()
    if active_tx:
        proof = transaction_manager.verify_and_commit(
            transaction_id=active_tx.transaction_id,
            pre_action_snapshot=pre_snapshot,
            verification_source=last_evidence.get("prometheus_source", "none"),
            authoritative=last_evidence.get("prometheus_authoritative", False)
        )
        last_evidence["recovery_proof"] = proof.model_dump()
        last_evidence["transaction_status"] = "ROLLED_BACK"
        last_evidence["remediation_transaction_id"] = active_tx.transaction_id
        last_evidence["status"] = "PENDING"
        last_evidence["verified"] = False
        last_evidence["rollback_executed"] = True

    return last_evidence

async def continuity_rollback_remediation(transaction_id: str) -> Dict[str, Any]:
    """Rolls back a remediation transaction to its previous safe state snapshot."""
    tx = transaction_manager.rollback_transaction(transaction_id)
    return {
        "status": tx.status,
        "transaction_id": tx.transaction_id,
        "rollback_action": tx.rollback_action,
        "restored_state": tx.previous_state
    }

async def continuity_escalate_incident(incident_id: str, reason: str = "Unrecoverable incident") -> Dict[str, Any]:
    """Escalates an unrecoverable incident to human operator with full diagnostic dossier."""
    pkg = transaction_manager.create_escalation_package(
        incident_id=incident_id,
        diagnosis=reason,
        failed_gates=["Manual or policy-based escalation trigger"]
    )
    return pkg.model_dump()

# Continuous CONTINUITY-owned tools (never delegated to Grafana MCP)
CONTINUITY_FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="continuity_execute_remediation",
        description="Execute an autonomous edge traffic failover or BGP transit rerouting across Multi-CDN providers.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "action": types.Schema(type="STRING", description="The remediation policy: SHIFT_TRAFFIC_TO_AKAMAI, FAILOVER_DRM_KEY_CLUSTER, or REROUTE_BGP_TRANSIT."),
                "primary_cdn_pct": types.Schema(type="INTEGER", description="Egress percentage for primary CDN (e.g. 20)."),
                "secondary_cdn_pct": types.Schema(type="INTEGER", description="Egress percentage for secondary CDN (e.g. 80)."),
                "reason": types.Schema(type="STRING", description="Technical justification for the traffic shift.")
            },
            required=["action", "primary_cdn_pct", "secondary_cdn_pct", "reason"]
        )
    ),
    types.FunctionDeclaration(
        name="continuity_verify_closed_loop_recovery",
        description="Re-query Prometheus to verify that VPF dropped below 0.5% and forward buffer restabilized, providing falsifiable proof of resolution.",
        parameters=types.Schema(
            type="OBJECT",
            properties={}
        )
    ),
    types.FunctionDeclaration(
        name="continuity_rollback_remediation",
        description="Roll back a previous remediation transaction if health gates fail, restoring pre-action infrastructure snapshot.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "transaction_id": types.Schema(type="STRING", description="The ID of the transaction to roll back.")
            },
            required=["transaction_id"]
        )
    ),
    types.FunctionDeclaration(
        name="continuity_escalate_incident",
        description="Escalate an unrecoverable incident to human SRE with an automated diagnostic package.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "incident_id": types.Schema(type="STRING", description="The active incident ID to escalate."),
                "reason": types.Schema(type="STRING", description="Detailed technical reason for human escalation.")
            },
            required=["incident_id", "reason"]
        )
    )
]

STATIC_OFFICIAL_GRAFANA_DECLARATIONS = [
    types.FunctionDeclaration(
        name="query_prometheus",
        description="Query real-time Prometheus / Mimir QoS metrics such as VPF error rate, egress latency, and buffer health from Grafana Cloud.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "expr": types.Schema(type="STRING", description="The PromQL query string to execute against Grafana Cloud Prometheus.")
            },
            required=["expr"]
        )
    ),
    types.FunctionDeclaration(
        name="query_loki_logs",
        description="Query structured error logs from Grafana Cloud Loki to isolate HTTP 502 bad gateways, BGP peering drops, and DRM auth timeouts.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "logql": types.Schema(type="STRING", description="The LogQL query string to execute against Grafana Cloud Loki."),
                "limit": types.Schema(type="INTEGER", description="Maximum number of log entries to retrieve (default 20).")
            },
            required=["logql"]
        )
    ),
    types.FunctionDeclaration(
        name="create_annotation",
        description="Place a visible vertical annotation pin on the live Grafana Cloud dashboard documenting the autonomous incident diagnosis and fix.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "text": types.Schema(type="STRING", description="The descriptive annotation text."),
                "tags": types.Schema(type="ARRAY", items=types.Schema(type="STRING"), description="List of metadata tags for the annotation.")
            },
            required=["text"]
        )
    ),
    types.FunctionDeclaration(
        name="create_incident",
        description="Programmatically create a structured P1/P2 incident record in Grafana Cloud IRM.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "title": types.Schema(type="STRING", description="Incident title."),
                "severity": types.Schema(type="STRING", description="Severity level: CRITICAL, MAJOR, or MINOR."),
                "summary": types.Schema(type="STRING", description="Executive summary of the incident and impacted audience.")
            },
            required=["title", "severity", "summary"]
        )
    ),
    types.FunctionDeclaration(
        name="update_incident",
        description="Update an existing Grafana incident in Grafana Cloud IRM (e.g. resolve upon verified recovery).",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "incidentId": types.Schema(type="STRING", description="Incident ID to update."),
                "status": types.Schema(type="STRING", description="Status string: active or resolved.")
            },
            required=["incidentId", "status"]
        )
    ),
]

LEGACY_GRAFANA_DECLARATION_ALIASES = [
    types.FunctionDeclaration(
        name="grafana_query_prometheus",
        description="Query real-time Prometheus / Mimir QoS metrics such as VPF error rate, egress latency, and buffer health from Grafana Cloud.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "promql": types.Schema(type="STRING", description="The PromQL query string to execute against Grafana Cloud Prometheus.")
            },
            required=["promql"]
        )
    ),
    types.FunctionDeclaration(
        name="grafana_query_loki",
        description="Query structured error logs from Grafana Cloud Loki to isolate HTTP 502 bad gateways, BGP peering drops, and DRM auth timeouts.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "logql": types.Schema(type="STRING", description="The LogQL query string to execute against Grafana Cloud Loki."),
                "limit": types.Schema(type="INTEGER", description="Maximum number of log entries to retrieve (default 20).")
            },
            required=["logql"]
        )
    ),
    types.FunctionDeclaration(
        name="grafana_create_annotation",
        description="Place a visible vertical annotation pin on the live Grafana Cloud dashboard documenting the autonomous incident diagnosis and fix.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "text": types.Schema(type="STRING", description="The descriptive annotation text."),
                "tags": types.Schema(type="ARRAY", items=types.Schema(type="STRING"), description="List of metadata tags for the annotation.")
            },
            required=["text"]
        )
    ),
    types.FunctionDeclaration(
        name="grafana_create_incident",
        description="Programmatically create a structured P1/P2 incident record in Grafana Cloud IRM.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "title": types.Schema(type="STRING", description="Incident title."),
                "severity": types.Schema(type="STRING", description="Severity level: CRITICAL, MAJOR, or MINOR."),
                "summary": types.Schema(type="STRING", description="Executive summary of the incident and impacted audience.")
            },
            required=["title", "severity", "summary"]
        )
    ),
]

# Static fallback schemas guaranteeing deterministic validation offline
GEMINI_MCP_TOOLS = [
    types.Tool(
        function_declarations=[
            *STATIC_OFFICIAL_GRAFANA_DECLARATIONS,
            *LEGACY_GRAFANA_DECLARATION_ALIASES,
            *CONTINUITY_FUNCTION_DECLARATIONS,
        ]
    )
]

async def get_gemini_tools() -> List[types.Tool]:
    """Returns dynamic Gemini tool definitions leveraging ADK McpToolset discovered schemas with CONTINUITY fallbacks."""
    adk_decls = await official_mcp_bridge.get_gemini_declarations()
    if adk_decls:
        return [
            types.Tool(
                function_declarations=[
                    *adk_decls,
                    *LEGACY_GRAFANA_DECLARATION_ALIASES,
                    *CONTINUITY_FUNCTION_DECLARATIONS,
                ]
            )
        ]
    return GEMINI_MCP_TOOLS

# Dispatcher for executing tool calls made by Gemini or client runners
async def dispatch_mcp_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatches and executes an MCP tool call by name, supporting both official ADK names and legacy aliases."""
    logger.info(f"[MCP Dispatcher] Calling {name} with args {args}")
    try:
        if name in ("query_prometheus", "grafana_query_prometheus"):
            promql = args.get("expr") or args.get("promql", "")
            res = await grafana_query_prometheus(promql)
        elif name in ("query_loki_logs", "grafana_query_loki"):
            logql = args.get("logql") or args.get("query", "")
            limit = int(args.get("limit", 20))
            res = await grafana_query_loki(logql, limit=limit)
        elif name in ("create_annotation", "grafana_create_annotation"):
            text = args.get("text", "")
            tags = args.get("tags")
            res = await grafana_create_annotation(text, tags)
        elif name in ("create_incident", "grafana_create_incident"):
            title = args.get("title", "")
            severity = args.get("severity", "CRITICAL")
            summary = args.get("summary") or args.get("description", "")
            res = await grafana_create_incident(title, severity, summary)
        elif name in ("update_incident", "grafana_resolve_incident"):
            incident_id = args.get("incidentId") or args.get("incident_id", "")
            summary = args.get("summary", "Verified closed-loop recovery.")
            res = await grafana_resolve_incident(incident_id, summary)
        elif name == "grafana_search_dashboards":
            res = await grafana_search_dashboards(args.get("query", ""))
        elif name == "continuity_execute_remediation":
            res = await continuity_execute_remediation(
                action=args.get("action", "SHIFT_TRAFFIC_TO_AKAMAI"),
                primary_cdn_pct=int(args.get("primary_cdn_pct", 20)),
                secondary_cdn_pct=int(args.get("secondary_cdn_pct", 80)),
                reason=args.get("reason", "Autonomous failover")
            )
        elif name == "continuity_verify_closed_loop_recovery":
            res = await continuity_verify_closed_loop_recovery()
        elif name == "continuity_rollback_remediation":
            res = await continuity_rollback_remediation(args.get("transaction_id", ""))
        elif name == "continuity_escalate_incident":
            res = await continuity_escalate_incident(
                incident_id=args.get("incident_id", ""),
                reason=args.get("reason", "Autonomous escalation triggered")
            )
        else:
            raise ValueError(f"Unknown MCP tool: {name}")

        try:
            PROM_AGENT_MCP_TOOL_CALLS.labels(tool_name=name, status="success").inc()
        except Exception:
            pass
        return res
    except Exception as e:
        try:
            PROM_AGENT_MCP_TOOL_CALLS.labels(tool_name=name, status="error").inc()
        except Exception:
            pass
        raise


