from fastapi import APIRouter
from typing import List, Dict, Any
from services.agent_commander import agent_commander, InvestigationResult
from services.mcp_service import official_mcp_bridge
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
    return {
        "status": "CONNECTED" if tools else "OFFLINE",
        "binary_path": official_mcp_bridge.get_binary_path(),
        "total_tools": len(tools),
        "tools": tools
    }

@router.post("/investigate-and-remediate", response_model=InvestigationResult)
async def trigger_investigation():
    """Triggers autonomous SRE investigation, root cause diagnosis, Grafana annotation, and edge remediation."""
    return await agent_commander.investigate_and_remediate()

@router.get("/history", response_model=List[InvestigationResult])
async def get_investigation_history():
    """Returns the historical log of autonomous SRE investigations and post-mortem reports."""
    return agent_commander.get_history()
