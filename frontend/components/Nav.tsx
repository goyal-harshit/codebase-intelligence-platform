"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  BookOpen,
  LogIn,
  LogOut,
  Network,
  Settings,
  Share2,
  FileText,
  Search,
  ShieldCheck,
  Wrench,
  UploadCloud,
  UserCircle2,
} from "lucide-react";
import { useAuth } from "@/components/AuthProvider";

const LINKS = [
  { href: "/", label: "Ingest", icon: UploadCloud },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/graph", label: "Graph", icon: Share2 },
  { href: "/query", label: "Ask", icon: Search },
  { href: "/risks", label: "Risks", icon: AlertTriangle },
  { href: "/security", label: "Security", icon: ShieldCheck },
  { href: "/refactor", label: "Refactor", icon: Wrench },
  { href: "/impact", label: "Impact", icon: Network },
  { href: "/wiki", label: "Wiki", icon: BookOpen },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Nav() {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <nav className="mx-auto flex min-h-16 max-w-7xl flex-col gap-3 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:py-0">
        <Link href="/" className="flex items-center gap-3 font-semibold text-slate-950">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-slate-950 text-white">
            <Activity size={18} />
          </span>
          <span>
            <span className="block text-sm uppercase tracking-wide text-slate-500">
              Codebase
            </span>
            <span className="block leading-4">Intelligence</span>
          </span>
        </Link>

        <div className="flex gap-1 overflow-x-auto pb-1 text-sm lg:pb-0">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 transition ${
                  active
                    ? "bg-slate-950 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </div>

        <div className="flex items-center gap-3 text-sm">
          {loading ? (
            <span className="h-8 w-20 animate-pulse rounded-lg bg-slate-100" />
          ) : user ? (
            <>
              <span
                className="flex items-center gap-2 text-slate-600"
                title={user.email}
              >
                <UserCircle2 size={18} className="text-slate-400" />
                <span className="hidden max-w-[12rem] truncate sm:inline">
                  {user.full_name || user.email}
                </span>
              </span>
              <button
                onClick={logout}
                className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-slate-600 transition hover:bg-slate-100 hover:text-slate-950"
              >
                <LogOut size={15} />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 transition ${
                pathname === "/login"
                  ? "bg-slate-950 text-white"
                  : "border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-950"
              }`}
            >
              <LogIn size={15} />
              Sign in
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
