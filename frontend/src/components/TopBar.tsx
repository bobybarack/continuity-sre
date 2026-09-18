"use client";

import React from "react";
import {
  Notification01Icon,
  CheckmarkCircle01Icon,
  Alert01Icon,
  Clock01Icon,
  CpuIcon,
} from "hugeicons-react";
import { ContinuityLogo } from "./ContinuityLogo";
import { TelemetrySnapshot } from "../types/telemetry";

interface TopBarProps {
  telemetry: TelemetrySnapshot | null;
  investigationCount: number;
  onOpenNotifications: () => void;
}

export function TopBar({
  telemetry,
  investigationCount,
  onOpenNotifications,
}: TopBarProps) {
  const isOutage = telemetry?.is_outage ?? false;
  const isRecovered = telemetry?.status_label === "RECOVERED";

  return (
    <header className="bg-white border border-gray-200/80 rounded-2xl px-5 py-3.5 subtle-card-shadow flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      {/* Brand & Stream Selector */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 flex items-center justify-center">
          <ContinuityLogo className="w-8 h-8" />
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

      {/* Right Status Badges & Controls */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Live SLA Status Badge */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
            isOutage
              ? "bg-red-50 text-red-700 border-red-200 animate-pulse"
              : isRecovered
              ? "bg-emerald-50 text-emerald-800 border-emerald-300 font-bold"
              : "bg-emerald-50 text-emerald-700 border-emerald-200"
          }`}
        >
          {isOutage ? (
            <Alert01Icon className="w-4 h-4 text-red-600" />
          ) : (
            <CheckmarkCircle01Icon className="w-4 h-4 text-emerald-600" />
          )}
          <span>
            {isOutage
              ? "Critical Edge Outage Active"
              : isRecovered
              ? "Failover Restored"
              : "SLA Operational (99.98%)"}
          </span>
        </div>

        {/* Gemini Engine Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
          <CpuIcon className="w-3.5 h-3.5 text-purple-600" />
          <span>Google Cloud Gemini 3.7 Flash</span>
        </div>

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
