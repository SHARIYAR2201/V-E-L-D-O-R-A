"use client";
import { create } from "zustand";

type Auth = { token: string | null; set: (t: string | null) => void };
export const useAuth = create<Auth>((set) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("veldora_token") : null,
  set: (t) => {
    if (typeof window !== "undefined") t ? localStorage.setItem("veldora_token", t) : localStorage.removeItem("veldora_token");
    set({ token: t });
  },
}));

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const token = useAuth.getState().token;
  const res = await fetch(`/api${path}`, {
    method: opts.method ?? (opts.body ? "POST" : "GET"),
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (res.status === 401 && token) useAuth.getState().set(null);
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}
