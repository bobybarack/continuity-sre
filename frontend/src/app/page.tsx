"use client";

import React, { useState, useEffect, useCallback } from "react";
import { TopBar } from "../components/TopBar";
import { MetricCardsRow } from "../components/MetricCardsRow";
import { PlaybackChartCard } from "../components/PlaybackChartCard";
import { LivePlayerCard } from "../components/LivePlayerCard";
import { SreCommanderCard } from "../components/SreCommanderCard";
import { CdnSplitCard } from "../components/CdnSplitCard";
import { LiveLogsCard } from "../components/LiveLogsCard";
import { ChaosDock } from "../components/ChaosDock";
import { IncidentDrawer } from "../components/IncidentDrawer";
import { ApiService } from "../services/api";
import {
  TelemetrySnapshot,
  InvestigationResult,
  ChaosState,
} from "../types/telemetry";

export default function ContinuityDashboard() {
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot | null>(null);
  const [history, setHistory] = useState<TelemetrySnapshot[]>([]);
  const [chaosState, setChaosState] = useState<ChaosState | null>(null);
  const [investigations, setInvestigations] = useState<InvestigationResult[]>([]);
  const [isInvestigating, setIsInvestigating] = useState<boolean>(false);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  // Initial Data Fetch
  const fetchInitialData = useCallback(async () => {
    try {
      const [cur, hist, state, invHist] = await Promise.allSettled([
        ApiService.getCurrentTelemetry(),
        ApiService.getTelemetryHistory(),
        ApiService.getChaosState(),
        ApiService.getInvestigationHistory(),
      ]);

      if (cur.status === "fulfilled") setTelemetry(cur.value);
      if (hist.status === "fulfilled") setHistory(hist.value);
      if (state.status === "fulfilled") setChaosState(state.value);
      if (invHist.status === "fulfilled") setInvestigations(invHist.value);
    } catch (err) {
      console.warn("Initial data load partial failure:", err);
    }
  }, []);

  useEffect(() => {
    fetchInitialData();
  }, [fetchInitialData]);

  // Ensure window stays at top on initial link visit
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  // Connect 1Hz SSE Real-Time Stream with fallback polling
  useEffect(() => {
    const unsub = ApiService.createTelemetryEventSource(
      (newSnapshot) => {
        setTelemetry(newSnapshot);
        setHistory((prev) => {
          const updated = [...prev, newSnapshot];
          if (updated.length > 60) updated.shift();
          return updated;
        });
      },
      () => {
        ApiService.getCurrentTelemetry()
          .then((snap) => {
            setTelemetry(snap);
            setHistory((prev) => [...prev.slice(-59), snap]);
          })
          .catch(() => {});
      }
    );

    return () => unsub();
  }, []);

  // Chaos Injection Handlers
  const handleInjectCdnOutage = async () => {
    setIsActionLoading(true);
    try {
      const state = await ApiService.injectCdnOutage();
      setChaosState(state);
      const snap = await ApiService.getCurrentTelemetry();
      setTelemetry(snap);
    } catch (err) {
      console.error("Failed to inject CDN outage:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleInjectDrmTimeout = async () => {
    setIsActionLoading(true);
    try {
      const state = await ApiService.injectDrmTimeout();
      setChaosState(state);
      const snap = await ApiService.getCurrentTelemetry();
      setTelemetry(snap);
    } catch (err) {
      console.error("Failed to inject DRM timeout:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleInjectIspDrop = async () => {
    setIsActionLoading(true);
    try {
      const state = await ApiService.injectIspDrop();
      setChaosState(state);
      const snap = await ApiService.getCurrentTelemetry();
      setTelemetry(snap);
    } catch (err) {
      console.error("Failed to inject ISP drop:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleTriggerAutonomousInvestigation = async () => {
    setIsInvestigating(true);
    try {
      const result = await ApiService.investigateAndRemediate();
      setInvestigations((prev) => [result, ...prev]);
      const [state, snap] = await Promise.all([
        ApiService.getChaosState(),
        ApiService.getCurrentTelemetry(),
      ]);
      setChaosState(state);
      setTelemetry(snap);
    } catch (err) {
      console.error("Autonomous SRE investigation failed:", err);
    } finally {
      setIsInvestigating(false);
    }
  };

  const handleResetChaos = async () => {
    setIsActionLoading(true);
    try {
      const state = await ApiService.resetChaos();
      setChaosState(state);
      const snap = await ApiService.getCurrentTelemetry();
      setTelemetry(snap);
    } catch (err) {
      console.error("Reset failed:", err);
    } finally {
      setIsActionLoading(false);
    }
  };

  const latestInvestigation = investigations.length > 0 ? investigations[0] : null;
  const isOutage = telemetry?.is_outage ?? false;

  return (
    <div className="min-h-[100dvh] bg-[#f8f9fb]">
      {/* Main Full-Width Container */}
      <main className="max-w-[1600px] mx-auto p-4 sm:p-6 lg:p-8 space-y-5">
        {/* Top Header with Brand & Incident Notification Bell */}
        <TopBar
          telemetry={telemetry}
          investigationCount={investigations.length}
          onOpenNotifications={() => setIsDrawerOpen(true)}
        />

        {/* 1. Top 5 Real-Time Metric Cards */}
        <MetricCardsRow current={telemetry} />

        {/* 2. Central Row: Option 2 Command Center - Video Hero (8 cols / 66.7%) + Stacked Telemetry (4 cols / 33.3%) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
          <div className="lg:col-span-8 flex flex-col">
            <LivePlayerCard telemetry={telemetry} />
          </div>
          <div className="lg:col-span-4 flex flex-col gap-5 justify-between">
            <div className="flex-1">
              <PlaybackChartCard telemetry={telemetry} history={history} />
            </div>
            <div className="flex-1">
              <CdnSplitCard telemetry={telemetry} />
            </div>
          </div>
        </div>

        {/* 3. Bottom Row: SRE Commander (50%) + Live Logs Stream (50%) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <SreCommanderCard
            latestInvestigation={latestInvestigation}
            isInvestigating={isInvestigating}
            onTriggerInvestigation={handleTriggerAutonomousInvestigation}
            isOutage={isOutage}
          />
          <LiveLogsCard telemetry={telemetry} history={history} />
        </div>

        {/* 4. Chaos Injection & Self-Healing Control Dock */}
        <ChaosDock
          chaosState={chaosState}
          onInjectCdnOutage={handleInjectCdnOutage}
          onInjectDrmTimeout={handleInjectDrmTimeout}
          onInjectIspDrop={handleInjectIspDrop}
          onAutoRemediate={handleTriggerAutonomousInvestigation}
          onReset={handleResetChaos}
          isLoading={isActionLoading || isInvestigating}
        />
      </main>

      {/* Slide-over Incident Log Drawer */}
      <IncidentDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        investigations={investigations}
      />
    </div>
  );
}
