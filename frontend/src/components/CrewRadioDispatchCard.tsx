"use client";

import React, { useRef, useEffect } from "react";
import { DatabaseIcon } from "hugeicons-react";
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
        return "bg-slate-100 text-slate-800 border-slate-300";
      case "DIT":
        return "bg-amber-50 text-amber-900 border-amber-300";
      case "KEY GRIP":
        return "bg-sky-50 text-sky-900 border-sky-300";
      case "CONTINUITY":
        return "bg-emerald-50 text-emerald-900 border-emerald-300";
      case "EDGE":
        return "bg-purple-50 text-purple-900 border-purple-300";
    }
  };

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-5 subtle-card-shadow flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-gray-100 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-gray-900 tracking-tight">
              Live Edge Error & Ingest Stream
            </h3>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded font-bold bg-gray-100 text-gray-700 border border-gray-200">
              Query: &#123;app="ott-edge-router"&#125;
            </span>
          </div>
          <p className="text-xs text-gray-500 font-medium mt-0.5">
            Real-time edge POP telemetry & multi-agent radio dispatches
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
            1Hz Live Stream
          </span>
        </div>
      </div>

      {/* Structured Radio Dispatches Feed - Full Card Height / Zero Negative Space (Light Format) */}
      <div className="flex-1 mt-3.5 flex flex-col min-h-[380px] lg:min-h-0">
        <div
          ref={scrollContainerRef}
          className="flex-1 w-full p-3.5 bg-gray-50/90 rounded-xl border border-gray-200/80 font-mono text-[11px] space-y-2.5 overflow-y-auto shadow-inner flex flex-col justify-start"
        >
          {/* Baseline Comms Line */}
          <div className="flex items-start gap-2 text-gray-600">
            <span className="text-gray-400 shrink-0 text-[10px]">[{baseTime}]</span>
            <span className="text-emerald-600 font-bold shrink-0">200 OK</span>
            <span className="text-gray-700 leading-snug">
              Fastly Edge POP (iad-01) &mdash; Chunk delivery nominal (42ms)
            </span>
          </div>

          {/* Active Outage Warning */}
          {isOutage && (
            <div className="flex items-start gap-2 bg-red-50 p-2.5 rounded-lg border border-red-200 text-red-800">
              <span className="text-red-500 shrink-0 text-[10px]">[{baseTime}]</span>
              <span className="text-red-600 font-bold shrink-0">502 BAD GATEWAY</span>
              <span className="font-semibold leading-snug">
                Upstream transit connection failed (packet loss: 60%)
              </span>
            </div>
          )}

          {/* Loki Error Ingest Stream */}
          <div className="flex items-start gap-2 text-gray-600">
            <span className="text-gray-400 shrink-0 text-[10px]">[{baseTime}]</span>
            <span className="text-blue-600 font-bold shrink-0">LOKI INGEST</span>
            <span className="text-gray-700 leading-snug">
              {telemetry?.latest_log || "Fastly Edge POP iad-01 502 BAD GATEWAY - Upstream packet drop 60% (ASN 3356)"}
            </span>
          </div>

          {/* Reasoning Trace Dispatches */}
          {traceDispatches.length > 0 ? (
            traceDispatches.map((disp) => (
              <div key={disp.id} className="flex items-start gap-2 text-gray-800">
                <span className="text-gray-400 shrink-0 text-[10px]">
                  [{disp.timestamp}]
                </span>
                <span
                  className={`px-1.5 py-0.2 rounded text-[9px] font-bold border shrink-0 ${getSenderBadgeStyle(
                    disp.sender
                  )}`}
                >
                  {disp.sender}
                </span>
                <span
                  className={`leading-snug ${
                    disp.severity === "critical"
                      ? "text-red-700 font-bold"
                      : disp.severity === "success"
                      ? "text-emerald-700 font-semibold"
                      : disp.severity === "warning"
                      ? "text-amber-800 font-medium"
                      : "text-gray-700"
                  }`}
                >
                  {disp.message}
                </span>
              </div>
            ))
          ) : (
            <>
              <div className="flex items-start gap-2 text-gray-700">
                <span className="text-gray-400 shrink-0 text-[10px]">[{baseTime}]</span>
                <span className="px-1.5 py-0.2 rounded text-[9px] font-bold border shrink-0 bg-amber-50 text-amber-900 border-amber-300">
                  DIT
                </span>
                <span className="text-gray-700 leading-snug">
                  Continuous Grafana Cloud Mimir polling: VPF ratio nominal (&le; 0.20%), 4K buffer depth 28.5s.
                </span>
              </div>
              <div className="flex items-start gap-2 text-gray-700">
                <span className="text-gray-400 shrink-0 text-[10px]">[{baseTime}]</span>
                <span className="px-1.5 py-0.2 rounded text-[9px] font-bold border shrink-0 bg-sky-50 text-sky-900 border-sky-300">
                  KEY GRIP
                </span>
                <span className="text-gray-700 leading-snug">
                  Primary trunk Fastly Edge iad-01 nominal at 100% (63.4 Gbps). Secondary Akamai failover armed.
                </span>
              </div>
              <div className="flex items-start gap-2 text-gray-700">
                <span className="text-gray-400 shrink-0 text-[10px]">[{baseTime}]</span>
                <span className="px-1.5 py-0.2 rounded text-[9px] font-bold border shrink-0 bg-emerald-50 text-emerald-900 border-emerald-300">
                  CONTINUITY
                </span>
                <span className="text-gray-700 leading-snug">
                  Closed-loop recovery gates armed. Monitoring forward buffer depth threshold &ge; 20.0s.
                </span>
              </div>
            </>
          )}

          {/* Recent Edge Ingest Log */}
          <div className="flex items-start gap-2 pt-1.5 border-t border-gray-200/80 text-gray-500 mt-auto">
            <span className="text-gray-400 shrink-0 text-[10px]">[{baseTime}]</span>
            <span className="px-1.5 py-0.2 rounded text-[9px] font-bold border shrink-0 bg-purple-50 text-purple-700 border-purple-200">
              EDGE INGEST
            </span>
            <span className="text-gray-700 truncate">
              {telemetry?.latest_log || "All edge delivery streams nominal [Fastly Edge POP iad-01: 200 OK]"}
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-3 pt-2.5 border-t border-gray-100 text-xs text-gray-500 font-medium flex items-center justify-between shrink-0">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-purple-500" />
          <span>Grafana Cloud Loki & Prometheus Ingest</span>
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
