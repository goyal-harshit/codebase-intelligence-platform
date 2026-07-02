import { SecurityFinding } from "@/lib/api";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-gray-100 text-gray-700",
};

export default function SecurityTable({ findings }: { findings: SecurityFinding[] }) {
  if (findings.length === 0)
    return <p className="text-sm text-slate-500">No security findings.</p>;

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-500">
          <tr>
            <th className="px-3 py-2">Severity</th>
            <th className="px-3 py-2">Rule</th>
            <th className="px-3 py-2">Location</th>
            <th className="px-3 py-2">Finding</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((f, i) => (
            <tr key={i} className="border-t border-slate-100 align-top">
              <td className="px-3 py-2">
                <span className={`rounded px-2 py-0.5 text-xs ${SEVERITY_COLOR[f.severity] ?? ""}`}>
                  {f.severity}
                </span>
              </td>
              <td className="px-3 py-2 font-medium text-slate-950">
                {f.rule}
                {f.source && f.source !== "builtin" && (
                  <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-normal text-slate-500">
                    {f.source}
                  </span>
                )}
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-slate-500">
                {f.file}:{f.line}
              </td>
              <td className="px-3 py-2 text-slate-600">
                <div>{f.message}</div>
                {f.snippet && (
                  <code className="mt-1 block break-all rounded bg-slate-50 px-2 py-1 text-xs text-slate-700">
                    {f.snippet}
                  </code>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
