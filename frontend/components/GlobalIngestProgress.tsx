"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { IngestJob, listIngest } from "@/lib/api";

const ACTIVE = new Set(["queued", "running"]);
const TERMINAL = new Set(["complete", "complete_with_warnings", "failed"]);

const POLL_ACTIVE_MS = 4_000; // a job is queued/running
const POLL_IDLE_MS = 15_000; // nothing in flight — keep a slow heartbeat
const POLL_ERROR_BASE_MS = 30_000; // 401/403/network — back off, render nothing
const POLL_ERROR_MAX_MS = 5 * 60_000;
const NOTICE_MS = 8_000;

/** "https://github.com/pallets/flask.git" | "C:\repos\flask\" -> "flask" */
function repoName(job: IngestJob): string {
  const src = job.repo_path || job.repo_url || "";
  const base = src.replace(/[\\/]+$/, "").split(/[\\/]/).pop() ?? "";
  return base.replace(/\.git$/i, "") || "repository";
}

/**
 * Slim, app-wide ingestion status bar rendered directly under the header.
 * Polls the recent-jobs endpoint (fast while a job runs, slow when idle,
 * paused while the tab is hidden) so users can browse other pages during a
 * long embedding run. Renders nothing when idle or when the API is
 * unreachable/unauthorized.
 */
export default function GlobalIngestProgress() {
  const [activeJob, setActiveJob] = useState<IngestJob | null>(null);
  const [notice, setNotice] = useState<IngestJob | null>(null);
  // job_id -> last seen status, so we only announce transitions we observed.
  const seenRef = useRef<Map<string, string>>(new Map());
  const errorStreakRef = useRef(0);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const noticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const tick = useCallback(async (): Promise<number> => {
    try {
      const { jobs } = await listIngest(10);
      errorStreakRef.current = 0;
      const seen = seenRef.current;
      const justFinished = jobs.find(
        (j) =>
          TERMINAL.has(j.status) &&
          ACTIVE.has(seen.get(j.job_id) ?? "")
      );
      seenRef.current = new Map(jobs.map((j) => [j.job_id, j.status]));
      const active = jobs.find((j) => ACTIVE.has(j.status)) ?? null;
      setActiveJob(active);
      if (justFinished) {
        setNotice(justFinished);
        if (noticeTimerRef.current) clearTimeout(noticeTimerRef.current);
        noticeTimerRef.current = setTimeout(() => setNotice(null), NOTICE_MS);
      }
      return active ? POLL_ACTIVE_MS : POLL_IDLE_MS;
    } catch {
      // 401/403 (not signed in), network failure, or the endpoint not being
      // deployed yet: disappear and retry with exponential backoff.
      errorStreakRef.current += 1;
      setActiveJob(null);
      return Math.min(
        POLL_ERROR_BASE_MS * 2 ** (errorStreakRef.current - 1),
        POLL_ERROR_MAX_MS
      );
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loop = async () => {
      if (cancelled || document.hidden) return; // resumed by visibilitychange
      const delay = await tick();
      if (cancelled) return;
      pollTimerRef.current = setTimeout(loop, delay);
    };

    const onVisibility = () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (!document.hidden) void loop();
    };

    void loop();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelled = true;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (noticeTimerRef.current) clearTimeout(noticeTimerRef.current);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [tick]);

  /* ── Active job: name + step + 2px progress track ── */
  if (activeJob) {
    const pct =
      typeof activeJob.progress === "number"
        ? Math.max(0, Math.min(100, activeJob.progress))
        : null;
    return (
      <div role="status" aria-live="polite" className="border-b border-sky-200 bg-sky-50">
        <div className="mx-auto flex max-w-7xl items-center gap-2 px-4 py-1.5 text-xs text-sky-700 sm:px-6">
          <Loader2 size={13} className="shrink-0 animate-spin" />
          <span className="truncate font-medium">
            Ingesting {repoName(activeJob)}
          </span>
          {activeJob.step && (
            <span className="hidden truncate text-sky-600 sm:inline">
              — {activeJob.step}
            </span>
          )}
          <span className="ml-auto flex shrink-0 items-center gap-3">
            {pct !== null && (
              <span className="font-medium tabular-nums">{pct}%</span>
            )}
            <Link
              href="/"
              className="underline decoration-sky-300 underline-offset-2 transition hover:text-sky-950"
            >
              View
            </Link>
          </span>
        </div>
        <div className="h-0.5 w-full overflow-hidden bg-sky-100">
          {pct !== null ? (
            <div
              className="h-full bg-sky-500 transition-[width] duration-500"
              style={{ width: `${pct}%` }}
            />
          ) : (
            <div className="h-full w-1/4 animate-[ingest-indeterminate_1.4s_ease-in-out_infinite] bg-sky-500" />
          )}
        </div>
      </div>
    );
  }

  /* ── Brief terminal notice, then hide ── */
  if (notice) {
    const failed = notice.status === "failed";
    const warned = notice.status === "complete_with_warnings";
    const tone = failed
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : warned
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : "border-emerald-200 bg-emerald-50 text-emerald-700";
    const Icon = failed ? XCircle : warned ? AlertTriangle : CheckCircle2;
    return (
      <div role="status" aria-live="polite" className={`border-b ${tone}`}>
        <div className="mx-auto flex max-w-7xl items-center gap-2 px-4 py-1.5 text-xs sm:px-6">
          <Icon size={13} className="shrink-0" />
          <span className="truncate font-medium">
            {failed
              ? `Ingestion of ${repoName(notice)} failed${notice.error ? ` — ${notice.error}` : ""}`
              : warned
                ? `Analysis of ${repoName(notice)} finished with warnings`
                : "Analysis ready — dashboards updated"}
          </span>
          <Link
            href="/"
            className="ml-auto shrink-0 underline underline-offset-2 transition hover:opacity-75"
          >
            Details
          </Link>
        </div>
      </div>
    );
  }

  return null;
}
