"use client";

import { useState } from "react";
import { startIngest, getIngest } from "@/lib/api";

export default function Home() {
  const [repo, setRepo] = useState("");
  const [job, setJob] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const isUrl = repo.startsWith("http") || repo.includes("github.com");

  const submit = async () => {
    setError(null);
    setJob(null);
    try {
      const body = isUrl ? { repo_url: repo } : { repo_path: repo };
      const res = await startIngest(body);
      setJob({ ...res });
      poll(res.job_id);
    } catch (e: any) {
      setError(e?.message ?? "request failed");
    }
  };

  const poll = (jobId: string) => {
    const id = setInterval(async () => {
      try {
        const s = await getIngest(jobId);
        setJob(s);
        if (s.status === "complete" || s.status === "failed")
          clearInterval(id);
      } catch {
        clearInterval(id);
      }
    }, 1500);
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-3xl font-bold mb-2">Analyze a codebase</h1>
      <p className="text-gray-600 mb-6">
        Enter a Git URL or a local path. The backend will parse it, build a
        knowledge graph, embed it, and detect risks.
      </p>

      <div className="flex gap-2">
        <input
          className="flex-1 border rounded-lg px-4 py-2"
          placeholder="https://github.com/pallets/flask  or  /path/to/repo"
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && repo && submit()}
        />
        <button
          onClick={submit}
          disabled={!repo}
          className="bg-black text-white px-6 py-2 rounded-lg disabled:opacity-40"
        >
          Ingest
        </button>
      </div>

      {error && <p className="mt-4 text-red-600 text-sm">Error: {error}</p>}

      {job && (
        <div className="mt-6 border rounded-lg p-4 bg-white text-sm">
          <p>
            Job <span className="font-mono">{job.job_id}</span>
          </p>
          <p className="mt-1">
            Status: <span className="font-semibold">{job.status}</span>
            {job.step ? ` — ${job.step}` : ""}
          </p>
          {job.error && <p className="mt-1 text-red-600">{job.error}</p>}
          {job.result && (
            <pre className="mt-2 text-xs bg-gray-50 p-2 rounded">
              {JSON.stringify(job.result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
