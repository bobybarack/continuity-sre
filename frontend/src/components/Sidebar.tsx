"use client";

import React from "react";
import {
  Shield01Icon,
  Activity01Icon,
  CpuIcon,
  CloudIcon,
  Radio01Icon,
  File01Icon,
  Settings01Icon,
} from "hugeicons-react";
import { ContinuityLogo } from "./ContinuityLogo";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  investigationCount: number;
  onOpenPostMortem: () => void;
}

export function Sidebar({
  activeTab,
  setActiveTab,
  investigationCount,
  onOpenPostMortem,
}: SidebarProps) {
  const navItems = [
    { id: "overview", label: "Live Overview", icon: Activity01Icon },
    { id: "commander", label: "SRE Commander", icon: CpuIcon },
    { id: "routes", label: "Edge CDN Routes", icon: CloudIcon },
    { id: "drm", label: "DRM Security", icon: Radio01Icon },
  ];

  return (
    <aside className="w-64 shrink-0 hidden lg:flex flex-col justify-between bg-white border-r border-gray-200/80 p-5 min-h-[calc(100dvh-1.5rem)] my-3 ml-3 rounded-2xl subtle-card-shadow">
      <div>
        {/* Logo & Brand */}
        <div className="flex items-center gap-2.5 px-2 py-3 mb-6 border-b border-gray-100">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-500 to-cyan-400 p-1.5 flex items-center justify-center text-white shadow-sm shadow-sky-500/20">
            <ContinuityLogo className="w-full h-full text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-900 tracking-tight">
              CONTINUITY
            </h1>
            <p className="text-[11px] text-gray-500 font-medium">Stream Continuity SRE</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200/80 font-semibold"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon
                    className={`w-4 h-4 ${
                      isActive ? "text-emerald-600" : "text-gray-400"
                    }`}
                  />
                  <span>{item.label}</span>
                </div>

                {item.id === "commander" && investigationCount > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-200 text-emerald-800">
                    {investigationCount}
                  </span>
                )}
              </button>
            );
          })}

          {/* Incident Reports Link */}
          <button
            onClick={onOpenPostMortem}
            className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-all"
          >
            <div className="flex items-center gap-2.5">
              <File01Icon className="w-4 h-4 text-gray-400" />
              <span>Incident Audit Logs</span>
            </div>
            {investigationCount > 0 && (
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            )}
          </button>
        </nav>
      </div>

      {/* Bottom Settings */}
      <div className="pt-4 border-t border-gray-100 space-y-1 text-xs text-gray-500">
        <div className="flex items-center gap-2.5 px-3.5 py-2 text-gray-600 hover:text-gray-900 cursor-pointer rounded-lg hover:bg-gray-50">
          <Settings01Icon className="w-4 h-4 text-gray-400" />
          <span>Stream SLA Config</span>
        </div>
      </div>
    </aside>
  );
}
