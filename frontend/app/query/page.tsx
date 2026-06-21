"use client";

import { useState } from "react";
import { ask, QueryResult } from "@/lib/api";
import AnswerCard from "@/components/AnswerCard";

export default function QueryPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const search = async () => {
    if (!question) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await ask(question));
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">Ask your codebase</h1>
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded-lg px-4 py-2"
          placeholder="What functions call validate_user?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <button
          onClick={search}
          className="bg-black text-white px-6 py-2 rounded-lg"
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
      </div>

      {error && <p className="mt-4 text-red-600 text-sm">{error}</p>}
      {result && (
        <div className="mt-8">
          <AnswerCard result={result} />
        </div>
      )}
    </div>
  );
}
