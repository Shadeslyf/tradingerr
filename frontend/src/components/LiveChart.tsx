"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickSeries, createSeriesMarkers, ISeriesMarkersPluginApi } from "lightweight-charts";

export interface Candle {
  time: number; // Unix timestamp
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface Signal {
  timestamp: string;
  action: string;
  price: number;
  confidence: number;
}

interface LiveChartProps {
  candles: Candle[];
  signals: Signal[];
  openPosition?: any;
  currentLtp?: number;
}

export default function LiveChart({ candles, signals, openPosition, currentLtp = 0 }: LiveChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<any> | null>(null);
  const priceLinesRef = useRef<any[]>([]);

  // Calculate live PnL if there's an open position
  const pnl = openPosition 
    ? (openPosition.direction === "LONG" 
        ? (currentLtp - openPosition.entry_price) * openPosition.quantity
        : (openPosition.entry_price - currentLtp) * openPosition.quantity)
    : 0;

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#111827" }, // tailwind gray-900
        textColor: "#9CA3AF", // tailwind gray-400
      },
      grid: {
        vertLines: { color: "#1F2937" },
        horzLines: { color: "#1F2937" },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: number) => {
          const date = new Date(time * 1000);
          return date.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: false });
        },
      },
      localization: {
        locale: 'en-IN',
        timeFormatter: (time: number) => {
          const date = new Date(time * 1000);
          return date.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: false });
        }
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10B981", // tailwind emerald-500
      downColor: "#EF4444", // tailwind red-500
      borderVisible: false,
      wickUpColor: "#10B981",
      wickDownColor: "#EF4444",
    });

    const seriesMarkers = createSeriesMarkers(candlestickSeries);

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;
    markersRef.current = seriesMarkers;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  // Update data when it changes
  useEffect(() => {
    if (seriesRef.current && candles.length > 0) {
      // deduplicate candles by time
      const uniqueCandles = Array.from(new Map(candles.map(c => [c.time, c])).values());
      uniqueCandles.sort((a, b) => a.time - b.time);
      
      try {
        seriesRef.current.setData(uniqueCandles as any);

        if (markersRef.current) {
          const markers = signals.map(sig => {
            const time = Math.floor(new Date(sig.timestamp).getTime() / 1000);
            const isBuy = sig.action.includes("LONG");
            return {
              time: time,
              position: isBuy ? 'belowBar' : 'aboveBar',
              color: isBuy ? '#3B82F6' : '#F59E0B',
              shape: isBuy ? 'arrowUp' : 'arrowDown',
              text: sig.action
            };
          }).sort((a, b) => a.time - b.time) as any;
          
          markersRef.current.setMarkers(markers);
        }

        // Manage Price Lines for open position
        if (seriesRef.current) {
          // Remove existing lines
          priceLinesRef.current.forEach(line => seriesRef.current?.removePriceLine(line));
          priceLinesRef.current = [];

          if (openPosition) {
            priceLinesRef.current.push(seriesRef.current.createPriceLine({
              price: openPosition.entry_price,
              color: '#3B82F6',
              lineWidth: 2,
              lineStyle: 0, // Solid
              axisLabelVisible: true,
              title: `ENTRY (${openPosition.direction})`,
            }));
            
            if (openPosition.target) {
              priceLinesRef.current.push(seriesRef.current.createPriceLine({
                price: openPosition.target,
                color: '#10B981', // Green
                lineWidth: 2,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'TARGET',
              }));
            }
            
            if (openPosition.trailing_sl) {
              priceLinesRef.current.push(seriesRef.current.createPriceLine({
                price: openPosition.trailing_sl,
                color: '#EF4444', // Red
                lineWidth: 2,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'STOP LOSS',
              }));
            }
          }
        }
      } catch (e) {
        console.error("Error setting chart data", e);
      }
    }
  }, [candles, signals, openPosition]);

  return (
    <div className="w-full h-full relative">
      <div ref={chartContainerRef} className="w-full h-full rounded-md overflow-hidden shadow-inner absolute inset-0" />
      
      {openPosition && currentLtp > 0 && (
        <div className="absolute top-4 left-4 z-10 bg-[var(--color-panel)]/95 border border-[var(--color-hairline)] p-4 rounded-lg shadow-xl backdrop-blur-md flex flex-col gap-2 min-w-[200px] pointer-events-none">
          <div className="flex justify-between items-center border-b border-[var(--color-hairline)] pb-2 mb-1">
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--color-dim)]">Active Position</span>
            <span className={`text-xs font-black px-2 py-0.5 rounded ${openPosition.direction === "LONG" ? 'bg-blue-500/20 text-blue-400' : 'bg-orange-500/20 text-orange-400'}`}>
              {openPosition.direction}
            </span>
          </div>
          
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <div className="text-[var(--color-dim)]">Entry:</div>
            <div className="font-mono text-right">₹{openPosition.entry_price.toFixed(2)}</div>
            
            <div className="text-[var(--color-dim)]">Qty:</div>
            <div className="font-mono text-right">{openPosition.quantity}</div>
            
            <div className="text-[var(--color-dim)] font-medium mt-1">Live PnL:</div>
            <div className={`font-mono text-right font-bold text-lg mt-1 ${pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {pnl >= 0 ? '+' : ''}₹{pnl.toFixed(2)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
