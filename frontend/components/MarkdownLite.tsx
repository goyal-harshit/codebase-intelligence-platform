/* Tiny renderer for the docgen wiki's markdown subset (headings, bullet
   lists, horizontal rules, `code` / **bold** / _em_ inline). React elements
   only — no innerHTML, so page content can never inject markup. */

import { Fragment, ReactNode } from "react";

function inline(text: string, keyPrefix: string): ReactNode[] {
  // Order matters: code spans win over bold/em inside them.
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|_[^_]+_)/g);
  return parts.map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith("`") && part.endsWith("`") && part.length > 1)
      return (
        <code key={key} className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[0.85em] text-slate-800">
          {part.slice(1, -1)}
        </code>
      );
    if (part.startsWith("**") && part.endsWith("**") && part.length > 3)
      return (
        <strong key={key} className="font-semibold text-slate-950">
          {part.slice(2, -2)}
        </strong>
      );
    if (part.startsWith("_") && part.endsWith("_") && part.length > 1)
      return (
        <em key={key} className="text-slate-500">
          {part.slice(1, -1)}
        </em>
      );
    return <Fragment key={key}>{part}</Fragment>;
  });
}

export default function MarkdownLite({ markdown }: { markdown: string }) {
  const blocks: ReactNode[] = [];
  let list: string[] = [];

  const flushList = (key: string) => {
    if (list.length === 0) return;
    const items = list;
    list = [];
    blocks.push(
      <ul key={key} className="mb-3 list-disc space-y-1 pl-5 text-sm text-slate-700">
        {items.map((item, i) => (
          <li key={i}>{inline(item, `${key}-${i}`)}</li>
        ))}
      </ul>
    );
  };

  markdown.split("\n").forEach((line, n) => {
    const key = `b${n}`;
    if (line.startsWith("- ")) {
      list.push(line.slice(2));
      return;
    }
    flushList(`${key}-ul`);
    if (line.startsWith("# "))
      blocks.push(
        <h1 key={key} className="mb-3 text-xl font-semibold text-slate-950">
          {inline(line.slice(2), key)}
        </h1>
      );
    else if (line.startsWith("## "))
      blocks.push(
        <h2 key={key} className="mb-2 mt-4 text-sm font-semibold uppercase tracking-wide text-slate-500">
          {inline(line.slice(3), key)}
        </h2>
      );
    else if (line.trim() === "---") blocks.push(<hr key={key} className="my-4 border-slate-200" />);
    else if (line.trim() !== "")
      blocks.push(
        <p key={key} className="mb-2 text-sm text-slate-700">
          {inline(line, key)}
        </p>
      );
  });
  flushList("tail-ul");

  return <div>{blocks}</div>;
}
