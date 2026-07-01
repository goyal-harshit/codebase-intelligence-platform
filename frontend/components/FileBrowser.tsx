"use client";

import { useEffect, useMemo, useState } from "react";
import { FolderTree, Search, RefreshCw } from "lucide-react";
import { getRepoFiles } from "@/lib/api";

/**
 * Searchable list of files from the most recent completed ingest. Clicking a
 * path calls `onSelect(path)` — used by the Impact and Ask pages so users pick
 * an exact repo path instead of guessing the free-text form the graph stored.
 */
export default function FileBrowser({
  onSelect,
  selected,
}: {
  onSelect: (path: string) => void;
  selected?: string;
}) {
  const [files, setFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const load = () => {
    setLoading(true);
    setError(null);
    getRepoFiles()
      .then((r) => setFiles(r.files))
      .catch((e) =>
        setError(e?.response?.data?.detail ?? e?.message ?? "could not load files")
      )
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const shown = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const list = q ? files.filter((f) => f.toLowerCase().includes(q)) : files;
    return list.slice(0, 300);
  }, [files, filter]);

  return (
    <div className="rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2">
        <FolderTree size={16} className="text-slate-500" />
        <span className="text-sm font-medium text-slate-700">Ingested files</span>
        <span className="text-xs text-slate-400">{files.length}</span>
        <button
          onClick={load}
          title="Reload file list"
          className="ml-auto rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>
      <div className="relative border-b border-slate-100 p-2">
        <Search className="pointer-events-none absolute left-4 top-4 text-slate-400" size={15} />
        <input
          className="w-full rounded-md border border-slate-200 py-2 pl-9 pr-3 text-sm text-slate-950 outline-none focus:ring-2 focus:ring-slate-300"
          placeholder="Filter files…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>
      <div className="max-h-72 overflow-y-auto p-1">
        {loading && <p className="px-2 py-3 text-sm text-slate-500">Loading files…</p>}
        {error && !loading && (
          <p className="px-2 py-3 text-sm text-rose-700">{error}</p>
        )}
        {!loading && !error && shown.length === 0 && (
          <p className="px-2 py-3 text-sm text-slate-500">No matching files.</p>
        )}
        {shown.map((f) => (
          <button
            key={f}
            onClick={() => onSelect(f)}
            title={f}
            className={`block w-full truncate rounded px-2 py-1.5 text-left text-sm ${
              selected === f
                ? "bg-slate-950 text-white"
                : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {f}
          </button>
        ))}
      </div>
    </div>
  );
}
