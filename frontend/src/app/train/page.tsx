"use client";

import React, { useState, useEffect } from "react";
import { fetchDatasetInfo, trainModel, runBacktest, listModels, getJobStatus, getBacktest } from "@/lib/api";
import { BacktestResultView } from "@/components/ui/BacktestResultView";
import { format } from "date-fns";
import { FlaskConical, Play, CheckCircle2, Loader2, XCircle } from "lucide-react";

export default function TrainPage() {
  const [dataset, setDataset] = useState<any>(null);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  
  // Train Form State
  const [modelName, setModelName] = useState("V4 (Pro + WF)");
  const [trainStart, setTrainStart] = useState("");
  const [trainEnd, setTrainEnd] = useState("");
  
  // Backtest Form State
  const [btModel, setBtModel] = useState("");
  const [btStart, setBtStart] = useState("");
  const [btEnd, setBtEnd] = useState("");
  const [capital, setCapital] = useState(100000);

  // Job Tracking
  const [activeJob, setActiveJob] = useState<any>(null);
  const [activeBacktestResult, setActiveBacktestResult] = useState<any>(null);

  useEffect(() => {
    fetchDatasetInfo().then(d => {
      setDataset(d);
      // Auto-fill dates with recent 3 months for backtest, previous 6 months for train
      if (d.max_date && d.min_date) {
        const max = new Date(d.max_date);
        const endStr = max.toISOString().split("T")[0];
        
        const startBt = new Date(max);
        startBt.setMonth(startBt.getMonth() - 3);
        const startBtStr = startBt.toISOString().split("T")[0];
        
        const endTrain = new Date(startBt);
        const endTrainStr = endTrain.toISOString().split("T")[0];
        
        const startTrain = new Date(endTrain);
        startTrain.setMonth(startTrain.getMonth() - 6);
        const startTrainStr = startTrain.toISOString().split("T")[0];

        setBtEnd(endStr);
        setBtStart(startBtStr);
        setTrainEnd(endTrainStr);
        setTrainStart(startTrainStr);
      }
    });
    listModels().then(m => {
      setAvailableModels(m);
      if (m.length > 0) {
        const v4 = m.find(model => model.name.includes("v4") || model.name.includes("V4"));
        setBtModel(v4 ? v4.name : m[0].name);
      }
    });
  }, []);

  // Job Polling
  useEffect(() => {
    if (!activeJob || activeJob.status === "COMPLETED" || activeJob.status === "FAILED") return;

    const interval = setInterval(async () => {
      try {
        const status = await getJobStatus(activeJob.job_id);
        setActiveJob(status);
        if (status.status === "COMPLETED") {
          if (status.job_type === "BACKTEST") {
            getBacktest(`job_${status.job_id}`).then(setActiveBacktestResult).catch(console.error);
          } else {
            listModels().then(setAvailableModels); // Refresh models if training finished
          }
        }
      } catch (err) {
        console.error("Failed to poll job", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeJob]);

  const handleTrain = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modelName || !trainStart || !trainEnd) return;
    try {
      const res = await trainModel({
        model_name: modelName,
        start_date: trainStart,
        end_date: trainEnd
      });
      setActiveJob({ ...res, status: "PENDING", progress: 0 });
    } catch (err: any) {
      alert("Failed to start training: " + err.message);
    }
  };

  const handleBacktest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!btModel || !btStart || !btEnd || !capital) return;
    try {
      const res = await runBacktest({
        model_name: btModel,
        start_date: btStart,
        end_date: btEnd,
        initial_capital: capital
      });
      setActiveJob({ ...res, status: "PENDING", progress: 0 });
    } catch (err: any) {
      alert("Failed to start backtest: " + err.message);
    }
  };

  return (
    <div className="flex flex-col h-full space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-medium tracking-tight text-[var(--color-primary)] flex items-center">
          <FlaskConical className="w-5 h-5 mr-2 text-purple-400" />
          Model Studio
        </h1>
        {dataset && (
          <div className="text-xs text-[var(--color-dim)]">
            Dataset Range: {format(new Date(dataset.min_date), "yyyy-MM-dd")} to {format(new Date(dataset.max_date), "yyyy-MM-dd")}
          </div>
        )}
      </div>

      {activeJob && (
        <div className={`p-4 border ${activeJob.status === 'FAILED' ? 'border-red-500/50 bg-red-500/10' : activeJob.status === 'COMPLETED' ? 'border-green-500/50 bg-green-500/10' : 'border-blue-500/50 bg-blue-500/10'} rounded-lg flex items-center justify-between`}>
          <div className="flex items-center">
            {activeJob.status === 'PENDING' || activeJob.status === 'RUNNING' ? (
              <Loader2 className="w-5 h-5 animate-spin mr-3 text-blue-400" />
            ) : activeJob.status === 'COMPLETED' ? (
              <CheckCircle2 className="w-5 h-5 mr-3 text-green-400" />
            ) : (
              <XCircle className="w-5 h-5 mr-3 text-red-400" />
            )}
            <div>
              <h3 className="font-medium capitalize">{activeJob.job_type?.toLowerCase()} Job: {activeJob.status}</h3>
              {activeJob.progress !== undefined && activeJob.status !== 'COMPLETED' && (
                <p className="text-sm opacity-80">Progress: {(activeJob.progress * 100).toFixed(0)}%</p>
              )}
            </div>
          </div>
          {activeJob.status === 'COMPLETED' && (
            <button onClick={() => { setActiveJob(null); setActiveBacktestResult(null); }} className="text-sm opacity-60 hover:opacity-100">Dismiss</button>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Train New Model */}
        <form onSubmit={handleTrain} className="bg-[var(--color-panel)] border border-[var(--color-hairline)] flex flex-col">
          <div className="p-4 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)]">
            <h2 className="text-sm font-medium text-[var(--color-primary)]">Train New Model</h2>
            <p className="text-xs text-[var(--color-dim)] mt-1">Train an XGBoost model and fit Isotonic Calibrators.</p>
          </div>
          <div className="p-4 space-y-4 flex-1">
            <div>
              <label className="block text-xs font-medium text-[var(--color-muted)] mb-1">Model Name / Version</label>
              <input 
                type="text" 
                required
                value={modelName}
                onChange={e => setModelName(e.target.value)}
                placeholder="e.g., V5_Bullish_Regime"
                className="w-full bg-[var(--color-elevated)] border border-[var(--color-hairline)] rounded p-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[var(--color-muted)] mb-1">Start Date</label>
                <input 
                  type="date" 
                  required
                  value={trainStart}
                  onChange={e => setTrainStart(e.target.value)}
                  min={dataset ? dataset.min_date.split("T")[0] : ""}
                  max={dataset ? dataset.max_date.split("T")[0] : ""}
                  className="w-full bg-[var(--color-elevated)] border border-[var(--color-hairline)] rounded p-2 text-sm outline-none focus:border-[var(--color-primary)] [color-scheme:dark]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--color-muted)] mb-1">End Date</label>
                <input 
                  type="date" 
                  required
                  value={trainEnd}
                  onChange={e => setTrainEnd(e.target.value)}
                  min={dataset ? dataset.min_date.split("T")[0] : ""}
                  max={dataset ? dataset.max_date.split("T")[0] : ""}
                  className="w-full bg-[var(--color-elevated)] border border-[var(--color-hairline)] rounded p-2 text-sm outline-none focus:border-[var(--color-primary)] [color-scheme:dark]"
                />
              </div>
            </div>
          </div>
          <div className="p-4 border-t border-[var(--color-hairline)] bg-black/20">
            <button 
              type="submit"
              disabled={!!activeJob && activeJob.status !== "COMPLETED" && activeJob.status !== "FAILED"}
              className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded transition-colors disabled:opacity-50 flex items-center justify-center"
            >
              <Play className="w-4 h-4 mr-2" /> Start Training
            </button>
          </div>
        </form>

        {/* Run Walk-Forward Backtest */}
        <form onSubmit={handleBacktest} className="bg-[var(--color-panel)] border border-[var(--color-hairline)] flex flex-col">
          <div className="p-4 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)]">
            <h2 className="text-sm font-medium text-[var(--color-primary)]">Run Backtest</h2>
            <p className="text-xs text-[var(--color-dim)] mt-1">Simulate historical trading using a trained model.</p>
          </div>
          <div className="p-4 space-y-4 flex-1">
            <div>
              <label className="block text-xs font-medium text-[var(--color-muted)] mb-1">Select Model</label>
              <select 
                required
                value={btModel}
                onChange={e => setBtModel(e.target.value)}
                className="w-full bg-[var(--color-elevated)] border border-[var(--color-hairline)] rounded p-2 text-sm outline-none focus:border-[var(--color-primary)]"
              >
                <option value="" disabled>Select model...</option>
                {availableModels.map(m => (
                  <option key={m.name} value={m.name}>{m.name}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[var(--color-muted)] mb-1">Start Date</label>
                <input 
                  type="date" 
                  required
                  value={btStart}
                  onChange={e => setBtStart(e.target.value)}
                  min={dataset ? dataset.min_date.split("T")[0] : ""}
                  max={dataset ? dataset.max_date.split("T")[0] : ""}
                  className="w-full bg-[var(--color-elevated)] border border-[var(--color-hairline)] rounded p-2 text-sm outline-none focus:border-[var(--color-primary)] [color-scheme:dark]"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--color-muted)] mb-1">End Date</label>
                <input 
                  type="date" 
                  required
                  value={btEnd}
                  onChange={e => setBtEnd(e.target.value)}
                  min={dataset ? dataset.min_date.split("T")[0] : ""}
                  max={dataset ? dataset.max_date.split("T")[0] : ""}
                  className="w-full bg-[var(--color-elevated)] border border-[var(--color-hairline)] rounded p-2 text-sm outline-none focus:border-[var(--color-primary)] [color-scheme:dark]"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-[var(--color-muted)] mb-1">Initial Capital (₹)</label>
              <input 
                type="number" 
                required
                min={10000}
                step={10000}
                value={capital}
                onChange={e => setCapital(parseInt(e.target.value) || 100000)}
                className="w-full bg-[var(--color-elevated)] border border-[var(--color-hairline)] rounded p-2 text-sm outline-none focus:border-[var(--color-primary)]"
              />
            </div>
          </div>
          <div className="p-4 border-t border-[var(--color-hairline)] bg-black/20">
            <button 
              type="submit"
              disabled={!!activeJob && activeJob.status !== "COMPLETED" && activeJob.status !== "FAILED"}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition-colors disabled:opacity-50 flex items-center justify-center"
            >
              <Play className="w-4 h-4 mr-2" /> Start Simulation
            </button>
          </div>
        </form>
      </div>

      {activeBacktestResult && (
        <div className="mt-6 border-t border-[var(--color-hairline)] pt-6">
          <BacktestResultView resultData={activeBacktestResult} />
        </div>
      )}
    </div>
  );
}
