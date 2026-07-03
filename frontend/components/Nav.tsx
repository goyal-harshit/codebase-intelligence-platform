"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  BookOpen,
  LogIn,
  LogOut,
  Menu,
  Network,
  Settings,
  Share2,
  FileText,
  Search,
  ShieldCheck,
  Wrench,
  UploadCloud,
  UserCircle2,
  X,
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
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        {/* ── Top bar: brand + auth + mobile toggle ── */}
        <div className="flex h-14 items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5 font-semibold text-slate-950">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-sm">
              <Activity size={16} />
            </span>
            <span className="text-[15px] tracking-tight">
              Codebase <span className="text-slate-500 font-normal">Intelligence</span>
            </span>
          </Link>

          {/* Auth (desktop) */}
          <div className="hidden items-center gap-3 text-sm md:flex">
            {loading ? (
              <span className="h-8 w-20 animate-pulse rounded-lg bg-slate-100" />
            ) : user ? (
              <>
                <span
                  className="flex items-center gap-2 text-slate-500"
                  title={user.email}
                >
                  <UserCircle2 size={17} className="text-slate-400" />
                  <span className="max-w-[12rem] truncate">
                    {user.full_name || user.email}
                  </span>
                </span>
                <button
                  onClick={logout}
                  className="flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950"
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition ${
                  pathname === "/login"
                    ? "bg-slate-950 text-white"
                    : "border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-950"
                }`}
              >
                <LogIn size={14} />
                Sign in
              </Link>
            )}
          </div>

          {/* Mobile toggle */}
          <button
            onClick={() => setMobileOpen((v) => !v)}
            className="grid h-9 w-9 place-items-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-950 md:hidden"
            aria-label="Toggle navigation"
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* ── Nav links (desktop): single scrollable row, no wrap ── */}
        <div className="hidden gap-0.5 overflow-x-auto pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden md:flex">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-md px-2 py-1.5 text-[13px] font-medium transition ${
                  active
                    ? "bg-slate-900 text-white shadow-sm"
                    : "text-slate-500 hover:bg-slate-100 hover:text-slate-950"
                }`}
              >
                <Icon size={14} />
                {label}
              </Link>
            );
          })}
        </div>
      </div>

      {/* ── Mobile menu ── */}
      {mobileOpen && (
        <div className="border-t border-slate-100 bg-white px-4 pb-4 pt-2 md:hidden">
          <div className="grid grid-cols-2 gap-1 sm:grid-cols-3">
            {LINKS.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-2 rounded-md px-3 py-2.5 text-sm transition ${
                    active
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-950"
                  }`}
                >
                  <Icon size={15} />
                  {label}
                </Link>
              );
            })}
          </div>

          {/* Auth (mobile) */}
          <div className="mt-3 border-t border-slate-100 pt-3 text-sm">
            {loading ? (
              <span className="h-8 w-full animate-pulse rounded-lg bg-slate-100 block" />
            ) : user ? (
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-slate-500">
                  <UserCircle2 size={17} className="text-slate-400" />
                  <span className="max-w-[14rem] truncate">
                    {user.full_name || user.email}
                  </span>
                </span>
                <button
                  onClick={logout}
                  className="flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1.5 text-slate-600 transition hover:bg-slate-50"
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              </div>
            ) : (
              <Link
                href="/login"
                onClick={() => setMobileOpen(false)}
                className="flex w-full items-center justify-center gap-1.5 rounded-md border border-slate-200 px-3 py-2 text-slate-600 transition hover:bg-slate-50"
              >
                <LogIn size={14} />
                Sign in
              </Link>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
