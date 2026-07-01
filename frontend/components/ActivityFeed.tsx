"use client";

import Link from "next/link";
import useSWR from "swr";
import { getActivity, ActivityEvent } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Activity, FileEdit, Trash2, MessageSquare, AlertCircle, LogIn } from "lucide-react";

export default function ActivityFeed() {
  const { user } = useAuth();
  const { data: activities, error } = useSWR<ActivityEvent[]>(
    // Activity requires a signed-in user; skip the fetch (and the guaranteed
    // 401) when logged out by passing a null SWR key.
    user ? "activity-feed" : null,
    () => getActivity()
  );

  const getIcon = (action: string) => {
    const act = action.toLowerCase();
    if (act.includes("comment")) return <MessageSquare className="w-4 h-4 text-blue-400" />;
    if (act.includes("delete")) return <Trash2 className="w-4 h-4 text-red-400" />;
    if (act.includes("update") || act.includes("edit")) return <FileEdit className="w-4 h-4 text-yellow-400" />;
    return <Activity className="w-4 h-4 text-emerald-400" />;
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b border-slate-700 bg-slate-800 flex items-center gap-2">
        <Activity className="w-5 h-5 text-indigo-400" />
        <h3 className="font-semibold text-slate-100">Activity Feed</h3>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!user && (
          <div className="text-slate-400 text-sm flex flex-col items-start gap-2 bg-slate-800/50 p-3 rounded">
            <span className="flex items-center gap-2">
              <LogIn className="w-4 h-4" />
              Sign in to see team activity.
            </span>
            <Link
              href="/login"
              className="text-indigo-400 hover:text-indigo-300 font-medium"
            >
              Go to sign in →
            </Link>
          </div>
        )}
        {user && error && (
          <div className="text-red-400 text-sm flex items-center gap-2 bg-red-900/20 p-3 rounded">
            <AlertCircle className="w-4 h-4" />
            Failed to load activity.
          </div>
        )}
        {user && !activities && !error && (
          <div className="text-slate-400 text-sm animate-pulse">Loading activity feed...</div>
        )}
        {activities?.length === 0 && (
          <div className="text-slate-400 text-sm italic">No recent activity.</div>
        )}
        {activities?.map((activity) => (
          <div key={activity.id} className="flex gap-3 items-start group">
            <div className="mt-1 bg-slate-800 p-1.5 rounded-full border border-slate-700 group-hover:border-slate-500 transition-colors">
              {getIcon(activity.action)}
            </div>
            <div className="flex-1">
              <p className="text-sm text-slate-200">
                <span className="font-medium text-slate-100">{activity.user_id || "System"}</span>{" "}
                <span className="text-slate-300">{activity.action}</span>
                {activity.target && (
                  <span className="text-slate-400"> on {activity.target}</span>
                )}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                {new Date(activity.created_at).toLocaleString()}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
