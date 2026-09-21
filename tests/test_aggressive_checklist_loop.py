import time
import pytest
from unittest.mock import AsyncMock, patch
from services.chaos import ChaosStateManager, IncidentLifecycle, FailureMode
from services.scenarios import SCENARIOS, SCENARIO_ACTIONS
from services.telemetry import TelemetryEngine, PREMIERE_REGISTRY
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
from services.agent_commander import AgentCommander
from main import app
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_aggressive_50_cycle_audit_loop():
    """Aggressive multi-cycle test loop validating all core truth invariants 50 times back-to-back."""
    for cycle in range(1, 51):
        # ----------------------------------------------------
        # 1. State Truth & Lifecycle (Issue 1)
        # ----------------------------------------------------
        mgr = ChaosStateManager()
        assert mgr.state.lifecycle == IncidentLifecycle.NORMAL
        assert mgr.state.is_outage_active is False

        mgr.inject_cdn_outage()
        assert mgr.state.lifecycle == IncidentLifecycle.INCIDENT_ACTIVE
        assert mgr.state.is_outage_active is True

        state_rec = mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
        assert state_rec.lifecycle == IncidentLifecycle.RECOVERING
        assert state_rec.is_outage_active is True
        assert state_rec.remediation_action == "SHIFT_TRAFFIC_TO_AKAMAI"

        # Verification pass path
        state_pass = mgr.mark_verified_recovered({"vpf": 0.18})
        assert state_pass.lifecycle == IncidentLifecycle.VERIFIED_RECOVERED
        assert state_pass.is_outage_active is False
        assert state_pass.verified_recovered_at is not None

        # Verification fail path
        mgr.inject_cdn_outage()
        mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
        state_fail = mgr.mark_recovery_failed("Metrics unresolved", {"vpf": 3.8})
        assert state_fail.lifecycle == IncidentLifecycle.ESCALATED
        assert state_fail.is_outage_active is True

        # ----------------------------------------------------
        # 2. Scenario-Specific State Truth (Issue 2)
        # ----------------------------------------------------
        # CDN modifies only CDN
        mgr.reset_to_normal()
        mgr.inject_cdn_outage()
        cdn_state = mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
        assert cdn_state.primary_cdn_traffic_pct == 20
        assert cdn_state.secondary_cdn_traffic_pct == 80
        assert cdn_state.active_drm_cluster == "drm-key-cluster-primary"
        assert cdn_state.active_transit_route == "ASN-3356-Direct"

        # DRM modifies only DRM
        mgr.reset_to_normal()
        mgr.inject_drm_timeout()
        drm_state = mgr.apply_autonomous_remediation("FAILOVER_DRM_KEY_CLUSTER")
        assert drm_state.active_drm_cluster == "drm-key-cluster-failover"
        assert drm_state.secondary_drm_cluster_status == "ACTIVE"
        assert drm_state.primary_cdn_traffic_pct == 100
        assert drm_state.active_transit_route == "ASN-3356-Direct"

        # ISP modifies only Transit
        mgr.reset_to_normal()
        mgr.inject_isp_peering_drop()
        isp_state = mgr.apply_autonomous_remediation("REROUTE_BGP_TRANSIT")
        assert isp_state.active_transit_route == "ASN-2914-Backup"
        assert isp_state.secondary_transit_status == "ACTIVE"
        assert isp_state.primary_cdn_traffic_pct == 100
        assert isp_state.active_drm_cluster == "drm-key-cluster-primary"

        # Inapplicable actions fail explicitly
        mgr.reset_to_normal()
        mgr.inject_cdn_outage()
        with pytest.raises(ValueError):
            mgr.apply_autonomous_remediation("FAILOVER_DRM_KEY_CLUSTER")

        with pytest.raises(ValueError):
            mgr.apply_autonomous_remediation("UNKNOWN_ACTION_XYZ")

        # ----------------------------------------------------
        # 3. Telemetry Truth & Side-Effect Free Reads (Issue 3)
        # ----------------------------------------------------
        engine = TelemetryEngine()
        snap1 = engine.get_current_snapshot()
        snap2 = engine.get_current_snapshot()
        assert snap1.timestamp == snap2.timestamp
        assert snap1.video_playback_failures_pct == snap2.video_playback_failures_pct

        # ----------------------------------------------------
        # 4. Convergence Curve & Falsifiable Failure (Issue 4)
        # ----------------------------------------------------
        mgr.reset_to_normal()
        mgr.inject_cdn_outage()
        mgr.set_force_recovery_failure(True)
        mgr.apply_autonomous_remediation("SHIFT_TRAFFIC_TO_AKAMAI")
        # Under force_recovery_failure, VPF never drops below 2.0%
        engine._chaos_manager = mgr
        tick_fail = engine._tick()
        assert tick_fail.video_playback_failures_pct > 0.5

        # ----------------------------------------------------
        # 5. MTTR & Healthy Workflow Semantics (Issue 7 & 19)
        # ----------------------------------------------------
        commander = AgentCommander()
        commander.client = None
        mgr.reset_to_normal()
        engine._chaos_manager = mgr
        engine._tick()

        mock_healthy_prom = PrometheusQueryResult(
            status="success",
            query="ott_video_playback_failures_ratio",
            metric_value=0.18,
            source="official_mcp"
        )

        with patch("services.agent_commander.chaos_manager", mgr), \
             patch("services.agent_commander.telemetry_engine", engine), \
             patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value=mock_healthy_prom)):
            healthy_res = await commander.investigate_and_remediate()
            assert healthy_res.severity == "HEALTHY"
            assert healthy_res.workflow_status == "HEALTHY"
            assert healthy_res.verification_status == "NOT_REQUIRED"
            assert healthy_res.mttr_seconds is None

        # ----------------------------------------------------
        # 6. Scenario PromQL / LogQL Routing (Issue 8)
        # ----------------------------------------------------
        for failure_name, scenario_def in SCENARIOS.items():
            assert "promql" in scenario_def
            assert "logql" in scenario_def
            assert len(scenario_def["promql"]) > 0
            assert len(scenario_def["logql"]) > 0

        # ----------------------------------------------------
        # 7. Schema Normalization (Issue 20)
        # ----------------------------------------------------
        prom_mcp = normalize_prometheus_result(
            {"status": "success", "data": {"result": [{"value": [1000, "0.0019"]}]}},
            query="test",
            source="official_mcp"
        )
        assert isinstance(prom_mcp, PrometheusQueryResult)
        assert prom_mcp.metric_value == 0.19
        assert prom_mcp.source == "official_mcp"

        prom_rest = normalize_prometheus_result(
            {"status": "success", "data": {"result": [{"value": [1000, "55.0"]}]}},
            query="test",
            source="direct_rest"
        )
        assert isinstance(prom_rest, PrometheusQueryResult)
        assert prom_rest.metric_value == 55.0
        assert prom_rest.source == "direct_rest"

        loki_mcp = normalize_loki_result(["line1", "line2"], query="test", source="official_mcp")
        assert isinstance(loki_mcp, LokiQueryResult)
        assert loki_mcp.entry_count == 2

        inc_norm = normalize_incident_result({"incident_id": "INC-LOOP", "severity": "CRITICAL"})
        assert isinstance(inc_norm, GrafanaIncidentRef)
        assert inc_norm.incident_id == "INC-LOOP"
        assert inc_norm.id == "INC-LOOP"

        ann_norm = normalize_annotation_result({"Payload": {"id": 1234}})
        assert isinstance(ann_norm, GrafanaAnnotationRef)
        assert ann_norm.id == 1234

        # ----------------------------------------------------
        # 8. Prometheus Cardinality Bounds (Issue 15)
        # ----------------------------------------------------
        for metric in PREMIERE_REGISTRY.collect():
            for sample in metric.samples:
                assert "incident_id" not in sample.labels
                assert "uuid" not in sample.labels

@pytest.mark.asyncio
async def test_aggressive_api_security_loop():
    """Aggressive 10-cycle loop testing mutation protection, CORS, and probe endpoints."""
    transport = ASGITransport(app=app)
    from config import CONTINUITY_DEMO_KEY

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(10):
            # Public reads must succeed without key
            assert (await client.get("/healthz")).status_code == 200
            assert (await client.get("/readyz")).status_code == 200
            assert (await client.get("/api/telemetry/current")).status_code == 200
            assert (await client.get("/api/telemetry/metrics")).status_code == 200
            assert (await client.get("/api/chaos/state")).status_code == 200

            # Mutations must fail without key
            assert (await client.post("/api/chaos/inject-cdn-outage")).status_code == 401
            assert (await client.post("/api/chaos/reset")).status_code == 401
            assert (await client.post("/api/agent/investigate-and-remediate")).status_code == 401

            # Mutations must succeed with valid key
            headers = {"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY}
            assert (await client.post("/api/chaos/reset", headers=headers)).status_code == 200
            assert (await client.post("/api/chaos/inject-cdn-outage", headers=headers)).status_code == 200
            assert (await client.post("/api/chaos/reset", headers=headers)).status_code == 200
