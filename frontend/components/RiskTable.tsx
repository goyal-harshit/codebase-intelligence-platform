import { Risk } from "@/lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

export default function RiskTable({ risks }: { risks: Risk[] }) {
  if (risks.length === 0)
    return <p className="text-sm text-slate-500">No risks found.</p>;

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-500">
          <tr>
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2">Type</th>
            <th className="px-3 py-2">Target</th>
            <th className="px-3 py-2">File</th>
            <th className="px-3 py-2">Details</th>
          </tr>
        </thead>
        <tbody>
          {risks.map((r, i) => (
            <tr key={i} className="border-t border-slate-100">
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
          ))}
        </tbody>
      </table>
    </div>
  );
}
