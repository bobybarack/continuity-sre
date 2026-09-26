"use client";

import React from "react";
import { ChaosState } from "../types/telemetry";

interface ChaosDockProps {
  chaosState: ChaosState | null;
  onInjectCdnOutage: () => void;
  onInjectDrmTimeout: () => void;
  onInjectIspDrop: () => void;
  onAutoRemediate: () => void;
  onReset: () => void;
  isLoading: boolean;
}

export function ChaosDock({
  chaosState,
  onInjectCdnOutage,
  onInjectDrmTimeout,
  onInjectIspDrop,
  onAutoRemediate,
  onReset,
  isLoading,
}: ChaosDockProps) {
  const isOutage = chaosState?.is_outage_active || false;
  const currentMode = chaosState?.current_mode || "NORMAL";

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-4 subtle-card-shadow flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0" />
        <div>
          <span className="text-xs font-bold text-gray-900 block">
            Chaos Injection Suite
          </span>
          <span className="text-[11px] text-gray-500 font-medium">
            Simulate live delivery failures and verify autonomous self-healing
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap w-full sm:w-auto">
        <button
          onClick={onInjectCdnOutage}
          disabled={isLoading}
          className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all active:scale-[0.98] ${
            currentMode === "CDN_OUTAGE"
              ? "bg-red-50 text-red-700 border-red-300 font-bold"
              : "bg-gray-50 hover:bg-gray-100 text-gray-700 border-gray-200"
          }`}
        >
          Inject CDN Outage
        </button>

        <button
          onClick={onInjectDrmTimeout}
          disabled={isLoading}
          className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all active:scale-[0.98] ${
            currentMode === "DRM_TIMEOUT"
              ? "bg-red-50 text-red-700 border-red-300 font-bold"
              : "bg-gray-50 hover:bg-gray-100 text-gray-700 border-gray-200"
          }`}
        >
          Inject DRM Timeout
        </button>

        <button
          onClick={onInjectIspDrop}
          disabled={isLoading}
          className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all active:scale-[0.98] ${
            currentMode === "ISP_PEERING_DROP"
              ? "bg-red-50 text-red-700 border-red-300 font-bold"
              : "bg-gray-50 hover:bg-gray-100 text-gray-700 border-gray-200"
          }`}
        >
          Inject ISP Drop
        </button>

        <button
          onClick={onAutoRemediate}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-all active:scale-[0.98] shadow-sm"
        >
          <span>SRE Auto-Heal</span>
        </button>

        <button
          onClick={onReset}
          disabled={isLoading}
          className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 border border-gray-200 text-xs font-semibold text-gray-600 transition-all active:scale-[0.98]"
        >
          <span>Reset</span>
        </button>
      </div>
    </div>
  );
}
