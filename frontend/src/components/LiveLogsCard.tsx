"use client";

import React, { useRef, useEffect } from "react";
import { DatabaseIcon } from "hugeicons-react";
import { TelemetrySnapshot } from "../types/telemetry";

interface LiveLogsCardProps {
  telemetry: TelemetrySnapshot | null;
  history: TelemetrySnapshot[];
}

export function LiveLogsCard({ telemetry, history }: LiveLogsCardProps) {
  const isOutage = telemetry?.is_outage ?? false;
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [telemetry]);

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-5 subtle-card-shadow flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
              <DatabaseIcon className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900 tracking-tight">
                Live Edge Error & Ingest Stream
              </h3>
              <p className="text-xs text-gray-500 font-medium">
                Query: &#123;app="ott-edge-router"&#125;
              </p>
            </div>
          </div>

          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            1Hz Live Stream
          </span>
        </div>

        {/* Live Structured Logs Feed */}
        <div
          ref={scrollContainerRef}
          className="mt-3.5 p-3 bg-gray-50 rounded-xl border border-gray-200/60 font-mono text-[11px] space-y-2 max-h-36 overflow-y-auto"
        >
          <div className="flex items-start gap-2 text-gray-600">
            <span className="text-gray-400 shrink-0">[14:04:15]</span>
            <span className="text-emerald-600 font-bold shrink-0">200 OK</span>
            <span className="truncate text-gray-700">
              Fastly Edge POP (iad-01) - chunk #89204 (48ms)
            </span>
          </div>

          {isOutage && (
            <div className="flex items-start gap-2 text-red-700 bg-red-50 p-1.5 rounded border border-red-200 font-semibold animate-pulse">
              <span className="text-red-400 shrink-0">[14:04:17]</span>
              <span className="text-red-600 font-bold shrink-0">502 BAD GATEWAY</span>
              <span className="truncate">
                Upstream transit connection failed (packet loss: 68%)
              </span>
            </div>
          )}

          <div className="flex items-start gap-2 text-gray-700">
            <span className="text-gray-400 shrink-0">[14:04:18]</span>
            <span className="text-blue-600 font-bold shrink-0">LOKI INGEST</span>
            <span className="truncate">
              {telemetry?.latest_log || "All edge delivery streams nominal"}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-500 font-medium flex items-center justify-between">
        <span>Prometheus & Loki Data Ingest</span>
        <span className="font-semibold text-emerald-600">100% Ingest Rate</span>
      </div>
    </div>
  );
}
