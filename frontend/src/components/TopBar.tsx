"use client";

import React from "react";
import { Notification01Icon, Alert01Icon } from "hugeicons-react";
import { ContinuityLogo } from "./ContinuityLogo";
import { TelemetrySnapshot, ChaosState } from "../types/telemetry";

interface TopBarProps {
  telemetry: TelemetrySnapshot | null;
  investigationCount: number;
  onOpenNotifications: () => void;
  chaosState?: ChaosState | null;
  onInjectCdnOutage?: () => void;
  onInjectDrmTimeout?: () => void;
  onInjectIspDrop?: () => void;
  onAutoRemediate?: () => void;
  onReset?: () => void;
  isLoading?: boolean;
}

export function TopBar({
  telemetry,
  investigationCount,
  onOpenNotifications,
  chaosState,
  onInjectCdnOutage,
  onInjectDrmTimeout,
  onInjectIspDrop,
  onAutoRemediate,
  onReset,
  isLoading,
}: TopBarProps) {
  const isOutage = telemetry?.is_outage ?? false;
  const currentMode = chaosState?.current_mode || "NORMAL";

  return (
    <header className="bg-white border border-gray-200/80 rounded-2xl px-5 py-3.5 subtle-card-shadow flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      {/* Brand & Stream Selector */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 flex items-center justify-center shrink-0">
          <ContinuityLogo className="w-8 h-8 text-gray-900" />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold text-gray-900 tracking-tight">
              CONTINUITY
            </h1>
            <span className="text-gray-300">•</span>
            <span className="text-xs font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded-md">
              Spider-Man: Brand New Day (World Premiere 4K)
            </span>
          </div>
          <p className="text-xs text-gray-500 font-medium mt-0.5">
            Autonomous Stream Continuity Incident Commander
          </p>
        </div>
      </div>

      {/* Center Demo Controls Suite */}
      {onInjectCdnOutage && (
        <div className="flex items-center gap-1.5 p-1 bg-gray-50 border border-gray-200/80 rounded-xl flex-wrap">
          <span className="text-[10px] font-mono font-bold text-gray-400 uppercase px-2 hidden md:inline-block">
            DEMO:
          </span>

          <button
            onClick={onInjectCdnOutage}
            disabled={isLoading}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all active:scale-95 ${
              currentMode === "CDN_OUTAGE"
                ? "bg-red-500 text-white font-bold shadow-sm"
                : "bg-white hover:bg-gray-100 text-gray-700 border border-gray-200/80 shadow-xs"
            }`}
          >
            CDN Outage
          </button>

          <button
            onClick={onInjectDrmTimeout}
            disabled={isLoading}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all active:scale-95 ${
              currentMode === "DRM_TIMEOUT"
                ? "bg-red-500 text-white font-bold shadow-sm"
                : "bg-white hover:bg-gray-100 text-gray-700 border border-gray-200/80 shadow-xs"
            }`}
          >
            DRM Timeout
          </button>

          <button
            onClick={onInjectIspDrop}
            disabled={isLoading}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all active:scale-95 ${
              currentMode === "ISP_PEERING_DROP"
                ? "bg-red-500 text-white font-bold shadow-sm"
                : "bg-white hover:bg-gray-100 text-gray-700 border border-gray-200/80 shadow-xs"
            }`}
          >
            ISP Drop
          </button>

          <div className="h-4 w-[1px] bg-gray-200 mx-0.5" />

          <button
            onClick={onAutoRemediate}
            disabled={isLoading}
            className="px-3 py-1 rounded-lg text-[11px] font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition-all active:scale-95 shadow-xs"
          >
            SRE Auto-Heal
          </button>

          <button
            onClick={onReset}
            disabled={isLoading}
            className="px-2 py-1 rounded-lg text-[11px] font-semibold bg-white hover:bg-gray-100 text-gray-600 border border-gray-200/80 transition-all active:scale-95 shadow-xs"
            title="Reset to nominal"
          >
            Reset
          </button>
        </div>
      )}

      {/* Right Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Outage Alert Badge - Only displayed when critical outage is active */}
        {isOutage && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border bg-red-50 text-red-700 border-red-200 animate-pulse">
            <Alert01Icon className="w-4 h-4 text-red-600" />
            <span>Critical Edge Outage Active</span>
          </div>
        )}

        {/* Live Incident Notification Bell Button */}
        <button
          onClick={onOpenNotifications}
          className="relative flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 border border-gray-200/80 text-xs font-semibold text-gray-700 transition-all active:scale-[0.98]"
        >
          <Notification01Icon className="w-4 h-4 text-gray-600" />
          <span>Incident Logs</span>
          {investigationCount > 0 && (
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-600 text-white">
              {investigationCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}
