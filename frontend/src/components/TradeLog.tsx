import React from 'react';
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

interface Props {
  trades: Trade[];
}

export default function TradeLog({ trades }: Props) {
  if (!trades || trades.length === 0) {
    return <div className="text-sm text-[var(--color-dim)] p-4">No trades executed today.</div>;
  }

  // Show most recent first
  const displayTrades = [...trades].reverse();

  return (
    <div className="overflow-x-auto w-full">
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="border-b border-[var(--color-hairline)] text-[var(--color-dim)] uppercase tracking-wider">
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
    </div>
  );
}
