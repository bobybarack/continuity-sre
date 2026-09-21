"use client";

import React from "react";
import { File01Icon, CheckmarkCircle01Icon, Alert01Icon } from "hugeicons-react";
import { InvestigationResult } from "../types/telemetry";

interface IncidentHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  investigations: InvestigationResult[];
}

export function IncidentHistoryModal({
  isOpen,
  onClose,
  investigations,
}: IncidentHistoryModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-3xl max-h-[85vh] bg-white rounded-2xl border border-gray-200 shadow-xl flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
              <File01Icon className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <h3 className="text-base font-bold text-gray-900 tracking-tight">
                Incident Audit Logs & Post-Mortems
              </h3>
              <p className="text-xs text-gray-500 font-medium">
                Verified autonomous remediation history
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-700 transition-all"
          >
            Close
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 overflow-y-auto space-y-3 flex-1">
          {investigations.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-xs font-medium">
              No incidents recorded yet. Trigger an outage and autonomous SRE healing from the dashboard.
            </div>
          ) : (
            investigations.map((inv, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl bg-gray-50 border border-gray-200/80 text-xs space-y-2.5"
              >
                <div className="flex items-center justify-between">
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
                    <span className="text-gray-400 font-medium">
                      {new Date(inv.timestamp * 1000).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                <div className="p-2.5 bg-white rounded-lg border border-gray-200/60 text-gray-700 leading-relaxed font-medium">
                  {inv.root_cause_analysis}
                </div>

                <div className="flex items-center justify-between text-[11px] text-gray-500 pt-1 flex-wrap gap-2">
                  <span>
                    Action:{" "}
                    <span className="font-bold text-gray-800">
                      {inv.autonomous_action_taken || "Autonomous Failover"}
                    </span>
                  </span>
                  <span>
                    SLA Impact:{" "}
                    <span className="font-bold text-emerald-600">
                      {inv.estimated_subscriber_loss_prevented}
                    </span>
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-gray-200/80 text-gray-700">
                    Provenance: {inv.verification_source || "grafana_cloud_prometheus"} ({inv.verification_authoritative ? "Authoritative" : "Fallback"})
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
