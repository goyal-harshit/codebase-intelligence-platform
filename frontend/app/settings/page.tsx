"use client";

import Link from "next/link";
import { KeyRound, Shield, Users, LogIn, LogOut, UserCircle2, BadgeCheck } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import StateBlock from "@/components/StateBlock";
import SystemStatusPanel from "@/components/SystemStatusPanel";
import LlmConfigEditor from "@/components/LlmConfigEditor";
import { useAuth } from "@/components/AuthProvider";

const SETTINGS = [
  {
    title: "User sessions",
    detail: "JWT auth is wired to /auth/jwt; sign in from the top-right of any page.",
    icon: Shield,
  },
  {
    title: "API keys",
    detail: "Per-user API-key CRUD exists in the backend and can be wired to a protected key-management form next.",
    icon: KeyRound,
  },
  {
    title: "Repo access",
    detail: "Repo membership and RBAC routes are available for owner/member/viewer workflows.",
    icon: Users,
  },
];

export default function SettingsPage() {
  const { user, loading, logout } = useAuth();

  return (
    <div>
      <PageHeader
        eyebrow="Administration"
        title="Settings"
        description="Authentication, API-key, and repo access controls exposed by the backend."
      />

      <div className="mb-5">
        {loading ? (
          <div className="h-24 animate-pulse rounded-lg border border-slate-200 bg-slate-50" />
        ) : user ? (
          <section className="rounded-lg border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="grid h-11 w-11 place-items-center rounded-lg bg-slate-100 text-slate-700">
                  <UserCircle2 size={22} />
                </span>
                <div>
                  <p className="flex items-center gap-2 font-semibold text-slate-950">
                    {user.full_name || user.email}
                    {user.is_superuser && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-slate-950 px-2 py-0.5 text-xs font-medium text-white">
                        <BadgeCheck size={12} /> Admin
                      </span>
                    )}
                  </p>
                  <p className="text-sm text-slate-500">{user.email}</p>
                </div>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-100 hover:text-slate-950"
              >
                <LogOut size={15} /> Sign out
              </button>
            </div>
          </section>
        ) : (
          <StateBlock
            state="empty"
            title="You are browsing as a guest"
            detail="Sign in to unlock collaboration features like comments and the team activity feed. Anonymous access still works for read-only analysis routes."
            action={
              <Link
                href="/login"
                className="inline-flex items-center gap-1.5 rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
              >
                <LogIn size={15} /> Sign in
              </Link>
            }
          />
        )}
      </div>

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <SystemStatusPanel />
        <LlmConfigEditor />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {SETTINGS.map(({ title, detail, icon: Icon }) => (
          <section key={title} className="rounded-lg border border-slate-200 bg-white p-5">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
              <Icon size={20} />
            </div>
            <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
            <p className="mt-2 text-sm text-slate-500">{detail}</p>
          </section>
        ))}
      </div>
    </div>
  );
}
