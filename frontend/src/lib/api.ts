const API_BASE = "http://localhost:9000/api";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Failed to fetch health");
  return res.json();
}

export async function fetchLiveState() {
  const res = await fetch(`${API_BASE}/paper-trading/state`);
  if (!res.ok) throw new Error("Failed to fetch live state");
  return res.json();
}

export async function fetchDatasetInfo() {
  const res = await fetch(`${API_BASE}/dataset/info`);
  if (!res.ok) throw new Error("Failed to fetch dataset info");
  return res.json();
}

export async function listModels() {
  const res = await fetch(`${API_BASE}/models`);
  if (!res.ok) throw new Error("Failed to list models");
  return res.json();
}

export async function listBacktests() {
  const res = await fetch(`${API_BASE}/backtests`);
  if (!res.ok) throw new Error("Failed to list backtests");
  return res.json();
}

export async function getBacktest(id: string) {
  const res = await fetch(`${API_BASE}/backtests/${id}`);
  if (!res.ok) throw new Error("Failed to fetch backtest");
  return res.json();
}

export async function getLossAnalysis() {
  const res = await fetch(`${API_BASE}/loss-analysis`);
  if (!res.ok) throw new Error("Failed to fetch loss analysis");
  return res.json();
}

export async function trainModel(payload: { model_name: string; start_date: string; end_date: string }) {
  const res = await fetch(`${API_BASE}/train`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Failed to start training");
  return res.json();
}

export async function runBacktest(payload: { model_name: string; start_date: string; end_date: string; initial_capital: number }) {
  const res = await fetch(`${API_BASE}/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Failed to start backtest");
  return res.json();
}

export async function getJobStatus(jobId: string) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to fetch job status");
  return res.json();
}

export async function deleteModel(name: string) {
  const res = await fetch(`${API_BASE}/models/${name}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete model");
  return res.json();
}

export async function deleteBacktest(id: string) {
  const res = await fetch(`${API_BASE}/backtests/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete backtest");
  return res.json();
}
