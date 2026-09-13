import React, { useEffect, useRef } from "react";
import { createChart, ColorType, IChartApi, ISeriesApi, LineSeries } from "lightweight-charts";

interface SeriesData {
  name: string;
  data: { time: string; value: number }[];
  color: string;
}

interface MultiEquityCurveProps {
  series: SeriesData[];
  height?: number;
}

export function MultiEquityCurveChart({ series, height = 400 }: MultiEquityCurveProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<"Line">[]>([]);

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
    });

    lineSeriesRef.current = series.map(s => {
      const line = chartRef.current!.addSeries(LineSeries, {
        color: s.color,
        lineWidth: 2,
      });

      if (s.data && s.data.length > 0) {
        const sortedData = [...s.data].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());
        
        const formattedData: { time: any, value: number }[] = [];
        let prevTime = -1;
        
        sortedData.forEach(d => {
          const t = Math.floor(new Date(d.time).getTime() / 1000);
          if (t > prevTime) {
            formattedData.push({ time: t as any, value: d.value });
            prevTime = t;
          }
        });
        
        line.setData(formattedData);
      }
      return line;
    });

    chartRef.current.timeScale().fitContent();

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [series, height]);

  return (
    <div className="relative">
      {/* Legend */}
      <div className="absolute top-4 left-4 z-10 flex flex-col gap-1 bg-[var(--color-elevated)] p-2 rounded border border-[var(--color-hairline)] opacity-80 text-xs">
        {series.map(s => (
          <div key={s.name} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: s.color }} />
            <span>{s.name}</span>
          </div>
        ))}
      </div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  );
}
