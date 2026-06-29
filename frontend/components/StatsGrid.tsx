import { Stats } from "@/lib/api";

const CARDS: { key: keyof Stats; label: string }[] = [
  { key: "total_files", label: "Files" },
  { key: "total_functions", label: "Functions" },
  { key: "total_classes", label: "Classes" },
  { key: "total_calls", label: "Call edges" },
];

export default function StatsGrid({ stats }: { stats: Stats }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {CARDS.map((c) => (
        <div key={c.key} className="rounded-lg border border-slate-200 bg-white p-4">
          <p className="text-3xl font-semibold text-slate-950">{stats[c.key]}</p>
          <p className="mt-1 text-sm text-slate-500">{c.label}</p>
        </div>
      ))}
    </div>
  );
}
