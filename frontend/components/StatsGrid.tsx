import { Stats } from "@/lib/api";

const CARDS: { key: keyof Stats; label: string }[] = [
  { key: "total_files", label: "Files" },
  { key: "total_functions", label: "Functions" },
  { key: "total_classes", label: "Classes" },
  { key: "total_calls", label: "Call edges" },
];

export default function StatsGrid({ stats }: { stats: Stats }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {CARDS.map((c) => (
        <div key={c.key} className="border rounded-lg p-4 bg-white">
          <p className="text-3xl font-bold">{stats[c.key]}</p>
          <p className="text-sm text-gray-500">{c.label}</p>
        </div>
      ))}
    </div>
  );
}
