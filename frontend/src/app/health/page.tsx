"use client";

import React, { useEffect, useState } from "react";
import { fetchHealth, fetchDatasetInfo, listModels } from "@/lib/api";
import { StatusPill } from "@/components/ui/StatusPill";
import { DataTable } from "@/components/ui/DataTable";
import { format } from "date-fns";
import { Server, Database, Activity } from "lucide-react";

export default function HealthPage() {
  const [health, setHealth] = useState<any>(null);
  const [dataset, setDataset] = useState<any>(null);
  const [models, setModels] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [h, d, m] = await Promise.all([
          fetchHealth(),
          fetchDatasetInfo(),
          listModels()
        ]);
        setHealth(h);
        setDataset(d);
        setModels(m);
      } catch (err: any) {
        setError(err.message);
      }
    }
    load();
  }, []);

  const status = error ? "error" : (health ? "connected" : "reconnecting");

  return (
    <div className="flex flex-col h-full space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-medium tracking-tight text-[var(--color-primary)]">Pipeline Health</h1>
        <StatusPill status={status} text={error ? error : "API Connected"} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[var(--color-panel)] border border-[var(--color-hairline)] p-5 flex items-start space-x-4">
          <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
            <Activity className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-[var(--color-muted)] uppercase tracking-wider">Live Feed</h3>
            <p className="text-xl font-semibold mt-1">
              {health?.live_feed_status === "active" ? "Active (Polling)" : "Inactive"}
            </p>
          </div>
        </div>

        <div className="bg-[var(--color-panel)] border border-[var(--color-hairline)] p-5 flex items-start space-x-4">
          <div className="p-3 bg-green-500/10 rounded-lg border border-green-500/20">
            <Database className="w-6 h-6 text-green-400" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-[var(--color-muted)] uppercase tracking-wider">Dataset</h3>
            <p className="text-xl font-semibold mt-1">
              {dataset?.total_rows.toLocaleString()} Rows
            </p>
            <p className="text-xs text-[var(--color-dim)] mt-1">
              {dataset && `${format(new Date(dataset.min_date), "MMM d, yyyy")} - ${format(new Date(dataset.max_date), "MMM d, yyyy")}`}
            </p>
          </div>
        </div>

        <div className="bg-[var(--color-panel)] border border-[var(--color-hairline)] p-5 flex items-start space-x-4">
          <div className="p-3 bg-purple-500/10 rounded-lg border border-purple-500/20">
            <Server className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-[var(--color-muted)] uppercase tracking-wider">ML Pipeline</h3>
            <p className="text-xl font-semibold mt-1">
              {models.length} Models Ready
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-col bg-[var(--color-panel)] border border-[var(--color-hairline)] overflow-hidden">
        <div className="p-4 border-b border-[var(--color-hairline)] bg-[var(--color-elevated)]">
          <h2 className="text-sm font-medium">Model Calibration Status</h2>
        </div>
        <DataTable 
          data={models}
          keyExtractor={(item: any) => item.name}
          columns={[
            { header: "Model Version", accessorKey: "name" },
            { 
              header: "Isotonic Calibrator", 
              accessorKey: "has_calibrator",
              cell: (item) => (
                item.has_calibrator 
                  ? <span className="text-[var(--color-gain)]">Fitted ✅</span>
                  : <span className="text-[var(--color-loss)]">Missing ❌</span>
              )
            }
          ]}
        />
      </div>
    </div>
  );
}
