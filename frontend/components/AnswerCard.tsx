import { QueryResult } from "@/lib/api";

export default function AnswerCard({ result }: { result: QueryResult }) {
  return (
    <div className="border rounded-lg p-6 bg-white">
      <p className="text-xs text-gray-500 mb-2">
        strategy: {result.strategy}
        {result.cypher ? ` · cypher: ${result.cypher}` : ""}
      </p>
      <p className="whitespace-pre-wrap">{result.answer}</p>
      {result.sources?.length > 0 && (
        <div className="mt-4">
          <p className="font-semibold text-sm">Sources</p>
          <ul className="text-sm text-gray-600 mt-1 space-y-0.5">
            {result.sources.map((s, i) => (
              <li key={i}>📄 {s}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
