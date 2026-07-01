"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn, UserPlus, ShieldCheck, Loader2 } from "lucide-react";
import axios from "axios";
import { useAuth } from "@/components/AuthProvider";

type Mode = "login" | "register";

function errorMessage(err: unknown, mode: Mode): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") {
      if (detail === "LOGIN_BAD_CREDENTIALS") return "Incorrect email or password.";
      if (detail === "REGISTER_USER_ALREADY_EXISTS")
        return "An account with that email already exists.";
      return detail;
    }
    if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
    if (err.response?.status === 400)
      return mode === "register"
        ? "Registration failed. The password may be too weak or the email invalid."
        : "Incorrect email or password.";
    return err.message;
  }
  return "Something went wrong. Please try again.";
}

export default function LoginPage() {
  const router = useRouter();
  const { login, register } = useAuth();

  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password, fullName.trim() || undefined);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(errorMessage(err, mode));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-md flex-col">
      <div className="mb-6 flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-lg bg-slate-950 text-white">
          <ShieldCheck size={20} />
        </span>
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Authentication
          </p>
          <h1 className="text-xl font-semibold text-slate-950">
            {mode === "login" ? "Sign in" : "Create an account"}
          </h1>
        </div>
      </div>

      <div className="mb-4 flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-sm">
        <button
          type="button"
          onClick={() => {
            setMode("login");
            setError(null);
          }}
          className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 transition ${
            mode === "login"
              ? "bg-white font-medium text-slate-950 shadow-sm"
              : "text-slate-500 hover:text-slate-950"
          }`}
        >
          <LogIn size={15} /> Sign in
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("register");
            setError(null);
          }}
          className={`flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 transition ${
            mode === "register"
              ? "bg-white font-medium text-slate-950 shadow-sm"
              : "text-slate-500 hover:text-slate-950"
          }`}
        >
          <UserPlus size={15} /> Register
        </button>
      </div>

      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-slate-200 bg-white p-5"
      >
        {mode === "register" && (
          <label className="mb-4 block">
            <span className="mb-1 block text-sm font-medium text-slate-700">
              Full name <span className="text-slate-400">(optional)</span>
            </span>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              autoComplete="name"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-950 focus:outline-none"
              placeholder="Ada Lovelace"
            />
          </label>
        )}

        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium text-slate-700">Email</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-950 focus:outline-none"
            placeholder="you@example.com"
          />
        </label>

        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium text-slate-700">
            Password
          </span>
          <input
            type="password"
            required
            minLength={mode === "register" ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-slate-950 focus:outline-none"
            placeholder={mode === "register" ? "At least 8 characters" : "••••••••"}
          />
        </label>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-60"
        >
          {busy && <Loader2 size={16} className="animate-spin" />}
          {mode === "login" ? "Sign in" : "Create account"}
        </button>
      </form>

      <p className="mt-4 text-center text-xs text-slate-500">
        {mode === "login" ? "New here? " : "Already have an account? "}
        <button
          type="button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError(null);
          }}
          className="font-medium text-slate-950 underline-offset-2 hover:underline"
        >
          {mode === "login" ? "Create an account" : "Sign in instead"}
        </button>
      </p>
    </div>
  );
}
