import { QueryResult } from "@/lib/api";
import { FileCode2 } from "lucide-react";

export default function AnswerCard({ result }: { result: QueryResult }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <p className="mb-2 text-xs text-slate-500">
        strategy: {result.strategy}
        {result.cypher ? ` · cypher: ${result.cypher}` : ""}
      </p>
      <p className="whitespace-pre-wrap leading-7 text-slate-800">{result.answer}</p>
      {result.sources?.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-semibold text-slate-950">Sources</p>
          <ul className="mt-2 space-y-1 text-sm text-slate-600">
            {result.sources.map((s, i) => (
              <li key={i} className="flex items-start gap-2">
                <FileCode2 size={15} className="mt-0.5 shrink-0" />
                <span className="break-all">{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
