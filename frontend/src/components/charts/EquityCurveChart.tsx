import React, { useEffect, useRef } from "react";
import { createChart, ColorType, IChartApi, ISeriesApi, AreaSeries } from "lightweight-charts";

interface EquityCurveProps {
  data: { time: string; value: number }[];
  height?: number;
}

export function EquityCurveChart({ data, height = 400 }: EquityCurveProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const handleResize = () => {
      chartRef.current?.applyOptions({ width: chartContainerRef.current?.clientWidth });
    };

    chartRef.current = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8b8fa3",
      },
      grid: {
        vertLines: { color: "#2a2d3a" },
        horzLines: { color: "#2a2d3a" },
      },
      width: chartContainerRef.current.clientWidth,
      height,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: 1, // Magnet
      },
    });

    seriesRef.current = chartRef.current.addSeries(AreaSeries, {
      lineColor: "#22c55e",
      topColor: "rgba(34, 197, 94, 0.4)",
      bottomColor: "rgba(34, 197, 94, 0.0)",
      lineWidth: 2,
    });

    if (data && data.length > 0) {
      // Data must be sorted by time
      const sortedData = [...data].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
      
      const formattedData: { time: any, value: number }[] = [];
      let prevTime = -1;
      
      sortedData.forEach(d => {
        const t = Math.floor(new Date(d.time).getTime() / 1000);
        if (t > prevTime) {
          formattedData.push({ time: t as any, value: d.value });
          prevTime = t;
        }
      });
      
      seriesRef.current.setData(formattedData);
      chartRef.current.timeScale().fitContent();
    }

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [data, height]);

  return <div ref={chartContainerRef} className="w-full" />;
}
