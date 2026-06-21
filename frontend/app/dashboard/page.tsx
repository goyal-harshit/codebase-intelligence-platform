"use client";

import { useEffect, useState } from "react";
import { getStats, getRisks, Stats, Risk } from "@/lib/api";
import StatsGrid from "@/components/StatsGrid";
import RiskTable from "@/components/RiskTable";

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getStats(), getRisks()])
      .then(([s, r]) => {
        setStats(s);
        setRisks(r.risks.slice(0, 10));
      })
      .catch((e) => setError(e?.message ?? "backend unavailable"));
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      {error && (
        <p className="text-amber-700 text-sm mb-4">
          Could not load data ({error}). Is the backend running and a repo
          ingested?
        </p>
      )}
      {stats && <StatsGrid stats={stats} />}
      <h2 className="text-lg font-semibold mt-8 mb-3">Top risks</h2>
      <RiskTable risks={risks} />
    </div>
  );
}
