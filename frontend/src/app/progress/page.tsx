"use client";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Shell, { Card, Err, Loading, Stat } from "@/components/Shell";
import { api } from "@/lib/api";

export default function Progress() {
  const [m, setM] = useState<any>(), [ins, setIns] = useState<any>(), [w, setW] = useState(""), [err, setErr] = useState<string | null>(null);
  const load = () => { api("/me/metrics").then(setM).catch((e) => setErr(e.message)); api("/ai/insights").then(setIns).catch(() => {}); };
  useEffect(load, []);
  const wt = ins?.weight_trend;
  const series = m ? [...m.history.map((h: any) => ({ day: h.day, weight: h.weight_kg })), ...(wt?.available ? wt.forecast.map((f: any) => ({ day: f.date, forecast: f.predicted_kg })) : [])] : [];
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-bold">Progress</h1>
      <Err e={err} />
      {!m ? <Loading /> : (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card title="Weight (kg) and forecast" className="lg:col-span-2" glow>
            <div className="h-72"><ResponsiveContainer><LineChart data={series}><CartesianGrid stroke="rgba(255,255,255,.08)" /><XAxis dataKey="day" stroke="#999" fontSize={11} /><YAxis domain={["auto", "auto"]} stroke="#999" fontSize={11} /><Tooltip contentStyle={{ background: "#14070b", border: "1px solid #333" }} />
              <Line dataKey="weight" stroke="#DC143C" strokeWidth={2.5} dot connectNulls /><Line dataKey="forecast" stroke="#06B6D4" strokeDasharray="5 5" dot={false} connectNulls /></LineChart></ResponsiveContainer></div>
            <form className="mt-3 flex gap-2" onSubmit={async (e) => { e.preventDefault(); await api("/weight", { body: { weight_kg: Number(w) } }); setW(""); load(); }}>
              <input className="input !w-40" aria-label="Weight kg" inputMode="decimal" placeholder="Today, kg" value={w} onChange={(e) => setW(e.target.value)} /><button className="btn btn-primary">Add</button>
            </form>
          </Card>
          <Card title="Forecast (estimate)">
            {wt?.available ? <div className="space-y-2 text-sm"><Stat label="Trend" value={`${wt.slope_kg_per_week > 0 ? "+" : ""}${wt.slope_kg_per_week}`} unit="kg/week" />
              <p>Confidence: <b>{wt.confidence}</b> (n={wt.n}, R²={wt.r2})</p>{wt.forecast.slice(0, 3).map((f: any) => <p key={f.days_ahead}>In {f.days_ahead} d: {f.predicted_kg} kg ({f.range_kg[0]}–{f.range_kg[1]})</p>)}
              {wt.goal_eta && <p>Goal weight at this pace: {wt.goal_eta}</p>}<p className="text-xs text-white/55">{wt.caveat}</p></div> : <p className="text-sm text-white/65">{wt?.reason}</p>}
          </Card>
          <Card title="Consistency">{ins && <><Stat label="Score" value={ins.consistency.score} unit="/100" bar={ins.consistency.score} /><p className="mt-2 text-xs text-white/60">{ins.consistency.method}</p></>}</Card>
          <Card title="Nutrition adherence" className="lg:col-span-2">{ins?.nutrition_adherence?.available ? <p className="text-sm">{ins.nutrition_adherence.days_within_10pct_kcal} of {ins.nutrition_adherence.days_logged} logged days within 10% of your calorie target ({ins.nutrition_adherence.adherence_pct}%). {ins.nutrition_adherence.note}</p> : <p className="text-sm text-white/65">{ins?.nutrition_adherence?.reason}</p>}</Card>
        </div>
      )}
    </Shell>
  );
}
