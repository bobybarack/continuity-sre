import React from "react";

interface ContinuityLogoProps {
  className?: string;
}

export function ContinuityLogo({ className = "w-8 h-8" }: ContinuityLogoProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="CONTINUITY"
    >
      <path
        d="M16 2L4 7v8c0 7.5 5.1 14.5 12 16 6.9-1.5 12-8.5 12-16V7L16 2z"
        fill="url(#shield-grad)"
        stroke="#10b981"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M9 16h3.5l2-4 3 8 2-4h3.5"
        stroke="#ffffff"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="16" r="1.5" fill="#34d399" />
      <defs>
        <linearGradient id="shield-grad" x1="16" y1="2" x2="16" y2="31" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0f172a" />
          <stop offset="1" stopColor="#022c22" />
        </linearGradient>
      </defs>
    </svg>
  );
}
