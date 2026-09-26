"use client";

import React from "react";
import { TelemetrySnapshot } from "../types/telemetry";

interface CdnSplitCardProps {
  telemetry: TelemetrySnapshot | null;
}

export function CdnSplitCard({ telemetry }: CdnSplitCardProps) {
  const primaryPct = telemetry?.primary_traffic_pct ?? 100;
  const secondaryPct = telemetry?.secondary_traffic_pct ?? 0;
  const isOutage = telemetry?.is_outage ?? false;
  const isFailoverActive = secondaryPct > 0;

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-5 subtle-card-shadow flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <h3 className="text-sm font-bold text-gray-900 tracking-tight">
                Multi-CDN Traffic Distribution
              </h3>
            </div>
            <p className="text-xs text-gray-500 font-medium mt-0.5">
              Live Egress Routing & Balance
            </p>
          </div>

          <span
            className={`px-2 py-0.5 rounded-full text-xs font-bold border ${
              isFailoverActive
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-gray-100 text-gray-600 border-gray-200"
            }`}
          >
            {isFailoverActive ? "Dual Failover Active" : "Primary Route"}
          </span>
        </div>

        {/* Primary CDN */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs font-semibold text-gray-800 mb-1.5">
            <span>Fastly Edge (Primary Ingest)</span>
            <span className="font-bold">{primaryPct}%</span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-gray-100 overflow-hidden border border-gray-200/80">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isOutage ? "bg-red-500" : "bg-emerald-500"
              }`}
              style={{ width: `${primaryPct}%` }}
            />
          </div>
        </div>

        {/* Secondary CDN */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs font-semibold text-gray-800 mb-1.5">
            <span>Akamai Cloud (Secondary Failover)</span>
            <span className="font-bold">{secondaryPct}%</span>
          </div>
          <div className="w-full h-2.5 rounded-full bg-gray-100 overflow-hidden border border-gray-200/80">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all duration-500"
              style={{ width: `${secondaryPct}%` }}
            />
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500 font-medium">
        <span>Global Peak Egress</span>
        <span className="font-bold text-gray-900">~63.4 Gbps Total</span>
      </div>
    </div>
  );
}
