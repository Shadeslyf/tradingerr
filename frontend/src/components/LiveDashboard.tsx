"use client";

import React, { useEffect, useState, useRef } from 'react';
import LiveChart, { Candle, Signal } from './LiveChart';
import OptionChain from './OptionChain';
import TradeLog from './TradeLog';
import { Loader2 } from 'lucide-react';

const API_BASE = "http://localhost:9000/api";
const WS_BASE = "ws://localhost:9000/api/live/stream";

export default function LiveDashboard({ liveState }: { liveState: any }) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [currentLtp, setCurrentLtp] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  
  // Extract data from backend polling state (for trades, signals, option chain)
  const models = liveState?.models || {};
  const activeModelName = Object.keys(models).includes("V4") ? "V4" : (Object.keys(models).includes("V3") ? "V3" : Object.keys(models)[0]);
  const activeModel = models[activeModelName] || {};
  
  const trades = activeModel.trades || [];
  const signalsRaw = activeModel.recent_signals || [];
  const optionChainData = liveState?.option_chain || [];
  
  // Convert backend signals to chart format
  const chartSignals: Signal[] = signalsRaw
    .filter((s: any) => s.acted_on) // Only plot executed trades
    .map((s: any) => ({
      timestamp: s.timestamp,
      action: s.signal,
      price: 0, // Not strictly needed for arrows, just time is needed
      confidence: s.confidence
    }));

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimeout: NodeJS.Timeout;
    let isIntentionallyClosed = false;

    const connect = () => {
      ws = new WebSocket(WS_BASE);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          if (msg.type === "HISTORY") {
            // Bulk load candles
            const historyCandles = msg.data.map((c: any) => ({
              time: Math.floor(new Date(c[0]).getTime() / 1000),
              open: c[1],
              high: c[2],
              low: c[3],
              close: c[4],
            }));
            setCandles(historyCandles);
            
            if (historyCandles.length > 0) {
              setCurrentLtp(historyCandles[historyCandles.length - 1].close);
            }
          } 
          else if (msg.type === "TICK") {
            // Live Tick
            const tickTime = new Date(msg.timestamp);
            // Floor to the minute
            tickTime.setSeconds(0, 0);
            const timeUnix = Math.floor(tickTime.getTime() / 1000);
            const price = msg.price;
            
            setCurrentLtp(price);

            setCandles(prev => {
              if (prev.length === 0) return prev;
              
              const newCandles = [...prev];
              const lastCandle = newCandles[newCandles.length - 1];
              
              if (lastCandle.time === timeUnix) {
                // Update current candle
                lastCandle.high = Math.max(lastCandle.high, price);
                lastCandle.low = Math.min(lastCandle.low, price);
                lastCandle.close = price;
              } else if (timeUnix > lastCandle.time) {
                // New candle minute!
                newCandles.push({
                  time: timeUnix,
                  open: price,
                  high: price,
                  low: price,
                  close: price
                });
                
                // keep max 200 bars in frontend
                if (newCandles.length > 200) {
                  newCandles.shift();
                }
              }
              
              return newCandles;
            });
          }
        } catch (e) {
          console.error("Failed to parse WS msg", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        if (!isIntentionallyClosed) {
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };
      
      ws.onerror = () => {
        ws.close();
      };
    };

    connect();

    return () => {
      isIntentionallyClosed = true;
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-[600px]">
      
      {/* Chart Section (Left 2 columns) */}
      <div className="xl:col-span-2 flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] overflow-hidden">
        <div className="p-3 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)] flex justify-between items-center">
          <h2 className="text-sm font-medium flex items-center">
            NIFTY 50 Live Chart
            {isConnected ? (
              <span className="ml-3 px-2 py-0.5 rounded text-[10px] font-medium bg-green-500/10 text-green-500 border border-green-500/20">LIVE TICKING</span>
            ) : (
              <span className="ml-3 px-2 py-0.5 rounded text-[10px] font-medium bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 flex items-center"><Loader2 className="w-3 h-3 animate-spin mr-1"/> RECONNECTING WS</span>
            )}
          </h2>
          <div className="text-xs font-mono font-bold text-[var(--color-primary)]">
            LTP: ₹{currentLtp > 0 ? currentLtp.toFixed(2) : "---"}
          </div>
        </div>
        <div className="flex-1 min-h-0 relative">
          <LiveChart 
            candles={candles} 
            signals={chartSignals} 
            openPosition={activeModel.open_position}
            currentLtp={currentLtp}
          />
        </div>
      </div>

      {/* Right Column: Option Chain & Trades */}
      <div className="flex flex-col gap-6 min-h-0">
        
        {/* Option Chain */}
        <div className="flex-1 flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] overflow-hidden">
          <div className="p-3 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)] flex justify-between items-center">
            <h2 className="text-sm font-medium">Live Option Chain</h2>
          </div>
          <div className="flex-1 overflow-auto">
            <OptionChain data={optionChainData} currentPrice={currentLtp} />
          </div>
        </div>
        
        {/* Bot Trade Execution Log */}
        <div className="flex-1 flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] overflow-hidden">
          <div className="p-3 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)] flex justify-between items-center">
            <h2 className="text-sm font-medium">Bot Execution Log</h2>
          </div>
          <div className="flex-1 overflow-auto">
            <TradeLog trades={trades} signals={activeModel.recent_signals || []} />
          </div>
        </div>

      </div>
      
    </div>
  );
}
