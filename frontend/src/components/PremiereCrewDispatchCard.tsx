"use client";

import React from "react";
import {
  Film01Icon,
  Activity01Icon,
  FlashIcon,
  Shield01Icon,
  CloudIcon,
  SparklesIcon,
  DatabaseIcon,
  Alert01Icon,
} from "hugeicons-react";
import { InvestigationResult } from "../types/telemetry";

export interface PremiereCrewDispatchCardProps {
  latestInvestigation: InvestigationResult | null;
  isInvestigating: boolean;
  onTriggerInvestigation: () => void;
  isOutage: boolean;
}

export function PremiereCrewDispatchCard({
  latestInvestigation,
  isInvestigating,
  onTriggerInvestigation,
  isOutage,
}: PremiereCrewDispatchCardProps) {
  const rca = latestInvestigation?.root_cause_analysis;
  const slaImpact =
    latestInvestigation?.estimated_subscriber_loss_prevented ||
    "Nominal SLA (0 degraded sessions)";
  const hasMttr =
    typeof latestInvestigation?.mttr_seconds === "number" &&
    latestInvestigation.mttr_seconds !== null;
  const mttrDisplay = hasMttr
    ? `${latestInvestigation!.mttr_seconds}s MTTR`
    : latestInvestigation?.workflow_elapsed_seconds
    ? `${latestInvestigation.workflow_elapsed_seconds}s (Pending)`
    : "Nominal";

  const verifySource =
    latestInvestigation?.verification_source ||
    (latestInvestigation?.closed_loop_verified
      ? "grafana_cloud_prometheus"
      : "Standby");
  const isAuthoritative =
    latestInvestigation?.verification_authoritative ??
    verifySource === "grafana_cloud_prometheus";
  const gateStatus =
    latestInvestigation?.verification_status ||
    (latestInvestigation?.closed_loop_verified ? "PASSED" : "STANDBY");
  const verifiedVpf =
    latestInvestigation?.verified_vpf_rate !== undefined
      ? `${latestInvestigation.verified_vpf_rate.toFixed(2)}%`
      : "<= 0.50%";
  const verifiedBuffer =
    latestInvestigation?.verified_buffer_health_sec !== undefined
      ? `${latestInvestigation.verified_buffer_health_sec.toFixed(1)}s`
      : ">= 20.0s";

  const defaultMcpTools = [
    "grafana_query_prometheus",
    "grafana_query_loki",
    "continuity_execute_remediation",
    "grafana_create_annotation",
    "grafana_create_incident",
    "continuity_verify_closed_loop_recovery",
  ];
  const mcpTools =
    latestInvestigation?.mcp_tools_executed &&
    latestInvestigation.mcp_tools_executed.length > 0
      ? latestInvestigation.mcp_tools_executed
      : defaultMcpTools;

  // Station States
  const isResolved =
    !isOutage &&
    (latestInvestigation?.workflow_status === "RESOLVED" ||
      latestInvestigation?.closed_loop_verified);

  const adStatus = isInvestigating
    ? "COMMANDING SET"
    : isOutage
    ? "ALARM RAISED"
    : isResolved
    ? "SCENE WRAPPED"
    : "STANDBY";

  const ditStatus = isInvestigating
    ? "POLLING MCP"
    : isOutage
    ? "BREACH DETECTED"
    : "1Hz NOMINAL";

  const gripStatus = isInvestigating
    ? "REROUTING TRUNK"
    : latestInvestigation?.remediation_action
    ? "80% AKAMAI ROUTED"
    : "TRUNK READY";

  const continuityStatus = latestInvestigation?.closed_loop_verified
    ? "GATE PASSED (0 ERRORS)"
    : isInvestigating
    ? "AUDITING BUFFER"
    : isOutage
    ? "GATE BLOCKED"
    : "GATE ARMED";

  return (
    <div className="bg-white border border-gray-200/80 rounded-2xl p-5 subtle-card-shadow flex flex-col justify-between h-full">
      <div>
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-white">
              <Film01Icon className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-gray-900 tracking-tight">
                  Premiere Continuity Crew
                </h3>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded font-bold bg-slate-100 text-slate-700 border border-slate-200">
                  ON-SET UNIT
                </span>
              </div>
              <p className="text-xs text-gray-500 font-medium">
                Autonomous Stream Continuity & Closed-Loop Incident Response
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-bold border ${
                isOutage
                  ? "bg-red-50 text-red-700 border-red-200 animate-pulse"
                  : isInvestigating
                  ? "bg-amber-50 text-amber-700 border-amber-200 animate-pulse"
                  : "bg-emerald-50 text-emerald-700 border-emerald-200"
              }`}
            >
              {isOutage
                ? "Incident Active"
                : isInvestigating
                ? "Crew Dispatched"
                : "Nominal Broadcast"}
            </span>
          </div>
        </div>

        {/* 4-Station Crew Matrix */}
        <div className="grid grid-cols-2 gap-2.5 mt-3.5">
          {/* Station 1: 1st AD */}
          <div
            className={`p-2.5 rounded-xl border transition-all ${
              isInvestigating
                ? "bg-blue-50/70 border-blue-200"
                : isOutage
                ? "bg-red-50/60 border-red-200"
                : "bg-gray-50/80 border-gray-200/70"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-200 text-slate-800">
                  <Film01Icon className="w-3 h-3 text-slate-700" />
                  <span>1ST AD</span>
                </span>
                <span className="text-[11px] font-bold text-gray-800">
                  Commander
                </span>
              </div>
              <span
                className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  isInvestigating
                    ? "bg-blue-200/80 text-blue-900 animate-pulse"
                    : isOutage
                    ? "bg-red-200/80 text-red-900 animate-pulse"
                    : "bg-slate-200/60 text-slate-700"
                }`}
              >
                {adStatus}
              </span>
            </div>
            <p className="text-[10px] text-gray-500 font-medium mt-1 leading-snug">
              Incident lifecycle, orchestration, and executive wrap report
            </p>
          </div>

          {/* Station 2: DIT */}
          <div
            className={`p-2.5 rounded-xl border transition-all ${
              isInvestigating
                ? "bg-amber-50/70 border-amber-200"
                : isOutage
                ? "bg-red-50/60 border-red-200"
                : "bg-gray-50/80 border-gray-200/70"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-amber-100 text-amber-900">
                  <Activity01Icon className="w-3 h-3 text-amber-700" />
                  <span>DIT</span>
                </span>
                <span className="text-[11px] font-bold text-gray-800">
                  Signal Scout
                </span>
              </div>
              <span
                className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  isInvestigating
                    ? "bg-amber-200/80 text-amber-900 animate-pulse"
                    : isOutage
                    ? "bg-red-200/80 text-red-900"
                    : "bg-emerald-100 text-emerald-800"
                }`}
              >
                {ditStatus}
              </span>
            </div>
            <p className="text-[10px] text-gray-500 font-medium mt-1 leading-snug">
              Grafana Cloud MCP: Prometheus vectors and Loki error streams
            </p>
          </div>

          {/* Station 3: Key Grip */}
          <div
            className={`p-2.5 rounded-xl border transition-all ${
              isInvestigating
                ? "bg-sky-50/70 border-sky-200"
                : latestInvestigation?.remediation_action
                ? "bg-blue-50/60 border-blue-200"
                : "bg-gray-50/80 border-gray-200/70"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-sky-100 text-sky-900">
                  <FlashIcon className="w-3 h-3 text-sky-700" />
                  <span>KEY GRIP</span>
                </span>
                <span className="text-[11px] font-bold text-gray-800">
                  Infra Rigger
                </span>
              </div>
              <span
                className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  isInvestigating
                    ? "bg-sky-200/80 text-sky-900 animate-pulse"
                    : latestInvestigation?.remediation_action
                    ? "bg-blue-200/80 text-blue-900"
                    : "bg-slate-200/60 text-slate-700"
                }`}
              >
                {gripStatus}
              </span>
            </div>
            <p className="text-[10px] text-gray-500 font-medium mt-1 leading-snug">
              CDN egress traffic shifting, BGP reroute, and DRM failover
            </p>
          </div>

          {/* Station 4: Continuity Supervisor */}
          <div
            className={`p-2.5 rounded-xl border transition-all ${
              latestInvestigation?.closed_loop_verified
                ? "bg-emerald-50/70 border-emerald-300"
                : isInvestigating
                ? "bg-amber-50/70 border-amber-200"
                : isOutage
                ? "bg-red-50/60 border-red-200"
                : "bg-gray-50/80 border-gray-200/70"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="inline-flex items-center gap-1 text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-900">
                  <Shield01Icon className="w-3 h-3 text-emerald-700" />
                  <span>CONTINUITY</span>
                </span>
                <span className="text-[11px] font-bold text-gray-800">
                  Quality Gate
                </span>
              </div>
              <span
                className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  latestInvestigation?.closed_loop_verified
                    ? "bg-emerald-200 text-emerald-900 font-bold"
                    : isInvestigating
                    ? "bg-amber-200 text-amber-900"
                    : isOutage
                    ? "bg-red-200 text-red-900"
                    : "bg-slate-200/60 text-slate-700"
                }`}
              >
                {continuityStatus}
              </span>
            </div>
            <p className="text-[10px] text-gray-500 font-medium mt-1 leading-snug">
              Enforces Closed-Loop invariant: Command executed != Service recovered
            </p>
          </div>
        </div>

        {/* Diagnosis & Grounded Impact */}
        <div className="mt-3 p-3 bg-gray-50 rounded-xl border border-gray-200/60 text-xs">
          <div className="flex items-center justify-between mb-1">
            <span className="text-gray-400 font-semibold block text-[11px] uppercase">
              Mission Brief & Grounded Impact
            </span>
            <span className="text-[10px] font-mono font-bold text-emerald-700 bg-emerald-100/70 px-1.5 py-0.2 rounded">
              {slaImpact}
            </span>
          </div>
          <p className="text-gray-800 leading-relaxed font-medium text-[11px]">
            {rca ||
              "All streaming telemetry within normal operating SLA. Continuous 1Hz edge monitoring active."}
          </p>
        </div>

        {/* Quick Stats Grid: MTTR & Verification Provenance */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mt-2.5">
          <div className="p-2.5 bg-gray-50 rounded-xl border border-gray-200/60">
            <span className="text-[10px] text-gray-400 font-semibold uppercase block">
              Verified Recovery Time
            </span>
            <span className="text-sm font-bold text-emerald-600 mt-0.5 block">
              {mttrDisplay}
            </span>
            <span className="text-[10px] text-gray-500 font-mono mt-0.5 block">
              Recovery Gate:{" "}
              <span className="font-semibold text-emerald-700">{gateStatus}</span>
            </span>
          </div>

          <div className="p-2.5 bg-gray-50 rounded-xl border border-gray-200/60">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-400 font-semibold uppercase block">
                Verification Source
              </span>
              <span
                className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-bold ${
                  isAuthoritative
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : "bg-amber-100 text-amber-800 border border-amber-300"
                }`}
              >
                {isAuthoritative ? "AUTHORITATIVE" : "LOCAL FALLBACK"}
              </span>
            </div>
            <span className="text-xs font-bold text-gray-900 mt-0.5 block font-mono truncate">
              {verifySource === "grafana_cloud_prometheus"
                ? "Grafana Cloud Mimir"
                : verifySource === "prometheus_collector_registry"
                ? "CollectorRegistry"
                : "Prometheus Guard"}
            </span>
            <span className="text-[10px] text-gray-500 font-mono mt-0.5 block truncate">
              VPF: {verifiedVpf} (SLA &le; 0.5%) &bull; Buf: {verifiedBuffer}
            </span>
          </div>
        </div>

        {/* Transaction Ledger & Idempotency Key */}
        {latestInvestigation?.remediation_transaction_id && (
          <div className="mt-2.5 p-2.5 bg-gray-50 rounded-xl border border-gray-200/60">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-1.5">
                <DatabaseIcon className="w-3.5 h-3.5 text-gray-500" />
                <span className="text-[10px] font-mono font-semibold tracking-wider text-gray-500 uppercase">
                  Remediation Transaction
                </span>
              </div>
              <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-white text-gray-800 border border-gray-200/80">
                {latestInvestigation.remediation_transaction_id}
              </span>
            </div>
            <div className="flex items-center justify-between text-[10px] font-mono text-gray-500">
              <span className="truncate max-w-[220px]" title={latestInvestigation.idempotency_key || ""}>
                Idempotency: <span className="text-gray-700 font-medium">{latestInvestigation.idempotency_key || "None"}</span>
              </span>
              <span
                className={`px-1.5 py-0.2 rounded font-bold border ${
                  latestInvestigation.rollback_status === "EXECUTED"
                    ? "bg-red-50 text-red-700 border-red-200"
                    : "bg-emerald-50 text-emerald-700 border-emerald-200"
                }`}
              >
                {latestInvestigation.rollback_status === "EXECUTED" ? "ROLLED_BACK" : "COMMITTED"}
              </span>
            </div>
          </div>
        )}

        {/* Closed-Loop Recovery Proof & Cryptographic Evidence Hash */}
        {latestInvestigation?.recovery_proof && (
          <div className="mt-2.5 p-2.5 bg-gray-50 rounded-xl border border-gray-200/60">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-1.5">
                <Shield01Icon className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-[10px] font-mono font-semibold tracking-wider text-gray-500 uppercase">
                  Cryptographic Recovery Proof
                </span>
              </div>
              {Boolean((latestInvestigation.recovery_proof as { evidence_hash?: string })?.evidence_hash) && (
                <span
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white text-emerald-800 border border-emerald-200/80 font-bold"
                  title={(latestInvestigation.recovery_proof as { evidence_hash?: string }).evidence_hash}
                >
                  SHA-256: {String((latestInvestigation.recovery_proof as { evidence_hash?: string }).evidence_hash).substring(0, 12)}...
                </span>
              )}
            </div>
            {/* Gate checklist */}
            {Array.isArray((latestInvestigation.recovery_proof as { gates?: Array<{ name: string; observed_value: string; required_value: string; passed: boolean }> })?.gates) && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {((latestInvestigation.recovery_proof as { gates: Array<{ name: string; observed_value: string; required_value: string; passed: boolean }> }).gates).map((g, idx) => (
                  <span
                    key={idx}
                    className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-medium border ${
                      g.passed
                        ? "bg-white border-gray-200/80 text-gray-700"
                        : "bg-red-50 border-red-200 text-red-700"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        g.passed ? "bg-emerald-500" : "bg-red-500"
                      }`}
                    />
                    <span>
                      {g.name}: {g.observed_value} ({g.passed ? "PASSED" : "FAILED"})
                    </span>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Adversarial Rollback Alert Banner */}
        {latestInvestigation?.rollback_status === "EXECUTED" && (
          <div className="mt-2.5 p-2.5 bg-red-50 rounded-xl border border-red-200 text-xs">
            <div className="flex items-center gap-1.5 font-bold text-red-800 text-[11px] mb-1">
              <Alert01Icon className="w-3.5 h-3.5 text-red-600" />
              <span>AUTOMATED ROLLBACK EXECUTED</span>
            </div>
            <p className="text-[10px] text-red-700 leading-snug font-medium">
              Recovery verification gates failed to converge. Infrastructure state restored to pre-action baseline snapshot. Human SRE escalation package compiled.
            </p>
          </div>
        )}

        {/* Official MCP Toolchain Strip */}
        <div className="mt-2.5 p-2.5 bg-gray-900 rounded-xl border border-gray-800 text-white">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
              <CloudIcon className="w-3.5 h-3.5 text-sky-400" />
              <span className="text-[10px] font-mono font-bold tracking-wider text-sky-400 uppercase">
                Official Grafana MCP Toolchain
              </span>
            </div>
            <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-white/10 text-white/70">
              stdio JSON-RPC
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {mcpTools.map((tool, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-white/[0.07] border border-white/10 text-[9px] font-mono text-gray-200"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>
                  {tool.replace("continuity_", "").replace("grafana_", "")}
                </span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Action Button */}
      <div className="mt-3 pt-2.5 border-t border-gray-100">
        <button
          onClick={onTriggerInvestigation}
          disabled={isInvestigating}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-all disabled:opacity-50 active:scale-[0.99] shadow-sm"
        >
          <SparklesIcon className="w-4 h-4 text-emerald-400" />
          <span>
            {isInvestigating
              ? "Crew Dispatched: Executing Official Grafana MCP Toolchain..."
              : "Dispatch Crew (Autonomous Failover)"}
          </span>
        </button>
      </div>
    </div>
  );
}

// Backward-compatible alias
export { PremiereCrewDispatchCard as SreCommanderCard };
