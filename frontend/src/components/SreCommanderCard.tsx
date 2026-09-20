"use client";

import React from "react";
import {
  CpuIcon,
  CheckmarkCircle01Icon,
  Alert01Icon,
  SparklesIcon,
} from "hugeicons-react";
import { InvestigationResult } from "../types/telemetry";

interface SreCommanderCardProps {
  latestInvestigation: InvestigationResult | null;
  isInvestigating: boolean;
  onTriggerInvestigation: () => void;
  isOutage: boolean;
}

export function SreCommanderCard({
  latestInvestigation,
  isInvestigating,
  onTriggerInvestigation,
  isOutage,
}: SreCommanderCardProps) {
  const rca = latestInvestigation?.root_cause_analysis;
  const churnSaved =
    latestInvestigation?.estimated_subscriber_loss_prevented ||
    "$0 (Nominal)";
  const hasMttr = typeof latestInvestigation?.mttr_seconds === "number" && latestInvestigation.mttr_seconds !== null;
  const mttrDisplay = hasMttr
    ? `${latestInvestigation!.mttr_seconds}s MTTR`
    : latestInvestigation?.workflow_elapsed_seconds
    ? `${latestInvestigation.workflow_elapsed_seconds}s (Pending)`
    : "Nominal";

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-5 subtle-card-shadow flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
              <CpuIcon className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900 tracking-tight">
                Autonomous SRE Commander
              </h3>
              <p className="text-xs text-gray-500 font-medium">
                Live Anomaly Triage & Remediation
              </p>
            </div>
          </div>

          <span
            className={`px-2 py-0.5 rounded-full text-xs font-bold border ${
              isOutage
                ? "bg-red-50 text-red-700 border-red-200"
                : "bg-emerald-50 text-emerald-700 border-emerald-200"
            }`}
          >
            {isOutage ? "Anomaly Detected" : "Standby Active"}
          </span>
        </div>

        {/* RCA Diagnostics / Summary */}
        <div className="mt-4 p-3 bg-gray-50 rounded-xl border border-gray-200/60 text-xs">
          <span className="text-gray-400 font-semibold block text-[11px] uppercase mb-1">
            Latest Diagnosis & Resolution
          </span>
          <p className="text-gray-800 leading-relaxed font-medium">
            {rca ||
              "All streaming telemetry within normal operating SLA. Continuous 1Hz edge monitoring active."}
          </p>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 gap-3 mt-3">
          <div className="p-3 bg-gray-50 rounded-xl border border-gray-200/60">
            <span className="text-[11px] text-gray-400 font-semibold uppercase block">
              Last Verified Recovery
            </span>
            <span className="text-base font-bold text-emerald-600 mt-0.5 block">
              {mttrDisplay}
            </span>
          </div>

          <div className="p-3 bg-gray-50 rounded-xl border border-gray-200/60">
            <span className="text-[11px] text-gray-400 font-semibold uppercase block">
              Projected Churn Model
            </span>
            <span className="text-base font-bold text-emerald-600 mt-0.5 block">
              {churnSaved.split(" ")[0]}
            </span>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <div className="mt-4 pt-3 border-t border-gray-100">
        <button
          onClick={onTriggerInvestigation}
          disabled={isInvestigating}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all disabled:opacity-50 active:scale-[0.99] shadow-sm"
        >
          <SparklesIcon className="w-4 h-4" />
          <span>
            {isInvestigating
              ? "Diagnosing & Healing Stream..."
              : "Trigger Autonomous SRE Failover"}
          </span>
        </button>
      </div>
    </div>
  );
}
