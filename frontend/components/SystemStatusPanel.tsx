"use client";

import { useEffect, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import { getServiceHealth, ServiceHealth } from "@/lib/api";

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`}
    />
  );
}

/**
 * Backend service reachability (ArcadeDB / ChromaDB / LLM), so a down
 * dependency shows as an explicit red status instead of a mysterious 503 on the
 * Ask page (plan Phase A.3).
 */
export default function SystemStatusPanel() {
  const [health, setHealth] = useState<ServiceHealth | null>(null);
  const [loading, setLoading] = useState(false);

  const load = () => {
    setLoading(true);
    getServiceHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        <Activity size={18} className="text-slate-700" />
        <h2 className="text-lg font-semibold text-slate-950">Service health</h2>
        <button
          onClick={load}
          className="ml-auto rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          title="Recheck"
        >
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
        </button>
      </div>
      {health ? (
        <ul className="space-y-2 text-sm">
          {Object.entries(health.services).map(([name, s]) => (
            <li key={name} className="flex items-center gap-2">
              <Dot ok={s.ok} />
              <span className="font-medium capitalize text-slate-800">{name}</span>
              <span
                className="ml-auto truncate text-xs text-slate-500"
                title={s.error ?? s.url ?? ""}
              >
                {s.ok ? s.url : s.error ?? "unreachable"}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">Checking services…</p>
      )}
    </section>
  );
}
