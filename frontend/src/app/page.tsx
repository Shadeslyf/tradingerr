"use client";

import React, { useEffect, useState } from "react";
import { fetchLiveState, fetchHealth } from "@/lib/api";
import { PriceCell } from "@/components/ui/PriceCell";
import { StatusPill } from "@/components/ui/StatusPill";
import { MetricCard } from "@/components/ui/MetricCard";
import { DataTable } from "@/components/ui/DataTable";
import { format } from "date-fns";
import { PlayCircle } from "lucide-react";

export default function LiveTradingPage() {
  const [liveState, setLiveState] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    
    async function poll() {
      try {
        const h = await fetchHealth();
        if (mounted) setHealth(h);
        
        if (h.live_feed_status === "active") {
          const s = await fetchLiveState();
          if (mounted) {
            setLiveState(s);
            setError(null);
          }
        } else {
          if (mounted) setError("Live feed is not active");
        }
      } catch (err: any) {
        if (mounted) setError(err.message);
      }
    }
    
    poll();
    const interval = setInterval(poll, 5000); // 5s polling
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const status = error ? "error" : (health ? "connected" : "reconnecting");
  const statusText = error ? error : (health?.live_feed_status === "active" ? "Live Feed Connected" : "Awaiting Data...");

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
        <h1 className="text-xl font-medium tracking-tight text-[var(--color-primary)]">Live Paper Trading</h1>
        <StatusPill status={status} text={statusText} />
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
