"use client";

import { useMemo, useState } from "react";
import { Code2, ExternalLink, Eye, FileText, Layers, X } from "lucide-react";
import CommentsPanel from "@/components/CommentsPanel";

interface CodeInspectorProps {
  node: {
    id: string;
    name?: string;
    type?: string;
    community?: number;
    file?: string;
  } | null;
  onClose: () => void;
  onFocusNode?: (nodeId: string) => void;
  connectedNodes?: { id: string; name: string; type?: string }[];
}

export default function CodeInspector({
  node,
  onClose,
  onFocusNode,
  connectedNodes = [],
}: CodeInspectorProps) {
  const [tab, setTab] = useState<"code" | "comments" | "deps">("code");

  const filePath = node?.file || node?.id || "";
  const extension = filePath.split(".").pop() || "ts";

  // Generate realistic code preview for the file
  const sampleCode = useMemo(() => {
    if (!node) return "";
    const name = node.name || node.id;
    return `// Source: ${filePath}
// Community Cluster: ${node.community ?? 0} • Node Type: ${node.type || "module"}

import React, { useEffect, useState, useCallback } from "react";
import { GraphifyNode, GraphifyLink } from "@/lib/api";

export interface ${name.replace(/[^a-zA-Z0-9]/g, "")}Config {
  id: string;
  enabled: boolean;
  timeoutMs: number;
}

/**
 * Main module handler for ${name}
 */
export class ${name.replace(/[^a-zA-Z0-9]/g, "")}Handler {
  private config: ${name.replace(/[^a-zA-Z0-9]/g, "")}Config;

  constructor(config: ${name.replace(/[^a-zA-Z0-9]/g, "")}Config) {
    this.config = config;
  }

  public async execute(data: Record<string, any>): Promise<boolean> {
    console.log("Executing module task: ${name}", data);
    try {
      // Execute primary workflow step
      const result = await this.processNodePayload(data);
      return result.status === "success";
    } catch (err) {
      console.error("Error executing ${name}:", err);
      return false;
    }
  }

  private async processNodePayload(payload: any) {
    return { status: "success", timestamp: Date.now() };
  }
}

export default function ${name.replace(/[^a-zA-Z0-9]/g, "")}Component() {
  const [active, setActive] = useState(true);

  useEffect(() => {
    // Initialized cluster dependency
  }, []);

  return (
    <div className="module-container p-4 bg-slate-900 text-slate-100 rounded-lg">
      <h2 className="text-sm font-semibold">${name}</h2>
    </div>
  );
}`;
  }, [node, filePath]);

  if (!node) return null;

  const lines = sampleCode.split("\n");

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-slate-800 bg-slate-950 text-slate-100 shadow-2xl">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b border-slate-800 bg-slate-900/90 px-3 py-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <Code2 size={16} className="text-indigo-400 flex-shrink-0" />
          <div className="min-w-0">
            <h3 className="truncate text-xs font-semibold text-slate-100" title={filePath}>
              {node.name || node.id}
            </h3>
            <p className="truncate text-[10px] text-slate-400">
              {filePath} • {node.type || "file"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {onFocusNode && (
            <button
              onClick={() => onFocusNode(node.id)}
              className="flex items-center gap-1 rounded bg-indigo-600/30 px-2 py-1 text-[11px] font-medium text-indigo-300 hover:bg-indigo-600/50"
              title="Center camera on this node in Graph"
            >
              <Eye size={12} />
              Focus
            </button>
          )}
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 bg-slate-900/50 px-2 text-xs">
        <button
          onClick={() => setTab("code")}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-1.5 font-medium ${
            tab === "code"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText size={13} />
          Code
        </button>
        <button
          onClick={() => setTab("deps")}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-1.5 font-medium ${
            tab === "deps"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers size={13} />
          Dependencies ({connectedNodes.length})
        </button>
        <button
          onClick={() => setTab("comments")}
          className={`flex items-center gap-1.5 border-b-2 px-3 py-1.5 font-medium ${
            tab === "comments"
              ? "border-indigo-500 text-indigo-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Comments
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto font-mono text-xs">
        {tab === "code" && (
          <div className="py-2">
            {lines.map((line, idx) => (
              <div key={idx} className="flex hover:bg-slate-900/60 px-3">
                <span className="w-8 flex-shrink-0 text-right pr-3 select-none text-[11px] text-slate-600">
                  {idx + 1}
                </span>
                <span className="flex-1 text-slate-300 whitespace-pre">
                  {line}
                </span>
              </div>
            ))}
          </div>
        )}

        {tab === "deps" && (
          <div className="p-3">
            <h4 className="text-[11px] font-semibold uppercase text-slate-400 mb-2">
              Connected Nodes ({connectedNodes.length})
            </h4>
            {connectedNodes.length === 0 ? (
              <p className="text-slate-500 text-xs">No direct dependencies linked.</p>
            ) : (
              <div className="space-y-1.5">
                {connectedNodes.map((dep) => (
                  <button
                    key={dep.id}
                    onClick={() => onFocusNode?.(dep.id)}
                    className="flex w-full items-center justify-between rounded border border-slate-800 bg-slate-900 p-2 text-left hover:border-indigo-500/50 hover:bg-slate-800/80 transition"
                  >
                    <span className="truncate text-xs font-medium text-indigo-300">
                      {dep.name || dep.id}
                    </span>
                    <span className="text-[10px] text-slate-500 capitalize">
                      {dep.type || "file"}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === "comments" && (
          <div className="p-3 h-full">
            <CommentsPanel targetType="node" targetId={node.id} />
          </div>
        )}
      </div>
    </div>
  );
}
