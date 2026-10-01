"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Shell, { Card, Err } from "@/components/Shell";
import { api, useAuth } from "@/lib/api";

export default function AuthForm({ mode }: { mode: "login" | "register" }) {
  const [email, setEmail] = useState(""), [pw, setPw] = useState(""), [err, setErr] = useState<string | null>(null), [busy, setBusy] = useState(false);
  const router = useRouter(), setToken = useAuth((s) => s.set);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try {
      const r = await api(`/auth/${mode}`, { body: { email, password: pw } });
      setToken(r.access_token); router.push(mode === "register" ? "/profile" : "/dashboard");
    } catch (x: any) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <Shell protectedPage={false}>
      <div className="mx-auto max-w-md">
        <Card title={mode === "login" ? "Log in" : "Create your account"} glow>
          <form onSubmit={submit} className="space-y-3">
            <label className="block text-sm">Email<input className="input mt-1" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
            <label className="block text-sm">Password<input className="input mt-1" type="password" required minLength={8} autoComplete={mode === "login" ? "current-password" : "new-password"} value={pw} onChange={(e) => setPw(e.target.value)} /></label>
            <Err e={err} />
            <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}</button>
          </form>
          <p className="mt-4 text-sm text-white/60">{mode === "login" ? <>No account? <Link className="underline" href="/register">Register</Link></> : <>Have an account? <Link className="underline" href="/login">Log in</Link></>}</p>
        </Card>
      </div>
    </Shell>
  );
}
