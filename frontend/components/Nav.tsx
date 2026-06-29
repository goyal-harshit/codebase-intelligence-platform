"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  GitBranch,
  Network,
  Settings,
  FileText,
  Search,
  UploadCloud,
} from "lucide-react";

const LINKS = [
  { href: "/", label: "Ingest", icon: UploadCloud },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { href: "/query", label: "Ask", icon: Search },
  { href: "/risks", label: "Risks", icon: AlertTriangle },
  { href: "/impact", label: "Impact", icon: Network },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Nav() {
  const pathname = usePathname();

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

        <div className="hidden items-center gap-2 text-xs text-slate-500 xl:flex">
          <GitBranch size={15} />
          Self-hosted analysis workspace
        </div>
      </nav>
    </header>
  );
}
