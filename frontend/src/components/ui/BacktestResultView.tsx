import React from "react";
import { MetricCard } from "./MetricCard";
import { DataTable } from "./DataTable";
import { PriceCell } from "./PriceCell";
import { EquityCurveChart } from "@/components/charts/EquityCurveChart";
import { format } from "date-fns";
import { Trash2 } from "lucide-react";

export function BacktestResultView({ resultData, onDelete }: { resultData: any, onDelete?: (id: string) => void }) {
  const chartData = React.useMemo(() => {
    if (!resultData?.equity_curve || !resultData?.equity_times) return [];
    return resultData.equity_curve.map((val: number, i: number) => ({
      time: resultData.equity_times[i],
      value: val
    }));
  }, [resultData]);

  if (!resultData) return null;

  return (
    <div className="flex flex-col h-full space-y-4 overflow-y-auto">
      {/* Header row with optional Delete button */}
      <div className="flex justify-between items-end shrink-0">
        <div>
          <h2 className="text-lg font-medium">{resultData.label}</h2>
          <p className="text-sm text-[var(--color-dim)]">Initial Capital: <PriceCell value={resultData.initial_capital} isCurrency /></p>
        </div>
        {onDelete && (
          <button 
            onClick={() => onDelete(resultData.id)}
            className="flex items-center px-3 py-1.5 text-xs text-red-500 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 rounded transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5 mr-1.5" />
            Delete Run
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 shrink-0">
        <MetricCard label="Net P&L" value={resultData.net_pnl} isCurrency colored showSign subtext={<PriceCell value={resultData.total_return_pct * 100} isPercentage colored showSign />} />
        <MetricCard label="Win Rate" value={resultData.win_rate_pct} isPercentage subtext={`${resultData.win_trades} W / ${resultData.loss_trades} L`} />
        <MetricCard label="Max Drawdown" value={-resultData.max_drawdown_pct} isPercentage />
        <MetricCard 
          label="Risk : Reward" 
          value={(() => {
            if (!resultData.avg_loss_rs) return "0:0";
            const r = Math.abs(resultData.avg_win_rs / resultData.avg_loss_rs);
            return r >= 1 ? `1 : ${r.toFixed(2)}` : `${(1/r).toFixed(2)} : 1`;
          })()} 
        />
        <MetricCard label="Profit Factor" value={resultData.profit_factor || 0} />
        <MetricCard label="Total Trades" value={resultData.total_trades} />
      </div>

      <div className="bg-[var(--color-panel)] border border-[var(--color-hairline)] p-4 h-96 shrink-0">
        <h3 className="text-sm font-medium text-[var(--color-muted)] mb-4">Equity Curve</h3>
        <EquityCurveChart data={chartData} height={320} />
      </div>

      <div className="flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] min-h-[400px]">
        <div className="p-4 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)] shrink-0">
          <h2 className="text-sm font-medium">Trade Log</h2>
        </div>
        <div className="flex-1 overflow-auto">
          <DataTable 
            data={resultData.trades || []}
            keyExtractor={(item: any, idx) => `${item.entry_time}-${idx}`}
            columns={[
              { header: "Entry Time", accessorKey: "entry_time", cell: (item) => format(new Date(item.entry_time), "MMM d, yyyy HH:mm") },
              { header: "Exit Time", accessorKey: "exit_time", cell: (item) => item.exit_time ? format(new Date(item.exit_time), "MMM d, yyyy HH:mm") : "-" },
              { 
                header: "Type", 
                accessorKey: "direction", 
                cell: (item) => (
                  <span className={item.direction === "LONG" ? "text-[var(--color-gain)] font-medium" : "text-[var(--color-loss)] font-medium"}>
                    {item.direction === "LONG" ? "CALL (CE)" : "PUT (PE)"}
                  </span>
                ) 
              },
              { 
                header: "Lots", 
                accessorKey: "quantity", 
                cell: (item) => {
                  const lotSize = item.lot_size || 50; // Fallback to 50 for old backtest results
                  const lots = Math.floor((item.quantity || 0) / lotSize);
                  return (
                    <div className="flex flex-col">
                      <span className="text-[var(--color-primary)]">
                        {lots} Lot{lots > 1 ? 's' : ''} 
                        {item.is_house_money && (
                          <span className="ml-1 px-1 py-0.5 text-[8px] bg-purple-500/20 text-purple-400 rounded-sm uppercase tracking-wider font-bold">HM</span>
                        )}
                      </span>
                      <span className="text-[var(--color-dim)] text-xs">({item.quantity} Qty)</span>
                    </div>
                  );
                } 
              },
              { header: "Conf.", accessorKey: "confidence", cell: (item) => <PriceCell value={item.confidence * 100} isPercentage /> },
              { header: "Entry", accessorKey: "entry_price", cell: (item) => <PriceCell value={item.entry_price} /> },
              { header: "Exit", accessorKey: "exit_price", cell: (item) => <PriceCell value={item.exit_price} /> },
              { 
                header: "Costs", 
                accessorKey: "costs", 
                cell: (item) => {
                  const totalCosts = (item.theta_cost || 0) + (item.slippage_cost || 0) + (item.brokerage || 0);
                  return totalCosts > 0 ? (
                    <div className="flex flex-col" title={`Theta: ₹${item.theta_cost} | Slippage: ₹${item.slippage_cost} | Brokerage: ₹${item.brokerage}`}>
                      <PriceCell value={-totalCosts} isCurrency className="text-[var(--color-loss)]" />
                      <span className="text-[8px] text-[var(--color-dim)] mt-0.5">FEE+SLP+THT</span>
                    </div>
                  ) : "-";
                }
              },
              { header: "Net P&L", accessorKey: "pnl_rs", cell: (item) => <PriceCell value={item.pnl_rs} isCurrency colored showSign /> },
              { header: "Capital", accessorKey: "capital_after", cell: (item) => <PriceCell value={item.capital_after} isCurrency className="font-medium" /> },
              { header: "Reason", accessorKey: "exit_reason", cell: (item) => <span className="text-xs text-[var(--color-muted)]">{item.exit_reason}</span> },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
