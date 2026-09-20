import os
import time
import json
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp.server.mcpserver import MCPServer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google.genai import types

from config import GRAFANA_INSTANCE_URL, GRAFANA_TOKEN
from services.grafana_client import grafana_client
from services.chaos import chaos_manager
from services.telemetry import telemetry_engine

logger = logging.getLogger("continuity.mcp")

# Initialize official MCP Server instance for Continuity - Grafana Integration
mcp_server = MCPServer(name="continuity-grafana-mcp")

class OfficialGrafanaMCPBridge:
    """Manages live stdio JSON-RPC sessions to the official grafana/mcp-grafana runtime server."""
    def __init__(self):
        self.cached_tools: List[Dict[str, Any]] = []

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

    async def list_official_tools(self) -> List[Dict[str, Any]]:
        bin_path = self.get_binary_path()
        if not bin_path:
            logger.warning("[Official MCP] mcp-grafana binary not located.")
            return []
        try:
            params = StdioServerParameters(
                command=bin_path,
                args=[],
                env={
                    "GRAFANA_URL": GRAFANA_INSTANCE_URL,
                    "GRAFANA_SERVICE_ACCOUNT_TOKEN": GRAFANA_TOKEN
                }
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_resp = await session.list_tools()
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
        bin_path = self.get_binary_path()
        if not bin_path:
            return None
        try:
            params = StdioServerParameters(
                command=bin_path,
                args=[],
                env={
                    "GRAFANA_URL": GRAFANA_INSTANCE_URL,
                    "GRAFANA_SERVICE_ACCOUNT_TOKEN": GRAFANA_TOKEN
                }
            )
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    res = await session.call_tool(tool_name, arguments)
                    if res.content and len(res.content) > 0:
                        text_val = res.content[0].text
                        try:
                            return json.loads(text_val)
                        except Exception:
                            return text_val
                    return res
        except Exception as e:
            logger.warning(f"[Official MCP] Tool {tool_name} stdio execution failed: {e}. Falling back to direct client.")
            return None

official_mcp_bridge = OfficialGrafanaMCPBridge()

# Tool Functions implementing runtime Grafana Cloud MCP capabilities
async def grafana_query_prometheus(promql: str) -> Dict[str, Any]:
    """Queries real-time OpenMetrics and Prometheus telemetry via official Grafana Cloud MCP Server."""
    logger.info(f"[MCP Tool] Executing PromQL: {promql}")
    res = await official_mcp_bridge.call_official_tool("query_prometheus", {
        "datasourceUid": "grafanacloud-prom",
        "expr": promql,
        "endTime": "now",
        "queryType": "instant"
    })
    if res is not None and isinstance(res, dict) and ("data" in res or "status" in res):
        return res
    return await grafana_client.query_prometheus(promql)

async def grafana_query_loki(logql: str, limit: int = 20) -> Dict[str, Any]:
    """Queries distributed edge router and transcode logs via official Grafana Cloud MCP Server."""
    logger.info(f"[MCP Tool] Executing LogQL: {logql} (limit={limit})")
    res = await official_mcp_bridge.call_official_tool("query_loki_logs", {
        "datasourceUid": "grafanacloud-logs",
        "logql": logql,
        "limit": limit
    })
    if res is not None and isinstance(res, dict) and ("data" in res or "lines" in res):
        return res
    return await grafana_client.query_loki_logs(logql, limit=limit)

async def grafana_create_annotation(text: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Drops a visible timestamped vertical annotation pin on live Grafana dashboard via official MCP Server."""
    logger.info(f"[MCP Tool] Creating dashboard annotation: {text}")
    res = await official_mcp_bridge.call_official_tool("create_annotation", {
        "text": text,
        "tags": tags or []
    })
    if res is not None and isinstance(res, dict):
        if "Payload" in res and isinstance(res["Payload"], dict) and "id" in res["Payload"]:
            return {"id": res["Payload"]["id"], "message": res["Payload"].get("message", "Annotation added")}
        if "id" in res:
            return res
    return await grafana_client.create_annotation(text, tags)

async def grafana_create_incident(title: str, severity: str, summary: str) -> Dict[str, Any]:
    """Opens a structured P1/P2 incident record in Grafana Cloud IRM via official MCP Server."""
    logger.info(f"[MCP Tool] Opening Grafana IRM incident: {title} [{severity}]")
    res = await official_mcp_bridge.call_official_tool("create_incident", {
        "title": title,
        "severity": severity,
        "roomPrefix": "stream-incident"
    })
    if res is not None and isinstance(res, dict) and ("incident_id" in res or "id" in res):
        return res
    return await grafana_client.create_incident(title, severity, summary)

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
    if isinstance(prom_readback, dict):
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
        "prometheus_readback_status": prom_readback.get("status", "success") if isinstance(prom_readback, dict) else "ok",
        "prometheus_metric_value": prom_vpf_value,
        "prometheus_source": prom_source,
        "prometheus_value_available": is_value_available,
        "prometheus_authoritative": is_remote_authoritative,
        "verification_source_trusted": is_source_trusted,
        "verification_policy": VERIFICATION_POLICY,
        "prometheus_raw_readback": prom_readback,
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
        # Advance telemetry tick to reflect active convergence
        telemetry_engine._tick()
        
        evidence = await _evaluate_single_recovery_sample()
        last_evidence = evidence
        
        if evidence.get("verified", False) and evidence.get("status") == "PASSED":
            return evidence
            
        if loop.time() + poll_interval_sec > deadline:
            break
            
        await asyncio.sleep(poll_interval_sec)

    return last_evidence

# Register tools with MCP Server
@mcp_server.tool()
async def query_prometheus(promql: str) -> str:
    """Executes a PromQL metric query against Grafana Cloud Prometheus."""
    res = await grafana_query_prometheus(promql)
    return json.dumps(res)

@mcp_server.tool()
async def query_loki(logql: str, limit: int = 20) -> str:
    """Executes a LogQL query against Grafana Cloud Loki."""
    res = await grafana_query_loki(logql, limit)
    return json.dumps(res)

@mcp_server.tool()
async def create_annotation(text: str, tags: list[str] = None) -> str:
    """Creates a timestamped annotation on the live Grafana Cloud dashboard."""
    res = await grafana_create_annotation(text, tags)
    return json.dumps(res)

@mcp_server.tool()
async def create_incident(title: str, severity: str, summary: str) -> str:
    """Opens a structured incident in Grafana Cloud IRM."""
    res = await grafana_create_incident(title, severity, summary)
    return json.dumps(res)

@mcp_server.tool()
async def search_dashboards(query: str = "") -> str:
    """Searches dashboards on Grafana Cloud."""
    res = await grafana_search_dashboards(query)
    return json.dumps(res)

@mcp_server.tool()
async def shift_traffic(action: str, primary_cdn_pct: int, secondary_cdn_pct: int, reason: str) -> str:
    """Executes multi-CDN traffic reallocation across edge POPs."""
    res = await continuity_execute_remediation(action, primary_cdn_pct, secondary_cdn_pct, reason)
    return json.dumps(res)

@mcp_server.tool()
async def verify_recovery() -> str:
    """Validates falsifiable closed-loop recovery against the 0.5% VPF SLA."""
    res = await continuity_verify_closed_loop_recovery()
    return json.dumps(res)

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
