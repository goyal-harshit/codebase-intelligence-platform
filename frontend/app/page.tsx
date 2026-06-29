"use client";

import PageHeader from "@/components/PageHeader";
import IngestWorkspace from "@/components/IngestWorkspace";

export default function Home() {
  return (
    <div>
      <PageHeader
        eyebrow="Repository intake"
        title="Start a codebase analysis"
        description="Ingest a Git repository, local working tree, or ZIP archive and turn it into a searchable graph with risk findings and impact analysis."
      />
      <IngestWorkspace />
    </div>
  );
}
