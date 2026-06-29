import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

const ICONS = {
  loading: Loader2,
  empty: AlertCircle,
  error: AlertCircle,
  ready: CheckCircle2,
};

const STYLES = {
  loading: "border-sky-200 bg-sky-50 text-sky-900",
  empty: "border-slate-200 bg-white text-slate-700",
  error: "border-rose-200 bg-rose-50 text-rose-900",
  ready: "border-emerald-200 bg-emerald-50 text-emerald-900",
};

export default function StateBlock({
  state,
  title,
  detail,
}: {
  state: keyof typeof ICONS;
  title: string;
  detail?: string;
}) {
  const Icon = ICONS[state];
  return (
    <div className={`rounded-lg border p-4 ${STYLES[state]}`}>
      <div className="flex gap-3">
        <Icon size={20} className={state === "loading" ? "animate-spin" : ""} />
        <div>
          <p className="font-medium">{title}</p>
          {detail && <p className="mt-1 text-sm opacity-80">{detail}</p>}
        </div>
      </div>
    </div>
  );
}
