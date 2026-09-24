import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from main import app
from services.chaos import chaos_manager, FailureMode, IncidentLifecycle
from config import CONTINUITY_DEMO_KEY

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_state():
    chaos_manager.reset()
    yield
    chaos_manager.reset()

def test_webhook_unauthorized():
    response = client.post(
        "/api/alerts/grafana",
        json={"status": "firing", "alerts": []}
    )
    assert response.status_code == 401

def test_webhook_authorized_firing_alert():
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "PlaybackFailuresBreached",
                    "severity": "critical",
                    "service": "ott-edge-router",
                    "region": "us-east-2"
                },
                "annotations": {
                    "summary": "Primary edge CDN failure detected via VPF breach"
                },
                "fingerprint": "cdn-test-fp-101"
            }
        ]
    }
    response = client.post(
        "/api/alerts/grafana",
        json=payload,
        headers={"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert data["workflow_started"] is True
    assert data["failure_mode"] == "CDN_OUTAGE"
    assert data["incident_id"] is not None

def test_webhook_duplicate_deduplication():
    payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "PlaybackFailuresBreached",
                    "severity": "critical",
                    "region": "us-east-2"
                },
                "annotations": {
                    "summary": "Primary edge CDN failure"
                },
                "fingerprint": "cdn-dedup-fp-202"
            }
        ]
    }
    # First delivery
    res1 = client.post(
        "/api/alerts/grafana",
        json=payload,
        headers={"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY}
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "ACCEPTED"

    # Duplicate delivery
    res2 = client.post(
        "/api/alerts/grafana",
        json=payload,
        headers={"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "DEDUPLICATED"
    assert data2["workflow_started"] is False

def test_webhook_resolved_alert_ignored():
    payload = {
        "status": "resolved",
        "alerts": []
    }
    response = client.post(
        "/api/alerts/grafana",
        json=payload,
        headers={"X-Continuity-Demo-Key": CONTINUITY_DEMO_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "IGNORED"
    assert data["workflow_started"] is False

def test_webhook_failure_mode_mapping():
    # DRM failure mapping
    drm_payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "DRMHandshakeTimeout", "service": "drm-widevine-auth"},
                "annotations": {"description": "Widevine license server cluster unresponsive"},
                "fingerprint": "drm-fp-303"
            }
        ]
    }
    res_drm = client.post(
        "/api/alerts/grafana",
        json=drm_payload,
        headers={"Authorization": f"Bearer {CONTINUITY_DEMO_KEY}"}
    )
    assert res_drm.status_code == 200
    assert res_drm.json()["failure_mode"] == "DRM_TIMEOUT"

    chaos_manager.reset()

    # ISP failure mapping
    isp_payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "BGPTransitDegraded", "transit": "AS3356"},
                "annotations": {"description": "Severe packet loss on Tier-1 peering point"},
                "fingerprint": "isp-fp-404"
            }
        ]
    }
    res_isp = client.post(
        f"/api/alerts/grafana?token={CONTINUITY_DEMO_KEY}",
        json=isp_payload
    )
    assert res_isp.status_code == 200
    assert res_isp.json()["failure_mode"] == "ISP_PEERING_DROP"
