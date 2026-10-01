"use client";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Shell, { Card, Err } from "@/components/Shell";
import { api } from "@/lib/api";

export default function Recovery() {
  const [d, setD] = useState<any>(), [f, setF] = useState({ bedtime: "23:00", wake_time: "07:00", quality: 7 }), [err, setErr] = useState<string | null>(null);
  const load = () => api("/sleep").then(setD).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-bold">Recovery</h1>
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Log last night" glow>
          <form className="space-y-3 text-sm" onSubmit={async (e) => { e.preventDefault(); try { await api("/sleep", { body: f }); load(); } catch (x: any) { setErr(x.message); } }}>
            <label className="block">Bedtime<input type="time" className="input mt-1" value={f.bedtime} onChange={(e) => setF({ ...f, bedtime: e.target.value })} /></label>
            <label className="block">Wake time<input type="time" className="input mt-1" value={f.wake_time} onChange={(e) => setF({ ...f, wake_time: e.target.value })} /></label>
            <label className="block">Quality (1–10): {f.quality}<input type="range" min={1} max={10} className="w-full" value={f.quality} onChange={(e) => setF({ ...f, quality: Number(e.target.value) })} /></label>
            <button className="btn btn-primary w-full">Save</button>
          </form>
        </Card>
        <Card title="Sleep hours" className="lg:col-span-2">
          <div className="h-56"><ResponsiveContainer><BarChart data={d?.logs ?? []}><CartesianGrid stroke="rgba(255,255,255,.08)" /><XAxis dataKey="day" stroke="#999" fontSize={11} /><YAxis stroke="#999" fontSize={11} /><Tooltip contentStyle={{ background: "#14070b", border: "1px solid #333" }} /><Bar dataKey="hours" fill="#4F46E5" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </Card>
        <Card title="Insights (descriptive, not diagnostic)" className="lg:col-span-3">
          {d?.insights?.available ? d.insights.messages.map((m: string) => <p key={m} className="text-sm text-white/80">{m}</p>) : <p className="text-sm text-white/65">{d?.insights?.reason}</p>}
        </Card>
      </div>
    </Shell>
  );
}
