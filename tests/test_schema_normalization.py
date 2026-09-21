import pytest
from unittest.mock import AsyncMock, patch
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
from services.agent_commander import agent_commander
from services.chaos import chaos_manager, FailureMode

def test_prometheus_normalization_mcp_and_rest():
    mcp_raw = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"__name__": "ott_video_playback_failures_ratio"},
                    "value": [1726900000.0, "0.0019"]
                }
            ]
        }
    }
    mcp_norm = normalize_prometheus_result(mcp_raw, query="ott_video_playback_failures_ratio", source="official_mcp")
    assert isinstance(mcp_norm, PrometheusQueryResult)
    assert mcp_norm.status == "success"
    assert mcp_norm.source == "official_mcp"
    assert mcp_norm.result_type == "vector"
    assert mcp_norm.metric_value == 0.19
    assert mcp_norm["metric_value"] == 0.19
    assert mcp_norm.get("source") == "official_mcp"

    rest_raw = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"__name__": "cdn_latency"},
                    "value": [1726900000.0, "45.2"]
                }
            ]
        }
    }
    rest_norm = normalize_prometheus_result(rest_raw, query="cdn_latency", source="direct_rest")
    assert isinstance(rest_norm, PrometheusQueryResult)
    assert rest_norm.status == "success"
    assert rest_norm.source == "direct_rest"
    assert rest_norm.metric_value == 45.2

    error_raw = {"status": "error", "error": "Datasource proxy timed out"}
    error_norm = normalize_prometheus_result(error_raw, query="test_metric", source="direct_rest")
    assert error_norm.status == "error"
    assert "timed out" in error_norm.error

def test_loki_normalization_mcp_and_rest():
    mcp_raw = {
        "lines": [
            "HTTP 502 Bad Gateway - edge-pop-iad01",
            "HTTP 502 Bad Gateway - edge-pop-iad02"
        ]
    }
    mcp_norm = normalize_loki_result(mcp_raw, query="{app='edge-router'}", source="official_mcp")
    assert isinstance(mcp_norm, LokiQueryResult)
    assert mcp_norm.status == "success"
    assert mcp_norm.source == "official_mcp"
    assert mcp_norm.entry_count == 2
    assert len(mcp_norm.lines) == 2
    assert "iad01" in mcp_norm.lines[0]
    assert mcp_norm["entry_count"] == 2

    rest_raw = {
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"service": "edge-router"},
                    "values": [
                        ["1726900000000000000", "BGP peering drop detected on AS13335"],
                        ["1726900001000000000", "Packet drop rate exceeds 35%"]
                    ]
                }
            ]
        }
    }
    rest_norm = normalize_loki_result(rest_raw, query="{service='edge-router'}", source="direct_rest")
    assert isinstance(rest_norm, LokiQueryResult)
    assert rest_norm.status == "success"
    assert rest_norm.source == "direct_rest"
    assert rest_norm.entry_count == 2
    assert "BGP peering drop" in rest_norm.lines[0]

def test_grafana_incident_normalization():
    mcp_raw = {
        "incident_id": "INC-MCP-101",
        "title": "Edge CDN Degradation",
        "severity": "CRITICAL",
        "status": "active"
    }
    mcp_norm = normalize_incident_result(mcp_raw, source="official_mcp")
    assert isinstance(mcp_norm, GrafanaIncidentRef)
    assert mcp_norm.incident_id == "INC-MCP-101"
    assert mcp_norm.id == "INC-MCP-101"
    assert mcp_norm.lifecycle_status == "active"
    assert mcp_norm.source == "official_mcp"

    rest_raw = {
        "status": "success",
        "incident": {
            "id": "INC-REST-202",
            "title": "DRM Key Rotation",
            "severity": "MAJOR",
            "status": "resolved"
        }
    }
    rest_norm = normalize_incident_result(rest_raw, source="direct_rest")
    assert isinstance(rest_norm, GrafanaIncidentRef)
    assert rest_norm.incident_id == "INC-REST-202"
    assert rest_norm.id == "INC-REST-202"
    assert rest_norm.lifecycle_status == "resolved"
    assert rest_norm.source == "direct_rest"

def test_grafana_annotation_normalization():
    mcp_raw = {
        "Payload": {
            "id": 4040,
            "message": "Annotation added"
        }
    }
    mcp_norm = normalize_annotation_result(mcp_raw, source="official_mcp")
    assert isinstance(mcp_norm, GrafanaAnnotationRef)
    assert mcp_norm.id == 4040
    assert mcp_norm.status == "success"
    assert mcp_norm.source == "official_mcp"

    rest_raw = {"id": 5050, "message": "Annotation added"}
    rest_norm = normalize_annotation_result(rest_raw, source="direct_rest")
    assert isinstance(rest_norm, GrafanaAnnotationRef)
    assert rest_norm.id == 5050
    assert rest_norm.status == "success"
    assert rest_norm.source == "direct_rest"

@pytest.mark.asyncio
async def test_agent_commander_consumes_normalized_results():
    chaos_manager.inject_cdn_outage()
    
    mock_prom = PrometheusQueryResult(
        status="success",
        query="ott_video_playback_failures_ratio",
        metric_value=4.8,
        source="official_mcp"
    )
    mock_loki = LokiQueryResult(
        status="success",
        query="{service='edge'}",
        lines=["HTTP 502 Bad Gateway - Fastly Edge"],
        entry_count=1,
        source="official_mcp"
    )
    mock_inc = GrafanaIncidentRef(
        status="success",
        incident_id="INC-NORM-1234",
        id="INC-NORM-1234",
        title="CDN Outage",
        severity="CRITICAL",
        lifecycle_status="active",
        source="official_mcp"
    )
    mock_ann = GrafanaAnnotationRef(
        status="success",
        id=7788,
        text="Remediation applied",
        source="official_mcp"
    )
    mock_verify = {
        "status": "PASSED",
        "verified": True,
        "prometheus_query": "ott_video_playback_failures_ratio",
        "prometheus_readback_status": "success",
        "prometheus_metric_value": 0.18,
        "prometheus_source": "grafana_cloud_prometheus",
        "prometheus_value_available": True,
        "prometheus_authoritative": True,
        "verification_source_trusted": True,
        "current_vpf_pct": 0.18,
        "forward_buffer_sec": 26.5,
        "cdn_latency_ms": 42.0
    }

    with patch("services.agent_commander.grafana_query_prometheus", new=AsyncMock(return_value=mock_prom)), \
         patch("services.agent_commander.grafana_query_loki", new=AsyncMock(return_value=mock_loki)), \
         patch("services.agent_commander.grafana_create_incident", new=AsyncMock(return_value=mock_inc)), \
         patch("services.agent_commander.grafana_create_annotation", new=AsyncMock(return_value=mock_ann)), \
         patch("services.agent_commander.continuity_verify_closed_loop_recovery", new=AsyncMock(return_value=mock_verify)), \
         patch("services.agent_commander.grafana_resolve_incident", new=AsyncMock(return_value=mock_inc)), \
         patch.object(agent_commander, "client", None):
        
        result = await agent_commander.investigate_and_remediate()
        assert result.workflow_status == "RESOLVED"
        assert result.grafana_incident_id == "INC-NORM-1234"
        assert result.annotation_id == 7788
        assert result.closed_loop_verified is True
        assert result.verification_status == "PASSED"
