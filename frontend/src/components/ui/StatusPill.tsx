import React from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface StatusPillProps {
  status: "connected" | "reconnecting" | "disconnected" | "error";
  text?: string;
}

export function StatusPill({ status, text }: StatusPillProps) {
  const dotColor = {
    connected: "bg-[var(--color-gain)]",
    reconnecting: "bg-amber-500",
    disconnected: "bg-[var(--color-muted)]",
    error: "bg-[var(--color-loss)]",
  }[status];

  const defaultText = {
    connected: "Live Feed Active",
    reconnecting: "Reconnecting...",
    disconnected: "Disconnected",
    error: "Connection Error",
  }[status];

  return (
    <div className="flex items-center space-x-2 bg-[var(--color-elevated)] border border-[var(--color-hairline)] rounded-full px-3 py-1 shadow-sm">
      <div className={cn("w-2 h-2 rounded-full", dotColor, status === "connected" && "animate-pulse")} />
      <span className="text-xs font-medium text-[var(--color-primary)]">
        {text || defaultText}
      </span>
    </div>
  );
}
