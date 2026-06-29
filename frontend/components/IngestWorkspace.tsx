"use client";

import { ChangeEvent, useEffect, useRef, useState } from "react";
import { CheckCircle2, FolderInput, GitBranch, Loader2, UploadCloud } from "lucide-react";
import { getIngest, IngestJob, startIngest, uploadZip } from "@/lib/api";
import StateBlock from "@/components/StateBlock";

const TERMINAL = new Set(["complete", "complete_with_warnings", "failed"]);

function statusTone(status?: string) {
  if (status === "failed") return "text-rose-700 bg-rose-50 border-rose-200";
  if (status === "complete" || status === "complete_with_warnings") {
    return "text-emerald-700 bg-emerald-50 border-emerald-200";
  }
  return "text-sky-700 bg-sky-50 border-sky-200";
}

export default function IngestWorkspace() {
  const [mode, setMode] = useState<"url" | "path" | "zip">("url");
  const [repo, setRepo] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<IngestJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  const poll = (jobId: string) => {
    if (timer.current) clearInterval(timer.current);
    timer.current = setInterval(async () => {
      try {
        const next = await getIngest(jobId);
        setJob(next);
        if (TERMINAL.has(next.status) && timer.current) clearInterval(timer.current);
      } catch {
        if (timer.current) clearInterval(timer.current);
      }
    }, 1500);
  };

  const submit = async () => {
    setError(null);
    setJob(null);
    setSubmitting(true);
    try {
      const next =
        mode === "zip"
          ? await uploadZip(file as File)
          : await startIngest(mode === "url" ? { repo_url: repo } : { repo_path: repo });
      setJob(next);
      poll(next.job_id);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? "request failed");
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit = mode === "zip" ? Boolean(file) : repo.trim().length > 0;

  const onFile = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="mb-5 grid grid-cols-3 gap-2 rounded-lg bg-slate-100 p-1 text-sm">
          {[
            { id: "url", label: "Git URL", icon: GitBranch },
            { id: "path", label: "Local path", icon: FolderInput },
            { id: "zip", label: "ZIP upload", icon: UploadCloud },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setMode(id as typeof mode)}
              className={`flex min-h-10 items-center justify-center gap-2 rounded-md px-2 ${
                mode === id ? "bg-white text-slate-950 shadow-sm" : "text-slate-600"
              }`}
            >
              <Icon size={16} />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {mode === "zip" ? (
          <label className="flex min-h-48 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 text-center hover:border-slate-400">
            <UploadCloud size={32} className="mb-3 text-slate-500" />
            <span className="font-medium text-slate-950">
              {file ? file.name : "Choose a repository ZIP"}
            </span>
            <span className="mt-1 text-sm text-slate-500">
              The backend stores the archive and ingests the extracted repo.
            </span>
            <input className="sr-only" type="file" accept=".zip" onChange={onFile} />
          </label>
        ) : (
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">
              {mode === "url" ? "Repository URL" : "Repository path"}
            </label>
            <input
              className="w-full rounded-lg border border-slate-300 px-4 py-3 text-slate-950 outline-none ring-slate-300 placeholder:text-slate-400 focus:ring-2"
              placeholder={
                mode === "url"
                  ? "https://github.com/pallets/flask"
                  : "C:\\Users\\harsh\\Downloads\\some-repo"
              }
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && canSubmit && submit()}
            />
          </div>
        )}

        {error && <div className="mt-4"><StateBlock state="error" title="Ingest request failed" detail={error} /></div>}

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-500">
            Builds the AST, graph, embeddings, risk findings, and dashboard data.
          </p>
          <button
            onClick={submit}
            disabled={!canSubmit || submitting}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-slate-950 px-5 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
            Start analysis
          </button>
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-lg font-semibold text-slate-950">Job status</h2>
        {!job ? (
          <p className="mt-3 text-sm text-slate-500">
            Start an analysis to track parsing, graph build, embedding, and risk detection.
          </p>
        ) : (
          <div className="mt-4 space-y-4">
            <div className={`rounded-lg border p-3 ${statusTone(job.status)}`}>
              <p className="text-sm font-medium">{job.status}</p>
              <p className="mt-1 font-mono text-xs opacity-80">{job.job_id}</p>
              {job.step && <p className="mt-2 text-sm">Current step: {job.step}</p>}
            </div>
            {job.error && <StateBlock state="error" title="Analysis failed" detail={job.error} />}
            {job.warnings && job.warnings.length > 0 && (
              <StateBlock state="empty" title="Completed with warnings" detail={job.warnings.join("; ")} />
            )}
            {job.result && (
              <div className="grid grid-cols-2 gap-3 text-sm">
                {Object.entries(job.result).map(([key, value]) => (
                  <div key={key} className="rounded-lg bg-slate-50 p-3">
                    <p className="text-xs uppercase tracking-wide text-slate-500">{key}</p>
                    <p className="mt-1 text-xl font-semibold text-slate-950">{String(value)}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
