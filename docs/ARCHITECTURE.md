# CONTINUITY: Technical Architecture & System Specification

## 1. System Overview

CONTINUITY is an autonomous stream continuity SRE Incident Commander engineered for OTT live streaming platforms. It connects real-time video player quality-of-experience (QoE) telemetry, Grafana Cloud Prometheus metrics, Loki log streams, and Google Cloud Gemini Enterprise into a closed-loop, self-healing pipeline.

```
+---------------------------------------------------------------------------------------------------+
|                                   CONTINUITY SYSTEM ARCHITECTURE                                  |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [4.28M CONCURRENT OTT STREAM CLIENTS]                                                            |
|  (HLS / DASH Video Players streaming 'Continuity Premiere: Global Broadcast 4K')                  |
|                                 |                                                                 |
|                                 v (Pushes Telemetry & Edge Logs)                                  |
|  +---------------------------------------------------------------------------------------------+  |
|  |                             GRAFANA CLOUD OBSERVABILITY STACK                               |  |
|  |  • Prometheus Metrics: `ott_vpf_ratio`, `ott_cdn_latency_ms`, `ott_drm_handshake_ms`          |  |
|  |  • Loki Log Stream:    `{service="ott-edge-router"} |= "502 Bad Gateway"`                   |  |
|  |  • Grafana Live Dashboard with Real-Time Incident Annotations                              |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                 |                                                                 |
|                                 v (MCP Protocol over SSE/HTTP: 60+ Tools)                         |
|  +---------------------------------------------------------------------------------------------+  |
|  |                      GEMINI ENTERPRISE AUTONOMOUS SRE INCIDENT COMMANDER                    |  |
|  |                        (Powered by Google ADK / Gemini 3.6 Flash)                           |  |
|  |                                                                                             |  |
|  |  Step 1: Polls / Receives Alert -> Calls `grafana_query_metrics` (PromQL)                   |  |
|  |  Step 2: Deep Dives into Loki -> Calls `grafana_search_logs` (Finds saturated transit ISP) |  |
|  |  Step 3: Documents Incident  -> Calls `grafana_create_annotation` & `grafana_create_incident`|
|  |  Step 4: Autonomous Healing   -> Calls Cloud Run Edge API to shift traffic to Akamai CDN    |  |
|  |  Step 5: Synthesizes Post-Mortem -> Generates executive root-cause report                   |  |
|  +---------------------------------------------------------------------------------------------+  |
|                                 |                                                                 |
|                                 v (Immediate Stream Recovery)                                     |
|  [CONTINUITY COMMAND CENTER WEB APP (Hosted on Cloudflare / Cloud Run)]                           |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Core Telemetry & Prometheus Metric Specifications

All metric collection conforms to the OpenMetrics / Prometheus standard via a dedicated `CollectorRegistry`:

| Metric Name | Type | Labels | Description / SLA Range |
| :--- | :--- | :--- | :--- |
| `ott_video_playback_failures_ratio` | Gauge | `stream_title`, `region` | Ratio of playback requests resulting in stall or failure. Nominal: `< 0.005` (0.5%), Outage: `0.048` (4.8%). |
| `ott_cdn_egress_latency_ms` | Gauge | `stream_title`, `cdn_provider`, `region` | Edge CDN segment download latency in milliseconds. Nominal: `35 - 55ms`, Outage: `350 - 450ms`. |
| `ott_drm_handshake_ms` | Gauge | `stream_title`, `drm_system` | Widevine / FairPlay license acquisition time. Nominal: `100 - 140ms`, Outage: `2200 - 2600ms`. |
| `ott_active_viewers_count` | Gauge | `stream_title` | Active concurrent video sessions (~4.28M viewers). |
| `ott_buffer_health_seconds` | Gauge | `stream_title` | Forward playback buffer size in seconds. Nominal: `25 - 30s`, Outage: `< 4.0s`. |
| `ott_stream_bitrate_mbps` | Gauge | `stream_title`, `resolution` | Average stream throughput in Mbps (14.8 Mbps for 4K UHD). |
| `ott_cdn_traffic_split_percentage` | Gauge | `cdn_provider` | Percentage allocation of egress bandwidth (Fastly vs Akamai). |
| `ott_incident_active_status` | Gauge | `chaos_mode`, `incident_id` | Binary flag indicating active incident state (0 = normal, 1 = outage). |

---

## 3. Grafana Cloud Integration Architecture

* **Prometheus Proxy Endpoint:** `/api/datasources/proxy/uid/{GRAFANA_PROM_UID}/api/v1/query`
* **Loki Query Range Endpoint:** `/api/datasources/proxy/uid/{GRAFANA_LOKI_UID}/loki/api/v1/query_range`
* **Annotations Ingestion:** `/api/annotations`
* **Resilience Layer:** All Grafana Cloud outbound requests pass through an exponential backoff retry handler with connection pooling (`httpx.AsyncClient`) to guarantee fault-tolerant delivery.

---

## 4. Multi-Step Autonomous Reasoning Loop

```
+---------------------------------------------------------------------------------------------------+
|                                 GEMINI AUTONOMOUS SRE REASONING ENGINE                            |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [STAGE 1: ANOMALY DETECTION]                                                                     |
|  Checks: VPF > 1.0% | Latency > 200ms | DRM > 500ms | Buffer < 8s                                 |
|                                                                                                   |
|  [STAGE 2: MULTI-MODAL LOG & METRIC CORRELATION]                                                  |
|  Gemini evaluates Prometheus vectors and Loki error strings to isolate root cause.                 |
|                                                                                                   |
|  [STAGE 3: ACTION SELECTION & EXECUTION]                                                          |
|  Autonomous action selected from:                                                                 |
|  - `SHIFT_TRAFFIC_TO_AKAMAI` (Reallocates 80% egress to secondary CDN)                             |
|  - `FAILOVER_DRM_KEY_CLUSTER` (Spins backup license authentication pool)                          |
|  - `REROUTE_BGP_TRANSIT` (Bypasses congested Tier-1 transit ASN)                                  |
|                                                                                                   |
|  [STAGE 4: DASHBOARD ANNOTATION]                                                                  |
|  Creates visible vertical timestamp on live Grafana Cloud dashboard with diagnosis metadata.      |
|                                                                                                   |
|  [STAGE 5: POST-MORTEM & SLA RESTORATION REPORTING]                                               |
|  Verifies MTTR and recovery: VPF restabilized to 0.21% (< 0.50% SLA), buffer restored to 27.9s.     |
+---------------------------------------------------------------------------------------------------+
```

---

## 5. Concurrency & Reliability Guarantees

* **Thread Safety:** Chaos state mutations are protected by re-entrant mutexes (`threading.RLock`), preventing race conditions across concurrent HTTP requests.
* **Non-blocking Execution:** Gemini generation and Grafana Cloud network requests run asynchronously in managed worker thread pools with strict 4-second timeout guards.
* **Serverless Scale-to-Zero:** Designed for Google Cloud Run deployment, incurring zero idle compute costs when traffic is quiescent.
