import time
import random
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from services.chaos import chaos_manager, ChaosStateManager
from config import (
    STREAM_TITLE,
    TOTAL_ACTIVE_VIEWERS_BASE,
    TARGET_BITRATE_MBPS,
    TARGET_BUFFER_HEALTH_SEC
)

# Custom Prometheus Registry for Clean Isolation
PREMIERE_REGISTRY = CollectorRegistry(auto_describe=True)

# Prometheus Metrics Definitions
PROM_VPF_RATIO = Gauge(
    "ott_video_playback_failures_ratio",
    "Current ratio of video playback failures (VPF)",
    ["stream_title", "region"],
    registry=PREMIERE_REGISTRY
)

PROM_CDN_LATENCY = Gauge(
    "ott_cdn_egress_latency_ms",
    "Current CDN egress response latency in milliseconds",
    ["stream_title", "cdn_provider", "region"],
    registry=PREMIERE_REGISTRY
)

PROM_DRM_HANDSHAKE = Gauge(
    "ott_drm_handshake_ms",
    "DRM license acquisition and handshake duration in milliseconds",
    ["stream_title", "drm_system"],
    registry=PREMIERE_REGISTRY
)

PROM_ACTIVE_VIEWERS = Gauge(
    "ott_active_viewers_count",
    "Total concurrent active streaming viewers",
    ["stream_title"],
    registry=PREMIERE_REGISTRY
)

PROM_BUFFER_HEALTH = Gauge(
    "ott_buffer_health_seconds",
    "Forward playback buffer health in seconds",
    ["stream_title"],
    registry=PREMIERE_REGISTRY
)

PROM_BITRATE = Gauge(
    "ott_stream_bitrate_mbps",
    "Average delivered video stream bitrate in Mbps",
    ["stream_title", "resolution"],
    registry=PREMIERE_REGISTRY
)

PROM_CDN_SPLIT = Gauge(
    "ott_cdn_traffic_split_percentage",
    "Percentage of streaming traffic routed to CDN provider",
    ["cdn_provider"],
    registry=PREMIERE_REGISTRY
)

PROM_OUTAGE_STATUS = Gauge(
    "ott_incident_active_status",
    "Binary indicator (1=outage active, 0=healthy)",
    ["chaos_mode", "region"],
    registry=PREMIERE_REGISTRY
)

class TelemetrySnapshot(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    stream_title: str = STREAM_TITLE
    chaos_mode: str
    is_outage: bool
    
    # Core Observability Metrics
    video_playback_failures_pct: float
    cdn_egress_latency_ms: float
    drm_handshake_ms: float
    active_viewers: int
    buffer_health_sec: float
    avg_bitrate_mbps: float
    
    # CDN Traffic Distribution
    primary_cdn: str
    primary_traffic_pct: int
    secondary_cdn: str
    secondary_traffic_pct: int
    
    # Active Health Status
    status_label: str # "HEALTHY", "DEGRADED", "CRITICAL_OUTAGE", "RECOVERED"
    status_color: str # "green", "yellow", "red", "blue"
    latest_log: str

import asyncio
import threading

class TelemetryEngine:
    def __init__(self, rng: Optional[random.Random] = None, chaos_mgr: Optional[ChaosStateManager] = None, tick_interval_sec: float = 1.0):
        self._lock = threading.RLock()
        self.rng = rng or random.Random()
        self._chaos_manager = chaos_mgr
        self.history: List[TelemetrySnapshot] = []
        self.max_history_len = 60
        self.current_snapshot: Optional[TelemetrySnapshot] = None
        self._ticker_task: Optional[asyncio.Task] = None
        self._is_running = False
        self.tick_interval_sec = tick_interval_sec
        # Initialize an initial canonical snapshot immediately
        self._tick()

    def _tick(self) -> TelemetrySnapshot:
        """Executes a single canonical 1 Hz telemetry tick, updates Prometheus gauges, and appends to history."""
        with self._lock:
            mgr = self._chaos_manager or chaos_manager
            state = mgr.get_state()
            now = time.time()
            
            # Base jitter calculations
            viewer_jitter = self.rng.randint(-4500, 4500)
            viewers = max(100_000, TOTAL_ACTIVE_VIEWERS_BASE + viewer_jitter)
            
            mode = state.current_mode
            region = state.affected_region
            
            if mode == "NORMAL":
                vpf = round(max(0.05, 0.18 + self.rng.uniform(-0.04, 0.04)), 2)
                latency = round(max(30.0, 48.0 + self.rng.uniform(-5.0, 6.0)), 1)
                drm = round(max(80.0, 120.0 + self.rng.uniform(-15.0, 15.0)), 1)
                buffer_sec = round(max(20.0, TARGET_BUFFER_HEALTH_SEC + self.rng.uniform(-1.5, 1.5)), 1)
                bitrate = round(max(12.0, TARGET_BITRATE_MBPS + self.rng.uniform(-0.4, 0.4)), 1)
                status_label = "HEALTHY"
                status_color = "green"
                latest_log = f"[Fastly Edge POP {region}] 200 OK - Chunk #89204 segment.ts - {latency}ms"
                
            elif mode == "CDN_OUTAGE":
                vpf = round(4.85 + self.rng.uniform(-0.25, 0.35), 2)
                latency = round(412.0 + self.rng.uniform(-30.0, 45.0), 1)
                drm = round(135.0 + self.rng.uniform(-10.0, 15.0), 1)
                buffer_sec = round(max(0.8, 3.4 + self.rng.uniform(-0.8, 0.8)), 1)
                bitrate = round(max(1.5, 3.8 + self.rng.uniform(-0.6, 0.6)), 1)
                status_label = "CRITICAL_OUTAGE"
                status_color = "red"
                latest_log = f"[Fastly Edge POP {region}] 502 Bad Gateway - upstream transit link connection refused (loss: 68%)"
                
            elif mode == "DRM_TIMEOUT":
                vpf = round(3.20 + self.rng.uniform(-0.20, 0.20), 2)
                latency = round(65.0 + self.rng.uniform(-8.0, 10.0), 1)
                drm = round(2450.0 + self.rng.uniform(-150.0, 220.0), 1)
                buffer_sec = round(max(1.2, 5.2 + self.rng.uniform(-1.0, 1.0)), 1)
                bitrate = round(14.2 + self.rng.uniform(-0.5, 0.5), 1)
                status_label = "CRITICAL_OUTAGE"
                status_color = "red"
                latest_log = f"[DRM Auth Proxy] 504 Gateway Timeout - Widevine key license request timed out after {drm}ms"
                
            elif mode == "ISP_PEERING_DROP":
                vpf = round(2.90 + self.rng.uniform(-0.15, 0.25), 2)
                latency = round(180.0 + self.rng.uniform(-20.0, 25.0), 1)
                drm = round(140.0 + self.rng.uniform(-10.0, 10.0), 1)
                buffer_sec = round(max(2.0, 8.5 + self.rng.uniform(-1.2, 1.2)), 1)
                bitrate = round(max(2.0, 3.2 + self.rng.uniform(-0.4, 0.4)), 1)
                status_label = "DEGRADED"
                status_color = "yellow"
                latest_log = f"[ASN 3356 Transit] Packet loss rate 18.4% on link NYC-CHI - player downshifting resolution to 720p"
                
            elif mode in ["REMEDIATED", "RECOVERING"]:
                remediation_time = state.remediation_applied_at or now
                elapsed = max(0.0, now - remediation_time)
                conv_sec = getattr(state, "convergence_duration_sec", 1.5)
                
                if getattr(state, "force_recovery_failure", False):
                    # Stalls convergence at 40% progress - metrics never cross healthy SLA thresholds
                    progress = min(0.4, (elapsed / max(0.1, conv_sec)) * 0.4)
                elif mode == "REMEDIATED" or state.lifecycle == "VERIFIED_RECOVERED":
                    progress = 1.0
                else:
                    progress = min(1.0, elapsed / max(0.1, conv_sec))

                if state.failure_mode == "DRM_TIMEOUT":
                    drm = round(2450.0 - progress * (2450.0 - 95.0) + self.rng.uniform(-10.0, 10.0), 1)
                    vpf = round(3.20 - progress * (3.20 - 0.18) + self.rng.uniform(-0.03, 0.03), 2)
                    latency = round(65.0 - progress * (65.0 - 45.0) + self.rng.uniform(-3.0, 3.0), 1)
                    buffer_sec = round(5.2 + progress * (26.0 - 5.2) + self.rng.uniform(-0.5, 0.5), 1)
                    bitrate = round(14.2 + progress * (14.7 - 14.2) + self.rng.uniform(-0.2, 0.2), 1)
                    latest_log = f"[DRM Key Proxy] 200 OK - FairPlay/Widevine key license acquisition verified via {state.active_drm_cluster}"
                elif state.failure_mode == "ISP_PEERING_DROP":
                    bitrate = round(3.2 + progress * (14.5 - 3.2) + self.rng.uniform(-0.2, 0.2), 1)
                    vpf = round(2.90 - progress * (2.90 - 0.17) + self.rng.uniform(-0.03, 0.03), 2)
                    latency = round(180.0 - progress * (180.0 - 45.0) + self.rng.uniform(-5.0, 5.0), 1)
                    drm = round(140.0 - progress * (140.0 - 110.0) + self.rng.uniform(-5.0, 5.0), 1)
                    buffer_sec = round(8.5 + progress * (27.0 - 8.5) + self.rng.uniform(-0.5, 0.5), 1)
                    latest_log = f"[Transit Reroute] 200 OK - Egress rerouted via {state.active_transit_route} - packet loss: {state.packet_loss_pct}%"
                else:
                    vpf = round(4.85 - progress * (4.85 - 0.19) + self.rng.uniform(-0.04, 0.04), 2)
                    latency = round(412.0 - progress * (412.0 - 46.5) + self.rng.uniform(-5.0, 5.0), 1)
                    drm = round(135.0 - progress * (135.0 - 105.0) + self.rng.uniform(-5.0, 5.0), 1)
                    buffer_sec = round(3.4 + progress * (27.8 - 3.4) + self.rng.uniform(-0.5, 0.5), 1)
                    bitrate = round(3.8 + progress * (14.7 - 3.8) + self.rng.uniform(-0.2, 0.2), 1)
                    latest_log = f"[Akamai Cloud CDN {region}] 200 OK - Failover healthy - Active egress: {state.secondary_cdn_traffic_pct}%"

                if progress >= 1.0:
                    status_label = "RECOVERED"
                    status_color = "blue"
                else:
                    status_label = "RECOVERING"
                    status_color = "yellow"
                
            else:
                vpf, latency, drm, buffer_sec, bitrate = 0.2, 50.0, 120.0, 28.0, 14.8
                status_label = "HEALTHY"
                status_color = "green"
                latest_log = "System normal"

            # Update Prometheus Real Gauges
            PROM_VPF_RATIO.labels(stream_title=STREAM_TITLE, region=region).set(vpf / 100.0)
            PROM_CDN_LATENCY.labels(stream_title=STREAM_TITLE, cdn_provider=state.primary_cdn, region=region).set(latency)
            PROM_DRM_HANDSHAKE.labels(stream_title=STREAM_TITLE, drm_system="Widevine Modular").set(drm)
            PROM_ACTIVE_VIEWERS.labels(stream_title=STREAM_TITLE).set(viewers)
            PROM_BUFFER_HEALTH.labels(stream_title=STREAM_TITLE).set(buffer_sec)
            PROM_BITRATE.labels(stream_title=STREAM_TITLE, resolution="4K UHD").set(bitrate)
            PROM_CDN_SPLIT.labels(cdn_provider="Fastly").set(state.primary_cdn_traffic_pct)
            PROM_CDN_SPLIT.labels(cdn_provider="Akamai").set(state.secondary_cdn_traffic_pct)
            PROM_OUTAGE_STATUS.labels(chaos_mode=mode, region=state.affected_region).set(1.0 if state.is_outage_active else 0.0)

            snapshot = TelemetrySnapshot(
                timestamp=now,
                stream_title=STREAM_TITLE,
                chaos_mode=mode,
                is_outage=state.is_outage_active,
                video_playback_failures_pct=vpf,
                cdn_egress_latency_ms=latency,
                drm_handshake_ms=drm,
                active_viewers=viewers,
                buffer_health_sec=buffer_sec,
                avg_bitrate_mbps=bitrate,
                primary_cdn=state.primary_cdn,
                primary_traffic_pct=state.primary_cdn_traffic_pct,
                secondary_cdn=state.secondary_cdn,
                secondary_traffic_pct=state.secondary_cdn_traffic_pct,
                status_label=status_label,
                status_color=status_color,
                latest_log=latest_log
            )
            
            self.current_snapshot = snapshot
            self.history.append(snapshot)
            if len(self.history) > self.max_history_len:
                self.history.pop(0)
                
            return snapshot

    def get_current_snapshot(self) -> TelemetrySnapshot:
        """Returns the canonical current snapshot without side effects or mutation."""
        with self._lock:
            if self.current_snapshot is None:
                self._tick()
            return self.current_snapshot

    def generate_current_snapshot(self) -> TelemetrySnapshot:
        """Explicitly generates a fresh sample (backwards compatibility for tests)."""
        return self._tick()

    def get_history(self) -> List[TelemetrySnapshot]:
        with self._lock:
            return list(self.history)

    def get_prometheus_exposition(self) -> bytes:
        """Returns the current metric snapshot formatted as Prometheus exposition text without side effects."""
        return generate_latest(PREMIERE_REGISTRY)

    async def start(self):
        """Starts the background 1 Hz ticker loop if not already running."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
        self._ticker_task = asyncio.create_task(self._ticker_loop())

    async def stop(self):
        """Stops the background ticker loop cleanly."""
        with self._lock:
            self._is_running = False
        if self._ticker_task:
            self._ticker_task.cancel()
            try:
                await self._ticker_task
            except asyncio.CancelledError:
                pass
            self._ticker_task = None

    async def _ticker_loop(self):
        while self._is_running:
            try:
                await asyncio.sleep(self.tick_interval_sec)
                self._tick()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self.tick_interval_sec)

# Global telemetry engine singleton
telemetry_engine = TelemetryEngine()
