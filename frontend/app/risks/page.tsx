"use client";

import { useEffect, useState } from "react";
import { getRisks, Risk } from "@/lib/api";
import RiskTable from "@/components/RiskTable";

const SEVERITIES = ["", "critical", "high", "medium", "low"];

export default function RisksPage() {
  const [severity, setSeverity] = useState("");
  const [risks, setRisks] = useState<Risk[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getRisks(severity || undefined)
      .then((r) => {
        setRisks(r.risks);
        setError(null);
      })
      .catch((e) => setError(e?.message ?? "backend unavailable"));
  }, [severity]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Architecture risks</h1>
        <select
          className="border rounded-lg px-3 py-1.5 text-sm"
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
        >
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s === "" ? "all severities" : s}
            </option>
          ))}
        </select>
      </div>
      {error && (
        <p className="text-amber-700 text-sm mb-4">
          Could not load risks ({error}).
        </p>
      )}
      <RiskTable risks={risks} />
    </div>
  );
}
