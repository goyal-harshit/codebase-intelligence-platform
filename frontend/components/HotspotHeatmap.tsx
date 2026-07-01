import { Hotspot } from "@/lib/api";

function heatClass(score: number, maxScore: number) {
  const ratio = maxScore > 0 ? score / maxScore : 0;
  if (ratio >= 0.75) return "bg-red-600 text-white";
  if (ratio >= 0.5) return "bg-orange-500 text-white";
  if (ratio >= 0.25) return "bg-yellow-300 text-gray-950";
  return "bg-emerald-100 text-emerald-950";
}

export default function HotspotHeatmap({
  hotspots,
  mode = "churn_x_complexity",
}: {
  hotspots: Hotspot[];
  mode?: "churn_x_complexity" | "complexity_only";
}) {
  if (hotspots.length === 0) {
    return <p className="text-gray-500 text-sm">No hotspots found.</p>;
  }

  // In complexity-only mode churn is unknown (0), so show max complexity in its
  // place rather than a column of zeros.
  const complexityOnly = mode === "complexity_only";
  const maxScore = Math.max(...hotspots.map((item) => item.score));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      {hotspots.map((item) => (
        <div
          key={item.file}
          className={`${heatClass(
            item.score,
            maxScore
          )} rounded-lg p-3 min-h-28 flex flex-col justify-between`}
          title={
            complexityOnly
              ? `${item.file}: complexity ${item.total_complexity} (git history unavailable)`
              : `${item.file}: churn ${item.churn}, complexity ${item.total_complexity}`
          }
        >
          <p className="font-semibold text-sm leading-5 break-words">{item.file}</p>
          <div className="grid grid-cols-3 gap-2 text-xs mt-3">
            <span>
              <strong className="block text-base">
                {complexityOnly ? item.max_complexity : item.churn}
              </strong>
              {complexityOnly ? "max cx" : "churn"}
            </span>
            <span>
              <strong className="block text-base">{item.total_complexity}</strong>
              complexity
            </span>
            <span>
              <strong className="block text-base">{item.score}</strong>
              score
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
