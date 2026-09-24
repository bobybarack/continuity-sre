from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from services.agent_commander import agent_commander, InvestigationResult
from services.mcp_service import official_mcp_bridge
from services.auth import verify_demo_key
from config import GEMINI_MODEL, GOOGLE_CLOUD_PROJECT

router = APIRouter(prefix="/api/agent", tags=["AI SRE Incident Commander"])

@router.get("/status")
async def get_agent_status() -> Dict[str, Any]:
    """Returns the operational status of the Gemini Enterprise Agent Engine."""
    return {
        "configured": agent_commander.is_configured(),
        "model": GEMINI_MODEL,
        "google_cloud_project": GOOGLE_CLOUD_PROJECT,
        "total_investigations_conducted": len(agent_commander.get_history())
    }

@router.get("/mcp-tools")
async def get_mcp_tools() -> Dict[str, Any]:
    """Returns the runtime catalog of official Grafana Cloud MCP tools discovered over stdio."""
    tools = await official_mcp_bridge.list_official_tools()
    required = [
        "query_prometheus",
        "query_loki_logs",
        "create_annotation",
        "create_incident",
        "update_incident"
    ]
    required_present = all(t in tools for t in required)
    return {
        "status": "CONNECTED" if tools else "OFFLINE",
        "binary_path": official_mcp_bridge.get_binary_path(),
        "total_tools": len(tools),
        "tools": tools,
        "required_tools": required,
        "required_tools_present": required_present,
        "allowed_tools": official_mcp_bridge.get_allowed_tools(),
        "adk_mcp_toolset_ready": bool(tools)
    }

@router.post("/investigate-and-remediate", response_model=InvestigationResult, dependencies=[Depends(verify_demo_key)])
async def trigger_investigation():
    """Triggers autonomous SRE investigation, root cause diagnosis, Grafana annotation, and edge remediation."""
    return await agent_commander.investigate_and_remediate()

@router.get("/history", response_model=List[InvestigationResult])
async def get_investigation_history():
    """Returns the historical log of autonomous SRE investigations and post-mortem reports."""
    return agent_commander.get_history()
