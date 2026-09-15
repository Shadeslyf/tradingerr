import React, { useState } from 'react';
import { PriceCell } from './ui/PriceCell';
import { format } from 'date-fns';

interface Trade {
  entry_time: string;
  exit_time: string;
  direction: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl_rs: number;
  exit_reason: string;
}

interface Signal {
  timestamp: string;
  signal: string;
  confidence: number;
  acted_on: boolean;
  skip_reason: string | null;
}

interface Props {
  trades: Trade[];
  signals?: Signal[];
}

export default function TradeLog({ trades, signals = [] }: Props) {
  const [activeTab, setActiveTab] = useState<'trades' | 'signals'>('signals');

  const displayTrades = [...(trades || [])].reverse();
  
  // Filter out HOLD signals, show most recent first
  const displaySignals = [...signals]
    .filter(s => s.signal !== 'HOLD')
    .reverse();

  return (
    <div className="flex flex-col h-full w-full bg-[var(--color-panel)]">
      {/* Tabs */}
      <div className="flex border-b border-[var(--color-hairline)] bg-[var(--color-elevated)]">
        <button 
          onClick={() => setActiveTab('signals')}
          className={`flex-1 py-2 text-xs font-medium text-center border-b-2 transition-colors ${activeTab === 'signals' ? 'border-[var(--color-primary)] text-[var(--color-primary)] bg-[var(--color-accent)]/10' : 'border-transparent text-[var(--color-muted)] hover:text-[var(--color-primary)] hover:bg-[var(--color-panel)]'}`}
        >
          Live Decisions
        </button>
        <button 
          onClick={() => setActiveTab('trades')}
          className={`flex-1 py-2 text-xs font-medium text-center border-b-2 transition-colors ${activeTab === 'trades' ? 'border-[var(--color-primary)] text-[var(--color-primary)] bg-[var(--color-accent)]/10' : 'border-transparent text-[var(--color-muted)] hover:text-[var(--color-primary)] hover:bg-[var(--color-panel)]'}`}
        >
          Completed Trades ({displayTrades.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'trades' && (
          displayTrades.length === 0 ? (
            <div className="text-sm text-[var(--color-dim)] p-4 text-center mt-4">No trades completed today.</div>
          ) : (
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-[var(--color-hairline)] text-[var(--color-dim)] uppercase tracking-wider sticky top-0 bg-[var(--color-panel)]">
                  <th className="p-2 font-medium">Exit Time</th>
                  <th className="p-2 font-medium">Type</th>
                  <th className="p-2 font-medium">Qty</th>
                  <th className="p-2 font-medium text-right">Entry</th>
                  <th className="p-2 font-medium text-right">Exit</th>
                  <th className="p-2 font-medium text-right">P&L</th>
                  <th className="p-2 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody>
                {displayTrades.map((t, idx) => {
                  const isProfit = t.pnl_rs > 0;
                  return (
                    <tr key={idx} className="border-b border-[var(--color-hairline)] hover:bg-[var(--color-elevated)]">
                      <td className="p-2 font-mono text-[var(--color-muted)] whitespace-nowrap">
                        {format(new Date(t.exit_time), "HH:mm:ss")}
                      </td>
                      <td className="p-2">
                        <span className={`font-medium ${t.direction === "LONG" ? 'text-[var(--color-gain)]' : 'text-[var(--color-loss)]'}`}>
                          {t.direction}
                        </span>
                      </td>
                      <td className="p-2 text-[var(--color-primary)]">{t.quantity}</td>
                      <td className="p-2 text-right"><PriceCell value={t.entry_price} /></td>
                      <td className="p-2 text-right"><PriceCell value={t.exit_price} /></td>
                      <td className="p-2 text-right font-bold">
                        <span className={isProfit ? 'text-[var(--color-gain)]' : 'text-[var(--color-loss)]'}>
                          {isProfit ? '+' : ''}{t.pnl_rs.toFixed(2)}
                        </span>
                      </td>
                      <td className="p-2 text-[10px] text-[var(--color-dim)] uppercase">
                        {t.exit_reason.replace('_', ' ')}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )
        )}

        {activeTab === 'signals' && (
          displaySignals.length === 0 ? (
            <div className="text-sm text-[var(--color-dim)] p-4 text-center mt-4">Waiting for AI to generate signals...</div>
          ) : (
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-[var(--color-hairline)] text-[var(--color-dim)] uppercase tracking-wider sticky top-0 bg-[var(--color-panel)]">
                  <th className="p-2 font-medium">Time</th>
                  <th className="p-2 font-medium">Signal</th>
                  <th className="p-2 font-medium">Conf</th>
                  <th className="p-2 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {displaySignals.map((s, idx) => (
                  <tr key={idx} className="border-b border-[var(--color-hairline)] hover:bg-[var(--color-elevated)]">
                    <td className="p-2 font-mono text-[var(--color-muted)] whitespace-nowrap">
                      {format(new Date(s.timestamp), "HH:mm:ss")}
                    </td>
                    <td className="p-2">
                      <span className={`font-medium ${s.signal === "LONG" ? 'text-blue-500' : 'text-orange-500'}`}>
                        {s.signal}
                      </span>
                    </td>
                    <td className="p-2 font-mono text-[var(--color-dim)]">
                      {(s.confidence * 100).toFixed(1)}%
                    </td>
                    <td className="p-2">
                      {s.acted_on ? (
                        <span className="text-green-500 font-bold bg-green-500/10 px-2 py-0.5 rounded text-[10px] uppercase">Executed</span>
                      ) : (
                        <span className="text-red-400 font-medium bg-red-500/10 px-2 py-0.5 rounded text-[10px] uppercase" title={s.skip_reason || ""}>
                          Skipped: {s.skip_reason}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )
        )}
      </div>
    </div>
  );
}
