import Link from "next/link";
import { Activity } from "lucide-react";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/query", label: "Ask" },
  { href: "/risks", label: "Risks" },
  { href: "/impact", label: "Impact" },
];

export default function Nav() {
  return (
    <header className="border-b bg-white">
      <nav className="max-w-5xl mx-auto flex items-center gap-6 px-4 h-14">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Activity size={18} /> Codebase Intelligence
        </Link>
        <div className="flex gap-4 text-sm text-gray-600">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="hover:text-black">
              {l.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}
