import os
import sys
import json
import httpx
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import GRAFANA_INSTANCE_URL, GRAFANA_TOKEN, GRAFANA_PROM_UID, GRAFANA_LOKI_UID

async def provision_dashboard():
    print(f"Connecting to Grafana Cloud: {GRAFANA_INSTANCE_URL}...")
    headers = {
        "Authorization": f"Bearer {GRAFANA_TOKEN}",
        "Content-Type": "application/json"
    }

    dashboard_schema = {
        "dashboard": {
            "id": None,
            "uid": "continuity-premiere-hud",
            "title": "CONTINUITY — Premiere Night SRE Command Center",
            "tags": ["continuity", "sre", "gemini", "autonomous-fix", "mcp", "hollywood-premiere"],
            "timezone": "browser",
            "schemaVersion": 38,
            "version": 1,
            "refresh": "5s",
            "time": {
                "from": "now-15m",
                "to": "now"
            },
            "annotations": {
                "list": [
                    {
                        "builtIn": 1,
                        "datasource": "-- Grafana --",
                        "enable": True,
                        "hide": False,
                        "name": "Annotations & Alerts",
                        "type": "dashboard"
                    },
                    {
                        "name": "Continuity Auto-Fix Annotations",
                        "datasource": "-- Grafana --",
                        "enable": True,
                        "tags": ["continuity"],
                        "iconColor": "rgba(0, 210, 255, 1)",
                        "type": "tags"
                    }
                ]
            },
            "panels": [
                {
                    "id": 1,
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
                    "type": "stat",
                    "title": "Stream Delivery Status",
                    "datasource": {"type": "prometheus", "uid": GRAFANA_PROM_UID},
                    "targets": [
                        {"expr": "streaming_active_viewers", "refId": "A"}
                    ],
                    "options": {
                        "reduceOptions": {"calcs": ["lastNotNull"]},
                        "colorMode": "value",
                        "graphMode": "none"
                    }
                },
                {
                    "id": 2,
                    "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
                    "type": "stat",
                    "title": "Video Playback Failure (VPF)",
                    "datasource": {"type": "prometheus", "uid": GRAFANA_PROM_UID},
                    "targets": [
                        {"expr": "streaming_playback_failure_ratio * 100", "refId": "A"}
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "red", "value": 0.5}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 3,
                    "gridPos": {"h": 4, "w": 6, "x": 12, "y": 0},
                    "type": "stat",
                    "title": "Autonomous MTTR",
                    "options": {
                        "text": {"valueSize": 38},
                        "colorMode": "value",
                        "graphMode": "none"
                    }
                },
                {
                    "id": 4,
                    "gridPos": {"h": 4, "w": 6, "x": 18, "y": 0},
                    "type": "stat",
                    "title": "Prevented Churn Impact",
                    "options": {
                        "text": {"valueSize": 38},
                        "colorMode": "value",
                        "graphMode": "none"
                    }
                },
                {
                    "id": 5,
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
                    "type": "timeseries",
                    "title": "Live 4K QoS: Video Playback Failures vs. SLA Threshold",
                    "datasource": {"type": "prometheus", "uid": GRAFANA_PROM_UID},
                    "targets": [
                        {"expr": "streaming_playback_failure_ratio * 100", "legendFormat": "VPF Rate (%)", "refId": "A"}
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "lineWidth": 2,
                                "thresholdsStyle": {"mode": "dashed"}
                            },
                            "unit": "percent",
                            "thresholds": {
                                "mode": "absolute",
                                "steps": [
                                    {"color": "green", "value": None},
                                    {"color": "red", "value": 0.5}
                                ]
                            }
                        }
                    }
                },
                {
                    "id": 6,
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
                    "type": "timeseries",
                    "title": "Client Forward Buffer Depth & CDN Egress Latency",
                    "datasource": {"type": "prometheus", "uid": GRAFANA_PROM_UID},
                    "targets": [
                        {"expr": "streaming_buffer_health_seconds", "legendFormat": "Forward Buffer Depth (s)", "refId": "A"},
                        {"expr": "streaming_cdn_latency_seconds * 1000", "legendFormat": "CDN Latency (ms)", "refId": "B"}
                    ]
                },
                {
                    "id": 7,
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 12},
                    "type": "bargauge",
                    "title": "Multi-CDN Egress Route Steering Ratio",
                    "datasource": {"type": "prometheus", "uid": GRAFANA_PROM_UID},
                    "targets": [
                        {"expr": "streaming_primary_traffic_ratio * 100", "legendFormat": "Fastly POP Primary (%)", "refId": "A"},
                        {"expr": "streaming_secondary_traffic_ratio * 100", "legendFormat": "Akamai Edge Failover (%)", "refId": "B"}
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "max": 100,
                            "min": 0
                        }
                    }
                },
                {
                    "id": 8,
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 12},
                    "type": "logs",
                    "title": "Loki Edge Router 502 Bad Gateway & ASN Transit Stream",
                    "datasource": {"type": "loki", "uid": GRAFANA_LOKI_UID},
                    "targets": [
                        {"expr": '{service="ott-edge-router"}', "refId": "A"}
                    ]
                }
            ]
        },
        "overwrite": True
    }

    url = f"{GRAFANA_INSTANCE_URL}/api/dashboards/db"
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(url, headers=headers, json=dashboard_schema)
        if res.status_code in [200, 201]:
            data = res.json()
            print("Dashboard Provisioned Successfully!")
            print(f"UID: {data.get('uid')}")
            print(f"URL: {GRAFANA_INSTANCE_URL}{data.get('url')}")
            print(f"Status: {data.get('status')}")
            return data
        else:
            print(f"Failed to provision dashboard: {res.status_code} - {res.text}")
            return None

if __name__ == "__main__":
    asyncio.run(provision_dashboard())
