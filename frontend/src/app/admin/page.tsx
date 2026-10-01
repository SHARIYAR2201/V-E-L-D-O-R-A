"use client";
import { useEffect, useState } from "react";
import Shell, { Card, Err, Stat } from "@/components/Shell";
import { api } from "@/lib/api";

export default function Admin() {
  const [s, setS] = useState<any>(), [u, setU] = useState<any[]>([]), [d, setD] = useState<any>(), [err, setErr] = useState<string | null>(null);
  useEffect(() => { Promise.all([api("/admin/stats").then(setS), api("/admin/users").then(setU), api("/admin/datasets").then(setD)]).catch((e) => setErr(e.message)); }, []);
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-bold">Admin</h1>
      <Err e={err} />
      {s && <div className="mb-4 grid grid-cols-2 gap-4 md:grid-cols-6">{Object.entries(s).map(([k, v]: any) => <Card key={k}><Stat label={k.replace(/_/g, " ")} value={v} /></Card>)}</div>}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Users"><div className="space-y-1 text-sm">{u.map((x) => <div key={x.id} className="flex items-center justify-between"><span>{x.email} · {x.role}</span>
          <button className="btn btn-ghost !py-0.5 text-xs" onClick={async () => { await api(`/admin/users/${x.id}`, { method: "PATCH", body: { is_active: !x.active } }); setU(await api("/admin/users")); }}>{x.active ? "Deactivate" : "Activate"}</button></div>)}</div></Card>
        <Card title="Model audit (honest metrics)">{d?.models && <div className="space-y-2 text-sm text-white/80">
          <p><b>Calorie model:</b> {d.models.calorie_burn.finding}</p><p><b>Lifestyle risk model:</b> {d.models.lifestyle_risk_indicator.finding}</p>
          <p><b>Sleep model:</b> holdout R² {d.models.sleep_quality.holdout_r2} on a synthetic-looking dataset; used descriptively only.</p></div>}</Card>
        <Card title="Wearable survey (n=30)" className="lg:col-span-2">{d?.survey && <p className="text-sm text-white/80">{Math.round(d.survey.share_agree_motivated * 100)}% agree wearables keep them motivated; {Math.round(d.survey.share_agree_exercise_more * 100)}% say they exercise more; {Math.round(d.survey.share_agree_change_diet * 100)}% changed their diet. Small sample, aggregate use only.</p>}</Card>
      </div>
    </Shell>
  );
}
