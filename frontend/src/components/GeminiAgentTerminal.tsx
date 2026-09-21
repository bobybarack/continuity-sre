"use client";

import React, { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  CpuIcon,
  SparklesIcon,
  Activity01Icon,
  CheckmarkCircle01Icon,
  Alert01Icon,
  DollarCircleIcon,
  Clock01Icon,
  ArrowRight01Icon,
  Shield01Icon,
  CloudIcon,
  DatabaseIcon,
} from "hugeicons-react";
import { DoubleBezelCard } from "./DoubleBezelCard";
import { InvestigationResult } from "../types/telemetry";

interface GeminiAgentTerminalProps {
  latestInvestigation: InvestigationResult | null;
  isInvestigating: boolean;
  onTriggerInvestigation: () => void;
  isOutage: boolean;
}

export function GeminiAgentTerminal({
  latestInvestigation,
  isInvestigating,
  onTriggerInvestigation,
  isOutage,
}: GeminiAgentTerminalProps) {
  const terminalContainerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = terminalContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [latestInvestigation, isInvestigating]);

  const defaultTrace = [
    "[14:04:10] Gemini Enterprise Agent Engine active. Standby monitoring 60+ Grafana Cloud MCP tools.",
    "[14:04:11] Polling Prometheus metrics `rate(ott_video_playback_failures_total[1m])` and Loki edge logs.",
    "[14:04:12] Operational Status: Nominal (VPF: 0.18%, Latency: 48ms). Zero anomalous SLA breaches detected.",
  ];

  const trace = latestInvestigation?.reasoning_trace || defaultTrace;
  const mttr = latestInvestigation?.mttr_seconds
    ? `${latestInvestigation.mttr_seconds}s`
    : latestInvestigation?.workflow_elapsed_seconds
    ? `${latestInvestigation.workflow_elapsed_seconds}s (Pending)`
    : "Nominal";
  const churnSaved =
    latestInvestigation?.estimated_subscriber_loss_prevented ||
    "$0 USD (Nominal Operation)";
  const rca = latestInvestigation?.root_cause_analysis;
  const actionTaken = latestInvestigation?.autonomous_action_taken;
  const subsystems = latestInvestigation?.affected_subsystems || [
    "Edge CDN",
    "Transit Subsystems",
  ];

  // Pipeline stages
  const stages = [
    { label: "1. Telemetry Ingest", icon: Activity01Icon, active: true },
    { label: "2. PromQL / Loki RAG", icon: DatabaseIcon, active: isInvestigating || !!latestInvestigation },
    { label: "3. Gemini RCA", icon: CpuIcon, active: isInvestigating || !!latestInvestigation },
    { label: "4. Grafana Annotation", icon: CloudIcon, active: !!latestInvestigation },
    { label: "5. Akamai Edge Failover", icon: Shield01Icon, active: !!latestInvestigation },
    { label: "6. SLA Restored", icon: CheckmarkCircle01Icon, active: !!latestInvestigation && !isOutage },
  ];

  return (
    <DoubleBezelCard
      glowColor={isOutage ? "red" : latestInvestigation ? "indigo" : "none"}
      innerClassName="p-4 sm:p-5 flex flex-col justify-between"
    >
      <div>
        {/* Terminal Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3.5 border-b border-white/[0.08]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#6366f1]/15 border border-[#6366f1]/30 shadow-[0_0_16px_rgba(99,102,241,0.2)] flex items-center justify-center">
              <CpuIcon className="w-5 h-5 text-[#6366f1]" />
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold font-mono text-white tracking-wider uppercase flex items-center gap-2">
                  Gemini Enterprise Autonomous SRE Commander
                  <SparklesIcon className="w-3.5 h-3.5 text-[#00d2ff]" />
                </h3>
              </div>
              <p className="text-xs font-mono text-white/50">
                Google ADK Engine • 60+ Grafana Cloud MCP Tools • Real-Time PromQL / Loki RAG
              </p>
            </div>
          </div>

          {/* Quick Metrics (MTTR & Churn Saved) */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/10 text-xs font-mono">
              <Clock01Icon className="w-3.5 h-3.5 text-[#00d2ff]" />
              <span className="text-white/50">MTTR:</span>
              <span className="text-[#00f5a0] font-bold">{mttr}s</span>
            </div>

            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/10 text-xs font-mono">
              <CloudIcon className="w-3.5 h-3.5 text-[#00d2ff]" />
              <span className="text-white/50">Provenance:</span>
              <span className="text-[#00f5a0] font-bold">Grafana Cloud Mimir (Authoritative)</span>
            </div>
          </div>
        </div>

        {/* 6-Stage Autonomous Reasoning Pipeline Steps */}
        <div className="mt-3.5 pt-1 pb-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 border-b border-white/[0.06]">
          {stages.map((st, i) => {
            const Icon = st.icon;
            return (
              <div
                key={i}
                className={`p-2 rounded-xl border font-mono text-[11px] flex items-center gap-2 transition-all ${
                  st.active
                    ? "bg-white/[0.04] border-white/15 text-white"
                    : "bg-white/[0.01] border-white/[0.05] text-white/30"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 ${
                    st.active
                      ? "bg-[#6366f1]/20 text-[#00d2ff]"
                      : "bg-white/5 text-white/20"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <span className="truncate font-medium">{st.label}</span>
              </div>
            );
          })}
        </div>

        {/* RCA & Incident Summary Card */}
        <AnimatePresence>
          {rca && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              className="mt-3.5 p-3.5 rounded-xl bg-[#6366f1]/10 border border-[#6366f1]/30"
            >
              <div className="flex items-center justify-between flex-wrap gap-2 mb-1.5">
                <span className="flex items-center gap-1.5 text-xs font-mono font-bold text-[#6366f1] uppercase">
                  <Shield01Icon className="w-4 h-4 text-[#00d2ff]" />
                  Root Cause Analysis (RCA) & Remediation Summary
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#00f5a0]/15 text-[#00f5a0] border border-[#00f5a0]/30 font-bold">
                  AUTONOMOUS ACTION: {actionTaken || "SHIFT_TRAFFIC_TO_AKAMAI"}
                </span>
              </div>

              <p className="text-xs font-mono text-white/90 leading-relaxed">
                {rca}
              </p>

              <div className="mt-2.5 pt-2 border-t border-white/[0.08] flex items-center justify-between flex-wrap gap-2 text-[11px] font-mono">
                <div className="flex items-center gap-1.5 text-white/60">
                  <span>Affected Subsystems:</span>
                  <div className="flex items-center gap-1 flex-wrap">
                    {subsystems.map((sub, i) => (
                      <span
                        key={i}
                        className="px-1.5 py-0.5 rounded bg-white/[0.06] border border-white/10 text-white/80"
                      >
                        {sub}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="text-[#00d2ff]">
                  <span>Grounded SLA Impact: </span>
                  <span className="font-bold text-white">{churnSaved}</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Terminal Reasoning Output Log */}
        <div
          ref={terminalContainerRef}
          className="mt-3.5 p-4 rounded-xl bg-black/80 border border-white/[0.08] font-mono text-xs text-white/80 space-y-2 max-h-56 overflow-y-auto"
        >
          {trace.map((line, idx) => {
            const isAlert = line.includes("ALERT") || line.includes("CRITICAL");
            const isMcp = line.includes("MCP") || line.includes("Grafana");
            const isAction = line.includes("Autonomous") || line.includes("Failover");
            const isSuccess =
              line.includes("Resolved") ||
              line.includes("HEALTHY") ||
              line.includes("Nominal");

            return (
              <div
                key={idx}
                className={`flex items-start gap-2 leading-relaxed ${
                  isAlert
                    ? "text-[#ff3366] font-semibold"
                    : isAction
                    ? "text-[#00d2ff] font-semibold"
                    : isSuccess
                    ? "text-[#00f5a0]"
                    : isMcp
                    ? "text-[#6366f1]"
                    : "text-white/70"
                }`}
              >
                <span className="text-white/30 shrink-0 select-none">&gt;</span>
                <span>{line}</span>
              </div>
            );
          })}

          {isInvestigating && (
            <div className="flex items-center gap-2 text-[#6366f1] animate-pulse">
              <span className="text-white/30">&gt;</span>
              <span className="w-2 h-2 rounded-full bg-[#6366f1] animate-ping" />
              <span>
                Gemini 3.1 Pro querying Grafana Cloud MCP PromQL and isolating edge logs...
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Trigger Button & Status Footer */}
      <div className="mt-4 pt-3 border-t border-white/[0.06] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 text-xs font-mono text-white/50">
          <span className="w-2 h-2 rounded-full bg-[#00f5a0]" />
          <span>
            Grafana Cloud IRM: Auto-Annotation {latestInvestigation?.annotation_id ? `(ID: ${latestInvestigation.annotation_id})` : "Enabled"}
          </span>
        </div>

        {/* Button-In-Button Interactive CTA */}
        <button
          onClick={onTriggerInvestigation}
          disabled={isInvestigating}
          className="group flex items-center gap-3 pl-4 pr-1.5 py-1.5 rounded-full bg-gradient-to-r from-[#6366f1] to-[#00d2ff] hover:opacity-95 text-white text-xs font-mono font-bold tracking-wider transition-all duration-200 active:scale-[0.98] disabled:opacity-50 shadow-[0_0_20px_rgba(99,102,241,0.3)]"
        >
          <span>
            {isInvestigating
              ? "INVESTIGATING SRE INCIDENT..."
              : "TRIGGER GEMINI AUTONOMOUS SRE"}
          </span>
          <div className="w-7 h-7 rounded-full bg-black/30 flex items-center justify-center group-hover:translate-x-0.5 transition-transform">
            <ArrowRight01Icon className="w-4 h-4 text-white" />
          </div>
        </button>
      </div>
    </DoubleBezelCard>
  );
}
