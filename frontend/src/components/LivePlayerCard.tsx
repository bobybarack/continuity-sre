"use client";

import React, { useRef, useEffect, useState } from "react";
import { TelemetrySnapshot } from "../types/telemetry";

interface LivePlayerCardProps {
  telemetry: TelemetrySnapshot | null;
}

export function LivePlayerCard({ telemetry }: LivePlayerCardProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [isVideoLoading, setIsVideoLoading] = useState<boolean>(true);
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
              onLoadStart={() => setIsVideoLoading(true)}
              onLoadedData={() => setIsVideoLoading(false)}
              onCanPlay={() => setIsVideoLoading(false)}
              onPlaying={() => setIsVideoLoading(false)}
              onWaiting={() => setIsVideoLoading(true)}
              onError={() => {
                setHasVideoError(true);
                setIsVideoLoading(false);
              }}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="relative w-full h-full flex flex-col items-center justify-center text-center p-6 bg-[#0a0f1d] overflow-hidden">
              <img
                src="/assets/premiere_poster.jpg"
                alt="Broadcast Poster"
                className="absolute inset-0 w-full h-full object-cover filter blur-lg opacity-30 scale-105"
              />
              <div className="relative z-10 flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/30 mb-2 flex items-center justify-center">
                  <span className="w-3 h-3 rounded-full bg-amber-400 animate-pulse" />
                </div>
                <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider">
                  Broadcast Signal Standby
                </h4>
                <p className="text-[11px] font-mono text-gray-400 mt-1 max-w-xs">
                  Edge stream relay reconnecting. Standby for frame sync.
                </p>
                <button
                  onClick={() => {
                    setHasVideoError(false);
                    setIsVideoLoading(true);
                    if (videoRef.current) {
                      videoRef.current.load();
                    }
                  }}
                  className="mt-3 px-3 py-1 rounded text-[11px] font-mono font-semibold bg-white/10 hover:bg-white/20 border border-white/20 text-white transition-all cursor-pointer"
                >
                  Reconnect Feed
                </button>
              </div>
            </div>
          )}

          {/* Blurred Pre-Load Screen Overlay */}
          <div
            className={`absolute inset-0 z-10 bg-black/60 backdrop-blur-xl transition-opacity duration-700 flex flex-col items-center justify-center p-6 text-center select-none ${
              isVideoLoading && !isOutage
                ? "opacity-100 pointer-events-auto"
                : "opacity-0 pointer-events-none"
            }`}
          >
            {/* Background blurred poster hint */}
            <img
              src="/assets/premiere_poster.jpg"
              alt=""
              className="absolute inset-0 w-full h-full object-cover filter blur-xl scale-110 opacity-40 pointer-events-none"
            />

            {/* Glowing Radar Spinner */}
            <div className="relative z-10 flex items-center justify-center mb-3">
              <div className="absolute w-12 h-12 rounded-full bg-cyan-500/20 animate-ping" />
              <div className="w-10 h-10 rounded-full border-2 border-cyan-400/30 border-t-cyan-400 animate-spin flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-cyan-400" />
              </div>
            </div>

            {/* Status Information */}
            <div className="relative z-10 flex flex-col items-center">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                <span className="text-xs font-mono font-bold tracking-widest text-cyan-300 uppercase">
                  Synchronizing 4K Broadcast Feed
                </span>
              </div>
              <p className="text-[11px] font-mono text-gray-300 max-w-xs leading-relaxed">
                Handshaking DRM license and priming edge playback buffers...
              </p>

              {/* Shimmer Progress Bar */}
              <div className="w-44 h-1.5 bg-white/10 rounded-full overflow-hidden mt-3 border border-white/10">
                <div className="h-full bg-gradient-to-r from-cyan-500 via-emerald-400 to-cyan-400 animate-pulse rounded-full w-4/5" />
              </div>

              {/* Technical Spec Badges */}
              <div className="flex items-center gap-1.5 mt-3 text-[10px] font-mono text-white/70">
                <span className="px-2 py-0.5 rounded bg-white/10 border border-white/10">
                  3840x2160 UHD
                </span>
                <span className="px-2 py-0.5 rounded bg-white/10 border border-white/10">
                  60 FPS
                </span>
                <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  Fastly Edge
                </span>
              </div>
            </div>
          </div>

          {/* Outage Banner */}
          {isOutage && (
            <div className="absolute inset-0 bg-black/75 flex flex-col items-center justify-center p-4 text-center">
              <div className="w-8 h-8 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center text-red-500 font-bold text-sm mb-1 animate-pulse">
                !
              </div>
              <p className="text-xs font-bold text-white uppercase">
                {telemetry?.chaos_mode === "DRM_TIMEOUT"
                  ? "DRM License Acquisition Stall"
                  : telemetry?.chaos_mode === "ISP_PEERING_DROP"
                  ? "Transit Peering Degradation"
                  : "Edge Buffer Stall Detected"}
              </p>
              <p className="text-[11px] text-gray-300 mt-0.5">
                {telemetry?.chaos_mode === "DRM_TIMEOUT"
                  ? "Widevine key authentication proxy timeout"
                  : telemetry?.chaos_mode === "ISP_PEERING_DROP"
                  ? "Tier-1 BGP transit peering packet loss (ASN 3356)"
                  : "Primary edge CDN upstream connection failure (HTTP 502)"}
              </p>
            </div>
          )}

          {/* Bottom Bar Controls */}
          <div className="absolute bottom-0 left-0 right-0 p-2.5 bg-gradient-to-t from-black/80 to-transparent flex items-center justify-between text-white text-xs">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="px-2 py-0.5 rounded bg-white/20 hover:bg-white/30 transition-all font-mono text-[11px]"
            >
              {isPlaying ? "❚❚" : "▶"}
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
