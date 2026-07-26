"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, FileCode, Folder, FolderOpen, Search } from "lucide-react";

interface TreeNode {
  name: string;
  path: string;
  isFolder: boolean;
  children?: TreeNode[];
}

function buildTree(paths: string[]): TreeNode[] {
  const root: TreeNode[] = [];

  paths.forEach((path) => {
    const parts = path.split("/").filter(Boolean);
    let currentLevel = root;

    parts.forEach((part, index) => {
      const isFile = index === parts.length - 1;
      const currentPath = parts.slice(0, index + 1).join("/");
      let existing = currentLevel.find((item) => item.name === part);

      if (!existing) {
        existing = {
          name: part,
          path: currentPath,
          isFolder: !isFile,
          children: isFile ? undefined : [],
        };
        currentLevel.push(existing);
      }

      if (!isFile && existing.children) {
        currentLevel = existing.children;
      }
    });
  });

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach((n) => {
      if (n.children) sortNodes(n.children);
    });
  };

  sortNodes(root);
  return root;
}

function TreeItem({
  node,
  selectedPath,
  onSelect,
  level = 0,
}: {
  node: TreeNode;
  selectedPath?: string;
  onSelect: (path: string) => void;
  level?: number;
}) {
  const [isOpen, setIsOpen] = useState(level < 1);

  if (node.isFolder) {
    return (
      <div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          style={{ paddingLeft: `${level * 12 + 8}px` }}
          className="flex w-full items-center gap-1.5 py-1 text-left text-xs font-medium text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
        >
          {isOpen ? (
            <ChevronDown size={14} className="text-slate-500 flex-shrink-0" />
          ) : (
            <ChevronRight size={14} className="text-slate-500 flex-shrink-0" />
          )}
          {isOpen ? (
            <FolderOpen size={14} className="text-indigo-400 flex-shrink-0" />
          ) : (
            <Folder size={14} className="text-slate-400 flex-shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </button>
        {isOpen && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeItem
                key={child.path}
                node={child}
                selectedPath={selectedPath}
                onSelect={onSelect}
                level={level + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  const isSelected = selectedPath === node.path || selectedPath?.endsWith(node.name);

  return (
    <button
      onClick={() => onSelect(node.path)}
      style={{ paddingLeft: `${level * 12 + 20}px` }}
      className={`flex w-full items-center gap-1.5 py-1 text-left text-xs transition ${
        isSelected
          ? "bg-indigo-600/30 text-indigo-300 font-semibold border-r-2 border-indigo-500"
          : "text-slate-300 hover:bg-slate-800/50 hover:text-white"
      }`}
    >
      <FileCode size={13} className={isSelected ? "text-indigo-400" : "text-slate-500"} />
      <span className="truncate">{node.name}</span>
    </button>
  );
}

export default function FileTreeExplorer({
  files,
  selectedPath,
  onSelect,
}: {
  files: string[];
  selectedPath?: string;
  onSelect: (path: string) => void;
}) {
  const [filter, setFilter] = useState("");

  const filteredFiles = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return files;
    return files.filter((f) => f.toLowerCase().includes(q));
  }, [files, filter]);

  const tree = useMemo(() => buildTree(filteredFiles), [filteredFiles]);

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border border-slate-800 bg-slate-950 text-slate-200 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2.5">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Explorer
        </span>
        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
          {files.length} items
        </span>
      </div>

      <div className="relative border-b border-slate-800 p-2">
        <Search className="pointer-events-none absolute left-4 top-4 text-slate-500" size={14} />
        <input
          className="w-full rounded-md border border-slate-800 bg-slate-900 py-1.5 pl-8 pr-3 text-xs text-slate-200 outline-none placeholder:text-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          placeholder="Search files..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </div>

      <div className="flex-1 overflow-y-auto py-1 custom-scrollbar">
        {tree.length === 0 ? (
          <p className="p-3 text-center text-xs text-slate-500">No matching files found.</p>
        ) : (
          tree.map((node) => (
            <TreeItem
              key={node.path}
              node={node}
              selectedPath={selectedPath}
              onSelect={onSelect}
            />
          ))
        )}
      </div>
    </div>
  );
}
