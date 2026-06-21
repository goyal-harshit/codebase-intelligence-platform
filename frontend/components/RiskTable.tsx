import { Risk } from "@/lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

export default function RiskTable({ risks }: { risks: Risk[] }) {
  if (risks.length === 0)
    return <p className="text-gray-500 text-sm">No risks found.</p>;

  return (
    <div className="overflow-x-auto border rounded-lg bg-white">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-left text-gray-500">
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
            <tr key={i} className="border-t">
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
              <td className="px-3 py-2 font-medium">{r.target}</td>
              <td className="px-3 py-2 text-gray-500">{r.file}</td>
              <td className="px-3 py-2 text-gray-500">{r.details}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
