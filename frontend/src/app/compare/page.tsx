"use client";

import React, { useEffect, useState } from "react";
import { listBacktests, getBacktest } from "@/lib/api";
import { MultiEquityCurveChart } from "@/components/charts/MultiEquityCurveChart";
import { PriceCell } from "@/components/ui/PriceCell";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7"];

export default function ComparePage() {
  const [available, setAvailable] = useState<any[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [results, setResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listBacktests().then(data => setAvailable(data));
  }, []);

  const toggleSelection = async (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(prev => prev.filter(x => x !== id));
    } else {
      if (selectedIds.length >= 5) {
        alert("Maximum 5 models can be compared at once.");
        return;
      }
      setSelectedIds(prev => [...prev, id]);
      if (!results[id]) {
        setLoading(true);
        const data = await getBacktest(id);
        setResults(prev => ({ ...prev, [id]: data }));
        setLoading(false);
      }
    }
  };

  const chartSeries = React.useMemo(() => {
    return selectedIds.map((id, index) => {
      const resultData = results[id];
      if (!resultData?.equity_curve || !resultData?.equity_times) return null;
      
      return {
        name: resultData.label || id,
        color: COLORS[index % COLORS.length],
        data: resultData.equity_curve.map((val: number, i: number) => ({
          time: resultData.equity_times[i],
          value: val
        }))
      };
    }).filter(Boolean) as any[];
  }, [selectedIds, results]);

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-medium tracking-tight text-[var(--color-primary)]">Model Comparison</h1>
      </div>

      <div className="flex gap-6 flex-1 min-h-0 overflow-hidden">
        {/* Sidebar selection */}
        <div className="w-64 flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] overflow-hidden shrink-0">
          <div className="p-3 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)]">
            <h2 className="text-sm font-medium">Select Backtests</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {available.map(b => {
              const isSelected = selectedIds.includes(b.id);
              return (
                <div 
                  key={b.id}
                  onClick={() => toggleSelection(b.id)}
                  className={`p-2 cursor-pointer border rounded text-xs transition-colors ${
                    isSelected 
                      ? "border-[var(--color-accent)] bg-[var(--color-accent)]/10 text-white" 
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
            })}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col space-y-4 overflow-y-auto pr-2">
          {selectedIds.length === 0 ? (
            <div className="flex-1 flex items-center justify-center border border-[var(--color-hairline)] bg-[var(--color-panel)] text-[var(--color-dim)]">
              <p>Select at least one backtest to compare.</p>
            </div>
          ) : (
            <>
              {loading && <div className="text-sm text-[var(--color-dim)] animate-pulse">Loading data...</div>}
              
              {/* Chart */}
              <div className="bg-[var(--color-panel)] border border-[var(--color-hairline)] p-4 h-96 shrink-0">
                <MultiEquityCurveChart series={chartSeries} height={350} />
              </div>

              {/* Comparison Table */}
              <div className="w-full overflow-x-auto border border-[var(--color-hairline)] bg-[var(--color-panel)]">
                <table className="w-full text-sm text-left">
                  <thead className="bg-[var(--color-elevated)] border-b border-[var(--color-hairline)] text-[var(--color-muted)]">
                    <tr>
                      <th className="p-3 font-medium">Metric</th>
                      {selectedIds.map(id => (
                        <th key={id} className="p-3 font-medium min-w-[120px]">{results[id]?.label || id}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--color-hairline)]">
                    <tr className="hover:bg-[var(--color-elevated)]/50">
                      <td className="p-3 text-[var(--color-dim)]">Net P&L</td>
                      {selectedIds.map(id => <td key={id} className="p-3"><PriceCell value={results[id]?.net_pnl || 0} isCurrency /></td>)}
                    </tr>
                    <tr className="hover:bg-[var(--color-elevated)]/50">
                      <td className="p-3 text-[var(--color-dim)]">Total Return</td>
                      {selectedIds.map(id => <td key={id} className="p-3"><PriceCell value={(results[id]?.total_return_pct || 0) * 100} isPercentage /></td>)}
                    </tr>
                    <tr className="hover:bg-[var(--color-elevated)]/50">
                      <td className="p-3 text-[var(--color-dim)]">Win Rate</td>
                      {selectedIds.map(id => <td key={id} className="p-3"><PriceCell value={results[id]?.win_rate_pct || 0} isPercentage /></td>)}
                    </tr>
                    <tr className="hover:bg-[var(--color-elevated)]/50">
                      <td className="p-3 text-[var(--color-dim)]">Max Drawdown</td>
                      {selectedIds.map(id => <td key={id} className="p-3"><PriceCell value={-(results[id]?.max_drawdown_pct || 0)} isPercentage /></td>)}
                    </tr>
                    <tr className="hover:bg-[var(--color-elevated)]/50">
                      <td className="p-3 text-[var(--color-dim)]">Total Trades</td>
                      {selectedIds.map(id => <td key={id} className="p-3 text-[var(--color-primary)]">{results[id]?.total_trades || 0}</td>)}
                    </tr>
                    <tr className="hover:bg-[var(--color-elevated)]/50">
                      <td className="p-3 text-[var(--color-dim)]">Profit Factor</td>
                      {selectedIds.map(id => <td key={id} className="p-3 text-[var(--color-primary)]">{results[id]?.profit_factor?.toFixed(2) || "0.00"}</td>)}
                    </tr>
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
