"use client";
import { useEffect, useState } from "react";
import Shell, { Card, Err, Stat } from "@/components/Shell";
import { api } from "@/lib/api";

export default function Nutrition() {
  const [text, setText] = useState(""), [meal, setMeal] = useState("lunch"), [parsed, setParsed] = useState<any>(), [day, setDay] = useState<any>();
  const [picks, setPicks] = useState<Record<number, { fdc_id: number; grams: string }>>({}), [err, setErr] = useState<string | null>(null), [plan, setPlan] = useState<any>();
  const [ml, setMl] = useState(250);
  const load = () => api("/nutrition/day").then(setDay).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  const parse = async () => {
    setErr(null);
    try {
      const r = await api("/nutrition/parse", { body: { text, meal } }); setParsed(r);
      const p: any = {}; r.items.forEach((it: any, i: number) => { if (it.selected) p[i] = { fdc_id: it.selected.fdc_id, grams: it.selected.estimate ? String(it.selected.estimate.grams) : "" }; }); setPicks(p);
    } catch (e: any) { setErr(e.message); }
  };
  const confirm = async () => {
    const items = Object.values(picks).filter((p) => Number(p.grams) > 0).map((p) => ({ fdc_id: p.fdc_id, grams: Number(p.grams) }));
    if (!items.length) return setErr("Enter grams for at least one item.");
    try { await api("/nutrition/log", { body: { meal, items } }); setParsed(undefined); setText(""); load(); } catch (e: any) { setErr(e.message); }
  };
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-bold">Nutrition Center</h1>
      <Err e={err} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Log food in plain language" glow>
          <div className="flex gap-2">
            <input className="input" aria-label="What did you eat" placeholder="I had 150g chicken with rice" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && parse()} />
            <select className="input !w-auto" aria-label="Meal" value={meal} onChange={(e) => setMeal(e.target.value)}>{["breakfast", "lunch", "dinner", "snack"].map((m) => <option key={m}>{m}</option>)}</select>
            <button className="btn btn-ai" onClick={parse}>Analyse</button>
          </div>
          {parsed && (
            <div className="mt-4 space-y-3">
              {parsed.items.map((it: any, i: number) => (
                <div key={i} className="rounded-xl border border-white/10 p-3">
                  <div className="text-sm text-white/60">“{it.raw}”</div>
                  {it.candidates.length ? (
                    <div className="mt-2 grid gap-2 sm:grid-cols-[1fr_7rem]">
                      <select className="input" aria-label="Matched food" value={picks[i]?.fdc_id ?? ""} onChange={(e) => setPicks({ ...picks, [i]: { fdc_id: Number(e.target.value), grams: picks[i]?.grams ?? "" } })}>
                        {it.candidates.map((c: any) => <option key={c.fdc_id} value={c.fdc_id}>{c.description} ({c.kcal_per_100g} kcal/100 g)</option>)}
                      </select>
                      <input className="input" aria-label="Grams" inputMode="decimal" placeholder="grams" value={picks[i]?.grams ?? ""} onChange={(e) => setPicks({ ...picks, [i]: { fdc_id: picks[i]?.fdc_id ?? it.candidates[0].fdc_id, grams: e.target.value } })} />
                    </div>
                  ) : null}
                  {it.issues.map((s: string) => <p key={s} className="mt-1 text-xs text-amber-200/90">{s}</p>)}
                </div>
              ))}
              <p className="text-xs text-white/55">{parsed.message}</p>
              <button className="btn btn-primary" onClick={confirm}>Confirm and log</button>
            </div>
          )}
        </Card>
        <Card title="Today" glow>
          {day && <>
            <div className="mb-4 grid grid-cols-4 gap-3"><Stat label="kcal" value={Math.round(day.total.kcal)} /><Stat label="Protein g" value={Math.round(day.total.protein_g)} /><Stat label="Carbs g" value={Math.round(day.total.carb_g)} /><Stat label="Fat g" value={Math.round(day.total.fat_g)} /></div>
            {Object.entries(day.meals).map(([k, v]: any) => v.length ? <div key={k} className="mb-2"><div className="text-xs capitalize text-white/50">{k}</div>{v.map((r: any) => <div key={r.id} className="flex justify-between text-sm"><span className="truncate pr-2">{r.description} · {r.grams} g</span><span className="tabular-nums">{Math.round(r.kcal)} kcal</span></div>)}</div> : null)}
          </>}
          <div className="mt-4 flex items-center gap-2 border-t border-white/10 pt-4">
            <span className="text-sm">Water</span>
            <select className="input !w-auto" aria-label="Amount ml" value={ml} onChange={(e) => setMl(Number(e.target.value))}>{[150, 250, 330, 500, 750].map((v) => <option key={v} value={v}>{v} ml</option>)}</select>
            <button className="btn btn-ghost !py-1.5" onClick={async () => { const r = await api("/water", { body: { ml } }); setErr(r.reminder ? `${r.total_ml} ml logged · ${r.reminder}` : `${r.total_ml} ml logged`); }}>Add</button>
          </div>
        </Card>
        <Card title="AI meal plan" className="lg:col-span-2">
          <button className="btn btn-ai" onClick={async () => { setErr(null); try { setPlan(await api("/plans/diet?days=1")); } catch (e: any) { setErr(e.message); } }}>Generate today’s plan</button>
          {plan?.blocked && plan.blocked.map((b: string) => <p key={b} className="mt-3 text-amber-200">{b}</p>)}
          {plan?.days && (
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {plan.days[0].meals.map((m: any) => (
                <div key={m.slot} className="rounded-xl border border-white/10 p-3"><div className="font-semibold capitalize">{m.slot} · {Math.round(m.total.kcal)} kcal</div>
                  {m.items.map((it: any) => <div key={it.fdc_id} className="text-sm text-white/75">{it.grams} g {it.description}</div>)}</div>
              ))}
              <div className="md:col-span-2 space-y-1 text-sm">
                <p className="text-white/70">Total {Math.round(plan.days[0].total.kcal)} kcal vs target {plan.targets.kcal}. {plan.method}</p>
                {plan.why.map((w: any) => <p key={w.rule} className="text-white/70"><b>{w.condition}:</b> {w.rule}. {w.why}</p>)}
                {plan.rule_checks.filter((c: any) => c.day === 1).map((c: any) => <p key={c.check} className={c.ok ? "text-ok-emerald" : "text-amber-200"}>{c.ok ? "Met" : "Not met"}: {c.check} {c.actual} (limit {c.limit})</p>)}
                {plan.warnings.map((w: string) => <p key={w} className="text-amber-200">{w}</p>)}
              </div>
            </div>
          )}
        </Card>
      </div>
    </Shell>
  );
}
