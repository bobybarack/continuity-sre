import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from google.adk import Agent
from google.adk.tools.mcp_tool import McpToolset

from services.mcp_service import (
    official_mcp_bridge,
    ALLOWED_GRAFANA_TOOLS,
    get_gemini_tools,
    dispatch_mcp_tool,
    grafana_query_prometheus,
    grafana_query_loki,
    grafana_create_incident,
    grafana_create_annotation,
    grafana_resolve_incident,
    continuity_execute_remediation,
    continuity_verify_closed_loop_recovery
)
from services.agent_commander import agent_commander, InvestigationResult
from services.chaos import chaos_manager, FailureMode
from services.telemetry import telemetry_engine
from services.integration_models import PrometheusQueryResult, LokiQueryResult


@pytest.mark.asyncio
async def test_adk_wiring_and_tool_filtering():
    """Validates ADK Agent wiring and that only restricted Grafana MCP tools are exposed."""
    assert agent_commander.adk_agent is not None
    assert isinstance(agent_commander.adk_agent, Agent)
    assert agent_commander.adk_agent.name == "continuity_sre_agent"

    restricted_toolset = official_mcp_bridge.get_toolset(restricted=True)
    assert isinstance(restricted_toolset, McpToolset)

    # Validate tools exposed by bridge
    allowed = official_mcp_bridge.get_allowed_tools()
    expected_tools = {
        "query_prometheus",
        "query_loki_logs",
        "create_annotation",
        "create_incident",
        "update_incident"
    }
    assert set(allowed) == expected_tools

    # Dynamic declarations for Gemini should include ADK declarations plus CONTINUITY custom tools
    gemini_tools = await get_gemini_tools()
    assert len(gemini_tools) > 0
    all_func_names = [fn.name for fn in gemini_tools[0].function_declarations]
    for required in expected_tools:
        assert required in all_func_names
    assert "continuity_execute_remediation" in all_func_names
    assert "continuity_verify_closed_loop_recovery" in all_func_names


@pytest.mark.asyncio
async def test_grafana_query_flow_via_mcp():
    """Validates Prometheus and Loki query flow through official MCP bridge with normalization."""
    mock_prom = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {"metric": {"service": "edge-video-delivery"}, "value": [1700000000.0, "3.85"]}
            ]
        }
    }
    mock_loki = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {"stream": {"level": "error"}, "values": [[str(1700000000 * 10**9), "HTTP 502 Bad Gateway Fastly edge"]]}
            ]
        }
    }

    with patch.object(official_mcp_bridge, "call_official_tool") as mock_call:
        async def _fake_call(name, args):
            if name == "query_prometheus":
                return mock_prom
            elif name == "query_loki_logs":
                return mock_loki
            return {}
        mock_call.side_effect = _fake_call

        prom_res = await grafana_query_prometheus("rate(vpf[1m])")
        assert isinstance(prom_res, PrometheusQueryResult)
        assert prom_res.status == "success"
        assert prom_res.metric_value == 3.85
        assert "result" in prom_res.data

        loki_res = await grafana_query_loki('{service="edge"} |= "error"')
        assert isinstance(loki_res, LokiQueryResult)
        assert loki_res.status == "success"
        assert len(loki_res.lines) >= 1


@pytest.mark.asyncio
async def test_incident_flow_verification_gate():
    """Validates incident creation, annotation, and verification gate semantics."""
    mock_incident_create = {"id": "INC-ADK-777", "incident_id": "INC-ADK-777", "status": "active"}
    mock_annotation_create = {"id": 888, "text": "Remediation applied"}
    mock_incident_resolve = {"id": "INC-ADK-777", "status": "resolved"}

    with patch.object(official_mcp_bridge, "call_official_tool") as mock_call:
        async def _fake_call(name, args):
            if name == "create_incident":
                return mock_incident_create
            elif name == "create_annotation":
                return mock_annotation_create
            elif name == "update_incident":
                return mock_incident_resolve
            return {}
        mock_call.side_effect = _fake_call

        inc = await grafana_create_incident("CDN Failover", "CRITICAL", "Primary edge failure")
        assert inc.incident_id == "INC-ADK-777"
        assert inc.status == "success"

        ann = await grafana_create_annotation("Failover applied", ["continuity", "test"])
        assert ann.id == 888

        # When recovery passes, incident is updated to resolved
        res = await grafana_resolve_incident("INC-ADK-777", "Verified closed-loop recovery")
        assert res.status == "resolved"


@pytest.mark.asyncio
async def test_continuity_native_tools_invariants():
    """Verifies continuity_execute_remediation and continuity_verify_closed_loop_recovery state control."""
    chaos_manager.reset_to_normal()
    chaos_manager.inject_cdn_outage()

    # Remediation does NOT mark recovered
    rem_res = await continuity_execute_remediation("SHIFT_TRAFFIC_TO_AKAMAI", 20, 80, "Primary edge down")
    assert rem_res["status"] == "REMEDIATED"
    state = chaos_manager.get_state()
    assert state.current_mode == "REMEDIATING"
    assert state.lifecycle_state == "RECOVERING"

    # Only verification gate can mark verified recovery
    mock_prom_recovered = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {"metric": {}, "value": [1700000000.0, "0.15"]}
            ]
        }
    }
    with patch("services.mcp_service.grafana_query_prometheus", new=AsyncMock(return_value=mock_prom_recovered)):
        verify_res = await continuity_verify_closed_loop_recovery()
        assert verify_res["verified"] is True
        assert verify_res["status"] == "PASSED"

    chaos_manager.reset_to_normal()


@pytest.mark.asyncio
async def test_mcp_timeout_and_fallback_resilience():
    """Ensures MCP timeout or connection error degrades safely without crashing."""
    with patch.object(official_mcp_bridge, "call_official_tool", side_effect=asyncio.TimeoutError("MCP call timed out")):
        with patch("services.mcp_service.grafana_client.query_prometheus_instant") as mock_rest:
            mock_rest.return_value = {
                "status": "success",
                "data": {"resultType": "vector", "result": []}
            }
            res = await grafana_query_prometheus("up")
            assert isinstance(res, PrometheusQueryResult)
            assert res.status == "success"


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario_injector,expected_action", [
    (chaos_manager.inject_cdn_outage, "SHIFT_TRAFFIC_TO_AKAMAI"),
    (chaos_manager.inject_drm_timeout, "FAILOVER_DRM_KEY_CLUSTER"),
    (chaos_manager.inject_isp_peering_drop, "REROUTE_BGP_TRANSIT"),
])
async def test_full_lifecycle_scenarios_verified(scenario_injector, expected_action):
    """Executes full lifecycle for CDN, DRM, and ISP failure scenarios resulting in verified resolution."""
    chaos_manager.reset_to_normal()
    scenario_injector()

    mock_prom = PrometheusQueryResult(
        status="success",
        data={"resultType": "vector", "result": [{"metric": {}, "value": [1700000000.0, 3.5]}]}
    )
    mock_loki = LokiQueryResult(
        status="success",
        data={"resultType": "streams", "result": []}
    )
    mock_verify_pass = {
        "verified": True,
        "status": "PASSED",
        "current_vpf_pct": 0.12,
        "forward_buffer_sec": 24.5,
        "cdn_latency_ms": 38.0,
        "prometheus_source": "grafana_mcp_mimir",
        "prometheus_authoritative": True
    }

    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value=mock_prom)), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=mock_loki)), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify_pass)), \
         patch("services.agent_commander.grafana_resolve_incident", new=AsyncMock(return_value={"status": "resolved"})):

        result = await agent_commander.investigate_and_remediate()
        assert result.workflow_status == "RESOLVED"
        assert result.remediation_status == "SUCCESS"
        assert result.closed_loop_verified is True
        assert result.verification_status == "PASSED"
        assert result.mttr_seconds is not None
        assert result.remediation_action == expected_action

    chaos_manager.reset_to_normal()


@pytest.mark.asyncio
async def test_full_lifecycle_deliberately_failed_convergence():
    """Verifies that failed convergence results in PENDING status without resolving the incident."""
    chaos_manager.reset_to_normal()
    chaos_manager.inject_cdn_outage()

    mock_prom = PrometheusQueryResult(
        status="success",
        data={"resultType": "vector", "result": [{"metric": {}, "value": [1700000000.0, 4.2]}]}
    )
    mock_loki = LokiQueryResult(
        status="success",
        data={"resultType": "streams", "result": []}
    )
    mock_verify_pending = {
        "verified": False,
        "status": "PENDING",
        "current_vpf_pct": 2.4,
        "forward_buffer_sec": 8.0,
        "cdn_latency_ms": 180.0,
        "prometheus_source": "grafana_mcp_mimir",
        "prometheus_authoritative": True
    }

    resolve_mock = AsyncMock()

    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value=mock_prom)), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=mock_loki)), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify_pending)), \
         patch("services.agent_commander.grafana_resolve_incident", new=resolve_mock):

        result = await agent_commander.investigate_and_remediate()
        assert result.workflow_status == "PENDING_VERIFICATION"
        assert result.remediation_status == "PENDING_CONVERGENCE"
        assert result.closed_loop_verified is False
        assert result.verification_status == "PENDING"
        assert result.mttr_seconds is None
        # Incident resolution must NOT be called when verification fails
        resolve_mock.assert_not_called()

    chaos_manager.reset_to_normal()
