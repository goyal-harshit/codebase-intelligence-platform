"use client";

import { useState } from "react";
import { Search, Sparkles, FolderTree } from "lucide-react";
import { ask, QueryResult } from "@/lib/api";
import AnswerCard from "@/components/AnswerCard";
import FileBrowser from "@/components/FileBrowser";
import PageHeader from "@/components/PageHeader";
import StateBlock from "@/components/StateBlock";

const EXAMPLES = [
  "Where is authentication enforced?",
  "What calls the ingestion pipeline?",
  "Which modules look risky to change?",
];

export default function QueryPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showBrowser, setShowBrowser] = useState(false);

  const insertPath = (path: string) => {
    setQuestion((q) => (q.trim() ? `${q.trimEnd()} ${path}` : `In ${path}, `));
  };

  const search = async (value = question) => {
    if (!value.trim()) return;
    setQuestion(value);
    setLoading(true);
    setError(null);
    try {
      setResult(await ask(value));
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Code Q&A"
        title="Ask your codebase"
        description="Use retrieval and graph-backed context to answer architecture, ownership, and implementation questions."
      />

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-col gap-3 lg:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-3.5 text-slate-400" size={18} />
            <input
              className="w-full rounded-lg border border-slate-300 py-3 pl-10 pr-4 text-slate-950 outline-none ring-slate-300 placeholder:text-slate-400 focus:ring-2"
              placeholder="What functions call validate_user?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
            />
          </div>
          <button
            onClick={() => search()}
            disabled={loading || !question.trim()}
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-slate-950 px-6 py-2 text-sm font-medium text-white disabled:opacity-40"
          >
            <Sparkles size={16} />
            {loading ? "Thinking" : "Ask"}
          </button>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              onClick={() => search(example)}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-950"
            >
              {example}
            </button>
          ))}
          <button
            onClick={() => setShowBrowser((v) => !v)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-950"
          >
            <FolderTree size={15} />
            {showBrowser ? "Hide files" : "Reference a file"}
          </button>
        </div>
        {showBrowser && (
          <div className="mt-3">
            <FileBrowser onSelect={insertPath} />
          </div>
        )}
      </section>

      <div className="mt-6">
        {loading && <StateBlock state="loading" title="Searching graph and semantic index" />}
        {error && <StateBlock state="error" title="Query unavailable" detail={error} />}
        {!loading && !error && !result && (
          <StateBlock
            state="empty"
            title="No answer yet"
            detail="Ask a question after ingesting a repo to get an answer with sources."
          />
        )}
        {result && !loading && (
          <div className="mt-6">
            <AnswerCard result={result} />
          </div>
        )}
      </div>
    </div>
  );
}
