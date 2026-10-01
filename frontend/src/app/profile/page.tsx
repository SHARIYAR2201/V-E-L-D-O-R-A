"use client";
import { useEffect, useState } from "react";
import Shell, { Card, Err } from "@/components/Shell";
import { api } from "@/lib/api";

const NUM = ["age", "height_cm", "weight_kg", "target_weight_kg"] as const;
export default function Profile() {
  const [p, setP] = useState<any>(), [conds, setConds] = useState<Record<string, string>>({}), [allergens, setAll] = useState<string[]>([]), [diets, setDiets] = useState<string[]>([]), [msg, setMsg] = useState("");
  useEffect(() => { api("/me").then((m) => setP(m.profile)); api("/conditions").then((c) => { setConds(c.conditions); setAll(c.allergens); setDiets(c.diets); }); }, []);
  if (!p) return <Shell><p>Loading…</p></Shell>;
  const set = (k: string, v: any) => setP({ ...p, [k]: v });
  const toggle = (k: string, v: string) => set(k, (p[k] ?? []).includes(v) ? p[k].filter((x: string) => x !== v) : [...(p[k] ?? []), v]);
  const save = async () => {
    setMsg("");
    const body: any = { ...p }; delete body.name;
    NUM.forEach((k) => (body[k] = body[k] === "" || body[k] == null ? null : Number(body[k])));
    if (!body.target_date) delete body.target_date;
    try { await api("/me/profile", { method: "PUT", body }); setMsg("Saved."); } catch (e: any) { setMsg(e.message); }
  };
  const Chips = ({ k, opts }: { k: string; opts: string[] }) => <div className="flex flex-wrap gap-2">{opts.map((o) => <button type="button" key={o} aria-pressed={(p[k] ?? []).includes(o)} onClick={() => toggle(k, o)} className={`btn btn-ghost !py-1 text-xs ${(p[k] ?? []).includes(o) ? "!bg-crimson/30" : ""}`}>{o.replace(/_/g, " ")}</button>)}</div>;
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-bold">Profile</h1>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Body and goal" glow><div className="grid grid-cols-2 gap-3 text-sm">
          {NUM.map((k) => <label key={k}>{k.replace(/_/g, " ")}<input className="input mt-1" inputMode="decimal" value={p[k] ?? ""} onChange={(e) => set(k, e.target.value)} /></label>)}
          <label>Sex<select className="input mt-1" value={p.sex ?? ""} onChange={(e) => set("sex", e.target.value || null)}><option value="">—</option><option>male</option><option>female</option></select></label>
          <label>Activity<select className="input mt-1" value={p.activity_level} onChange={(e) => set("activity_level", e.target.value)}>{["sedentary", "light", "moderate", "active", "very_active"].map((a) => <option key={a}>{a}</option>)}</select></label>
          <label>Goal<select className="input mt-1" value={p.goal_type} onChange={(e) => set("goal_type", e.target.value)}>{["lose", "maintain", "gain"].map((a) => <option key={a}>{a}</option>)}</select></label>
          <label>Experience<select className="input mt-1" value={p.experience} onChange={(e) => set("experience", e.target.value)}>{["beginner", "intermediate", "advanced"].map((a) => <option key={a}>{a}</option>)}</select></label>
          <label className="col-span-2">Target date<input type="date" className="input mt-1" value={p.target_date ?? ""} onChange={(e) => set("target_date", e.target.value)} /></label></div></Card>
        <Card title="Health conditions (optional)"><p className="mb-2 text-xs text-white/55">Used only to apply safety limits. Nothing here is a diagnosis.</p><Chips k="conditions" opts={Object.keys(conds)} /></Card>
        <Card title="Allergies"><Chips k="allergies" opts={allergens} /></Card>
        <Card title="Diet and equipment"><div className="space-y-3"><Chips k="diet_preferences" opts={diets} /><Chips k="equipment" opts={["dumbbells", "gym"]} /></div></Card>
      </div>
      <div className="mt-4 flex items-center gap-3"><button className="btn btn-primary" onClick={save}>Save profile</button><Err e={msg !== "Saved." ? msg : null} />{msg === "Saved." && <span role="status" className="text-ok-emerald">Saved.</span>}</div>
    </Shell>
  );
}
