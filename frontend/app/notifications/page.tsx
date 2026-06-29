"use client";

import { useEffect, useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import {
  getNotifications,
  markAllNotificationsRead,
  NotificationItem,
} from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import StateBlock from "@/components/StateBlock";

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    getNotifications()
      .then((data) => {
        setItems(data);
        setError(null);
      })
      .catch((e) => setError(e?.response?.data?.detail ?? e?.message ?? "login required"))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const markAll = async () => {
    await markAllNotificationsRead();
    load();
  };

  return (
    <div>
      <PageHeader
        eyebrow="Activity"
        title="Notifications"
        description="Review ingestion completion, warning, and failure events delivered by the backend notification pipeline."
        actions={
          <button
            onClick={markAll}
            disabled={items.length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-3 py-2 text-sm text-white disabled:opacity-40"
          >
            <CheckCheck size={16} />
            Mark all read
          </button>
        }
      />

      {loading ? (
        <StateBlock state="loading" title="Loading notifications" />
      ) : error ? (
        <StateBlock
          state="error"
          title="Notifications require a logged-in user"
          detail={error}
        />
      ) : items.length === 0 ? (
        <StateBlock
          state="empty"
          title="No notifications yet"
          detail="Completed or failed ingestion jobs will appear here for authenticated users."
        />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <section
              key={item.id}
              className={`rounded-lg border p-4 ${
                item.read ? "border-slate-200 bg-white" : "border-sky-200 bg-sky-50"
              }`}
            >
              <div className="flex gap-3">
                <Bell size={18} className="mt-1 shrink-0 text-slate-500" />
                <div className="min-w-0">
                  <p className="font-medium text-slate-950">{item.title}</p>
                  {item.body && <p className="mt-1 text-sm text-slate-600">{item.body}</p>}
                  <p className="mt-2 text-xs text-slate-500">
                    {item.level} · {new Date(item.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
