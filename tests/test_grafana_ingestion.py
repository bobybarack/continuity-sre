import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from services.grafana_client import grafana_client
from services.telemetry import telemetry_engine

@pytest.mark.asyncio
async def test_push_loki_log_mocked():
    """Unit-test push_loki_log behavior with mocked HTTP client response."""
    with patch.object(grafana_client, "_execute_with_retry", new_callable=AsyncMock) as mock_exec:
        mock_response = AsyncMock()
        mock_response.status_code = 204
        mock_exec.return_value = mock_response
        
        res = await grafana_client.push_loki_log(
            stream_labels={"service": "ott-edge-router", "failure_mode": "CDN_OUTAGE"},
            log_line="502 Bad Gateway test line"
        )
        
        assert res["status"] == "success"
        assert res["code"] == 204
        mock_exec.assert_called_once()

@pytest.mark.asyncio
async def test_metrics_scrape_format():
    """Verifies that the /metrics exposition format contains all required Prometheus metrics."""
    exposition = telemetry_engine.get_prometheus_exposition().decode("utf-8")
    
    assert "ott_video_playback_failures_ratio" in exposition
    assert "ott_cdn_egress_latency_ms" in exposition
    assert "ott_drm_handshake_ms" in exposition
    assert "ott_buffer_health_seconds" in exposition
    assert "ott_stream_bitrate_mbps" in exposition

@pytest.mark.grafana_live
@pytest.mark.asyncio
async def test_live_grafana_health_and_datasources():
    """Opt-in live integration test verifying live connectivity to Grafana Cloud."""
    health = await grafana_client.check_health()
    assert health["connected"] is True
    assert health["status"] == "HEALTHY"
    assert health["datasources_count"] >= 5
