"use client";

import React, { useEffect, useState } from "react";
import { fetchLiveState, fetchHealth, startPaperTrading, stopPaperTrading } from "@/lib/api";
import { PriceCell } from "@/components/ui/PriceCell";
import { StatusPill } from "@/components/ui/StatusPill";
import { MetricCard } from "@/components/ui/MetricCard";
import { DataTable } from "@/components/ui/DataTable";
import { format } from "date-fns";
import { PlayCircle, Square, Play, Loader2 } from "lucide-react";

export default function LiveTradingPage() {
  const [liveState, setLiveState] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isToggling, setIsToggling] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const h = await fetchHealth();
        setHealth(h);
        
        // Only fetch state if healthy or active
        if (h.status === "healthy") {
          const state = await fetchLiveState();
          setLiveState(state);
          setError(null);
        }
      } catch (err: any) {
        setError(err.message || "Failed to connect to backend");
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleFeed = async () => {
    setIsToggling(true);
    try {
      if (health?.is_running) {
        await stopPaperTrading();
      } else {
        await startPaperTrading();
      }
      // Instantly refresh health
      const h = await fetchHealth();
      setHealth(h);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setIsToggling(false);
    }
  };

  const status = error ? "error" : (health?.live_feed_status === "active" ? "connected" : "reconnecting");
  const statusText = error ? error : (health?.is_running ? (health?.live_feed_status === "active" ? "Live Feed Connected" : "Awaiting Data...") : "Stopped");

  // Extract V4 (or fallback to first model)
  const models = liveState?.models || {};
  const activeModelName = Object.keys(models).includes("V4") ? "V4" : Object.keys(models)[0];
  const activeModel = models[activeModelName] || {};
  
  const currentCapital = activeModel.capital || 100000;
  const netPnl = currentCapital - 100000;
  const pnlPct = (netPnl / 100000) * 100;

  const positions = activeModel.open_position ? [activeModel.open_position] : [];
  const signals = activeModel.recent_signals || [];
  
  // Format signals for display (newest first)
  const displaySignals = [...signals].reverse().slice(0, 50);

  return (
    <div className="flex flex-col h-full space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-medium tracking-tight text-[var(--color-primary)] flex items-center">
            <PlayCircle className="w-5 h-5 mr-2 text-[var(--color-gain)]" />
            Live Paper Trading
          </h1>
          <StatusPill status={status as any} text={statusText} />
        </div>
        
        <button 
          onClick={handleToggleFeed}
          disabled={isToggling || !health}
          className={`flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            health?.is_running 
              ? "bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20" 
              : "bg-green-500/10 text-green-500 hover:bg-green-500/20 border border-green-500/20"
          } disabled:opacity-50 disabled:cursor-not-allowed`}
        >
          {isToggling ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : health?.is_running ? (
            <Square className="w-4 h-4 mr-2" />
          ) : (
            <Play className="w-4 h-4 mr-2 fill-current" />
          )}
          {health?.is_running ? "Stop Paper Trading" : "Start Paper Trading"}
        </button>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard 
          label="Today's Realized P&L" 
          value={netPnl} 
          isCurrency 
          subtext={<PriceCell value={pnlPct} isPercentage className="font-semibold" />} 
        />
        <MetricCard 
          label="Current Capital" 
          value={currentCapital} 
          isCurrency 
        />
        <MetricCard 
          label="Active Model" 
          value={activeModelName || "None"} 
          subtext="Running on Live NIFTY Spot"
        />
        <MetricCard 
          label="Open Positions" 
          value={positions.length} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        {/* Positions Table */}
        <div className="flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] overflow-hidden">
          <div className="p-4 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)] flex justify-between items-center">
            <h2 className="text-sm font-medium">Open Positions</h2>
          </div>
          <div className="flex-1 overflow-auto">
            <DataTable 
              data={positions}
              emptyMessage="No active positions"
              keyExtractor={(item: any) => item.entry_time}
              columns={[
                { 
                  header: "Type", 
                  accessorKey: "direction", 
                  cell: (item) => (
                    <span className={item.direction === "LONG" ? "text-[var(--color-gain)] font-medium" : "text-[var(--color-loss)] font-medium"}>
                      {item.direction === "LONG" ? "CALL (CE)" : "PUT (PE)"}
                    </span>
                  ) 
                },
                { header: "Entry Price", accessorKey: "entry_price", cell: (item) => <PriceCell value={item.entry_price} /> },
                { 
                  header: "Lots", 
                  accessorKey: "quantity", 
                  cell: (item) => {
                    const lots = Math.floor((item.quantity || 0) / 25);
                    return <span className="text-[var(--color-primary)]">{lots} Lot{lots > 1 ? 's' : ''} <span className="text-[var(--color-dim)] text-xs">({item.quantity} Qty)</span></span>;
                  } 
                },
                { header: "Confidence", accessorKey: "confidence", cell: (item) => <PriceCell value={item.confidence * 100} isPercentage /> },
                { header: "Bars Held", accessorKey: "bars_held" },
              ]}
            />
          </div>
        </div>

        {/* Signal Feed */}
        <div className="flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] overflow-hidden">
          <div className="p-4 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)] flex justify-between items-center">
            <h2 className="text-sm font-medium">Live Signal Feed (1-Min)</h2>
            <div className="flex items-center text-[var(--color-dim)] text-xs">
              <PlayCircle className="w-4 h-4 mr-1 animate-pulse text-[var(--color-gain)]" />
              Monitoring
            </div>
          </div>
          <div className="flex-1 overflow-auto">
            <DataTable 
              data={displaySignals}
              emptyMessage="Waiting for signals..."
              keyExtractor={(item: any, idx) => `${item.timestamp}-${idx}`}
              columns={[
                { 
                  header: "Time", 
                  accessorKey: "timestamp", 
                  cell: (item) => <span className="font-mono text-xs">{format(new Date(item.timestamp), "HH:mm:ss")}</span> 
                },
                { 
                  header: "Signal", 
                  accessorKey: "signal",
                  cell: (item) => (
                    <span className={
                      item.signal === "LONG" ? "text-[var(--color-gain)] font-bold" : 
                      item.signal === "SHORT" ? "text-[var(--color-loss)] font-bold" : 
                      "text-[var(--color-muted)]"
                    }>
                      {item.signal}
                    </span>
                  )
                },
                { header: "Conf.", accessorKey: "confidence", cell: (item) => <PriceCell value={item.confidence * 100} isPercentage /> },
                { 
                  header: "Action", 
                  accessorKey: "acted_on",
                  cell: (item) => (
                    <div className="flex items-center">
                      {item.acted_on ? (
                        <span className="text-[var(--color-gain)] text-xs font-medium bg-green-500/10 px-2 py-0.5 rounded border border-green-500/20">EXECUTED</span>
                      ) : (
                        <span className="text-[var(--color-muted)] text-xs font-medium flex items-center">
                          SKIPPED {item.skip_reason && <span className="ml-1 text-[var(--color-dim)] text-[10px]">({item.skip_reason})</span>}
                        </span>
                      )}
                    </div>
                  )
                },
              ]}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
