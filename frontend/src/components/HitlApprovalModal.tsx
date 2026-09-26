"use client";

import React, { useState } from "react";
import { PendingHitlEvent } from "../types/telemetry";

interface HitlApprovalModalProps {
  isOpen: boolean;
  onClose: () => void;
  pendingHitl: PendingHitlEvent | null;
  onApprove: (incidentId: string, note: string) => Promise<void>;
  onDeny: (incidentId: string, reason: string) => Promise<void>;
  isLoading: boolean;
}

export function HitlApprovalModal({
  isOpen,
  onClose,
  pendingHitl,
  onApprove,
  onDeny,
  isLoading,
}: HitlApprovalModalProps) {
  const [operatorNote, setOperatorNote] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  if (!isOpen || !pendingHitl) return null;

  const blastRadiusPct = Math.round(pendingHitl.blast_radius * 100);
  const isCritical = pendingHitl.blast_radius >= 0.8;

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      await onApprove(pendingHitl.incident_id, operatorNote || "Authorized by broadcast supervisor");
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeny = async () => {
    setIsSubmitting(true);
    try {
      await onDeny(pendingHitl.incident_id, operatorNote || "Rejected by supervisor due to operational constraints");
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-4 animate-slideDown">
      <div className="bg-white/95 backdrop-blur-md border border-amber-500/40 rounded-2xl p-5 shadow-2xl subtle-card-shadow">
        {/* Header Tag & Dismiss */}
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping" />
            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300 uppercase tracking-wider">
              HITL Gate: Authorization Required
            </span>
            <span className="text-xs font-semibold text-gray-400">&bull;</span>
            <span className="text-xs font-mono text-gray-600 font-semibold">
              Checkpoint: {pendingHitl.checkpoint_id.slice(0, 16)}
            </span>
          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xs font-mono font-bold p-1 rounded-lg hover:bg-gray-100 transition-all"
            title="Dismiss modal to inspect live stream"
          >
            ✕ Dismiss
          </button>
        </div>

        {/* Action Title & Rationale */}
        <div className="mt-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-900 tracking-tight">
              Action: <span className="font-mono text-amber-800">{pendingHitl.action}</span>
            </h3>
            <span className="text-[11px] font-mono font-bold text-gray-500">
              Incident: {pendingHitl.incident_id}
            </span>
          </div>
          <p className="text-xs text-gray-600 mt-1 leading-relaxed">
            {pendingHitl.rationale || "Autonomous SRE identified high-impact mitigation requiring supervisor confirmation."}
          </p>
        </div>

        {/* Blast Radius & Safety Meter */}
        <div className="mt-3.5 p-3 bg-amber-50/70 rounded-xl border border-amber-200/80">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="font-semibold text-amber-900 text-[11px]">
              Estimated Blast Radius:
            </span>
            <span className={`font-mono font-bold text-[11px] ${isCritical ? "text-red-700" : "text-amber-800"}`}>
              {blastRadiusPct}% ({pendingHitl.blast_radius.toFixed(2)}) &bull; {isCritical ? "CRITICAL RISK" : "HIGH RISK"}
            </span>
          </div>
          <div className="w-full bg-amber-200/60 rounded-full h-2 overflow-hidden">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${isCritical ? "bg-red-500" : "bg-amber-500"}`}
              style={{ width: `${Math.min(100, blastRadiusPct)}%` }}
            />
          </div>

          {/* Rollback Plan Assurance */}
          <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-amber-200/60 text-[11px]">
            <span className="text-gray-600 font-medium">Automatic Rollback Guarantee:</span>
            <span className="font-mono font-bold text-gray-800">
              {pendingHitl.rollback_plan || "SNAPSHOT_REVERT"}
            </span>
          </div>
        </div>

        {/* Optional Supervisor Note Input */}
        <div className="mt-3">
          <input
            type="text"
            placeholder="Optional broadcast supervisor authorization notes..."
            value={operatorNote}
            onChange={(e) => setOperatorNote(e.target.value)}
            className="w-full text-xs px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-amber-500 font-mono text-gray-800 placeholder-gray-400"
          />
        </div>

        {/* Dual Decision Buttons */}
        <div className="flex items-center justify-end gap-2.5 mt-3.5 pt-3 border-t border-gray-100">
          <button
            onClick={handleDeny}
            disabled={isSubmitting || isLoading}
            className="px-3.5 py-1.5 rounded-xl border border-gray-300 hover:bg-gray-100 text-gray-700 text-xs font-semibold transition-all disabled:opacity-50"
          >
            ✕ Reject &amp; Escalate
          </button>
          <button
            onClick={handleApprove}
            disabled={isSubmitting || isLoading}
            className="px-4 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold shadow-sm transition-all disabled:opacity-50"
          >
            {isSubmitting ? "Executing..." : "✓ Authorize Remediation"}
          </button>
        </div>
      </div>
    </div>
  );
}
