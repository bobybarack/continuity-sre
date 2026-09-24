"use client";

import React, { useRef, useEffect } from "react";
import { Radio01Icon, DatabaseIcon } from "hugeicons-react";
import { TelemetrySnapshot, InvestigationResult } from "../types/telemetry";

export interface CrewRadioDispatchCardProps {
  telemetry: TelemetrySnapshot | null;
  history?: TelemetrySnapshot[];
  latestInvestigation?: InvestigationResult | null;
}

interface DispatchMessage {
  id: string;
  timestamp: string;
  sender: "1ST AD" | "DIT" | "KEY GRIP" | "CONTINUITY" | "EDGE";
  message: string;
  severity: "info" | "warning" | "critical" | "success";
}

function parseReasoningToDispatches(
  trace: string[] | undefined,
  baseTime: string
): DispatchMessage[] {
  if (!trace || trace.length === 0) return [];

  return trace.map((line, idx) => {
    const lower = line.toLowerCase();
    let sender: DispatchMessage["sender"] = "1ST AD";
    let severity: DispatchMessage["severity"] = "info";

    if (
      lower.includes("promql") ||
      lower.includes("loki") ||
      lower.includes("telemetry ingested") ||
      lower.includes("vpf")
    ) {
      sender = "DIT";
      severity = lower.includes("breached") || lower.includes("spike") ? "warning" : "info";
    } else if (
      lower.includes("remediation") ||
      lower.includes("shift") ||
      lower.includes("akamai") ||
      lower.includes("reroute") ||
      lower.includes("failover")
    ) {
      sender = "KEY GRIP";
      severity = "info";
    } else if (
      lower.includes("verify") ||
      lower.includes("closed-loop") ||
      lower.includes("buffer") ||
      lower.includes("gate")
    ) {
      sender = "CONTINUITY";
      severity = lower.includes("passed") ? "success" : "info";
    } else if (lower.includes("critical") || lower.includes("anomaly")) {
      sender = "1ST AD";
      severity = "critical";
    } else {
      sender = "1ST AD";
      severity = "info";
    }

    // Clean timestamp prefix if present
    const cleanLine = line.replace(/^\[\d{2}:\d{2}:\d{2}\]\s*/, "");

    return {
      id: `trace-${idx}`,
      timestamp: baseTime,
      sender,
      message: cleanLine,
      severity,
    };
  });
}

export function CrewRadioDispatchCard({
  telemetry,
  latestInvestigation,
}: CrewRadioDispatchCardProps) {
  const isOutage = telemetry?.is_outage ?? false;
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  const baseTime = React.useMemo(() => {
    return new Date().toLocaleTimeString("en-US", { hour12: false });
  }, []);

  const traceDispatches = React.useMemo(() => {
    return parseReasoningToDispatches(
      latestInvestigation?.reasoning_trace,
      baseTime
    );
  }, [latestInvestigation?.reasoning_trace, baseTime]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [telemetry, traceDispatches]);

  const getSenderBadgeStyle = (sender: DispatchMessage["sender"]) => {
    switch (sender) {
      case "1ST AD":
        return "bg-slate-200 text-slate-800 border-slate-300";
      case "DIT":
        return "bg-amber-100 text-amber-900 border-amber-300";
      case "KEY GRIP":
        return "bg-sky-100 text-sky-900 border-sky-300";
      case "CONTINUITY":
        return "bg-emerald-100 text-emerald-900 border-emerald-300";
      case "EDGE":
        return "bg-purple-100 text-purple-900 border-purple-300";
    }
  };

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-5 subtle-card-shadow flex flex-col justify-between h-full">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-700 border border-purple-200 flex items-center justify-center">
              <Radio01Icon className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-gray-900 tracking-tight">
                  Crew Radio Intercom
                </h3>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded font-bold bg-purple-50 text-purple-800 border border-purple-200">
                  CH-1 PREMIERE
                </span>
              </div>
              <p className="text-xs text-gray-500 font-medium">
                Live Multi-Agent Radio Comms & Edge Telemetry LogQL Stream
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
              1Hz Intercom Active
            </span>
          </div>
        </div>

        {/* Structured Radio Dispatches Feed */}
        <div
          ref={scrollContainerRef}
          className="mt-3.5 p-3 bg-slate-950 rounded-xl border border-slate-800 font-mono text-[11px] space-y-2.5 max-h-56 overflow-y-auto shadow-inner"
        >
          {/* Baseline Comms Line */}
          <div className="flex items-start gap-2 text-slate-400">
            <span className="text-slate-500 shrink-0 text-[10px]">[{baseTime}]</span>
            <span className="px-1 py-0.2 rounded text-[9px] font-bold border shrink-0 bg-slate-800 text-slate-300 border-slate-700">
              1ST AD
            </span>
            <span className="text-slate-300 leading-snug">
              Premiere Night Live 4K broadcast on air. All stations report nominal baseline.
            </span>
          </div>

          {/* Active Outage Warning */}
          {isOutage && (
            <div className="flex items-start gap-2 bg-red-950/60 p-2 rounded-lg border border-red-800/80 animate-pulse text-red-200">
              <span className="text-red-400 shrink-0 text-[10px]">[{baseTime}]</span>
              <span className="px-1 py-0.2 rounded text-[9px] font-bold border shrink-0 bg-red-900 text-red-100 border-red-700">
                1ST AD
              </span>
              <span className="font-semibold leading-snug">
                SLA Breach Detected on 4K Broadcast Stream! All crew to emergency stations.
              </span>
            </div>
          )}

          {/* Reasoning Trace Dispatches */}
          {traceDispatches.length > 0 ? (
            traceDispatches.map((disp) => (
              <div key={disp.id} className="flex items-start gap-2 text-slate-300">
                <span className="text-slate-500 shrink-0 text-[10px]">
                  [{disp.timestamp}]
                </span>
                <span
                  className={`px-1 py-0.2 rounded text-[9px] font-bold border shrink-0 ${getSenderBadgeStyle(
                    disp.sender
                  )}`}
                >
                  {disp.sender}
                </span>
                <span
                  className={`leading-snug ${
                    disp.severity === "critical"
                      ? "text-red-300 font-bold"
                      : disp.severity === "success"
                      ? "text-emerald-300 font-semibold"
                      : disp.severity === "warning"
                      ? "text-amber-300 font-medium"
                      : "text-slate-200"
                  }`}
                >
                  {disp.message}
                </span>
              </div>
            ))
          ) : (
            <div className="flex items-start gap-2 text-slate-400">
              <span className="text-slate-500 shrink-0 text-[10px]">[{baseTime}]</span>
              <span className="px-1 py-0.2 rounded text-[9px] font-bold border shrink-0 bg-amber-900/60 text-amber-200 border-amber-700">
                DIT
              </span>
              <span className="text-slate-300 leading-snug">
                Continuous Grafana Cloud Mimir polling: VPF ratio nominal (&le; 0.20%), 4K buffer depth 28.5s.
              </span>
            </div>
          )}

          {/* Recent Edge Ingest Log */}
          <div className="flex items-start gap-2 pt-1 border-t border-slate-800/80 text-slate-400">
            <span className="text-slate-500 shrink-0 text-[10px]">[{baseTime}]</span>
            <span className="px-1 py-0.2 rounded text-[9px] font-bold border shrink-0 bg-slate-800 text-purple-300 border-purple-800/50">
              EDGE INGEST
            </span>
            <span className="text-slate-300 truncate">
              {telemetry?.latest_log || "All edge delivery streams nominal [Fastly Edge POP iad-01: 200 OK]"}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500 font-medium flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <DatabaseIcon className="w-3.5 h-3.5 text-purple-600" />
          <span>Grafana Cloud Loki & Prometheus Proxy</span>
        </div>
        <span className="font-semibold text-emerald-600 font-mono text-[11px]">
          production-intercom://ch-1
        </span>
      </div>
    </div>
  );
}

// Backward-compatible alias
export { CrewRadioDispatchCard as LiveLogsCard };
