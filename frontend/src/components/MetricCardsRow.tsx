"use client";

import React from "react";
import { TelemetrySnapshot } from "../types/telemetry";

interface MetricCardsRowProps {
  current: TelemetrySnapshot | null;
}

export function MetricCardsRow({ current }: MetricCardsRowProps) {
  const vpf = current?.video_playback_failures_pct ?? 0.18;
  const latency = current?.cdn_egress_latency_ms ?? 48.0;
  const drm = current?.drm_handshake_ms ?? 120.0;
  const viewers = current?.active_viewers ?? 4281902;
  const buffer = current?.buffer_health_sec ?? 28.4;

  const isVpfSpike = vpf > 1.0;
  const isLatencySpike = latency > 200.0;
  const isDrmSpike = drm > 500.0;
  const isBufferLow = buffer < 10.0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      {/* 1. Playback Failure Rate (VPF) */}
      <div className="bg-white border border-gray-200/80 rounded-2xl p-4 subtle-card-shadow hover-card-lift flex flex-col justify-between">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-500">
            Playback Failure Rate
          </span>
          <span
            className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${
              isVpfSpike
                ? "bg-red-50 text-red-700 border-red-200"
                : "bg-emerald-50 text-emerald-700 border-emerald-200"
            }`}
          >
            {isVpfSpike ? "Critical Breach" : "Optimal (<0.5%)"}
          </span>
        </div>
        <div>
          <div className="flex items-baseline gap-1">
            <span
              className={`text-2xl lg:text-3xl font-bold tracking-tight ${
                isVpfSpike ? "text-red-600" : "text-gray-900"
              }`}
            >
              {vpf.toFixed(2)}%
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {isVpfSpike ? "SLA Threshold Breached" : "Target: Under 0.50% SLA"}
          </p>
        </div>
      </div>

      {/* 2. CDN Egress Latency */}
      <div className="bg-white border border-gray-200/80 rounded-2xl p-4 subtle-card-shadow hover-card-lift flex flex-col justify-between">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-500">
            CDN Edge Latency
          </span>
          <span
            className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${
              isLatencySpike
                ? "bg-red-50 text-red-700 border-red-200"
                : "bg-emerald-50 text-emerald-700 border-emerald-200"
            }`}
          >
            {current?.primary_cdn || "Fastly"}
          </span>
        </div>
        <div>
          <div className="flex items-baseline gap-1">
            <span
              className={`text-2xl lg:text-3xl font-bold tracking-tight ${
                isLatencySpike ? "text-red-600" : "text-gray-900"
              }`}
            >
              {latency.toFixed(0)}
            </span>
            <span className="text-xs text-gray-500 font-semibold">ms</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {isLatencySpike ? "High Transit Congestion" : "Nominal Edge Egress"}
          </p>
        </div>
      </div>

      {/* 3. DRM Handshake Duration */}
      <div className="bg-white border border-gray-200/80 rounded-2xl p-4 subtle-card-shadow hover-card-lift flex flex-col justify-between">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-500">
            DRM Auth Handshake
          </span>
          <span
            className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${
              isDrmSpike
                ? "bg-red-50 text-red-700 border-red-200"
                : "bg-emerald-50 text-emerald-700 border-emerald-200"
            }`}
          >
            Widevine L1
          </span>
        </div>
        <div>
          <div className="flex items-baseline gap-1">
            <span
              className={`text-2xl lg:text-3xl font-bold tracking-tight ${
                isDrmSpike ? "text-red-600" : "text-gray-900"
              }`}
            >
              {drm.toFixed(0)}
            </span>
            <span className="text-xs text-gray-500 font-semibold">ms</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {isDrmSpike ? "License Server Timeout" : "License Key Verified"}
          </p>
        </div>
      </div>

      {/* 4. Active Concurrent Viewers */}
      <div className="bg-white border border-gray-200/80 rounded-2xl p-4 subtle-card-shadow hover-card-lift flex flex-col justify-between">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-500">
            Concurrent Viewers
          </span>
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            Live Audience
          </span>
        </div>
        <div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl lg:text-3xl font-bold tracking-tight text-gray-900">
              {viewers.toLocaleString()}
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {(viewers / 1_000_000).toFixed(2)}M Active Viewers
          </p>
        </div>
      </div>

      {/* 5. Forward Buffer Health */}
      <div className="bg-white border border-gray-200/80 rounded-2xl p-4 subtle-card-shadow hover-card-lift flex flex-col justify-between">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-500">
            Forward Buffer Health
          </span>
          <span
            className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${
              isBufferLow
                ? "bg-red-50 text-red-700 border-red-200"
                : "bg-emerald-50 text-emerald-700 border-emerald-200"
            }`}
          >
            4K HEVC
          </span>
        </div>
        <div>
          <div className="flex items-baseline gap-1">
            <span
              className={`text-2xl lg:text-3xl font-bold tracking-tight ${
                isBufferLow ? "text-red-600" : "text-gray-900"
              }`}
            >
              {buffer.toFixed(1)}
            </span>
            <span className="text-xs text-gray-500 font-semibold">sec</span>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {isBufferLow ? "Buffer Dropping Fast" : "Buffer Healthy (>20s)"}
          </p>
        </div>
      </div>
    </div>
  );
}
