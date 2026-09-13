import React from "react";
import { PriceCell } from "./PriceCell";

interface MetricCardProps {
  label: string;
  value: string | number;
  isCurrency?: boolean;
  isPercentage?: boolean;
  colored?: boolean;
  showSign?: boolean;
  subtext?: React.ReactNode;
}

export function MetricCard({ label, value, isCurrency, isPercentage, colored, showSign, subtext }: MetricCardProps) {
  return (
    <div className="bg-[var(--color-panel)] border border-[var(--color-hairline)] p-4 flex flex-col justify-between h-full">
      <h3 className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider mb-2">{label}</h3>
      <div className="text-2xl font-semibold text-[var(--color-primary)]">
        {typeof value === "number" ? (
          <PriceCell value={value} isCurrency={isCurrency} isPercentage={isPercentage} colored={colored} showSign={showSign} />
        ) : (
          <span>{value}</span>
        )}
      </div>
      {subtext && <div className="mt-2 text-xs text-[var(--color-dim)]">{subtext}</div>}
    </div>
  );
}
