"use client";
import { useEffect, useMemo, useState } from "react";
import Shell, { Card, Err } from "@/components/Shell";
import { api } from "@/lib/api";

export default function Workouts() {
  const [acts, setActs] = useState<any[]>([]), [cat, setCat] = useState("all"), [plan, setPlan] = useState<any>(), [err, setErr] = useState<string | null>(null);
  const [f, setF] = useState({ level: "beginner", minutes: 45, days: 3, equipment: [] as string[] }), [log, setLog] = useState({ activity_key: "walk_brisk", minutes: 30 }), [msg, setMsg] = useState("");
  useEffect(() => { api("/activities").then(setActs).catch(() => {}); }, []);
  const cats = useMemo(() => ["all", ...Array.from(new Set(acts.map((a) => a.category)))], [acts]);
  const toggle = (e: string) => setF({ ...f, equipment: f.equipment.includes(e) ? f.equipment.filter((x) => x !== e) : [...f.equipment, e] });
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-bold">Workouts</h1>
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Generate a plan" glow className="lg:col-span-1">
          <div className="space-y-3 text-sm">
            <label className="block">Level<select className="input mt-1" value={f.level} onChange={(e) => setF({ ...f, level: e.target.value })}>{["beginner", "intermediate", "advanced"].map((l) => <option key={l}>{l}</option>)}</select></label>
            <label className="block">Minutes per session<input type="number" min={15} max={120} className="input mt-1" value={f.minutes} onChange={(e) => setF({ ...f, minutes: Number(e.target.value) })} /></label>
            <label className="block">Days per week<input type="number" min={1} max={6} className="input mt-1" value={f.days} onChange={(e) => setF({ ...f, days: Number(e.target.value) })} /></label>
            <fieldset><legend className="mb-1">Equipment</legend>{["dumbbells", "gym"].map((e) => <label key={e} className="mr-4"><input type="checkbox" checked={f.equipment.includes(e)} onChange={() => toggle(e)} /> {e}</label>)}</fieldset>
            <button className="btn btn-ai w-full" onClick={async () => { setErr(null); try { setPlan(await api("/plans/workout", { body: { level: f.level, minutes: f.minutes, days_per_week: f.days, equipment: f.equipment } })); } catch (e: any) { setErr(e.message); } }}>Generate</button>
          </div>
        </Card>
        <div className="space-y-4 lg:col-span-2">
          {plan ? <>
            {plan.safety.notes.map((n: string) => <Card key={n}><p className="text-amber-200">{n}</p></Card>)}
            {plan.sessions.map((s: any) => (
              <Card key={s.day} title={`Day ${s.day} · ${s.focus} · ≈${s.est_kcal} kcal`}>
                <ul className="space-y-1 text-sm">{s.exercises.map((e: any) => <li key={e.exercise} className="flex justify-between"><span>{e.exercise}</span><span className="tabular-nums text-white/70">{e.sets} × {e.reps} · RPE {e.target_rpe}</span></li>)}
                  <li className="flex justify-between border-t border-white/10 pt-1"><span>{s.cardio.activity}</span><span className="text-white/70">{s.cardio.minutes} min</span></li></ul>
              </Card>
            ))}
            <Card title="Progressive overload">{plan.progressive_overload.map((p: any) => <p key={p.week} className="text-sm text-white/75">Week {p.week}: {p.rule}</p>)}</Card>
          </> : <Card><p className="text-white/60">Choose your options and generate a plan. Intensity is capped automatically for the health conditions in your profile.</p></Card>}
        </div>
        <Card title="Log a workout" className="lg:col-span-1">
          <div className="space-y-2 text-sm">
            <select className="input" aria-label="Activity" value={log.activity_key} onChange={(e) => setLog({ ...log, activity_key: e.target.value })}>{acts.map((a) => <option key={a.key} value={a.key}>{a.name} (MET {a.met})</option>)}</select>
            <input className="input" type="number" aria-label="Minutes" min={1} value={log.minutes} onChange={(e) => setLog({ ...log, minutes: Number(e.target.value) })} />
            <button className="btn btn-primary w-full" onClick={async () => { try { const r = await api("/workouts", { body: log }); setMsg(`≈${r.kcal_burned} kcal burned (${r.formula})`); } catch (e: any) { setMsg(e.message); } }}>Log</button>
            <p className="text-white/70" role="status">{msg}</p>
          </div>
        </Card>
        <Card title="Activity library (MET)" className="lg:col-span-2">
          <div className="mb-3 flex flex-wrap gap-2">{cats.map((c) => <button key={c} className={`btn btn-ghost !py-1 text-xs ${cat === c ? "!bg-white/15" : ""}`} onClick={() => setCat(c)}>{c}</button>)}</div>
          <div className="grid gap-2 sm:grid-cols-2">{acts.filter((a) => cat === "all" || a.category === cat).map((a) => <div key={a.key} className="flex justify-between rounded-lg bg-white/5 px-3 py-2 text-sm"><span>{a.name}</span><span className="tabular-nums text-white/60">MET {a.met}</span></div>)}</div>
        </Card>
      </div>
    </Shell>
  );
}
