"use client";

import React, { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  PlayIcon,
  PauseIcon,
  Film01Icon,
  Wifi01Icon,
  Radio01Icon,
  Alert01Icon,
  CheckmarkCircle01Icon,
  Shield01Icon,
  Activity01Icon,
  FlashIcon,
} from "hugeicons-react";
import { DoubleBezelCard } from "./DoubleBezelCard";
import { TelemetrySnapshot } from "../types/telemetry";

interface LiveStreamPlayerProps {
  telemetry: TelemetrySnapshot | null;
}

export function LiveStreamPlayer({ telemetry }: LiveStreamPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [isVideoLoading, setIsVideoLoading] = useState<boolean>(true);
  const [hasVideoError, setHasVideoError] = useState<boolean>(false);
  const [showAudioViz, setShowAudioViz] = useState<boolean>(true);

  const isOutage = telemetry?.is_outage ?? false;
  const isRemediated = telemetry?.status_label === "RECOVERED";
  const bufferSec = telemetry?.buffer_health_sec ?? 28.4;
  const bitrate = telemetry?.avg_bitrate_mbps ?? 14.8;
  const activeCdn =
    telemetry?.secondary_traffic_pct && telemetry.secondary_traffic_pct > 0
      ? `${telemetry.secondary_cdn} (${telemetry.secondary_traffic_pct}% Failover)`
      : `${telemetry?.primary_cdn || "Fastly Edge"} (100% Primary)`;

  // Video playback lifecycle tied to outage state and user toggle
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isOutage) {
      video.pause();
    } else if (isPlaying) {
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  }, [isPlaying, isOutage]);

  // Audio Spectrum Frequency Visualizer
  useEffect(() => {
    const canvas = audioCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let t = 0;

    const renderAudio = () => {
      t += 0.08;
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const barCount = 28;
      const barWidth = 3;
      const gap = (w - barCount * barWidth) / (barCount - 1);

      for (let i = 0; i < barCount; i++) {
        const freq = isOutage
          ? Math.random() * 0.2
          : 0.3 + 0.6 * Math.abs(Math.sin(t + i * 0.35) * Math.cos(t * 0.5 + i * 0.1));
        const barHeight = Math.max(3, freq * (h - 4));
        const x = i * (barWidth + gap);
        const y = h - barHeight;

        ctx.fillStyle = isOutage
          ? "#ff3366"
          : isRemediated
          ? "#00d2ff"
          : "#00f5a0";
        ctx.fillRect(x, y, barWidth, barHeight);
      }

      if (isPlaying) {
        animId = requestAnimationFrame(renderAudio);
      }
    };

    renderAudio();
    return () => cancelAnimationFrame(animId);
  }, [isPlaying, isOutage, isRemediated]);

  return (
    <DoubleBezelCard
      glowColor={isOutage ? "red" : isRemediated ? "blue" : "none"}
      innerClassName="relative flex flex-col"
    >
      {/* Stream Header Bar */}
      <div className="px-4 py-3 bg-[#080c14]/90 border-b border-white/[0.08] flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#ff3366] animate-pulse" />
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight flex items-center gap-2 font-mono">
              Continuity Premiere: Global Broadcast
              <span className="text-[11px] font-mono font-normal text-white/50">
                (Live 4K UHD Stream)
              </span>
            </h2>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="px-2 py-0.5 rounded bg-white/[0.06] border border-white/10 text-white/80">
            3840x2160 @ 60fps
          </span>
          <span className="px-2 py-0.5 rounded bg-[#00d2ff]/10 border border-[#00d2ff]/20 text-[#00d2ff]">
            Dolby Atmos 5.1
          </span>
          <span className="px-2 py-0.5 rounded bg-[#00f5a0]/10 border border-[#00f5a0]/20 text-[#00f5a0]">
            HEVC HDR10+
          </span>
        </div>
      </div>

      {/* Video Viewport Area */}
      <div className="relative aspect-video w-full bg-black flex items-center justify-center overflow-hidden">
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
              <div className="p-3 rounded-full bg-amber-500/10 border border-amber-500/30 mb-2">
                <Radio01Icon className="w-6 h-6 text-amber-400" />
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

        {/* DRM Security Overlay Pill */}
        <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-black/60 backdrop-blur-md border border-white/10 text-[11px] font-mono text-white/70">
          <Shield01Icon className="w-3.5 h-3.5 text-[#00d2ff]" />
          <span>DRM Widevine L1 • Hardware Secure</span>
        </div>

        {/* Live Active Edge Node Tag */}
        <div className="absolute top-3 right-3 flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-black/60 backdrop-blur-md border border-white/10 text-[11px] font-mono">
          <span
            className={`w-2 h-2 rounded-full ${
              isOutage ? "bg-[#ff3366] animate-ping" : "bg-[#00f5a0]"
            }`}
          />
          <span className="text-white/60">Edge Route:</span>
          <span className={isOutage ? "text-[#ff3366] font-bold" : "text-white"}>
            {activeCdn}
          </span>
        </div>

        {/* Outage / Buffering Warning Overlay */}
        <AnimatePresence>
          {isOutage && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 bg-black/75 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center"
            >
              <div className="relative p-3.5 rounded-2xl bg-[#ff3366]/20 border border-[#ff3366]/50 mb-3 alert-pulse-red">
                <Alert01Icon className="w-9 h-9 text-[#ff3366] animate-spin" />
              </div>
              <h3 className="text-base sm:text-lg font-bold font-mono text-white tracking-wider uppercase">
                CRITICAL EDGE BOTTLENECK / BUFFER UNDERFLOW
              </h3>
              <p className="text-xs font-mono text-white/70 max-w-md mt-1 leading-relaxed">
                {telemetry?.chaos_mode === "DRM_TIMEOUT"
                  ? `Widevine key proxy acquisition timeout. Forward buffer draining to ${bufferSec.toFixed(1)}s.`
                  : telemetry?.chaos_mode === "ISP_PEERING_DROP"
                  ? `Tier-1 BGP peering drop (ASN 3356). Bitrate degradation; buffer collapsing to ${bufferSec.toFixed(1)}s.`
                  : `Primary Edge CDN transit collapse. Playback failure rate exceeded 4.8%. Forward buffer collapsing to ${bufferSec.toFixed(1)}s.`}
              </p>
              <div className="mt-3.5 flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#ff3366]/30 border border-[#ff3366]/60 text-xs font-mono text-white">
                <span className="w-2 h-2 rounded-full bg-[#ff3366] animate-ping" />
                <span>Autonomous Gemini SRE failover initiating...</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Stream Restored Success Overlay Banner */}
        <AnimatePresence>
          {isRemediated && !isOutage && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute bottom-16 left-4 right-4 flex items-center justify-between px-4 py-2.5 rounded-xl bg-[#080c14]/95 backdrop-blur-xl border border-[#00d2ff]/40 shadow-[0_0_24px_rgba(0,210,255,0.25)] text-xs font-mono text-white"
            >
              <div className="flex items-center gap-2.5">
                <CheckmarkCircle01Icon className="w-4 h-4 text-[#00f5a0]" />
                <span>Failover Active: 80% egress shifted to Akamai Cloud Run. Playback SLA fully restored.</span>
              </div>
              <span className="text-[#00d2ff] font-bold">MTTR: 4.2s</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Player Controls Bar */}
        <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/95 via-black/60 to-transparent flex items-center justify-between gap-3 text-white text-xs font-mono">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 border border-white/15 transition-all"
            >
              {isPlaying ? (
                <PauseIcon className="w-4 h-4 text-white" />
              ) : (
                <PlayIcon className="w-4 h-4 text-white" />
              )}
            </button>
            <span className="text-white/60">01:42:18 / 02:46:00</span>
          </div>

          {/* Forward Buffer Progress Bar */}
          <div className="flex-1 max-w-xs flex items-center gap-2">
            <span className="text-[10px] text-white/50 uppercase">Buffer:</span>
            <div className="flex-1 h-2 rounded-full bg-white/10 overflow-hidden border border-white/10">
              <div
                className={`h-full transition-all duration-300 ${
                  isOutage
                    ? "bg-[#ff3366]"
                    : bufferSec < 15
                    ? "bg-[#ffb800]"
                    : "bg-[#00f5a0]"
                }`}
                style={{ width: `${Math.min(100, (bufferSec / 30.0) * 100)}%` }}
              />
            </div>
            <span className="text-[11px] font-bold text-white/80">
              {bufferSec.toFixed(1)}s
            </span>
          </div>

          {/* Audio Spectrum Bars */}
          <div className="hidden sm:flex items-center gap-2 bg-black/40 px-2 py-1 rounded-lg border border-white/10">
            <canvas
              ref={audioCanvasRef}
              width={80}
              height={16}
              className="w-20 h-4 block"
            />
            <span className="text-[10px] text-white/50">Atmos</span>
          </div>

          <div className="flex items-center gap-2 text-white/60">
            <span>{bitrate.toFixed(1)} Mbps</span>
          </div>
        </div>
      </div>
    </DoubleBezelCard>
  );
}
