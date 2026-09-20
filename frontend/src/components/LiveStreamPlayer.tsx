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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
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

  // Cinematic canvas render loop (fallback if video fails to load)
  useEffect(() => {
    if (!hasVideoError) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    let t = 0;

    const stars: { x: number; y: number; s: number; o: number }[] = [];
    for (let i = 0; i < 90; i++) {
      stars.push({
        x: Math.random() * 800,
        y: Math.random() * 450,
        s: Math.random() * 2 + 0.5,
        o: Math.random() * 0.8 + 0.2,
      });
    }

    const render = () => {
      t += 0.012;
      const w = canvas.width;
      const h = canvas.height;

      // Deep Space Gradient
      const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
      bgGrad.addColorStop(0, "#050811");
      bgGrad.addColorStop(0.45, "#0b1220");
      bgGrad.addColorStop(0.8, "#26130b");
      bgGrad.addColorStop(1, "#120803");
      ctx.fillStyle = bgGrad;
      ctx.fillRect(0, 0, w, h);

      // Starfield
      stars.forEach((st) => {
        ctx.fillStyle = `rgba(255, 255, 255, ${
          st.o * (0.75 + 0.25 * Math.sin(t * 1.5 + st.x))
        })`;
        ctx.fillRect(st.x, st.y, st.s, st.s);
      });

      // Giant Eclipse Horizon Planet
      const planetGrad = ctx.createRadialGradient(
        w * 0.74,
        h * 0.38,
        25,
        w * 0.74,
        h * 0.38,
        170
      );
      planetGrad.addColorStop(0, "#ffb800");
      planetGrad.addColorStop(0.28, "#e65c00");
      planetGrad.addColorStop(0.68, "#6b1402");
      planetGrad.addColorStop(1, "transparent");
      ctx.fillStyle = planetGrad;
      ctx.beginPath();
      ctx.arc(w * 0.74, h * 0.38, 135, 0, Math.PI * 2);
      ctx.fill();

      // Atmospheric Ring
      ctx.strokeStyle = "rgba(255, 184, 0, 0.3)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.ellipse(w * 0.74, h * 0.38, 185, 42, -0.22, 0, Math.PI * 2);
      ctx.stroke();

      // Distant Arrakis Mountain Range
      ctx.fillStyle = "#180d07";
      ctx.beginPath();
      ctx.moveTo(0, h);
      for (let x = 0; x <= w; x += 15) {
        const y =
          h * 0.68 + Math.sin(x * 0.007 + t * 0.3) * 14 + Math.cos(x * 0.015) * 7;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(w, h);
      ctx.closePath();
      ctx.fill();

      // Rolling Foreground Dunes
      ctx.fillStyle = "#0d0502";
      ctx.beginPath();
      ctx.moveTo(0, h);
      for (let x = 0; x <= w; x += 12) {
        const y =
          h * 0.82 + Math.sin(x * 0.011 - t * 0.6) * 12 + Math.cos(x * 0.02) * 5;
        ctx.lineTo(x, y);
      }
      ctx.lineTo(w, h);
      ctx.closePath();
      ctx.fill();

      // Outage Glitch Distortion
      if (isOutage) {
        for (let i = 0; i < 5; i++) {
          const sliceY = Math.random() * h;
          const sliceH = Math.random() * 20 + 4;
          const shift = (Math.random() - 0.5) * 44;
          ctx.drawImage(canvas, 0, sliceY, w, sliceH, shift, sliceY, w, sliceH);
        }

        ctx.fillStyle = "rgba(255, 51, 102, 0.14)";
        ctx.fillRect(0, 0, w, h);

        ctx.strokeStyle = "rgba(255, 51, 102, 0.25)";
        ctx.lineWidth = 1;
        for (let y = 0; y < h; y += 6) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();
        }
      }

      if (isPlaying) {
        animId = requestAnimationFrame(render);
      }
    };

    render();
    return () => cancelAnimationFrame(animId);
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
              Spider-Man: Brand New Day
              <span className="text-[11px] font-mono font-normal text-white/50">
                (World Premiere 4K Stream)
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
            autoPlay
            loop
            muted
            playsInline
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
