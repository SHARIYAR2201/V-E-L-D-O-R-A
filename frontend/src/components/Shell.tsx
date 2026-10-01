"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, useAuth } from "@/lib/api";
import Cursor from "./Cursor";

const NAV = [
  ["/dashboard", "Dashboard"], ["/coach", "AI Coach"], ["/nutrition", "Nutrition"], ["/workouts", "Workouts"],
  ["/progress", "Progress"], ["/recovery", "Recovery"], ["/community", "Community"], ["/profile", "Profile"],
] as const;

export const DISCLAIMER = "V-E-L-D-O-R-A provides informational health, nutrition, and fitness guidance only. This platform is not a medical device. It does not diagnose, treat, cure, or prevent disease. Predictions, calorie estimations, and recommendations are estimates and should not replace professional medical advice.";

export function Disclaimer() {
  return <p className="mt-10 max-w-3xl text-xs leading-relaxed text-white/50">{DISCLAIMER}</p>;
}

export default function Shell({ children, protectedPage = true }: { children: React.ReactNode; protectedPage?: boolean }) {
  const path = usePathname(), router = useRouter();
  const token = useAuth((s) => s.token), setToken = useAuth((s) => s.set);
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<string>();
  useEffect(() => { if (protectedPage && !token) router.replace("/login"); }, [protectedPage, token, router]);
  useEffect(() => { if (token) api("/me").then((m) => setRole(m.role)).catch(() => {}); }, [token]);
  const links = [...NAV, ...(role === "admin" ? ([["/admin", "Admin"]] as const) : [])];
  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <Cursor />
      <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(60%_50%_at_15%_0%,rgba(139,0,0,.45),transparent),radial-gradient(50%_40%_at_90%_10%,rgba(37,99,235,.18),transparent)]" />
      <header className="sticky top-0 z-40 border-b border-white/10 bg-ink/70 backdrop-blur-xl">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3" aria-label="Main">
          <Link href={token ? "/dashboard" : "/"} className="text-lg font-black tracking-[.3em]" data-magnetic>V·E·L·D·O·R·A</Link>
          <ul className="hidden gap-1 lg:flex">
            {links.map(([h, l]) => (
              <li key={h}><Link href={h} data-magnetic className={`rounded-full px-3 py-1.5 text-sm transition ${path === h ? "bg-white/10 text-white" : "text-white/60 hover:text-white"}`}>{l}</Link></li>
            ))}
          </ul>
          <div className="flex items-center gap-2">
            {token ? <button className="btn btn-ghost !py-1.5 text-sm" onClick={async () => { try { await api("/auth/logout", { method: "POST" }); } catch {} setToken(null); router.push("/"); }}>Log out</button>
              : <Link href="/login" className="btn btn-primary !py-1.5 text-sm">Log in</Link>}
            <button className="lg:hidden rounded-lg border border-white/15 px-2.5 py-1.5" aria-label="Menu" aria-expanded={open} onClick={() => setOpen(!open)}>☰</button>
          </div>
        </nav>
        <AnimatePresence>{open && (
          <motion.ul initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden px-4 pb-3 lg:hidden">
            {links.map(([h, l]) => <li key={h}><Link href={h} onClick={() => setOpen(false)} className="block py-2 text-white/80">{l}</Link></li>)}
          </motion.ul>)}
        </AnimatePresence>
      </header>
      <AnimatePresence mode="wait">
        <motion.main key={path} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="mx-auto max-w-7xl px-4 py-8">
          {children}
          <Disclaimer />
        </motion.main>
      </AnimatePresence>
    </div>
  );
}

export function Card({ title, children, className = "", glow }: { title?: string; children: React.ReactNode; className?: string; glow?: boolean }) {
  return (
    <section className={`glass ${glow ? "edge" : ""} p-5 transition hover:-translate-y-0.5 hover:shadow-[0_14px_50px_rgba(220,20,60,.18)] ${className}`}>
      {title && <h2 className="mb-3 text-sm font-semibold text-white/70">{title}</h2>}
      {children}
    </section>
  );
}

export function Stat({ label, value, unit, bar }: { label: string; value: number | string; unit?: string; bar?: number }) {
  return (
    <div>
      <div className="text-xs text-white/55">{label}</div>
      <div className="text-3xl font-bold tabular-nums">{value}<span className="ml-1 text-sm font-normal text-white/50">{unit}</span></div>
      {bar !== undefined && <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="pulse-bar h-full rounded-full bg-[linear-gradient(90deg,#8B0000,#DC143C,#9333EA,#8B0000)]" style={{ width: `${Math.min(Math.max(bar, 0), 100)}%` }} /></div>}
    </div>
  );
}

export function Err({ e }: { e?: string | null }) { return e ? <p role="alert" className="text-sm text-red-300">{e}</p> : null; }
export function Loading({ what = "Loading" }: { what?: string }) {
  return <div role="status" className="flex items-center gap-3 text-white/60"><span className="h-2 w-24 overflow-hidden rounded-full bg-white/10"><span className="pulse-bar block h-full w-full bg-[linear-gradient(90deg,#2563EB,#06B6D4,#4F46E5,#2563EB)]" /></span>{what}…</div>;
}
