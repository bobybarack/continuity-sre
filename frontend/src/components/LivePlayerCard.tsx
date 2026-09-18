"use client";

import React, { useRef, useEffect, useState } from "react";
import { PlayIcon, PauseIcon, Alert01Icon, CheckmarkCircle01Icon } from "hugeicons-react";
import { TelemetrySnapshot } from "../types/telemetry";

interface LivePlayerCardProps {
  telemetry: TelemetrySnapshot | null;
}

export function LivePlayerCard({ telemetry }: LivePlayerCardProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [hasVideoError, setHasVideoError] = useState<boolean>(false);

  const isOutage = telemetry?.is_outage ?? false;
  const isRecovered = telemetry?.status_label === "RECOVERED";
  const bufferSec = telemetry?.buffer_health_sec ?? 28.4;
  const bitrate = telemetry?.avg_bitrate_mbps ?? 14.8;
  const activeCdn =
    telemetry?.secondary_traffic_pct && telemetry.secondary_traffic_pct > 0
      ? `${telemetry.secondary_cdn} (${telemetry.secondary_traffic_pct}% Failover)`
      : `${telemetry?.primary_cdn || "Fastly"} (100% Primary)`;

  // Video playback lifecycle tied to outage state and user toggle
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isOutage) {
      video.pause();
    } else if (isPlaying) {
      video.play().catch(() => {
        // Autoplay may require user gesture on some browsers if unmuted
      });
    } else {
      video.pause();
    }
  }, [isPlaying, isOutage]);

  // Fallback procedural canvas rendering if video asset fails to load
  useEffect(() => {
    if (!hasVideoError) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let t = 0;

    const render = () => {
      t += 0.015;
      const w = canvas.width;
      const h = canvas.height;

      // Dark cinematic canvas
      const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
      bgGrad.addColorStop(0, "#0a0f1d");
      bgGrad.addColorStop(0.5, "#141c2e");
      bgGrad.addColorStop(1, "#26130b");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // Planet horizon
      const planetGrad = ctx.createRadialGradient(
        w * 0.75,
        h * 0.4,
        20,
        w * 0.75,
        h * 0.4,
        140
      );
      planetGrad.addColorStop(0, "#ffb800");
      planetGrad.addColorStop(0.4, "#e65c00");
      planetGrad.addColorStop(0.8, "#6b1402");
      planetGrad.addColorStop(1, "transparent");
      ctx.fillStyle = planetGrad;
      ctx.beginPath();
      ctx.arc(w * 0.75, h * 0.4, 110, 0, Math.PI * 2);
      ctx.fill();

      // Desert sand ridges
      ctx.fillStyle = "#120803";
      ctx.beginPath();
      ctx.moveTo(0, h);
      for (let x = 0; x <= w; x += 10) {
        const y =
          h * 0.75 + Math.sin(x * 0.01 + t * 0.4) * 12 + Math.cos(x * 0.02) * 6;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(w, h);
      ctx.closePath();
      ctx.fill();

      // Glitch FX if outage
      if (isOutage) {
        ctx.fillStyle = "rgba(239, 68, 68, 0.2)";
        ctx.fillRect(0, 0, w, h);
      }

      if (isPlaying) {
        animId = requestAnimationFrame(render);
      }
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [hasVideoError, isPlaying, isOutage]);

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-5 subtle-card-shadow flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div>
            <h3 className="text-sm font-bold text-gray-900 tracking-tight">
              Live Stream Monitor
            </h3>
            <p className="text-xs text-gray-500 mt-0.5 font-medium">
              Spider-Man: Brand New Day (4K UHD 60fps)
            </p>
          </div>

          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            {bitrate.toFixed(1)} Mbps
          </span>
        </div>

        {/* Video Container */}
        <div className="relative aspect-video max-h-[360px] w-full rounded-xl overflow-hidden mt-3 bg-black">
          {!hasVideoError ? (
            <video
              ref={videoRef}
              src="/assets/premiere_stream.mp4"
              poster="/assets/premiere_poster.jpg"
              autoPlay
              loop
              muted
              playsInline
              preload="auto"
              onError={() => setHasVideoError(true)}
              className="w-full h-full object-cover"
            />
          ) : (
            <canvas
              ref={canvasRef}
              width={800}
              height={450}
              className="w-full h-full object-cover"
            />
          )}

          {/* Outage Banner */}
          {isOutage && (
            <div className="absolute inset-0 bg-black/75 flex flex-col items-center justify-center p-4 text-center">
              <Alert01Icon className="w-8 h-8 text-red-500 animate-bounce mb-1" />
              <p className="text-xs font-bold text-white uppercase">
                Edge Buffer Stall Detected
              </p>
              <p className="text-[11px] text-gray-300 mt-0.5">
                Fastly POP 'iad-01' packet loss
              </p>
            </div>
          )}

          {/* Bottom Bar Controls */}
          <div className="absolute bottom-0 left-0 right-0 p-2.5 bg-gradient-to-t from-black/80 to-transparent flex items-center justify-between text-white text-xs">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-1 rounded bg-white/20 hover:bg-white/30 transition-all"
            >
              {isPlaying ? (
                <PauseIcon className="w-3.5 h-3.5" />
              ) : (
                <PlayIcon className="w-3.5 h-3.5" />
              )}
            </button>

            <span className="text-[11px] text-gray-300">
              Route: <span className="font-semibold text-white">{activeCdn}</span>
            </span>
          </div>
        </div>

        {/* Forward Buffer Progress */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs font-medium text-gray-500 mb-1">
            <span>Forward Playback Buffer</span>
            <span
              className={`font-bold ${
                isOutage ? "text-red-600" : "text-gray-900"
              }`}
            >
              {bufferSec.toFixed(1)}s
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden border border-gray-200">
            <div
              className={`h-full transition-all duration-300 ${
                isOutage ? "bg-red-500" : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(100, (bufferSec / 30.0) * 100)}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
