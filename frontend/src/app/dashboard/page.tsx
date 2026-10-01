"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import Shell, { Card, Err, Loading, Stat } from "@/components/Shell";
import { api } from "@/lib/api";

export default function Dashboard() {
  const [d, setD] = useState<any>(), [ins, setIns] = useState<any>(), [err, setErr] = useState<string | null>(null);
  useEffect(() => { api("/me/dashboard").then(setD).catch((e) => setErr(e.message)); api("/ai/insights").then(setIns).catch(() => {}); }, []);
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-bold">Today</h1>
      <Err e={err} />
      {!d ? <Loading /> : !d.profile_complete ? (
        <Card glow><p>Add your age, sex, height and weight to see targets. <Link href="/profile" className="underline">Complete profile</Link></p></Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card><Stat label="Calories eaten" value={Math.round(d.eaten.kcal)} unit={`/ ${d.targets.kcal}`} bar={(100 * d.eaten.kcal) / d.targets.kcal} /></Card>
          <Card><Stat label="Protein" value={Math.round(d.eaten.protein_g)} unit={`/ ${d.targets.protein_g} g`} bar={(100 * d.eaten.protein_g) / d.targets.protein_g} /></Card>
          <Card><Stat label="Water" value={Math.round(d.water_ml)} unit={`/ ${d.targets.water_ml} ml`} bar={(100 * d.water_ml) / d.targets.water_ml} /></Card>
          <Card><Stat label="Burned by workouts" value={Math.round(d.burned_kcal)} unit="kcal (est.)" /></Card>
          <Card title="Your numbers" className="md:col-span-2">
            <div className="grid grid-cols-4 gap-3"><Stat label="BMI" value={d.targets.bmi} /><Stat label="BMR" value={d.targets.bmr} unit="kcal" /><Stat label="TDEE" value={d.targets.tdee} unit="kcal" /><Stat label="Goal" value={d.targets.goal} /></div>
            {d.targets.notes?.map((n: string) => <p key={n} className="mt-3 text-sm text-amber-200/90">{n}</p>)}
          </Card>
          <Card title="AI insights" className="md:col-span-2" glow>
            {!ins ? <Loading /> : (
              <ul className="space-y-2 text-sm text-white/80">
                <li>Consistency {ins.consistency.score}/100, streak {ins.consistency.current_streak} day(s).</li>
                <li>{ins.weight_trend.available ? `Weight trend ${ins.weight_trend.slope_kg_per_week > 0 ? "+" : ""}${ins.weight_trend.slope_kg_per_week} kg/week (${ins.weight_trend.confidence} confidence).` : ins.weight_trend.reason}</li>
                {ins.behaviour_patterns.map((b: string) => <li key={b}>{b}</li>)}
              </ul>
            )}
            <Link className="mt-3 inline-block text-sm underline" href="/coach">Ask the coach</Link>
          </Card>
        </div>
      )}
    </Shell>
  );
}
