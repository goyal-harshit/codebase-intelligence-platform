"use client";

import { useEffect, useState } from "react";
import { Cpu, Download, Save } from "lucide-react";
import {
  getLlmConfig,
  getLlmModels,
  pullModel,
  updateLlmConfig,
  LlmConfig,
  LlmModels,
} from "@/lib/api";

const PROVIDERS = [
  { value: "ollama", label: "Ollama (local)" },
  { value: "openai_compatible", label: "OpenAI-compatible (LM Studio / llama.cpp / vLLM)" },
];

/**
 * Runtime LLM configuration editor (plan Phase C). Free/local providers only —
 * Ollama or any OpenAI-compatible local server. Saving persists to the backend
 * (`PUT /llm-config`, key encrypted at rest) and takes effect on the next query.
 * For Ollama, a model can be pulled in the background with progress via
 * notifications.
 */
export default function LlmConfigEditor() {
  const [cfg, setCfg] = useState<LlmConfig | null>(null);
  const [models, setModels] = useState<LlmModels | null>(null);
  const [provider, setProvider] = useState("ollama");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [pullName, setPullName] = useState("");

  const load = () => {
    getLlmConfig().then((c) => {
      setCfg(c);
      setProvider(c.provider);
      setBaseUrl(c.base_url ?? "");
      setModel(c.model ?? "");
    });
    getLlmModels().then(setModels).catch(() => setModels(null));
  };

  useEffect(load, []);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      const c = await updateLlmConfig({
        provider,
        base_url: baseUrl || null,
        model: model || null,
        // Only send the key when the user typed one — blank keeps the stored key.
        ...(apiKey ? { api_key: apiKey } : {}),
      });
      setCfg(c);
      setApiKey("");
      setMsg({ kind: "ok", text: "Saved. Applies to the next query." });
      getLlmModels().then(setModels).catch(() => setModels(null));
    } catch (e: any) {
      setMsg({ kind: "err", text: e?.response?.data?.detail ?? e?.message ?? "save failed" });
    } finally {
      setSaving(false);
    }
  };

  const pull = async () => {
    if (!pullName.trim()) return;
    setMsg(null);
    try {
      await pullModel(pullName.trim());
      setMsg({ kind: "ok", text: `Pulling ${pullName.trim()} — progress will appear in notifications.` });
      setPullName("");
    } catch (e: any) {
      setMsg({ kind: "err", text: e?.response?.data?.detail ?? e?.message ?? "pull failed" });
    }
  };

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        <Cpu size={18} className="text-slate-700" />
        <h2 className="text-lg font-semibold text-slate-950">LLM configuration</h2>
        {cfg && <span className="ml-auto text-xs text-slate-400">source: {cfg.source}</span>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1 block text-slate-500">Provider</span>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950"
          >
            {PROVIDERS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          <span className="mb-1 block text-slate-500">Base URL</span>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder={provider === "ollama" ? "http://localhost:11434" : "http://localhost:1234/v1"}
            className="w-full rounded-md border border-slate-300 px-3 py-2 font-mono text-xs text-slate-950"
          />
        </label>

        <label className="text-sm">
          <span className="mb-1 block text-slate-500">Model</span>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            list="llm-model-options"
            placeholder="model name / tag"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950"
          />
          <datalist id="llm-model-options">
            {(models?.models ?? []).map((m) => (
              <option key={m} value={m} />
            ))}
          </datalist>
        </label>

        {provider === "openai_compatible" && (
          <label className="text-sm">
            <span className="mb-1 block text-slate-500">
              API key <span className="text-slate-400">(optional; blank keeps existing)</span>
            </span>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={cfg?.api_key_set ? "•••••• (stored)" : "not set"}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-slate-950"
            />
          </label>
        )}
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={save}
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          <Save size={15} />
          {saving ? "Saving" : "Save configuration"}
        </button>
        {msg && (
          <span className={`text-sm ${msg.kind === "ok" ? "text-emerald-700" : "text-rose-700"}`}>
            {msg.text}
          </span>
        )}
      </div>

      {provider === "ollama" && (
        <div className="mt-5 border-t border-slate-100 pt-4">
          <p className="mb-2 text-sm font-medium text-slate-700">Pull a local model</p>
          <div className="flex gap-2">
            <input
              value={pullName}
              onChange={(e) => setPullName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && pull()}
              placeholder="e.g. llama3.2:latest, qwen2.5-coder:7b"
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-950"
            />
            <button
              onClick={pull}
              disabled={!pullName.trim()}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              <Download size={15} />
              Pull
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Downloads run in the background; progress appears in your notifications.
          </p>
        </div>
      )}
    </section>
  );
}
