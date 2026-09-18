import time
import json
import logging
from typing import Dict, Any, List, Optional
from mcp.server.mcpserver import MCPServer
from google.genai import types

from services.grafana_client import grafana_client
from services.chaos import chaos_manager
from services.telemetry import telemetry_engine

logger = logging.getLogger("continuity.mcp")

# Initialize official MCP Server instance for Continuity - Grafana Integration
mcp_server = MCPServer(name="continuity-grafana-mcp")

# Tool Functions implementing runtime Grafana Cloud MCP capabilities
async def grafana_query_prometheus(promql: str) -> Dict[str, Any]:
    """Queries real-time OpenMetrics and Prometheus telemetry from Grafana Cloud Mimir proxy."""
    logger.info(f"[MCP Tool] Executing PromQL: {promql}")
    res = await grafana_client.query_prometheus(promql)
    return res

async def grafana_query_loki(logql: str, limit: int = 20) -> Dict[str, Any]:
    """Queries distributed edge router and transcode logs from Grafana Cloud Loki proxy."""
    logger.info(f"[MCP Tool] Executing LogQL: {logql} (limit={limit})")
    res = await grafana_client.query_loki_logs(logql, limit=limit)
    return res

async def grafana_create_annotation(text: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Drops a visible timestamped vertical annotation pin on the live Grafana Cloud dashboard."""
    logger.info(f"[MCP Tool] Creating dashboard annotation: {text}")
    res = await grafana_client.create_annotation(text, tags)
    return res

async def grafana_create_incident(title: str, severity: str, summary: str) -> Dict[str, Any]:
    """Opens a structured P1/P2 incident record in Grafana Cloud IRM with live dashboard linkage."""
    logger.info(f"[MCP Tool] Opening Grafana IRM incident: {title} [{severity}]")
    res = await grafana_client.create_incident(title, severity, summary)
    return res

async def grafana_search_dashboards(query: str = "") -> Dict[str, Any]:
    """Searches active dashboards on the connected Grafana Cloud instance."""
    logger.info(f"[MCP Tool] Searching dashboards: query='{query}'")
    res = await grafana_client.search_dashboards(query)
    return res

async def continuity_execute_remediation(action: str, primary_cdn_pct: int, secondary_cdn_pct: int, reason: str) -> Dict[str, Any]:
    """Executes autonomous multi-CDN egress traffic failover and BGP route reallocation."""
    logger.info(f"[MCP Tool] Executing autonomous remediation: {action} (Primary={primary_cdn_pct}%, Secondary={secondary_cdn_pct}%)")
    updated_state = chaos_manager.apply_autonomous_remediation(action)
    return {
        "status": "APPLIED",
        "action": action,
        "primary_cdn": updated_state.primary_cdn,
        "primary_cdn_traffic_pct": updated_state.primary_cdn_traffic_pct,
        "secondary_cdn": updated_state.secondary_cdn,
        "secondary_cdn_traffic_pct": updated_state.secondary_cdn_traffic_pct,
        "reason": reason,
        "timestamp": time.time()
    }

async def continuity_verify_closed_loop_recovery() -> Dict[str, Any]:
    """Executes a closed-loop falsifiable recovery verification query against Prometheus and client telemetry."""
    logger.info("[MCP Tool] Verifying closed-loop stream restabilization...")
    snapshot = telemetry_engine.generate_current_snapshot()
    is_recovered = (
        snapshot.video_playback_failures_pct <= 0.5 and
        snapshot.cdn_egress_latency_ms <= 150.0 and
        snapshot.buffer_health_sec >= 20.0
    )
    return {
        "status": "PASSED" if is_recovered else "PENDING",
        "verified": is_recovered,
        "current_vpf_pct": snapshot.video_playback_failures_pct,
        "vpf_sla_target": 0.5,
        "forward_buffer_sec": snapshot.buffer_health_sec,
        "buffer_target_sec": 20.0,
        "cdn_latency_ms": snapshot.cdn_egress_latency_ms,
        "timestamp": time.time()
    }

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
