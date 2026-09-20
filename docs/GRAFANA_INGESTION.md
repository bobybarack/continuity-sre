# CONTINUITY — Grafana Ingestion Architecture & Verification

## 1. Executive Summary

CONTINUITY exposes real-time streaming QoS telemetry via an OpenMetrics / Prometheus scrape endpoint at `/api/telemetry/metrics`. This document establishes the exact ingestion pipeline into Grafana Cloud Mimir/Prometheus and Loki, detailing how telemetry flows from the local/Cloud Run runtime into Grafana Cloud.

---

## 2. Ingestion Topology

```text
  ┌─────────────────────────────────────────────────────────────┐
  │                      CONTINUITY Runtime                     │
  │                                                             │
  │   Canonical 1Hz Ticker ───> PREMIERE_REGISTRY (Prometheus)  │
  │                                     │                       │
  │                              GET /metrics                   │
  └─────────────────────────────────────┬───────────────────────┘
                                        │
                         (HTTP Scrape / Remote Write)
                                        │
                                        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                 Grafana Cloud Ingestion Layer               │
  │                                                             │
  │  Option A: Grafana Alloy / Prometheus Scraper Agent         │
  │    - Job: continuity-sre                                    │
  │    - Scrape Target: https://<cloud-run-domain>/api/telemetry/metrics
  │    - Scrape Interval: 1s - 5s                               │
  │                                                             │
  │  Option B: Prometheus Remote Write / OpenTelemetry          │
  │    - Direct push to https://prometheus-prod-.../api/prom/push
  └─────────────────────────────────────┬───────────────────────┘
                                        │
                                        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                     Grafana Cloud Mimir                     │
  │             (Datasource: grafanacloud-prom)                 │
  └─────────────────────────────────────┬───────────────────────┘
                                        │
                  Query Read-Back via stdio MCP / API Proxy
                                        │
                                        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │             CONTINUITY Closed-Loop Verifier                 │
  │   - Primary: Grafana Cloud Prometheus query                 │
  │   - Fallback: Authoritative Local PREMIERE_REGISTRY         │
  │   - Status: Falsifiable Verification Gate                   │
  └─────────────────────────────────────────────────────────────┘
```

---

## 3. Metrics Ingestion Architecture

### 3.1 Local Scrape Exposition
- **Endpoint**: `GET /api/telemetry/metrics`
- **Format**: OpenMetrics / Prometheus text format (`text/plain; version=0.0.4`)
- **Isolation**: Uses isolated `PREMIERE_REGISTRY = CollectorRegistry(auto_describe=True)` to guarantee clean metrics isolation.
- **Key Metrics Exposed**:
  - `ott_video_playback_failures_ratio`: Gauge, video playback failure ratio [0.0 - 1.0].
  - `ott_cdn_egress_latency_ms`: Gauge, egress round-trip latency in ms.
  - `ott_drm_handshake_ms`: Gauge, Widevine/FairPlay key acquisition latency in ms.
  - `ott_active_viewers_count`: Gauge, total concurrent active viewers.
  - `ott_buffer_health_seconds`: Gauge, forward playback buffer health in seconds.
  - `ott_stream_bitrate_mbps`: Gauge, delivered video bitrate in Mbps.
  - `ott_cdn_traffic_split_percentage`: Gauge, traffic allocation split per provider.

### 3.2 Grafana Alloy Agent Scrape Configuration
To pull metrics into Grafana Cloud Prometheus from the deployed Cloud Run instance, configure Grafana Alloy (`config.alloy`):

```alloy
prometheus.scrape "continuity" {
  targets = [{
    __address__ = "continuity-api-121300560395.us-central1.run.app:443",
    __scheme__  = "https",
    __metrics_path__ = "/api/telemetry/metrics",
  }]
  forward_to = [prometheus.remote_write.grafanacloud.receiver]
  scrape_interval = "2s"
}

prometheus.remote_write "grafanacloud" {
  endpoint {
    url = "https://prometheus-prod-66-prod-us-east-3.grafana.net/api/prom/push"
    basic_auth {
      username = "3555484"
      password = env("GRAFANA_CLOUD_API_KEY")
    }
  }
}
```

---

## 4. Log Ingestion & Loki Boundary

### 4.1 Proxied Datasource vs Direct Push
- In Grafana Cloud, `/api/datasources/proxy/uid/grafanacloud-logs/loki/api/v1/push` rejects arbitrary un-allowlisted POST requests with HTTP 403 (`non allow-listed POSTs not allowed on proxied loki datasource`).
- Direct Loki ingestion requires forwarding logs via Grafana Alloy or using the dedicated Loki remote write endpoint (`https://logs-prod-042.grafana.net/loki/api/v1/push`) with Basic Auth credentials (`1773417:<Loki Token>`).
- To maintain UI and operational truthfulness (addressing Issue 12):
  - Local simulation events are strictly labeled `SIMULATED EDGE EVENT` in the UI rather than falsely claiming `LOKI INGEST`.
  - When Loki query reads return live records, the UI and agent attribute them to Grafana Cloud Loki.

---

## 5. Verification & Closed-Loop Read-Back

1. **Remote Authoritative Source**:
   - `continuity_verify_closed_loop_recovery` executes PromQL (`ott_video_playback_failures_ratio`) against Grafana Cloud Mimir.
   - If scraped values are present in Grafana Cloud, `prometheus_source="grafana_cloud_prometheus"` and `prometheus_authoritative=True`.
2. **Local Registry Fallback**:
   - If Grafana Cloud proxy does not yet have recent scraped data, the verifier queries the local in-process `PREMIERE_REGISTRY`.
   - `prometheus_source="prometheus_collector_registry"`, `prometheus_authoritative=False`, `verification_source_trusted=True`.
3. **Fail-Closed Guard**:
   - If no authoritative metric value is parseable from either source, verification strictly fails closed with `status="PENDING"` and `is_recovered=False`.
