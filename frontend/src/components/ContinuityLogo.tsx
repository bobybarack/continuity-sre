import React from "react";

interface ContinuityLogoProps {
  className?: string;
}

export function ContinuityLogo({ className = "w-8 h-8" }: ContinuityLogoProps) {
  return (
    <img
      src="/continuity-logo-dark.svg"
      alt="CONTINUITY"
      className={`object-contain ${className}`}
    />
  );
}
