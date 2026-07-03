"use client";

import { Download, FileText, Sparkles, Table } from "lucide-react";
import {
  exportRisksUrl,
  exportSecurityUrl,
  exportGraphReportUrl,
  exportGraphJsonUrl,
  exportRefactorUrl,
  narrativeReportUrl,
  riskReportUrl,
} from "@/lib/api";
import PageHeader from "@/components/PageHeader";

const REPORTS = [
  {
    title: "Risk report",
    detail: "HTML/PDF report of architecture and maintainability findings.",
    icon: FileText,
    actions: [
      { label: "Open HTML", href: riskReportUrl("html") },
      { label: "Download PDF", href: riskReportUrl("pdf") },
    ],
  },
  {
    title: "Narrative report",
    detail: "LLM-authored executive summary layered over the risk table.",
    icon: Sparkles,
    actions: [
      { label: "Open HTML", href: narrativeReportUrl("html") },
      { label: "Download PDF", href: narrativeReportUrl("pdf") },
    ],
  },
  {
    title: "Risk data export",
    detail: "Structured CSV/XLSX export for audits, spreadsheets, and reviews.",
    icon: Table,
    actions: [
      { label: "CSV", href: exportRisksUrl("csv") },
      { label: "XLSX", href: exportRisksUrl("xlsx") },
    ],
  },
  {
    title: "Security data export",
    detail: "Structured CSV/XLSX export of all detected security vulnerabilities.",
    icon: Table,
    actions: [
      { label: "CSV", href: exportSecurityUrl("csv") },
      { label: "XLSX", href: exportSecurityUrl("xlsx") },
    ],
  },
  {
    title: "Refactoring recommendations",
    detail: "Structured CSV/XLSX export of all refactoring recommendations.",
    icon: Table,
    actions: [
      { label: "CSV", href: exportRefactorUrl("csv") },
      { label: "XLSX", href: exportRefactorUrl("xlsx") },
    ],
  },
  {
    title: "Graph exports",
    detail: "Download the architecture knowledge graph context and raw JSON data.",
    icon: FileText,
    actions: [
      { label: "Download MD", href: exportGraphReportUrl() },
      { label: "Download JSON", href: exportGraphJsonUrl() },
    ],
  },
];

export default function ReportsPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Artifacts"
        title="Reports and exports"
        description="Generate shareable reports and structured exports from the current analysis graph."
      />

      <div className="grid gap-4 lg:grid-cols-3">
        {REPORTS.map(({ title, detail, icon: Icon, actions }) => (
          <section key={title} className="rounded-lg border border-slate-200 bg-white p-5">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
              <Icon size={20} />
            </div>
            <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
            <p className="mt-2 min-h-12 text-sm text-slate-500">{detail}</p>
            <div className="mt-5 flex flex-wrap gap-2">
              {actions.map((action, index) => (
                <a
                  key={action.label}
                  href={action.href}
                  target={action.label.includes("Open") ? "_blank" : undefined}
                  className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm ${
                    index === 0
                      ? "bg-slate-950 text-white"
                      : "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <Download size={15} />
                  {action.label}
                </a>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
