"use client";

import React from "react";
import { File01Icon, CheckmarkCircle01Icon, Alert01Icon, Clock01Icon } from "hugeicons-react";
import { InvestigationResult } from "../types/telemetry";

interface IncidentDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  investigations: InvestigationResult[];
}

export function IncidentDrawer({
  isOpen,
  onClose,
  investigations,
}: IncidentDrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-lg bg-white h-full shadow-2xl border-l border-gray-200 flex flex-col justify-between animate-slideLeft">
        {/* Drawer Header */}
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
              <File01Icon className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900 tracking-tight">
                Incident Audit Logs
              </h3>
              <p className="text-xs text-gray-500 font-medium">
                Autonomous SRE Reasoning & Failover History
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-700 transition-all active:scale-95"
          >
            Close
          </button>
        </div>

        {/* Drawer Content */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1">
          {investigations.length === 0 ? (
            <div className="text-center py-16 text-gray-400 text-xs font-medium">
              No incident post-mortems logged yet. Trigger an outage and click SRE Auto-Heal to generate an audit log.
            </div>
          ) : (
            investigations.map((inv, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-gray-50 border border-gray-200/80 text-xs space-y-3"
              >
                <div className="flex items-center justify-between pb-2 border-b border-gray-200/60">
                  <span className="font-bold text-gray-900">
                    {inv.incident_id || `INC-${Math.floor(inv.timestamp)}`}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        inv.severity === "CRITICAL"
                          ? "bg-red-50 text-red-700 border-red-200"
                          : "bg-emerald-50 text-emerald-700 border-emerald-200"
                      }`}
                    >
                      {inv.severity}
                    </span>
                    <span className="text-gray-400 text-[11px] font-medium">
                      {new Date(inv.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2 bg-white rounded-lg border border-gray-200/60">
                    <span className="text-[10px] text-gray-400 font-semibold uppercase block">
                      Recovery Time
                    </span>
                    <span className="text-xs font-bold text-emerald-600 mt-0.5 block">
                      {inv.mttr_seconds ? `${inv.mttr_seconds}s MTTR` : (inv.workflow_elapsed_seconds ? `${inv.workflow_elapsed_seconds}s Elapsed` : "Pending")}
                    </span>
                  </div>

                  <div className="p-2 bg-white rounded-lg border border-gray-200/60">
                    <span className="text-[10px] text-gray-400 font-semibold uppercase block">
                      Prevented Churn
                    </span>
                    <span className="text-xs font-bold text-emerald-600 mt-0.5 block">
                      {inv.estimated_subscriber_loss_prevented.split(" ")[0]}
                    </span>
                  </div>
                </div>

                {/* RCA */}
                <div className="p-2.5 bg-white rounded-lg border border-gray-200/60 text-gray-700 leading-relaxed font-medium">
                  {inv.root_cause_analysis}
                </div>

                {/* Reasoning Trace Terminal */}
                <div className="mt-3">
                  <span className="text-[10px] text-gray-400 font-semibold uppercase block mb-1.5">
                    Gemini Reasoning Log
                  </span>
                  <div className="p-2 bg-gray-900 rounded-lg text-gray-300 font-mono text-[10px] space-y-1 max-h-28 overflow-y-auto">
                    {inv.reasoning_trace.map((step, sIdx) => (
                      <div key={sIdx}>&gt; {step}</div>
                    ))}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500 font-medium">
          <span>Total Incidents: {investigations.length}</span>
          <span className="text-emerald-600 font-semibold">
            {investigations.length === 0
              ? "No Incidents Recorded"
              : `${investigations.filter((i) => i.closed_loop_verified || i.workflow_status === "RESOLVED").length} Resolved${
                  investigations.filter((i) => !i.closed_loop_verified && i.workflow_status !== "RESOLVED").length > 0
                    ? ` (${investigations.filter((i) => !i.closed_loop_verified && i.workflow_status !== "RESOLVED").length} Pending)`
                    : ""
                }`}
          </span>
        </div>
      </div>
    </div>
  );
}
