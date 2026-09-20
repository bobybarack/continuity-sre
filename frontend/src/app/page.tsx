"use client";

import React, { useState, useEffect, useCallback } from "react";
import { TopBar } from "../components/TopBar";
import { MetricCardsRow } from "../components/MetricCardsRow";
import { PlaybackChartCard } from "../components/PlaybackChartCard";
import { LivePlayerCard } from "../components/LivePlayerCard";
import { SreCommanderCard } from "../components/SreCommanderCard";
import { CdnSplitCard } from "../components/CdnSplitCard";
import { LiveLogsCard } from "../components/LiveLogsCard";
import { ChaosDock } from "../components/ChaosDock";
import { IncidentDrawer } from "../components/IncidentDrawer";
import { ApiService } from "../services/api";
import {
  TelemetrySnapshot,
  InvestigationResult,
  ChaosState,
} from "../types/telemetry";

export default function ContinuityDashboard() {
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot | null>(null);
  const [history, setHistory] = useState<TelemetrySnapshot[]>([]);
  const [chaosState, setChaosState] = useState<ChaosState | null>(null);
  const [investigations, setInvestigations] = useState<InvestigationResult[]>([]);
  const [isInvestigating, setIsInvestigating] = useState<boolean>(false);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [demoFixtureStage, setDemoFixtureStage] = useState<string | null>(null);

  // Initial Data Fetch & Demo Stage Handling
  const applyDemoStage = useCallback((stage: string) => {
    setDemoFixtureStage(stage);
    const baseSnap = (vpf: number, lat: number, mode: string, isOutage: boolean, buf: number, br: number, pPct: number, sPct: number, label: string, color: string, log: string): TelemetrySnapshot => ({
      timestamp: Date.now() / 1000,
      stream_title: "Spider-Man: Brand New Day (World Premiere 4K UHD)",
      chaos_mode: mode,
      is_outage: isOutage,
      video_playback_failures_pct: vpf,
      cdn_egress_latency_ms: lat,
      drm_handshake_ms: 115.0,
      active_viewers: 4281902,
      buffer_health_sec: buf,
      avg_bitrate_mbps: br,
      primary_cdn: "Fastly Edge POP",
      primary_traffic_pct: pPct,
      secondary_cdn: "Akamai Cloud CDN",
      secondary_traffic_pct: sPct,
      status_label: label,
      status_color: color,
      latest_log: log,
    });

    const sampleInvestigation: InvestigationResult = {
      timestamp: Date.now() / 1000 - 120,
      incident_id: "INC-89211",
      stream_title: "Spider-Man: Brand New Day (World Premiere 4K UHD)",
      initial_anomaly_detected: true,
      vpf_rate: 5.08,
      cdn_latency_ms: 840.0,
      drm_handshake_ms: 118.0,
      severity: "CRITICAL",
      root_cause_analysis:
        "Correlated Loki edge logs with Prometheus VPF surge (5.08% > 1.00% threshold). Automated traffic rebalance initiated: 80% shifted to secondary CDN.",
      affected_subsystems: ["Edge CDN POP", "Primary Transit Provider"],
      autonomous_action_taken: "SHIFT_TRAFFIC_TO_AKAMAI",
      remediation_action: "SHIFT_TRAFFIC_TO_AKAMAI",
      remediation_status: "APPLIED",
      workflow_status: "RESOLVED",
      traffic_shift_details: {
        primary_cdn: "Fastly Edge POP",
        primary_cdn_pct: 20,
        secondary_cdn: "Akamai Cloud CDN",
        secondary_cdn_pct: 80,
      },
      workflow_elapsed_seconds: 1.28,
      mttr_seconds: 1.28,
      estimated_subscriber_loss_prevented: "Simulated Model: Zero Impact",
      executive_summary: "Automated mitigation completed with verified recovery in 1.28s.",
      closed_loop_verified: true,
      verified_vpf_rate: 0.21,
      verified_buffer_health_sec: 27.9,
      verified_latency_ms: 46.0,
      verification_status: "PASSED",
      verification_source: "grafana_cloud_prometheus",
      verification_authoritative: true,
      mcp_tools_executed: [
        "continuity_query_prometheus",
        "continuity_query_loki",
        "continuity_execute_remediation",
        "continuity_verify_stream_recovery",
      ],
      reasoning_trace: [
        "Ingesting Prometheus ott_video_playback_failures_ratio metric (5.08%)",
        "Querying Grafana Loki {service=\"ott-edge-router\"} |= \"502 Bad Gateway\"",
        "Diagnosed edge POP degradation; selecting secondary CDN failover target",
        "Dispatching SHIFT_TRAFFIC_TO_AKAMAI",
        "Verifying downstream forward buffer and VPF recovery via Prometheus",
        "Closed-loop verification passed: VPF 0.21% (threshold < 1.00%)",
      ],
    };

    if (stage === "baseline") {
      const snap = baseSnap(0.15, 42.0, "NORMAL", false, 28.5, 14.8, 100, 0, "HEALTHY", "green", "[Fastly Edge POP iad-01] 200 OK - Chunk #89204 delivery nominal (42ms)");
      const hist: TelemetrySnapshot[] = [];
      for (let i = 0; i < 60; i++) {
        hist.push(baseSnap(0.14 + (Math.sin(i * 0.3) * 0.02), 42 + (i % 2), "NORMAL", false, 28.5, 14.8, 100, 0, "HEALTHY", "green", ""));
      }
      setTelemetry(snap);
      setHistory(hist);
      setChaosState({ current_mode: "NORMAL", is_outage_active: false, affected_region: "us-east-1", primary_cdn: "Fastly", primary_cdn_traffic_pct: 100, secondary_cdn: "Akamai", secondary_cdn_traffic_pct: 0 });
      setInvestigations([]);
      setIsDrawerOpen(false);
    } else if (stage === "outage") {
      const snap = baseSnap(5.08, 840.0, "CDN_OUTAGE", true, 2.9, 4.2, 100, 0, "CRITICAL_OUTAGE", "red", "[Fastly Edge POP iad-01] 502 BAD GATEWAY - Upstream packet drop 60% (ASN 3356)");
      const hist: TelemetrySnapshot[] = [];
      for (let i = 0; i < 45; i++) hist.push(baseSnap(0.15 + (Math.sin(i * 0.2) * 0.02), 43, "NORMAL", false, 28.5, 14.8, 100, 0, "HEALTHY", "green", ""));
      for (let i = 0; i < 15; i++) {
        const p = (i + 1) / 15;
        hist.push(baseSnap(0.15 + p * 4.93, 45 + p * 795, "CDN_OUTAGE", true, 28.5 - p * 25.6, 14.8 - p * 10.6, 100, 0, "CRITICAL_OUTAGE", "red", ""));
      }
      setTelemetry(snap);
      setHistory(hist);
      setChaosState({ current_mode: "CDN_OUTAGE", is_outage_active: true, affected_region: "us-east-1 (Fastly iad-01)", primary_cdn: "Fastly", primary_cdn_traffic_pct: 100, secondary_cdn: "Akamai", secondary_cdn_traffic_pct: 0 });
      setInvestigations([]);
      setIsDrawerOpen(false);
    } else if (stage === "gemini_modal") {
      const snap = baseSnap(5.08, 840.0, "CDN_OUTAGE", true, 2.9, 4.2, 100, 0, "CRITICAL_OUTAGE", "red", "[Fastly Edge POP iad-01] 502 BAD GATEWAY - Upstream packet drop 60% (ASN 3356)");
      const hist: TelemetrySnapshot[] = [];
      for (let i = 0; i < 45; i++) hist.push(baseSnap(0.15 + (Math.sin(i * 0.2) * 0.02), 43, "NORMAL", false, 28.5, 14.8, 100, 0, "HEALTHY", "green", ""));
      for (let i = 0; i < 15; i++) {
        const p = (i + 1) / 15;
        hist.push(baseSnap(0.15 + p * 4.93, 45 + p * 795, "CDN_OUTAGE", true, 28.5 - p * 25.6, 14.8 - p * 10.6, 100, 0, "CRITICAL_OUTAGE", "red", ""));
      }
      setTelemetry(snap);
      setHistory(hist);
      setChaosState({ current_mode: "CDN_OUTAGE", is_outage_active: true, affected_region: "us-east-1 (Fastly iad-01)", primary_cdn: "Fastly", primary_cdn_traffic_pct: 100, secondary_cdn: "Akamai", secondary_cdn_traffic_pct: 0 });
      setInvestigations([sampleInvestigation]);
      setIsDrawerOpen(true);
    } else if (stage === "recovered") {
      const snap = baseSnap(0.21, 46.0, "REMEDIATED", false, 27.9, 14.9, 20, 80, "RECOVERED", "blue", "[Akamai Cloud CDN us-east-2] 200 OK - Failover healthy - Active egress: 80%");
      const hist: TelemetrySnapshot[] = [];
      for (let i = 0; i < 30; i++) {
        const v = 5.08 - i * 0.16;
        hist.push(baseSnap(Math.max(0.21, v), 840 - i * 26, "REMEDIATED", false, 2.9 + i * 0.83, 4.2 + i * 0.35, 20, 80, "RECOVERED", "blue", ""));
      }
      for (let i = 0; i < 30; i++) {
        hist.push(baseSnap(0.21 + (Math.sin(i * 0.3) * 0.02), 46, "REMEDIATED", false, 27.9, 14.9, 20, 80, "RECOVERED", "blue", ""));
      }
      setTelemetry(snap);
      setHistory(hist);
      setChaosState({ current_mode: "REMEDIATED", is_outage_active: false, affected_region: "us-east-1", primary_cdn: "Fastly", primary_cdn_traffic_pct: 20, secondary_cdn: "Akamai", secondary_cdn_traffic_pct: 80 });
      setInvestigations([sampleInvestigation]);
      setIsDrawerOpen(false);
    } else if (stage === "pipeline") {
      const snap = baseSnap(0.17, 44.0, "NORMAL", false, 28.2, 15.1, 20, 80, "HEALTHY", "green", "[Global Ingest Pipeline] All stream shards nominal (4K 60fps HEVC)");
      const hist: TelemetrySnapshot[] = [];
      for (let i = 0; i < 20; i++) {
        const v = 4.2 - i * 0.2;
        hist.push(baseSnap(Math.max(0.18, v), 600 - i * 27, "NORMAL", false, 15 + i * 0.65, 10 + i * 0.25, 20, 80, "HEALTHY", "green", ""));
      }
      for (let i = 0; i < 40; i++) {
        hist.push(baseSnap(0.17 + (Math.sin(i * 0.25) * 0.02), 44, "NORMAL", false, 28.2, 15.1, 20, 80, "HEALTHY", "green", ""));
      }
      setTelemetry(snap);
      setHistory(hist);
      setChaosState({ current_mode: "NORMAL", is_outage_active: false, affected_region: "us-east-1", primary_cdn: "Fastly", primary_cdn_traffic_pct: 20, secondary_cdn: "Akamai", secondary_cdn_traffic_pct: 80 });
      setInvestigations([sampleInvestigation]);
      setIsDrawerOpen(false);
    }
  }, []);

  const reloadLiveState = useCallback(async () => {
    try {
      const [cur, hist, state, invHist] = await Promise.allSettled([
        ApiService.getCurrentTelemetry(),
        ApiService.getTelemetryHistory(),
        ApiService.getChaosState(),
        ApiService.getInvestigationHistory(),
      ]);

      if (cur.status === "fulfilled") setTelemetry(cur.value);
      if (hist.status === "fulfilled") setHistory(hist.value);
      if (state.status === "fulfilled") setChaosState(state.value);
      if (invHist.status === "fulfilled") setInvestigations(invHist.value);
    } catch (err) {
      console.warn("Live data load partial failure:", err);
    }
  }, []);

  // Expose demo switcher to global window
  useEffect(() => {
    if (typeof window !== "undefined") {
      (window as unknown as { __setDemoState: (s: string) => void }).__setDemoState = applyDemoStage;
      const params = new URLSearchParams(window.location.search);
      const stage = params.get("stage");
      if (stage) {
        queueMicrotask(() => {
          applyDemoStage(stage);
        });
      }
    }
  }, [applyDemoStage]);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      if (typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        if (params.get("stage")) return;
      }
      try {
        const [cur, hist, state, invHist] = await Promise.allSettled([
          ApiService.getCurrentTelemetry(),
          ApiService.getTelemetryHistory(),
          ApiService.getChaosState(),
          ApiService.getInvestigationHistory(),
        ]);
        if (!isMounted) return;
        if (cur.status === "fulfilled") setTelemetry(cur.value);
        if (hist.status === "fulfilled") setHistory(hist.value);
        if (state.status === "fulfilled") setChaosState(state.value);
        if (invHist.status === "fulfilled") setInvestigations(invHist.value);
      } catch (err) {
        console.warn("Initial data load partial failure:", err);
      }
    };
    void load();
    return () => {
      isMounted = false;
    };
  }, []);

  // Ensure window stays at top on initial link visit
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  // Connect 1Hz SSE Real-Time Stream with fallback polling (only if not in demo stage)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("stage")) return;
    }

    const unsub = ApiService.createTelemetryEventSource(
      (newSnapshot) => {
        setTelemetry(newSnapshot);
        setHistory((prev) => {
          const updated = [...prev, newSnapshot];
          if (updated.length > 60) updated.shift();
          return updated;
        });
      },
      () => {
        ApiService.getCurrentTelemetry()
          .then((snap) => {
            setTelemetry(snap);
            setHistory((prev) => [...prev.slice(-59), snap]);
          })
          .catch(() => {});
      }
    );

    return () => unsub();
  }, []);

  // Chaos Injection Handlers
  const handleInjectCdnOutage = async () => {
    setIsActionLoading(true);
    try {
      const state = await ApiService.injectCdnOutage();
      setChaosState(state);
      const snap = await ApiService.getCurrentTelemetry();
      setTelemetry(snap);
    } catch (err) {
      console.error("Failed to inject CDN outage:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleInjectDrmTimeout = async () => {
    setIsActionLoading(true);
    try {
      const state = await ApiService.injectDrmTimeout();
      setChaosState(state);
      const snap = await ApiService.getCurrentTelemetry();
      setTelemetry(snap);
    } catch (err) {
      console.error("Failed to inject DRM timeout:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleInjectIspDrop = async () => {
    setIsActionLoading(true);
    try {
      const state = await ApiService.injectIspDrop();
      setChaosState(state);
      const snap = await ApiService.getCurrentTelemetry();
      setTelemetry(snap);
    } catch (err) {
      console.error("Failed to inject ISP drop:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleTriggerAutonomousInvestigation = async () => {
    setIsInvestigating(true);
    try {
      const result = await ApiService.investigateAndRemediate();
      setInvestigations((prev) => [result, ...prev]);
      const [state, snap] = await Promise.all([
        ApiService.getChaosState(),
        ApiService.getCurrentTelemetry(),
      ]);
      setChaosState(state);
      setTelemetry(snap);
    } catch (err) {
      console.error("Autonomous SRE investigation failed:", err);
    } finally {
      setIsInvestigating(false);
    }
  };

  const handleResetChaos = async () => {
    setIsActionLoading(true);
    try {
      const state = await ApiService.resetChaos();
      setChaosState(state);
      const snap = await ApiService.getCurrentTelemetry();
      setTelemetry(snap);
    } catch (err) {
      console.error("Reset failed:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleExitFixture = () => {
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("stage");
      window.history.replaceState({}, "", url.toString());
      setDemoFixtureStage(null);
      reloadLiveState();
    }
  };

  const latestInvestigation = investigations.length > 0 ? investigations[0] : null;
  const isOutage = telemetry?.is_outage ?? false;

  return (
    <div className="min-h-[100dvh] bg-[#f8f9fb]">
      {/* Main Full-Width Container */}
      <main className="max-w-[1680px] mx-auto px-4 py-3 sm:px-6 sm:py-3.5 space-y-3.5">
        {/* Demo Fixture Mode Indicator Banner */}
        {demoFixtureStage && (
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-2 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="font-mono uppercase font-bold text-amber-600 bg-amber-500/20 px-1.5 py-0.5 rounded text-[10px]">
                DEMO FIXTURE
              </span>
              <span className="text-amber-800 font-medium">
                Offline Preset Stage: <span className="font-mono font-bold">{demoFixtureStage}</span> &mdash; Telemetry is simulated client-side.
              </span>
            </div>
            <button
              onClick={handleExitFixture}
              className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded text-[11px] transition-colors"
            >
              Switch to Live Telemetry
            </button>
          </div>
        )}

        {/* Top Header with Brand & Incident Notification Bell */}
        <TopBar
          telemetry={telemetry}
          investigationCount={investigations.length}
          onOpenNotifications={() => setIsDrawerOpen(true)}
        />

        {/* 1. Top 5 Real-Time Metric Cards */}
        <MetricCardsRow current={telemetry} />

        {/* 2. Central Row: Option 2 Command Center - Video Hero (8 cols / 66.7%) + Stacked Telemetry (4 cols / 33.3%) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
          <div className="lg:col-span-8 flex flex-col">
            <LivePlayerCard telemetry={telemetry} />
          </div>
          <div className="lg:col-span-4 flex flex-col gap-4 justify-between">
            <div className="flex-1">
              <PlaybackChartCard telemetry={telemetry} history={history} />
            </div>
            <div className="flex-1">
              <CdnSplitCard telemetry={telemetry} />
            </div>
          </div>
        </div>

        {/* 3. Bottom Row: SRE Commander (50%) + Live Logs Stream (50%) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SreCommanderCard
            latestInvestigation={latestInvestigation}
            isInvestigating={isInvestigating}
            onTriggerInvestigation={handleTriggerAutonomousInvestigation}
            isOutage={isOutage}
          />
          <LiveLogsCard telemetry={telemetry} history={history} />
        </div>

        {/* 4. Chaos Injection & Self-Healing Control Dock */}
        <ChaosDock
          chaosState={chaosState}
          onInjectCdnOutage={handleInjectCdnOutage}
          onInjectDrmTimeout={handleInjectDrmTimeout}
          onInjectIspDrop={handleInjectIspDrop}
          onAutoRemediate={handleTriggerAutonomousInvestigation}
          onReset={handleResetChaos}
          isLoading={isActionLoading || isInvestigating}
        />
      </main>

      {/* Slide-over Incident Log Drawer */}
      <IncidentDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        investigations={investigations}
      />
    </div>
  );
}
