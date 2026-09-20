"use client";

import React, { useState, useEffect } from "react";
import { ContinuityLogo } from "./ContinuityLogo";
import {
  CpuIcon,
  CloudIcon,
  Activity01Icon,
  Clock01Icon,
  CheckmarkCircle01Icon,
  Alert01Icon,
} from "hugeicons-react";
import { TelemetrySnapshot, GrafanaHealth } from "../types/telemetry";

interface HeaderNavProps {
  telemetry: TelemetrySnapshot | null;
  grafanaHealth?: GrafanaHealth | null;
  onOpenPostMortem: () => void;
  investigationCount: number;
}

export function HeaderNav({
  telemetry,
  onOpenPostMortem,
  investigationCount,
}: HeaderNavProps) {
  const [timeStr, setTimeStr] = useState<string>("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString("en-US", {
          hour12: false,
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }) + " UTC"
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const isOutage = telemetry?.is_outage ?? false;
  const isRecovered = telemetry?.status_label === "RECOVERED";
  const statusLabel = isOutage
    ? "CRITICAL SLA BREACH"
    : isRecovered
    ? "STREAM SELF-HEALED"
    : "STREAM NOMINAL (OPERATIONAL)";

  const statusColorClass = isOutage
    ? "bg-[#ff3366]/15 border-[#ff3366]/40 text-[#ff3366] alert-pulse-red"
    : isRecovered
    ? "bg-[#00d2ff]/15 border-[#00d2ff]/40 text-[#00d2ff]"
    : "bg-[#00f5a0]/10 border-[#00f5a0]/30 text-[#00f5a0] alert-pulse-green";

  return (
    <header className="relative w-full z-40 border-b border-white/[0.08] bg-[#07090e]/80 backdrop-blur-xl">
      <div className="max-w-[1720px] mx-auto px-4 sm:px-6 lg:px-8 py-3.5">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          {/* Brand & Mission */}
          <div className="flex items-center gap-3.5">
            <div className="relative p-2 rounded-xl bg-gradient-to-br from-sky-500/20 to-cyan-500/10 border border-sky-500/30 shadow-[0_0_20px_rgba(0,210,255,0.2)] flex items-center justify-center">
              <ContinuityLogo className="w-6 h-6 text-[#00d2ff]" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-[#00f5a0] ring-2 ring-[#07090e] animate-pulse" />
            </div>

            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  CONTINUITY
                  <span className="text-xs font-mono font-normal px-2 py-0.5 rounded-md bg-white/[0.06] border border-white/10 text-white/70">
                    v2.4-PROD
                  </span>
                </h1>
                <span className="hidden sm:inline-block text-white/30 text-xs font-mono">
                  {"//"}
                </span>
                <span className="text-xs font-mono tracking-wide text-[#00d2ff] uppercase">
                  Autonomous OTT Streaming Incident Commander
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-white/50 mt-0.5">
                <span className="flex items-center gap-1 font-mono">
                  <CloudIcon className="w-3.5 h-3.5 text-[#00d2ff]" />
                  Grafana Cloud MCP
                </span>
                <span className="text-white/20">•</span>
                <span className="flex items-center gap-1 font-mono">
                  <CpuIcon className="w-3.5 h-3.5 text-[#6366f1]" />
                  Gemini 3.1 Enterprise
                </span>
                <span className="text-white/20">•</span>
                <span className="font-mono text-white/40">Cloud Run: us-central1</span>
              </div>
            </div>
          </div>

          {/* Right Status Badges & Controls */}
          <div className="flex items-center gap-3 flex-wrap w-full lg:w-auto justify-between lg:justify-end">
            {/* Live Clock Pill */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/10 text-xs font-mono text-white/70">
              <Clock01Icon className="w-3.5 h-3.5 text-white/50" />
              <span>{timeStr || "00:00:00 UTC"}</span>
            </div>

            {/* Grafana Cloud Datasource Pill */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/10 text-xs font-mono text-white/70">
              <span className="w-2 h-2 rounded-full bg-[#00f5a0] animate-pulse" />
              <span className="text-white/80">Grafana MCP:</span>
              <span className="text-[#00d2ff] font-semibold">60+ Tools Bound</span>
            </div>

            {/* Live System Status Pill */}
            <div
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-mono font-bold tracking-wider transition-all duration-300 ${statusColorClass}`}
            >
              {isOutage ? (
                <Alert01Icon className="w-4 h-4 animate-bounce" />
              ) : (
                <CheckmarkCircle01Icon className="w-4 h-4" />
              )}
              <span>{statusLabel}</span>
            </div>

            {/* Post-Mortem Audit Button */}
            <button
              onClick={onOpenPostMortem}
              className="group flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/[0.06] hover:bg-white/[0.12] border border-white/15 text-xs font-mono text-white transition-all duration-200 active:scale-[0.98]"
            >
              <Activity01Icon className="w-3.5 h-3.5 text-[#00d2ff] group-hover:rotate-12 transition-transform" />
              <span>Incident Audit Logs</span>
              {investigationCount > 0 && (
                <span className="w-4 h-4 rounded-full bg-[#6366f1] text-[10px] font-bold text-white flex items-center justify-center">
                  {investigationCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
