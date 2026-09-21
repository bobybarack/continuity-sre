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

from config import (
    GRAFANA_INSTANCE_URL,
    GRAFANA_TOKEN,
    GRAFANA_PROM_UID,
    GRAFANA_LOKI_UID,
)
from services.grafana_client import grafana_client
from services.chaos import chaos_manager
from services.telemetry import telemetry_engine
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

def parse_mcp_tool_result(res: Any) -> Any:
    """Parses full MCP CallToolResult handling isError, multiple content items, structured content, and fallbacks."""
    if res is None:
        return None

    is_error = getattr(res, "isError", False)
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
    """Manages stdio JSON-RPC sessions to the official grafana/mcp-grafana runtime server with robust lifecycle."""
    def __init__(self):
        self.cached_tools: List[Dict[str, Any]] = []
        self._session: Optional[ClientSession] = None
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

    async def close(self):
        """Explicitly resets session state on shutdown."""
        self._session = None

    async def list_official_tools(self) -> List[Dict[str, Any]]:
        """Discovers tools exposed by the official mcp-grafana binary."""
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

        if self.cached_tools:
            return self.cached_tools

        bin_path = self.get_binary_path()
        if not bin_path:
            logger.warning("[Official MCP] mcp-grafana binary not located.")
            return []

        env = {
            **os.environ,
            "GRAFANA_URL": GRAFANA_INSTANCE_URL,
            "GRAFANA_SERVICE_ACCOUNT_TOKEN": GRAFANA_TOKEN,
        }
        params = StdioServerParameters(command=bin_path, args=[], env=env)
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), timeout=self.init_timeout)
                    tools_resp = await asyncio.wait_for(
                        session.list_tools(),
                        timeout=self.call_timeout,
                    )
                    self.cached_tools = [
                        {"name": t.name, "description": t.description or ""}
                        for t in tools_resp.tools
                    ]
                    logger.info(f"[Official MCP] Successfully discovered {len(self.cached_tools)} tools from {bin_path}")
                    return self.cached_tools
        except Exception as e:
            logger.warning(f"[Official MCP] Tool enumeration via stdio failed: {e}")
            return self.cached_tools

    async def call_official_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Any]:
        """Calls a tool on the official mcp-grafana binary over stdio with timeout and error handling."""
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

        env = {
            **os.environ,
            "GRAFANA_URL": GRAFANA_INSTANCE_URL,
            "GRAFANA_SERVICE_ACCOUNT_TOKEN": GRAFANA_TOKEN,
        }
        params = StdioServerParameters(command=bin_path, args=[], env=env)
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), timeout=self.init_timeout)
                    res = await asyncio.wait_for(
                        session.call_tool(tool_name, arguments),
                        timeout=self.call_timeout,
                    )
                    return parse_mcp_tool_result(res)
        except (asyncio.TimeoutError, TimeoutError) as te:
            logger.warning(f"[Official MCP] Tool {tool_name} timed out after {self.call_timeout}s: {te}")
            return None
        except Exception as e:
            logger.warning(f"[Official MCP] Tool {tool_name} stdio execution failed: {e}. Falling back to direct client.")
            return None

official_mcp_bridge = OfficialGrafanaMCPBridge()

# Tool Functions implementing runtime Grafana Cloud MCP capabilities
async def grafana_query_prometheus(promql: str) -> PrometheusQueryResult:
    """Queries real-time OpenMetrics and Prometheus telemetry via official Grafana Cloud MCP Server or direct REST."""
    logger.info(f"[MCP Tool] Executing PromQL: {promql}")
    res = await official_mcp_bridge.call_official_tool("query_prometheus", {
        "datasourceUid": GRAFANA_PROM_UID,
        "expr": promql,
        "endTime": "now",
        "queryType": "instant"
    })
    if res is not None and isinstance(res, dict) and ("data" in res or "status" in res):
        return normalize_prometheus_result(res, query=promql, source="official_mcp")
    direct_res = await grafana_client.query_prometheus(promql)
    return normalize_prometheus_result(direct_res, query=promql, source="direct_rest")

async def grafana_query_loki(logql: str, limit: int = 20) -> LokiQueryResult:
    """Queries distributed edge router and transcode logs via official Grafana Cloud MCP Server or direct REST."""
    logger.info(f"[MCP Tool] Executing LogQL: {logql} (limit={limit})")
    res = await official_mcp_bridge.call_official_tool("query_loki_logs", {
        "datasourceUid": GRAFANA_LOKI_UID,
        "logql": logql,
        "limit": limit
    })
    if res is not None and isinstance(res, (dict, list)):
        return normalize_loki_result(res, query=logql, source="official_mcp")
    direct_res = await grafana_client.query_loki_logs(logql, limit=limit)
    return normalize_loki_result(direct_res, query=logql, source="direct_rest")

async def grafana_create_annotation(text: str, tags: Optional[List[str]] = None) -> GrafanaAnnotationRef:
    """Drops a visible timestamped vertical annotation pin on live Grafana dashboard via official MCP Server."""
    logger.info(f"[MCP Tool] Creating dashboard annotation: {text}")
    res = await official_mcp_bridge.call_official_tool("create_annotation", {
        "text": text,
        "tags": tags or []
    })
    if res is not None and isinstance(res, dict):
        if "Payload" in res and isinstance(res["Payload"], dict) and "id" in res["Payload"]:
            return normalize_annotation_result({"id": res["Payload"]["id"], "text": text, "tags": tags or []}, source="official_mcp")
        if "id" in res:
            return normalize_annotation_result(res, source="official_mcp")
    direct_res = await grafana_client.create_annotation(text, tags)
    return normalize_annotation_result(direct_res, source="direct_rest")

async def grafana_create_incident(title: str, severity: str, summary: str) -> GrafanaIncidentRef:
    """Opens a structured P1/P2 incident record in Grafana Cloud IRM via official MCP Server."""
    logger.info(f"[MCP Tool] Opening Grafana IRM incident: {title} [{severity}]")
    res = await official_mcp_bridge.call_official_tool("create_incident", {
        "title": title,
        "severity": severity,
        "roomPrefix": "stream-incident"
    })
    if res is not None and isinstance(res, dict) and ("incident_id" in res or "id" in res or "incident" in res):
        return normalize_incident_result(res, default_title=title, default_severity=severity, source="official_mcp")
    direct_res = await grafana_client.create_incident(title, severity, summary)
    return normalize_incident_result(direct_res, default_title=title, default_severity=severity, source="direct_rest")

async def grafana_resolve_incident(incident_id: str, summary: str = "Verified closed-loop recovery.") -> GrafanaIncidentRef:
    """Resolves an existing incident in Grafana Cloud IRM via official MCP Server or direct API."""
    logger.info(f"[MCP Tool] Resolving Grafana IRM incident: {incident_id}")
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
    direct_res = await grafana_client.resolve_incident(incident_id, summary)
    return normalize_incident_result(direct_res, source="direct_rest")

async def grafana_search_dashboards(query: str = "") -> Dict[str, Any]:
    """Searches active dashboards on the connected Grafana Cloud instance via official MCP Server."""
    logger.info(f"[MCP Tool] Searching dashboards: query='{query}'")
    res = await official_mcp_bridge.call_official_tool("search_dashboards", {"query": query})
    if res is not None:
        return res if isinstance(res, dict) else {"dashboards": res}
    return await grafana_client.search_dashboards(query)


async def continuity_execute_remediation(action: str, primary_cdn_pct: int = 20, secondary_cdn_pct: int = 80, reason: str = "") -> Dict[str, Any]:
    """Executes autonomous multi-CDN egress traffic failover, DRM cluster switch, or BGP transit rerouting."""
    logger.info(f"[MCP Tool] Executing autonomous remediation: {action} (Primary={primary_cdn_pct}%, Secondary={secondary_cdn_pct}%)")
    updated_state = chaos_manager.apply_autonomous_remediation(
        action=action,
        primary_cdn_pct=primary_cdn_pct,
        secondary_cdn_pct=secondary_cdn_pct
    )
    return {
        "status": "APPLIED",
        "action": action,
        "primary_cdn": updated_state.primary_cdn,
        "primary_cdn_traffic_pct": updated_state.primary_cdn_traffic_pct,
        "secondary_cdn": updated_state.secondary_cdn,
        "secondary_cdn_traffic_pct": updated_state.secondary_cdn_traffic_pct,
        "active_drm_cluster": updated_state.active_drm_cluster,
        "active_transit_route": updated_state.active_transit_route,
        "reason": reason,
        "timestamp": time.time()
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
    timeout_sec: float = 5.0,
    poll_interval_sec: float = 0.25
) -> Dict[str, Any]:
    """Executes a closed-loop falsifiable recovery verification query against Prometheus and client telemetry with convergence polling."""
    logger.info(f"[MCP Tool] Verifying closed-loop recovery (timeout={timeout_sec}s, poll={poll_interval_sec}s)...")
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout_sec
    last_evidence: Dict[str, Any] = {}

    while True:
        evidence = await _evaluate_single_recovery_sample()
        last_evidence = evidence
        
        if evidence.get("verified", False) and evidence.get("status") == "PASSED":
            return evidence
            
        if loop.time() + poll_interval_sec > deadline:
            break
            
        await asyncio.sleep(poll_interval_sec)

    return last_evidence

# Gemini function declaration schemas for native Google GenAI Tool Calling
GEMINI_MCP_TOOLS = [
    types.Tool(
        function_declarations=[
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
            )
        ]
    )
]

# Dispatcher for executing tool calls made by Gemini or client runners
async def dispatch_mcp_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatches and executes an MCP tool call by name."""
    logger.info(f"[MCP Dispatcher] Calling {name} with args {args}")
    if name == "grafana_query_prometheus":
        return await grafana_query_prometheus(args.get("promql", ""))
    elif name == "grafana_query_loki":
        return await grafana_query_loki(args.get("logql", ""), int(args.get("limit", 20)))
    elif name == "grafana_create_annotation":
        return await grafana_create_annotation(args.get("text", ""), args.get("tags"))
    elif name == "grafana_create_incident":
        return await grafana_create_incident(args.get("title", ""), args.get("severity", "CRITICAL"), args.get("summary", ""))
    elif name == "grafana_search_dashboards":
        return await grafana_search_dashboards(args.get("query", ""))
    elif name == "continuity_execute_remediation":
        return await continuity_execute_remediation(
            action=args.get("action", "SHIFT_TRAFFIC_TO_AKAMAI"),
            primary_cdn_pct=int(args.get("primary_cdn_pct", 20)),
            secondary_cdn_pct=int(args.get("secondary_cdn_pct", 80)),
            reason=args.get("reason", "Autonomous failover")
        )
    elif name == "continuity_verify_closed_loop_recovery":
        return await continuity_verify_closed_loop_recovery()
    else:
        raise ValueError(f"Unknown MCP tool: {name}")
