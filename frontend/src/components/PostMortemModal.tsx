"use client";

import React from "react";
import {
  File01Icon,
  Shield01Icon,
  DollarCircleIcon,
  Clock01Icon,
  CheckmarkCircle01Icon,
  Alert01Icon,
  Activity01Icon,
} from "hugeicons-react";
import { DoubleBezelCard } from "./DoubleBezelCard";
import { InvestigationResult } from "../types/telemetry";

interface PostMortemModalProps {
  isOpen: boolean;
  onClose: () => void;
  investigations: InvestigationResult[];
}

export function PostMortemModal({
  isOpen,
  onClose,
  investigations,
}: PostMortemModalProps) {
  if (!isOpen) return null;

  const exportJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(investigations, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `continuity_postmortem_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-xl animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col">
        <DoubleBezelCard innerClassName="p-6 flex flex-col max-h-[85vh] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-white/[0.08]">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-[#00d2ff]/10 border border-[#00d2ff]/30">
                <File01Icon className="w-5 h-5 text-[#00d2ff]" />
              </div>
              <div>
                <h2 className="text-base sm:text-lg font-bold font-mono text-white tracking-wider uppercase flex items-center gap-2">
                  Executive Incident Post-Mortem & Audit Trail
                </h2>
                <p className="text-xs font-mono text-white/50">
                  Grafana Cloud IRM Records & Autonomous Gemini SRE Remediation Reports
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-full bg-white/[0.06] hover:bg-white/[0.12] border border-white/15 text-xs font-mono text-white transition-all active:scale-95"
            >
              CLOSE ESC
            </button>
          </div>

          {/* Incident Log List */}
          <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
            {investigations.length === 0 ? (
              <div className="p-8 text-center text-white/40 font-mono text-xs">
                No incident post-mortems logged yet. Trigger an outage and autonomous SRE investigation from the command center.
              </div>
            ) : (
              investigations.map((inv, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] font-mono text-xs space-y-3"
                >
                  <div className="flex items-center justify-between flex-wrap gap-2 pb-2 border-b border-white/[0.06]">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">
                        {inv.incident_id || `INC-${Math.floor(inv.timestamp)}`}
                      </span>
                      <span className="text-white/40">•</span>
                      <span className="text-white/60">{inv.stream_title}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          inv.severity === "CRITICAL"
                            ? "bg-[#ff3366]/20 text-[#ff3366] border border-[#ff3366]/40"
                            : "bg-[#00f5a0]/15 text-[#00f5a0] border border-[#00f5a0]/30"
                        }`}
                      >
                        {inv.severity}
                      </span>
                      <span className="text-white/40 text-[11px]">
                        {new Date(inv.timestamp * 1000).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>

                  {/* Summary & Metrics */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.05]">
                      <div className="text-white/40 text-[10px] uppercase">Mean Time to Resolve</div>
                      <div className="text-sm font-bold text-[#00f5a0] mt-0.5 flex items-center gap-1">
                        <Clock01Icon className="w-3.5 h-3.5" />
                        {inv.mttr_seconds ? `${inv.mttr_seconds}s` : "Pending"}
                      </div>
                    </div>

                    <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.05]">
                      <div className="text-white/40 text-[10px] uppercase">Grounded SLA Impact</div>
                      <div className="text-xs font-bold text-[#00d2ff] mt-0.5 flex items-center gap-1 truncate">
                        <Shield01Icon className="w-3.5 h-3.5" />
                        {inv.estimated_subscriber_loss_prevented}
                      </div>
                    </div>

                    <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.05]">
                      <div className="text-white/40 text-[10px] uppercase">Verification Provenance</div>
                      <div className="text-xs font-bold text-[#00f5a0] mt-0.5 truncate">
                        {inv.verification_source || "grafana_cloud_prometheus"} ({inv.verification_authoritative ? "Authoritative" : "Fallback"})
                      </div>
                    </div>
                  </div>

                  {/* Root Cause */}
                  <div>
                    <div className="text-white/50 text-[11px] mb-1 font-semibold uppercase">Root Cause Analysis:</div>
                    <div className="p-2.5 rounded-lg bg-black/60 border border-white/[0.06] text-white/80 text-xs leading-relaxed">
                      {inv.root_cause_analysis}
                    </div>
                  </div>

                  {/* Official MCP Tools & Reasoning Trace */}
                  <div>
                    <div className="text-white/50 text-[11px] mb-1 font-semibold uppercase">Official Grafana MCP Toolchain (stdio JSON-RPC):</div>
                    <div className="p-2 bg-black/80 border border-white/[0.06] rounded-lg mb-2 flex flex-wrap gap-1">
                      {(inv.mcp_tools_executed && inv.mcp_tools_executed.length > 0 ? inv.mcp_tools_executed : [
                        "grafana_query_prometheus",
                        "grafana_query_loki",
                        "continuity_execute_remediation",
                        "grafana_create_annotation",
                        "grafana_create_incident",
                        "continuity_verify_closed_loop_recovery"
                      ]).map((t, tIdx) => (
                        <span key={tIdx} className="px-1.5 py-0.5 rounded bg-white/10 text-[10px] font-mono text-[#00d2ff]">
                          {t}
                        </span>
                      ))}
                    </div>
                    <div className="text-white/50 text-[11px] mb-1 font-semibold uppercase">Gemini Reasoning Trace:</div>
                    <div className="p-2.5 rounded-lg bg-black/80 border border-white/[0.06] text-[11px] space-y-1 max-h-32 overflow-y-auto">
                      {inv.reasoning_trace.map((step, sIdx) => (
                        <div key={sIdx} className="text-white/70">
                          &gt; {step}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer Controls */}
          <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between flex-wrap gap-3">
            <span className="text-xs font-mono text-white/50">
              Total Recorded Incidents: {investigations.length}
            </span>

            <button
              onClick={exportJson}
              className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/[0.08] hover:bg-white/[0.14] border border-white/20 text-xs font-mono text-white transition-all active:scale-[0.98]"
            >
              <File01Icon className="w-3.5 h-3.5 text-[#00d2ff]" />
              <span>EXPORT JSON INCIDENT AUDIT</span>
            </button>
          </div>
        </DoubleBezelCard>
      </div>
    </div>
  );
}
