"use client";

import { KeyRound, Shield, Users } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import StateBlock from "@/components/StateBlock";

const SETTINGS = [
  {
    title: "User sessions",
    detail: "Backend JWT auth is available at /auth/jwt and /users routes.",
    icon: Shield,
  },
  {
    title: "API keys",
    detail: "Per-user API-key CRUD exists in the backend and should be wired to a protected settings form next.",
    icon: KeyRound,
  },
  {
    title: "Repo access",
    detail: "Repo membership and RBAC routes are available for owner/member/viewer workflows.",
    icon: Users,
  },
];

export default function SettingsPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Administration"
        title="Settings"
        description="Authentication, API-key, and repo access controls exposed by the backend."
      />

      <div className="mb-5">
        <StateBlock
          state="empty"
          title="Auth UI is the next focused frontend slice"
          detail="The backend has JWT, per-user API keys, and RBAC; this page documents the available surfaces until login and key-management forms are wired."
        />
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
