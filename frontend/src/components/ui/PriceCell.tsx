import React from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface PriceCellProps {
  value: number;
  isCurrency?: boolean;
  isPercentage?: boolean;
  colored?: boolean;
  showSign?: boolean;
  className?: string;
}

export function PriceCell({ value, isCurrency = false, isPercentage = false, colored = false, showSign = false, className }: PriceCellProps) {
  const isPositive = value > 0;
  const isNegative = value < 0;
  
  const formattedValue = Math.abs(value).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <span
      className={cn(
        "tabular-nums font-mono whitespace-nowrap",
        colored ? (isPositive ? "text-[var(--color-gain)]" : isNegative ? "text-[var(--color-loss)]" : "text-[var(--color-primary)]") : "text-[var(--color-primary)]",
        className
      )}
    >
      {showSign && isPositive && "+"}
      {showSign && isNegative && "-"}
      {isCurrency && "₹"}
      {formattedValue}
      {isPercentage && "%"}
    </span>
  );
}
