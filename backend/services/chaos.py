from enum import Enum
import time
import threading
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class IncidentLifecycle(str, Enum):
    NORMAL = "NORMAL"
    INCIDENT_ACTIVE = "INCIDENT_ACTIVE"
    REMEDIATION_APPLIED = "REMEDIATION_APPLIED"
    RECOVERING = "RECOVERING"
    VERIFIED_RECOVERED = "VERIFIED_RECOVERED"
    ESCALATED = "ESCALATED"

class FailureMode(str, Enum):
    NONE = "NONE"
    CDN_OUTAGE = "CDN_OUTAGE"
    DRM_TIMEOUT = "DRM_TIMEOUT"
    ISP_PEERING_DROP = "ISP_PEERING_DROP"

class ChaosEvent(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    event_type: str
    description: str
    severity: str # "INFO", "WARNING", "CRITICAL", "RESOLVED"
    details: Dict[str, Any] = Field(default_factory=dict)

class ChaosState(BaseModel):
    failure_mode: FailureMode = FailureMode.NONE
    lifecycle: IncidentLifecycle = IncidentLifecycle.NORMAL
    current_mode: str = "NORMAL" # Kept for API and telemetry backwards compatibility
    is_outage_active: bool = False
    active_incident_id: Optional[str] = None
    affected_region: str = "us-east-2"
    primary_cdn: str = "Fastly Edge POP"
    secondary_cdn: str = "Akamai Cloud CDN"
    primary_cdn_traffic_pct: int = 100
    secondary_cdn_traffic_pct: int = 0
    edge_route_status: str = "OPTIMAL" # "OPTIMAL", "FAILING", "REROUTED"
    primary_drm_cluster: str = "drm-key-cluster-primary"
    secondary_drm_cluster: str = "drm-key-cluster-failover"
    active_drm_cluster: str = "drm-key-cluster-primary"
    primary_drm_cluster_status: str = "HEALTHY" # "HEALTHY", "FAILED"
    secondary_drm_cluster_status: str = "STANDBY" # "STANDBY", "ACTIVE"
    primary_transit_route: str = "ASN-3356-Direct"
    secondary_transit_route: str = "ASN-2914-Backup"
    active_transit_route: str = "ASN-3356-Direct"
    primary_transit_status: str = "HEALTHY" # "HEALTHY", "CONGESTED", "BYPASSED"
    secondary_transit_status: str = "STANDBY" # "STANDBY", "ACTIVE"
    packet_loss_pct: float = 0.0
    force_recovery_failure: bool = False
    convergence_duration_sec: float = 1.5
    injected_at: Optional[float] = None
    remediation_action: Optional[str] = None
    remediation_action_applied: Optional[str] = None
    remediation_applied_at: Optional[float] = None
    remediated_at: Optional[float] = None
    verified_recovered_at: Optional[float] = None
    recent_events: List[ChaosEvent] = Field(default_factory=list)

class ChaosStateManager:
    def __init__(self):
        self._lock = threading.RLock()
        self.state = ChaosState()
        self._record_event("SYSTEM_START", "Continuity telemetry engine initialized in NORMAL state", "INFO")

    def set_force_recovery_failure(self, force_failure: bool = True) -> None:
        """Sets flag to simulate failed or incomplete remediation convergence (Thread-Safe)."""
        with self._lock:
            self.state.force_recovery_failure = force_failure

    def _record_event(self, event_type: str, description: str, severity: str, details: Optional[Dict[str, Any]] = None):
        event = ChaosEvent(
            timestamp=time.time(),
            event_type=event_type,
            description=description,
            severity=severity,
            details=details or {}
        )
        self.state.recent_events.insert(0, event)
        if len(self.state.recent_events) > 50:
            self.state.recent_events.pop()

    def get_state(self) -> ChaosState:
        with self._lock:
            return self.state.model_copy(deep=True)

    def inject_cdn_outage(self) -> ChaosState:
        """Simulates primary edge CDN transit link collapse at US-East (Thread-Safe)."""
        with self._lock:
            self.state.failure_mode = FailureMode.CDN_OUTAGE
            self.state.lifecycle = IncidentLifecycle.INCIDENT_ACTIVE
            self.state.current_mode = "CDN_OUTAGE"
            self.state.is_outage_active = True
            self.state.injected_at = time.time()
            self.state.remediated_at = None
            self.state.remediation_applied_at = None
            self.state.remediation_action = None
            self.state.remediation_action_applied = None
            self.state.verified_recovered_at = None
            self.state.active_incident_id = f"INC-CDN-{int(time.time())}"
            self.state.primary_cdn_traffic_pct = 100
            self.state.secondary_cdn_traffic_pct = 0
            self.state.edge_route_status = "FAILING"
            
            self._record_event(
                "CHAOS_INJECT_CDN_OUTAGE",
                "Simulated transit link collapse on Primary Fastly Edge POP (us-east-2). 502 Bad Gateway storm initiated.",
                "CRITICAL",
                {"target_cdn": "Fastly", "region": "us-east-2", "expected_vpf": "4.85%"}
            )
            return self.state.model_copy(deep=True)

    def inject_drm_timeout(self) -> ChaosState:
        """Simulates DRM licensing token key server timeout (Thread-Safe)."""
        with self._lock:
            self.state.failure_mode = FailureMode.DRM_TIMEOUT
            self.state.lifecycle = IncidentLifecycle.INCIDENT_ACTIVE
            self.state.current_mode = "DRM_TIMEOUT"
            self.state.is_outage_active = True
            self.state.injected_at = time.time()
            self.state.remediated_at = None
            self.state.remediation_applied_at = None
            self.state.remediation_action = None
            self.state.remediation_action_applied = None
            self.state.verified_recovered_at = None
            self.state.active_incident_id = f"INC-DRM-{int(time.time())}"
            self.state.primary_drm_cluster_status = "FAILED"
            self.state.secondary_drm_cluster_status = "STANDBY"
            self.state.active_drm_cluster = self.state.primary_drm_cluster
            
            self._record_event(
                "CHAOS_INJECT_DRM_TIMEOUT",
                "Widevine/FairPlay key server token handshake latency exceeded 2000ms. License acquire errors spiking.",
                "CRITICAL",
                {"service": "drm-auth-proxy", "expected_latency": "2450ms"}
            )
            return self.state.model_copy(deep=True)

    def inject_isp_peering_drop(self) -> ChaosState:
        """Simulates major Tier-1 ISP peering congestion (Thread-Safe)."""
        with self._lock:
            self.state.failure_mode = FailureMode.ISP_PEERING_DROP
            self.state.lifecycle = IncidentLifecycle.INCIDENT_ACTIVE
            self.state.current_mode = "ISP_PEERING_DROP"
            self.state.is_outage_active = True
            self.state.injected_at = time.time()
            self.state.remediated_at = None
            self.state.remediation_applied_at = None
            self.state.remediation_action = None
            self.state.remediation_action_applied = None
            self.state.verified_recovered_at = None
            self.state.active_incident_id = f"INC-ISP-{int(time.time())}"
            self.state.primary_transit_status = "CONGESTED"
            self.state.secondary_transit_status = "STANDBY"
            self.state.active_transit_route = self.state.primary_transit_route
            self.state.packet_loss_pct = 18.4
            
            self._record_event(
                "CHAOS_INJECT_ISP_DROP",
                "Tier-1 transit peering packet loss detected on ASN 3356. Bitrate degraded to 3.2 Mbps.",
                "WARNING",
                {"asn": "3356", "affected_routes": "US-East / Midwest"}
            )
            return self.state.model_copy(deep=True)

    def apply_autonomous_remediation(
        self,
        action: str = "SHIFT_TRAFFIC_TO_AKAMAI",
        primary_cdn_pct: Optional[int] = None,
        secondary_cdn_pct: Optional[int] = None
    ) -> ChaosState:
        """Applies scenario-specific traffic rerouting or cluster failover to initiate recovery (Thread-Safe)."""
        from services.scenarios import SCENARIO_ACTIONS
        
        with self._lock:
            if action not in SCENARIO_ACTIONS:
                raise ValueError(f"Unknown remediation action: {action}")
                
            expected_failure_mode = SCENARIO_ACTIONS[action]
            if self.state.failure_mode != FailureMode.NONE and self.state.failure_mode != expected_failure_mode:
                raise ValueError(
                    f"Action '{action}' is invalid for active failure mode '{self.state.failure_mode.value}'"
                )

            self.state.lifecycle = IncidentLifecycle.RECOVERING
            self.state.is_outage_active = True
            now = time.time()
            self.state.remediation_applied_at = now
            self.state.remediated_at = now
            self.state.remediation_action = action
            self.state.remediation_action_applied = action
            self.state.current_mode = "RECOVERING"
            
            event_details = {"action": action}
            if action == "SHIFT_TRAFFIC_TO_AKAMAI":
                p_pct = 20 if primary_cdn_pct is None else primary_cdn_pct
                s_pct = 80 if secondary_cdn_pct is None else secondary_cdn_pct
                self.state.primary_cdn_traffic_pct = p_pct
                self.state.secondary_cdn_traffic_pct = s_pct
                self.state.edge_route_status = "REROUTED"
                event_details.update({"primary_traffic": f"{p_pct}%", "secondary_traffic": f"{s_pct}%"})
            elif action == "FAILOVER_DRM_KEY_CLUSTER":
                self.state.active_drm_cluster = self.state.secondary_drm_cluster
                self.state.secondary_drm_cluster_status = "ACTIVE"
                self.state.primary_drm_cluster_status = "FAILED"
                event_details.update({"active_drm_cluster": self.state.active_drm_cluster})
            elif action == "REROUTE_BGP_TRANSIT":
                self.state.active_transit_route = self.state.secondary_transit_route
                self.state.secondary_transit_status = "ACTIVE"
                self.state.primary_transit_status = "BYPASSED"
                self.state.packet_loss_pct = 0.2
                event_details.update({"active_transit_route": self.state.active_transit_route})

            self._record_event(
                "AGENT_REMEDIATION_APPLIED",
                f"Autonomous SRE Agent executed failover: {action}. Subsystem state modified; entering RECOVERING lifecycle.",
                "INFO",
                event_details
            )
            return self.state.model_copy(deep=True)

    def mark_verified_recovered(self, verification_evidence: Optional[Dict[str, Any]] = None) -> ChaosState:
        """Transitions state to VERIFIED_RECOVERED only after closed-loop verification passes (Thread-Safe)."""
        with self._lock:
            self.state.lifecycle = IncidentLifecycle.VERIFIED_RECOVERED
            self.state.is_outage_active = False
            self.state.verified_recovered_at = time.time()
            self.state.current_mode = "REMEDIATED"
            
            self._record_event(
                "CLOSED_LOOP_RECOVERY_VERIFIED",
                "Closed-loop telemetry verification passed. Incident confirmed resolved.",
                "RESOLVED",
                verification_evidence or {}
            )
            return self.state.model_copy(deep=True)

    def mark_recovery_failed(self, reason: str, details: Optional[Dict[str, Any]] = None) -> ChaosState:
        """Transitions state to ESCALATED when verification gate fails or times out (Thread-Safe)."""
        with self._lock:
            self.state.lifecycle = IncidentLifecycle.ESCALATED
            self.state.is_outage_active = True
            
            self._record_event(
                "RECOVERY_VERIFICATION_FAILED",
                f"Recovery verification failed: {reason}. Incident remains active and escalated.",
                "CRITICAL",
                details or {}
            )
            return self.state.model_copy(deep=True)

    def reset_to_normal(self) -> ChaosState:
        """Restores healthy baseline operation (Thread-Safe)."""
        with self._lock:
            self.state.failure_mode = FailureMode.NONE
            self.state.lifecycle = IncidentLifecycle.NORMAL
            self.state.current_mode = "NORMAL"
            self.state.is_outage_active = False
            self.state.active_incident_id = None
            self.state.injected_at = None
            self.state.remediated_at = None
            self.state.remediation_applied_at = None
            self.state.remediation_action = None
            self.state.remediation_action_applied = None
            self.state.verified_recovered_at = None
            self.state.primary_cdn_traffic_pct = 100
            self.state.secondary_cdn_traffic_pct = 0
            self.state.edge_route_status = "OPTIMAL"
            self.state.active_drm_cluster = self.state.primary_drm_cluster
            self.state.primary_drm_cluster_status = "HEALTHY"
            self.state.secondary_drm_cluster_status = "STANDBY"
            self.state.active_transit_route = self.state.primary_transit_route
            self.state.primary_transit_status = "HEALTHY"
            self.state.secondary_transit_status = "STANDBY"
            self.state.packet_loss_pct = 0.0
            self.state.force_recovery_failure = False
            self.state.convergence_duration_sec = 1.5
            
            self._record_event(
                "CHAOS_RESET",
                "Telemetry reset to baseline normal state. All systems operational.",
                "INFO"
            )
            return self.state.model_copy(deep=True)

# Global singleton instance
chaos_manager = ChaosStateManager()
