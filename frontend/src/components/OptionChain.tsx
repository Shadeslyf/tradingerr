import React from 'react';
import { PriceCell } from './ui/PriceCell';

interface OptionChainItem {
  Strike: number;
  CE_LTP?: number;
  CE_OI?: number;
  PE_LTP?: number;
  PE_OI?: number;
}

interface Props {
  data: OptionChainItem[];
  currentPrice: number;
}

export default function OptionChain({ data, currentPrice }: Props) {
  if (!data || data.length === 0) {
    return <div className="text-sm text-[var(--color-dim)] p-4">No Option Chain Data...</div>;
  }

  // Find nearest strike to highlight ATM
  let atmStrike = 0;
  let minDiff = Infinity;
  for (const item of data) {
    const diff = Math.abs(item.Strike - currentPrice);
    if (diff < minDiff) {
      minDiff = diff;
      atmStrike = item.Strike;
    }
  }

  return (
    <div className="overflow-x-auto w-full">
      <table className="w-full text-xs text-right">
        <thead>
          <tr className="border-b border-[var(--color-hairline)] text-[var(--color-dim)] uppercase tracking-wider">
            <th className="p-2 font-medium">CE OI</th>
            <th className="p-2 font-medium">CE LTP</th>
            <th className="p-2 text-center font-bold text-[var(--color-primary)]">STRIKE</th>
            <th className="p-2 font-medium">PE LTP</th>
            <th className="p-2 font-medium">PE OI</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item, idx) => {
            const isAtm = item.Strike === atmStrike;
            return (
              <tr key={idx} className={`border-b border-[var(--color-hairline)] ${isAtm ? 'bg-[var(--color-primary)]/10' : 'hover:bg-[var(--color-elevated)]'}`}>
                <td className="p-2 text-[var(--color-loss)]">
                  {item.CE_OI ? item.CE_OI.toLocaleString() : '-'}
                </td>
                <td className="p-2">
                  <PriceCell value={item.CE_LTP || 0} />
                </td>
                <td className={`p-2 text-center font-mono ${isAtm ? 'font-bold text-[var(--color-primary)]' : 'text-[var(--color-muted)]'}`}>
                  {item.Strike}
                </td>
                <td className="p-2">
                  <PriceCell value={item.PE_LTP || 0} />
                </td>
                <td className="p-2 text-[var(--color-gain)]">
                  {item.PE_OI ? item.PE_OI.toLocaleString() : '-'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
