import pytest
from unittest.mock import AsyncMock, patch
from services.chaos import chaos_manager, FailureMode, IncidentLifecycle
from services.agent_commander import agent_commander
from services.integration_models import (
    PrometheusQueryResult,
    LokiQueryResult,
    GrafanaIncidentRef,
    GrafanaAnnotationRef
)

@pytest.mark.asyncio
async def test_e2e_successful_recovery_lifecycle():
    """Acceptance Item 49: NORMAL -> failure -> investigate -> remediation -> recovering -> verified recovery."""
    # 1. Start in NORMAL state
    chaos_manager.reset_to_normal()
    state_init = chaos_manager.get_state()
    assert state_init.lifecycle == IncidentLifecycle.NORMAL
    assert state_init.is_outage_active is False

    # 2. Inject Failure (DRM cluster timeout)
    chaos_manager.inject_drm_timeout()
    state_outage = chaos_manager.get_state()
    assert state_outage.lifecycle == IncidentLifecycle.INCIDENT_ACTIVE
    assert state_outage.is_outage_active is True
    assert state_outage.failure_mode == FailureMode.DRM_TIMEOUT

    # 3. Fast convergence for test
    chaos_manager.state.convergence_duration_sec = 0.1

    mock_prom = PrometheusQueryResult(
        status="success",
        query="ott_drm_auth_errors_total",
        metric_value=0.15,
        source="official_mcp"
    )
    mock_loki = LokiQueryResult(
        status="success",
        query="{service='drm'}",
        lines=["DRM handshake timeout on cluster primary"],
        entry_count=1,
        source="official_mcp"
    )
    mock_inc = GrafanaIncidentRef(
        status="success",
        incident_id="INC-E2E-DRM-49",
        id="INC-E2E-DRM-49",
        title="DRM Outage",
        severity="CRITICAL",
        lifecycle_status="active",
        source="official_mcp"
    )
    mock_ann = GrafanaAnnotationRef(
        status="success",
        id=9090,
        text="Remediation applied",
        source="official_mcp"
    )
    mock_verify = {
        "status": "PASSED",
        "verified": True,
        "prometheus_query": "ott_video_playback_failures_ratio",
        "prometheus_readback_status": "success",
        "prometheus_metric_value": 0.15,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_value_available": True,
        "prometheus_authoritative": True,
        "verification_source_trusted": True,
        "current_vpf_pct": 0.15,
        "forward_buffer_sec": 28.0,
        "cdn_latency_ms": 40.0
    }
    mock_resolve = AsyncMock(return_value=GrafanaIncidentRef(
        status="success",
        incident_id="INC-E2E-DRM-49",
        id="INC-E2E-DRM-49",
        lifecycle_status="resolved",
        source="official_mcp"
    ))

    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value=mock_prom)), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=mock_loki)), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value=mock_inc)), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value=mock_ann)), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch("services.agent_commander.grafana_resolve_incident", mock_resolve), \
         patch.object(agent_commander, "client", None):

        result = await agent_commander.investigate_and_remediate()

        # 4. Verify orchestration assertions
        assert result.workflow_status == "RESOLVED"
        assert result.remediation_status == "SUCCESS"
        assert result.closed_loop_verified is True
        assert result.verification_status == "PASSED"
        assert result.mttr_seconds is not None
        assert result.mttr_seconds >= 0.0
        assert result.grafana_incident_id == "INC-E2E-DRM-49"
        assert result.annotation_id == 9090

        # Verify incident resolved in Grafana
        mock_resolve.assert_called_once()
        assert mock_resolve.call_args[1]["incident_id"] == "INC-E2E-DRM-49"

        # Verify system state transitioned to VERIFIED_RECOVERED
        final_state = chaos_manager.get_state()
        assert final_state.lifecycle == IncidentLifecycle.VERIFIED_RECOVERED
        assert final_state.is_outage_active is False

@pytest.mark.asyncio
async def test_e2e_deliberate_failure_pending_escalated():
    """Acceptance Item 50: NORMAL -> failure -> remediation -> recovery fails -> PENDING/ESCALATED."""
    # 1. Start in NORMAL state
    chaos_manager.reset_to_normal()

    # 2. Inject Failure (ISP Peering Drop)
    chaos_manager.inject_isp_peering_drop()
    state_outage = chaos_manager.get_state()
    assert state_outage.lifecycle == IncidentLifecycle.INCIDENT_ACTIVE
    assert state_outage.failure_mode == FailureMode.ISP_PEERING_DROP

    # 3. Force recovery failure to simulate persistent packet loss
    chaos_manager.set_force_recovery_failure(True)

    mock_prom = PrometheusQueryResult(
        status="success",
        query="ott_network_packet_loss_pct",
        metric_value=4.2,
        source="official_mcp"
    )
    mock_loki = LokiQueryResult(
        status="success",
        query="{service='edge'}",
        lines=["BGP peering drop detected on AS13335"],
        entry_count=1,
        source="official_mcp"
    )
    mock_inc = GrafanaIncidentRef(
        status="success",
        incident_id="INC-E2E-FAIL-50",
        id="INC-E2E-FAIL-50",
        title="ISP Peering Drop",
        severity="WARNING",
        lifecycle_status="active",
        source="official_mcp"
    )
    mock_ann = GrafanaAnnotationRef(
        status="success",
        id=9091,
        text="Remediation applied",
        source="official_mcp"
    )
    mock_verify_failed = {
        "status": "PENDING",
        "verified": False,
        "prometheus_query": "ott_video_playback_failures_ratio",
        "prometheus_readback_status": "success",
        "prometheus_metric_value": 3.8, # Unhealthy!
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_value_available": True,
        "prometheus_authoritative": True,
        "verification_source_trusted": True,
        "current_vpf_pct": 3.8,
        "forward_buffer_sec": 8.0,
        "cdn_latency_ms": 280.0
    }
    mock_resolve = AsyncMock()

    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value=mock_prom)), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=mock_loki)), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value=mock_inc)), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value=mock_ann)), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify_failed)), \
         patch("services.agent_commander.grafana_resolve_incident", mock_resolve), \
         patch.object(agent_commander, "client", None):

        result = await agent_commander.investigate_and_remediate()

        # 4. Verify deliberate failure assertions
        assert result.workflow_status == "PENDING_VERIFICATION"
        assert result.remediation_status == "PENDING_CONVERGENCE"
        assert result.closed_loop_verified is False
        assert result.verification_status == "PENDING"
        assert result.mttr_seconds is None  # MTTR must be None when recovery fails!
        assert result.grafana_incident_id == "INC-E2E-FAIL-50"

        # Grafana incident must NOT be resolved when verification is pending
        mock_resolve.assert_not_called()

        # Lifecycle remains ESCALATED and outage remains ACTIVE
        final_state = chaos_manager.get_state()
        assert final_state.lifecycle == IncidentLifecycle.ESCALATED
        assert final_state.is_outage_active is True
