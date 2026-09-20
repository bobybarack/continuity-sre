"use client";

import React, { useRef, useEffect, useState } from "react";
import {
  ChartLineData01Icon,
  DatabaseIcon,
} from "hugeicons-react";
import { DoubleBezelCard } from "./DoubleBezelCard";
import { TelemetrySnapshot, GrafanaHealth } from "../types/telemetry";

interface GrafanaTelemetryPanelProps {
  telemetry: TelemetrySnapshot | null;
  history: TelemetrySnapshot[];
  grafanaHealth?: GrafanaHealth | null;
}

export function GrafanaTelemetryPanel({
  telemetry,
  history,
}: GrafanaTelemetryPanelProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<"vpf" | "latency" | "drm">("vpf");

  // Dynamic Chart Renderer
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Draw Cyber Background Grid
    ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 40) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = 0; y < h; y += 30) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    if (history.length < 2) return;

    // Extract values based on selected metric
    let values: number[] = [];
    let threshold = 1.0;
    let strokeColor = "#00f5a0";
    let unit = "%";

    if (selectedMetric === "vpf") {
      values = history.map((s) => s.video_playback_failures_pct);
      threshold = 1.0;
      strokeColor = "#ff3366";
      unit = "%";
    } else if (selectedMetric === "latency") {
      values = history.map((s) => s.cdn_egress_latency_ms);
      threshold = 150.0;
      strokeColor = "#00d2ff";
      unit = "ms";
    } else {
      values = history.map((s) => s.drm_handshake_ms);
      threshold = 400.0;
      strokeColor = "#6366f1";
      unit = "ms";
    }

    const maxVal = Math.max(...values, threshold * 1.25, 1);
    const minVal = 0;
    const range = maxVal - minVal;

    // Draw SLA Threshold Line
    const threshY = h - ((threshold - minVal) / range) * (h - 30) - 15;
    ctx.beginPath();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "rgba(255, 51, 102, 0.5)";
    ctx.lineWidth = 1.5;
    ctx.moveTo(0, threshY);
    ctx.lineTo(w, threshY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw SLA Threshold Label
    ctx.fillStyle = "rgba(255, 51, 102, 0.8)";
    ctx.font = "10px monospace";
    ctx.fillText(`SLA THRESHOLD: ${threshold}${unit}`, 10, threshY - 5);

    // Plot Time Series Line
    const step = (w - 20) / (values.length - 1);
    ctx.beginPath();
    values.forEach((v, i) => {
      const x = 10 + i * step;
      const y = h - ((v - minVal) / range) * (h - 30) - 15;
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        const prevX = 10 + (i - 1) * step;
        const prevV = values[i - 1];
        const prevY = h - ((prevV - minVal) / range) * (h - 30) - 15;
        const midX = (prevX + x) / 2;
        ctx.bezierCurveTo(midX, prevY, midX, y, x, y);
      }
    });

    const isSpike = Math.max(...values) > threshold;
    ctx.strokeStyle = isSpike ? "#ff3366" : strokeColor;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // Fill Gradient
    ctx.lineTo(10 + (values.length - 1) * step, h);
    ctx.lineTo(10, h);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, isSpike ? "rgba(255, 51, 102, 0.25)" : "rgba(0, 245, 160, 0.2)");
    grad.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = grad;
    ctx.fill();

    // Data points & tooltip markers
    const lastX = 10 + (values.length - 1) * step;
    const lastY = h - ((values[values.length - 1] - minVal) / range) * (h - 30) - 15;
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
    ctx.fillStyle = isSpike ? "#ff3366" : strokeColor;
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }, [history, selectedMetric]);

  return (
    <DoubleBezelCard innerClassName="p-4 flex flex-col justify-between h-full">
      <div>
        {/* Panel Header */}
        <div className="flex items-center justify-between flex-wrap gap-2 pb-3 border-b border-white/[0.08]">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-[#00d2ff]/10 border border-[#00d2ff]/20">
              <ChartLineData01Icon className="w-4 h-4 text-[#00d2ff]" />
            </div>
            <div>
              <h3 className="text-xs font-bold font-mono text-white tracking-wider uppercase">
                Grafana Cloud Live Telemetry
              </h3>
              <p className="text-[10px] font-mono text-white/50">
                Prometheus PromQL & Loki Log Streams
              </p>
            </div>
          </div>

          {/* Metric Selector Tabs */}
          <div className="flex items-center gap-1 p-0.5 rounded-lg bg-white/[0.04] border border-white/10 text-[10px] font-mono">
            <button
              onClick={() => setSelectedMetric("vpf")}
              className={`px-2 py-1 rounded transition-all ${
                selectedMetric === "vpf"
                  ? "bg-[#ff3366]/20 text-[#ff3366] font-bold border border-[#ff3366]/30"
                  : "text-white/60 hover:text-white"
              }`}
            >
              VPF %
            </button>
            <button
              onClick={() => setSelectedMetric("latency")}
              className={`px-2 py-1 rounded transition-all ${
                selectedMetric === "latency"
                  ? "bg-[#00d2ff]/20 text-[#00d2ff] font-bold border border-[#00d2ff]/30"
                  : "text-white/60 hover:text-white"
              }`}
            >
              Latency
            </button>
            <button
              onClick={() => setSelectedMetric("drm")}
              className={`px-2 py-1 rounded transition-all ${
                selectedMetric === "drm"
                  ? "bg-[#6366f1]/20 text-[#6366f1] font-bold border border-[#6366f1]/30"
                  : "text-white/60 hover:text-white"
              }`}
            >
              DRM Time
            </button>
          </div>
        </div>

        {/* Live Canvas Chart */}
        <div className="relative mt-3 rounded-xl bg-black/40 border border-white/[0.06] p-2 overflow-hidden">
          <div className="flex items-center justify-between text-[11px] font-mono text-white/60 mb-1 px-1">
            <span className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00d2ff] animate-ping" />
              PromQL: {selectedMetric === "vpf" ? "rate(vpf_total[1m])" : selectedMetric === "latency" ? "ott_cdn_latency_ms" : "ott_drm_handshake_ms"}
            </span>
            <span className="text-white/40">Window: Last 60s (1Hz)</span>
          </div>

          <canvas
            ref={canvasRef}
            width={480}
            height={160}
            className="w-full h-40 block"
          />
        </div>

        {/* Loki Structured Live Logs Stream */}
        <div className="mt-3.5">
          <div className="flex items-center justify-between text-xs font-mono text-white/50 mb-1.5">
            <span className="flex items-center gap-1.5 uppercase">
              <DatabaseIcon className="w-3.5 h-3.5 text-[#00d2ff]" />
              Loki Edge Logs Stream
            </span>
            <span className="text-[10px] text-white/40 font-mono">
              Query: &#123;app=&quot;edge-cdn&quot;&#125;
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-black/60 border border-white/[0.08] font-mono text-[11px] space-y-1.5 max-h-28 overflow-y-auto">
            <div className="text-white/70 flex items-start gap-2">
              <span className="text-white/30 shrink-0">[14:04:18]</span>
              <span className="text-[#00f5a0] shrink-0">200 OK</span>
              <span className="truncate text-white/80">Fastly Edge: Chunk #89204 segment.ts (48ms)</span>
            </div>
            {telemetry?.is_outage && (
              <div className="text-[#ff3366] flex items-start gap-2 bg-[#ff3366]/10 p-1 rounded border border-[#ff3366]/20">
                <span className="text-white/40 shrink-0">[14:04:19]</span>
                <span className="font-bold shrink-0">502 BAD GATEWAY</span>
                <span className="truncate">Upstream transit link connection refused (packet loss: 68%)</span>
              </div>
            )}
            <div className="text-white/60 flex items-start gap-2">
              <span className="text-white/30 shrink-0">[14:04:20]</span>
              <span className="text-[#00d2ff] shrink-0">LOKI INGEST</span>
              <span className="truncate text-white/70">{telemetry?.latest_log || "Telemetry healthy across edge POPs"}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Grafana Cloud Datasources Health Bar */}
      <div className="mt-3 pt-2.5 border-t border-white/[0.06] grid grid-cols-3 gap-2 text-center text-[10px] font-mono">
        <div className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <div className="text-white/40">Prometheus</div>
          <div className="text-[#00f5a0] font-semibold mt-0.5 flex items-center justify-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00f5a0]" />
            Active (12ms)
          </div>
        </div>

        <div className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <div className="text-white/40">Loki Logs</div>
          <div className="text-[#00f5a0] font-semibold mt-0.5 flex items-center justify-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00f5a0]" />
            Active (18ms)
          </div>
        </div>

        <div className="p-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <div className="text-white/40">Grafana IRM</div>
          <div className="text-[#00d2ff] font-semibold mt-0.5 flex items-center justify-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00d2ff]" />
            Bound (MCP)
          </div>
        </div>
      </div>
    </DoubleBezelCard>
  );
}
