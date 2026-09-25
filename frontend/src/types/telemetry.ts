export interface TelemetrySnapshot {
  timestamp: number;
  stream_title: string;
  chaos_mode: string;
  is_outage: boolean;
  video_playback_failures_pct: number;
  cdn_egress_latency_ms: number;
  drm_handshake_ms: number;
  active_viewers: number;
  buffer_health_sec: number;
  avg_bitrate_mbps: number;
  primary_cdn: string;
  primary_traffic_pct: number;
  secondary_cdn: string;
  secondary_traffic_pct: number;
  status_label: "HEALTHY" | "DEGRADED" | "CRITICAL_OUTAGE" | "RECOVERED" | string;
  status_color: "green" | "yellow" | "red" | "blue" | string;
  latest_log: string;
}

export interface InvestigationResult {
  timestamp: number;
  incident_id?: string | null;
  failure_mode?: string | null;
  stream_title: string;
  initial_anomaly_detected: boolean;
  vpf_rate: number;
  cdn_latency_ms: number;
  drm_handshake_ms: number;
  severity: "CRITICAL" | "WARNING" | "HEALTHY" | string;
  root_cause_analysis: string;
  affected_subsystems: string[];
  autonomous_action_taken?: string | null;
  remediation_action?: string | null;
  remediation_status?: string | null;
  workflow_status?: string;
  traffic_shift_details: {
    primary_cdn?: string;
    primary_cdn_pct?: number;
    secondary_cdn?: string;
    secondary_cdn_pct?: number;
    [key: string]: unknown;
  };
  annotation_id?: number | null;
  grafana_incident_id?: string | null;
  workflow_elapsed_seconds?: number;
  mttr_seconds?: number | null;
  estimated_subscriber_loss_prevented: string;
  executive_summary: string;
  reasoning_trace: string[];
  mcp_tools_executed?: string[];
  closed_loop_verified?: boolean;
  verified_vpf_rate?: number;
  verified_buffer_health_sec?: number;
  verified_latency_ms?: number | null;
  verification_status?: string;
  verification_source?: string | null;
  verification_authoritative?: boolean;
  remediation_transaction_id?: string | null;
  idempotency_key?: string | null;
  rollback_action?: string | null;
  rollback_status?: string | null;
  recovery_proof?: Record<string, unknown> | null;
  escalation_package?: Record<string, unknown> | null;
}

export interface GrafanaHealth {
  connected: boolean;
  instance_url: string;
  prometheus: {
    status: string;
    latency_ms: number;
    datasource: string;
  };
  loki: {
    status: string;
    latency_ms: number;
    datasource: string;
  };
  annotations_enabled: boolean;
}

export interface ChaosState {
  current_mode: string;
  is_outage_active: boolean;
  affected_region: string;
  primary_cdn: string;
  primary_cdn_traffic_pct: number;
  secondary_cdn: string;
  secondary_cdn_traffic_pct: number;
  active_incident_id?: string | null;
  incident_start_time?: number | null;
}
