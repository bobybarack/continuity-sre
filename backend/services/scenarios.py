from typing import Dict, Any, List
from services.chaos import FailureMode

SCENARIO_ACTIONS: Dict[str, FailureMode] = {
    "SHIFT_TRAFFIC_TO_AKAMAI": FailureMode.CDN_OUTAGE,
    "FAILOVER_DRM_KEY_CLUSTER": FailureMode.DRM_TIMEOUT,
    "REROUTE_BGP_TRANSIT": FailureMode.ISP_PEERING_DROP,
}

SCENARIOS: Dict[str, Dict[str, Any]] = {
    FailureMode.CDN_OUTAGE.value: {
        "failure_mode": FailureMode.CDN_OUTAGE,
        "default_action": "SHIFT_TRAFFIC_TO_AKAMAI",
        "valid_actions": ["SHIFT_TRAFFIC_TO_AKAMAI"],
        "promql": "ott_video_playback_failures_ratio",
        "logql": '{service="ott-edge-router"} |= "502 Bad Gateway"',
        "affected_subsystems": ["Edge CDN", "Transit"],
        "initial_vpf": 4.85,
        "initial_latency_ms": 412.0,
        "initial_buffer_sec": 3.4,
    },
    FailureMode.DRM_TIMEOUT.value: {
        "failure_mode": FailureMode.DRM_TIMEOUT,
        "default_action": "FAILOVER_DRM_KEY_CLUSTER",
        "valid_actions": ["FAILOVER_DRM_KEY_CLUSTER"],
        "promql": "ott_drm_handshake_ms",
        "logql": '{service="drm-auth-proxy"} |= "504 Gateway Timeout"',
        "affected_subsystems": ["DRM Auth Proxy", "DRM Key Cluster"],
        "initial_drm_handshake_ms": 2450.0,
        "initial_vpf": 3.20,
    },
    FailureMode.ISP_PEERING_DROP.value: {
        "failure_mode": FailureMode.ISP_PEERING_DROP,
        "default_action": "REROUTE_BGP_TRANSIT",
        "valid_actions": ["REROUTE_BGP_TRANSIT"],
        "promql": "ott_stream_bitrate_mbps",
        "logql": '{service="transit-monitor"} |= "ASN 3356"',
        "affected_subsystems": ["Transit", "ASN 3356"],
        "initial_bitrate_mbps": 3.2,
        "initial_vpf": 2.90,
    },
}
