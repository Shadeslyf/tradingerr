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
}

export default function LiveChart({ candles, signals }: LiveChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<any> | null>(null);

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
      } catch (e) {
        console.error("Error setting chart data", e);
      }
    }
  }, [candles, signals]);

  return <div ref={chartContainerRef} className="w-full h-full rounded-md overflow-hidden shadow-inner" />;
}
