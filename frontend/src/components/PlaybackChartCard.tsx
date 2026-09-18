"use client";

import React, { useRef, useEffect, useState } from "react";
import { TelemetrySnapshot } from "../types/telemetry";

interface PlaybackChartCardProps {
  telemetry: TelemetrySnapshot | null;
  history: TelemetrySnapshot[];
}

export function PlaybackChartCard({
  telemetry,
  history,
}: PlaybackChartCardProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [activeMetric, setActiveMetric] = useState<"vpf" | "latency">("vpf");

  const vpf = telemetry?.video_playback_failures_pct ?? 0.18;
  const isOutage = telemetry?.is_outage ?? false;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Light subtle grid
    ctx.strokeStyle = "rgba(0, 0, 0, 0.04)";
    ctx.lineWidth = 1;
    for (let y = 30; y < h - 20; y += 35) {
      ctx.beginPath();
      ctx.moveTo(35, y);
      ctx.lineTo(w - 15, y);
      ctx.stroke();
    }

    if (history.length < 2) return;

    const values =
      activeMetric === "vpf"
        ? history.map((s) => s.video_playback_failures_pct)
        : history.map((s) => s.cdn_egress_latency_ms);

    const threshold = activeMetric === "vpf" ? 1.0 : 150.0;
    const maxVal = Math.max(...values, threshold * 1.3, 1);
    const minVal = 0;
    const range = maxVal - minVal;

    // Draw SLA Threshold Line
    const threshY = h - 25 - ((threshold - minVal) / range) * (h - 55);
    ctx.beginPath();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(239, 68, 68, 0.6)";
    ctx.lineWidth = 1.5;
    ctx.moveTo(35, threshY);
    ctx.lineTo(w - 15, threshY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw SLA Label
    ctx.fillStyle = "#ef4444";
    ctx.font = "10px sans-serif";
    ctx.fillText(
      `SLA LIMIT: ${threshold}${activeMetric === "vpf" ? "%" : "ms"}`,
      40,
      threshY - 5
    );

    // Draw Spline Curve
    const step = (w - 50) / (values.length - 1);
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = 35 + i * step;
      const y = h - 25 - ((v - minVal) / range) * (h - 55);
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        const prevX = 35 + (i - 1) * step;
        const prevV = values[i - 1];
        const prevY = h - 25 - ((prevV - minVal) / range) * (h - 55);
        const midX = (prevX + x) / 2;
        ctx.bezierCurveTo(midX, prevY, midX, y, x, y);
      }
    });

    const isSpike = Math.max(...values) > threshold;
    ctx.strokeStyle = isSpike ? "#ef4444" : "#10b981";
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Fill Gradient
    ctx.lineTo(35 + (values.length - 1) * step, h - 25);
    ctx.lineTo(35, h - 25);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 30, 0, h - 25);
    grad.addColorStop(
      0,
      isSpike ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)"
    );
    grad.addColorStop(1, "rgba(255, 255, 255, 0)");
    ctx.fillStyle = grad;
    ctx.fill();

    // Last Data Point
    const lastX = 35 + (values.length - 1) * step;
    const lastY =
      h - 25 - ((values[values.length - 1] - minVal) / range) * (h - 55);
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = isSpike ? "#ef4444" : "#10b981";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.stroke();
  }, [history, activeMetric]);

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-5 subtle-card-shadow flex flex-col justify-between h-full">
      <div>
        {/* Chart Header */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pb-3 border-b border-gray-100">
          <div>
            <h3 className="text-sm font-bold text-gray-900 tracking-tight">
              Playback Quality & Failure Rate
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Real-time video playback failures vs 1.00% SLA limit (60s rolling)
            </p>
          </div>

          <div className="flex items-center gap-2.5 ml-auto">
            <div className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl text-xs font-semibold">
              <button
                onClick={() => setActiveMetric("vpf")}
                className={`px-2.5 py-1 rounded-lg transition-all text-[11px] ${
                  activeMetric === "vpf"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-900"
                }`}
              >
                VPF (%)
              </button>
              <button
                onClick={() => setActiveMetric("latency")}
                className={`px-2.5 py-1 rounded-lg transition-all text-[11px] ${
                  activeMetric === "latency"
                    ? "bg-white text-gray-900 shadow-sm"
                    : "text-gray-500 hover:text-gray-900"
                }`}
              >
                Latency (ms)
              </button>
            </div>

            <div className="text-right pl-1">
              <span className="text-[10px] text-gray-400 block font-medium leading-none">
                Current
              </span>
              <span
                className={`text-sm font-bold leading-tight ${
                  isOutage ? "text-red-600" : "text-emerald-700"
                }`}
              >
                {activeMetric === "vpf"
                  ? `${vpf.toFixed(2)}%`
                  : `${(telemetry?.cdn_egress_latency_ms ?? 48).toFixed(0)}ms`}
              </span>
            </div>
          </div>
        </div>

        {/* Chart Canvas */}
        <div className="relative mt-3">
          <canvas
            ref={canvasRef}
            width={620}
            height={180}
            className="w-full h-36 sm:h-40 block"
          />
          <div className="flex items-center justify-between text-[11px] text-gray-400 font-medium px-4 sm:px-8 mt-1">
            <span>60s ago</span>
            <span>45s</span>
            <span>30s</span>
            <span>15s</span>
            <span>Now (Live)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
