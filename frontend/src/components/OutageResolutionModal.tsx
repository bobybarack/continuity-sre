"use client";

import React from "react";
import { TelemetrySnapshot, InvestigationResult } from "../types/telemetry";

interface OutageResolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAutoRemediate: () => void;
  isInvestigating: boolean;
  telemetry: TelemetrySnapshot | null;
  latestInvestigation: InvestigationResult | null;
}

export function OutageResolutionModal({
  isOpen,
  onClose,
  onAutoRemediate,
  isInvestigating,
  telemetry,
  latestInvestigation,
}: OutageResolutionModalProps) {
  if (!isOpen) return null;

  const chaosMode = telemetry?.chaos_mode || "CDN_OUTAGE";
  const vpf = telemetry?.video_playback_failures_pct ?? 5.08;
  const buffer = telemetry?.buffer_health_sec ?? 2.9;
  const isResolved =
    !telemetry?.is_outage &&
    (latestInvestigation?.closed_loop_verified ||
      latestInvestigation?.workflow_status === "RESOLVED");

  // Dynamic incident title and description based on active failure mode
  let title = "Simulated Transit Collapse & Buffer Stall Alert";
  let subtitle =
    "Injected upstream transit failure on Fastly Edge POP triggering immediate playback freeze.";
  let diagnostic = "Primary edge CDN upstream connection failure (HTTP 502)";

  if (chaosMode === "DRM_TIMEOUT") {
    title = "DRM License Server Acquisition Stall";
    subtitle =
      "Widevine L1 license proxy timeout prevented player decryption key exchange.";
    diagnostic = "Widevine key authentication proxy timeout (>500ms SLA)";
  } else if (chaosMode === "ISP_PEERING_DROP") {
    title = "Tier-1 BGP Transit Peering Degradation";
    subtitle =
      "Upstream AS-3356 transit route packet loss causing downstream playback starvation.";
    diagnostic = "Tier-1 BGP transit peering packet loss: 60% drop";
  }

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-4 animate-slideDown">
      <div className="bg-white/95 backdrop-blur-md border border-red-200/90 rounded-2xl p-5 shadow-2xl subtle-card-shadow">
        {/* Header Tag & Dismiss Button */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-red-100 text-red-800 border border-red-200 uppercase tracking-wider">
              {isResolved ? "Incident Resolved" : "Critical Outage Detected"}
            </span>
            <span className="text-xs font-semibold text-gray-400">&bull;</span>
            <span className="text-xs font-mono text-gray-500 font-semibold">
              Live Confidence Trigger
            </span>
          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xs font-mono font-bold p-1 rounded-lg hover:bg-gray-100 transition-all"
            title="Dismiss popup to inspect dashboard"
          >
            ✕ Dismiss
          </button>
        </div>

        {/* Incident Summary */}
        <div className="mt-3">
          <h3 className="text-sm font-bold text-gray-900 tracking-tight">
            {isResolved ? "Closed-Loop Recovery Verified" : title}
          </h3>
          <p className="text-xs text-gray-600 mt-1 leading-relaxed">
            {isResolved
              ? "Autonomous SRE successfully rerouted egress traffic to Akamai. Downstream buffer depth and VPF have normalized."
              : subtitle}
          </p>
        </div>

        {/* Telemetry Metric Callout Box */}
        {!isResolved ? (
          <div className="grid grid-cols-3 gap-2 mt-3.5 p-2.5 bg-red-50/80 rounded-xl border border-red-200/80 text-center">
            <div>
              <span className="text-[10px] font-mono font-semibold uppercase text-red-600 block">
                Playback Failure
              </span>
              <span className="text-sm font-bold text-red-700 mt-0.5 block font-mono">
                {vpf.toFixed(2)}%
              </span>
              <span className="text-[9px] text-red-500 font-medium">
                SLA &le; 0.50%
              </span>
            </div>

            <div>
              <span className="text-[10px] font-mono font-semibold uppercase text-red-600 block">
                Forward Buffer
              </span>
              <span className="text-sm font-bold text-red-700 mt-0.5 block font-mono">
                {buffer.toFixed(1)}s
              </span>
              <span className="text-[9px] text-red-500 font-medium">
                Target &ge; 20.0s
              </span>
            </div>

            <div>
              <span className="text-[10px] font-mono font-semibold uppercase text-red-600 block">
                Impacted Sessions
              </span>
              <span className="text-sm font-bold text-red-700 mt-0.5 block font-mono truncate">
                ~217,520
              </span>
              <span className="text-[9px] text-red-500 font-medium">
                At Risk
              </span>
            </div>
          </div>
        ) : (
          <div className="mt-3.5 p-3 bg-emerald-50 rounded-xl border border-emerald-200 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="font-semibold text-emerald-900">
                Recovery Gate Passed: VPF {latestInvestigation?.verified_vpf_rate ?? 0.21}% &bull; Buffer {latestInvestigation?.verified_buffer_health_sec ?? 27.9}s
              </span>
            </div>
            <span className="text-[10px] font-mono font-bold text-emerald-700 bg-white px-2 py-0.5 rounded border border-emerald-200">
              {latestInvestigation?.mttr_seconds ? `${latestInvestigation.mttr_seconds}s MTTR` : "1.28s MTTR"}
            </span>
          </div>
        )}

        {/* Diagnosis Strip */}
        <div className="mt-3 text-[11px] text-gray-500 flex items-center justify-between font-mono bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-200/60">
          <span className="truncate">Root Diagnostic: {diagnostic}</span>
          <span className="text-[10px] font-bold text-slate-700 shrink-0 ml-2">
            Target: Akamai Cloud CDN
          </span>
        </div>

        {/* Resolution Actions */}
        <div className="mt-4 flex items-center gap-3">
          {!isResolved ? (
            <button
              onClick={onAutoRemediate}
              disabled={isInvestigating}
              className="flex-1 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all disabled:opacity-50 active:scale-[0.98] shadow-md flex items-center justify-center gap-2"
            >
              <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
              <span>
                {isInvestigating
                  ? "Executing Official Grafana MCP Toolchain..."
                  : "Resolve Incident (SRE Auto-Heal & Failover)"}
              </span>
            </button>
          ) : (
            <button
              onClick={onClose}
              className="flex-1 py-2 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all active:scale-[0.98] shadow-sm text-center"
            >
              Resume Nominal Broadcast Monitoring
            </button>
          )}

          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-700 transition-all active:scale-[0.98]"
          >
            Inspect Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
