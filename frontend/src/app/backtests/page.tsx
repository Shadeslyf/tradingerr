"use client";

import React, { useEffect, useState } from "react";
import { listBacktests, getBacktest, deleteBacktest } from "@/lib/api";
import { BacktestResultView } from "@/components/ui/BacktestResultView";
import { PriceCell } from "@/components/ui/PriceCell";

export default function BacktestsPage() {
  const [backtests, setBacktests] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [resultData, setResultData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listBacktests().then(data => setBacktests(data));
  }, []);

  const handleSelect = (id: string) => {
    if (selectedId === id) return;
    setSelectedId(id);
    setLoading(true);
    getBacktest(id).then(data => {
      setResultData(data);
      setLoading(false);
    });
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this backtest?")) {
      await deleteBacktest(id);
      setBacktests(prev => prev.filter(b => b.id !== id));
      if (selectedId === id) {
        setSelectedId(null);
        setResultData(null);
      }
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-medium tracking-tight text-[var(--color-primary)]">Backtest Browser</h1>
      </div>

      <div className="flex gap-6 flex-1 min-h-0 overflow-hidden">
        {/* Sidebar selection */}
        <div className="w-64 flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] overflow-hidden shrink-0">
          <div className="p-3 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)]">
            <h2 className="text-sm font-medium">Select Backtest</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {backtests.length === 0 ? (
              <div className="p-4 text-center text-xs text-[var(--color-dim)]">No backtests found.</div>
            ) : (
              backtests.map(b => {
                const isSelected = selectedId === b.id;
                return (
                  <div 
                    key={b.id}
                    onClick={() => handleSelect(b.id)}
                    className={`p-2 cursor-pointer border rounded text-xs transition-colors ${
                      isSelected 
                        ? "border-[var(--color-accent)] bg-[var(--color-accent)]/10 text-[var(--color-primary)]" 
                        : "border-[var(--color-hairline)] hover:bg-[var(--color-elevated)] text-[var(--color-muted)]"
                    }`}
                  >
                    <div className="font-medium truncate">{b.label || b.id}</div>
                    <div className="flex justify-between mt-1 text-[10px] text-[var(--color-dim)]">
                      <span>{b.total_trades} trades</span>
                      <PriceCell value={b.win_rate_pct} isPercentage className="font-normal" />
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col min-h-0 overflow-y-auto pr-2">
          {!selectedId ? (
            <div className="flex-1 flex items-center justify-center border border-[var(--color-hairline)] bg-[var(--color-panel)] text-[var(--color-dim)] rounded-lg">
              <p>Select a backtest run to view details.</p>
            </div>
          ) : loading ? (
            <div className="flex-1 flex items-center justify-center border border-[var(--color-hairline)] bg-[var(--color-panel)] text-[var(--color-dim)] rounded-lg animate-pulse">
              <p>Loading result data...</p>
            </div>
          ) : resultData ? (
            <BacktestResultView resultData={resultData} onDelete={handleDelete} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
