"use client";

import React, { useEffect, useState } from "react";
import { listBacktests, getBacktest, deleteBacktest } from "@/lib/api";
import { BacktestResultView } from "@/components/ui/BacktestResultView";

export default function BacktestsPage() {
  const [backtests, setBacktests] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [resultData, setResultData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listBacktests().then(data => setBacktests(data));
  }, []);

  const handleSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value;
    setSelectedId(id);
    if (id) {
      setLoading(true);
      getBacktest(id).then(data => {
        setResultData(data);
        setLoading(false);
      });
    } else {
      setResultData(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this backtest?")) {
      await deleteBacktest(id);
      setBacktests(prev => prev.filter(b => b.id !== id));
      if (selectedId === id) {
        setSelectedId(null);
      }
    }
  };

  return (
    <div className="flex flex-col h-full space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-medium tracking-tight text-[var(--color-primary)]">Backtest Browser</h1>
        <select 
          className="bg-[var(--color-panel)] border border-[var(--color-hairline)] text-sm p-2 rounded outline-none"
          value={selectedId || ""}
          onChange={handleSelect}
        >
          <option value="" disabled>Select a backtest run...</option>
          {backtests.map(b => (
            <option key={b.id} value={b.id}>{b.label || b.id}</option>
          ))}
        </select>
      </div>

      {!selectedId ? (
        <div className="flex-1 flex flex-col items-center justify-center border border-[var(--color-hairline)] bg-[var(--color-panel)] text-[var(--color-dim)]">
          <p>Select a backtest run to view details.</p>
        </div>
      ) : loading ? (
        <div className="flex-1 flex items-center justify-center border border-[var(--color-hairline)] bg-[var(--color-panel)] text-[var(--color-dim)]">
          <p>Loading result data...</p>
        </div>
      ) : resultData ? (
        <BacktestResultView resultData={resultData} onDelete={handleDelete} />
      ) : null}
    </div>
  );
}
