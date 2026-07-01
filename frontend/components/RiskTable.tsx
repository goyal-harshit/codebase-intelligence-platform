import React, { useState } from "react";
import { Risk } from "@/lib/api";
import { ChevronDown, ChevronRight } from "lucide-react";
import CommentsPanel from "./CommentsPanel";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

export default function RiskTable({ risks }: { risks: Risk[] }) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (risks.length === 0)
    return <p className="text-sm text-slate-500">No risks found.</p>;

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-500">
          <tr>
            <th className="px-3 py-2 w-8"></th>
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2">Target</th>
            <th className="px-3 py-2">File</th>
            <th className="px-3 py-2">Details</th>
          </tr>
        </thead>
        <tbody>
          {risks.map((r, i) => {
            const isExpanded = expandedIndex === i;
            const riskId = `${r.type}-${r.target}`.replace(/[^a-zA-Z0-9-]/g, "_");
            return (
              <React.Fragment key={i}>
                <tr 
                  className={`border-t border-slate-100 cursor-pointer hover:bg-slate-50 ${isExpanded ? "bg-slate-50" : ""}`}
                  onClick={() => setExpandedIndex(isExpanded ? null : i)}
                >
                  <td className="px-3 py-2 text-slate-400">
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        SEVERITY_COLOR[r.severity] ?? ""
                      }`}
                    >
                      {r.severity}
                    </span>
                  </td>
                  <td className="px-3 py-2">{r.type}</td>
                  <td className="px-3 py-2 font-medium text-slate-950">{r.target}</td>
                  <td className="px-3 py-2 text-slate-500">{r.file}</td>
                  <td className="px-3 py-2 text-slate-500">{r.details}</td>
                </tr>
                {isExpanded && (
                  <tr className="border-t border-slate-100 bg-slate-50">
                    <td colSpan={6} className="p-0">
                      <div className="h-96 border-t border-slate-200 shadow-inner">
                        <CommentsPanel targetType="risk" targetId={riskId} />
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
