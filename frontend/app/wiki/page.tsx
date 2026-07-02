"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpen, Download, Sparkles } from "lucide-react";
import {
  DocgenPage,
  generateDocs,
  getDocgenModules,
  getWikiMarkdown,
} from "@/lib/api";
import MarkdownLite from "@/components/MarkdownLite";
import PageHeader from "@/components/PageHeader";
import StateBlock from "@/components/StateBlock";

export default function WikiPage() {
  const [modules, setModules] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [pages, setPages] = useState<DocgenPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [narrating, setNarrating] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const load = useCallback((module: string | null, narrative: boolean) => {
    if (narrative) setNarrating(true);
    else setLoading(true);
    setError(null);
    generateDocs(module ? [module] : undefined, narrative)
      .then((r) => setPages(r.pages))
      .catch((e) => setError(e?.response?.data?.detail ?? e?.message ?? "request failed"))
      .finally(() => {
        setLoading(false);
        setNarrating(false);
      });
  }, []);

  useEffect(() => {
    // Generating every module up front can take minutes on a large graph, so
    // start with the first module; "All modules" stays available on demand.
    getDocgenModules()
      .then((r) => {
        setModules(r.modules);
        const first = r.modules[0] ?? null;
        setSelected(first);
        load(first, false);
      })
      .catch(() => {
        setModules([]);
        load(null, false);
      });
  }, [load]);

  const select = (module: string | null) => {
    setSelected(module);
    load(module, false);
  };

  const download = async () => {
    setDownloading(true);
    try {
      const { markdown } = await getWikiMarkdown();
      const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "wiki.md";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError((e as Error)?.message ?? "download failed");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Auto-documentation"
        title="Repository wiki"
        description="Per-module documentation generated from the code knowledge graph — entity inventory, dependencies, and an optional AI-written purpose."
        actions={
          <div className="flex gap-2">
            <button
              onClick={() => load(selected, true)}
              disabled={loading || narrating || pages.length === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm text-white disabled:opacity-40"
            >
              <Sparkles size={16} />
              {narrating ? "Writing…" : "Add purpose (local LLM)"}
            </button>
            <button
              onClick={download}
              disabled={downloading || modules.length === 0}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              <Download size={16} />
              {downloading ? "Preparing…" : "Download wiki.md"}
            </button>
          </div>
        }
      />

      <div className="mt-2 flex flex-col gap-5 lg:flex-row">
        <aside className="shrink-0 lg:w-72">
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Modules ({modules.length})
            </p>
            <div className="max-h-[70vh] space-y-0.5 overflow-y-auto text-sm">
              <button
                onClick={() => select(null)}
                className={`w-full rounded-md px-2 py-1.5 text-left transition ${
                  selected === null
                    ? "bg-slate-950 text-white"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                All modules (slow)
              </button>
              {modules.map((m) => (
                <button
                  key={m}
                  onClick={() => select(m)}
                  title={m}
                  className={`w-full truncate rounded-md px-2 py-1.5 text-left font-mono text-xs transition ${
                    selected === m
                      ? "bg-slate-950 text-white"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1 space-y-4">
          {loading && <StateBlock state="loading" title="Generating documentation" />}
          {error && <StateBlock state="error" title="Wiki unavailable" detail={error} />}
          {!loading && !error && pages.length === 0 && (
            <StateBlock
              state="empty"
              title="No documented modules"
              detail="Ingest a repository first — the wiki is generated from its knowledge graph."
            />
          )}
          {!loading &&
            pages.map((p) => (
              <article key={p.module} className="rounded-lg border border-slate-200 bg-white p-5">
                <div className="mb-3 flex items-center gap-2 text-slate-400">
                  <BookOpen size={15} />
                  <span className="font-mono text-xs">{p.module}</span>
                </div>
                <MarkdownLite markdown={p.markdown} />
              </article>
            ))}
        </div>
      </div>
    </div>
  );
}
