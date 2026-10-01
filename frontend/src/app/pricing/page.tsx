"use client";
import Link from "next/link";
import Shell, { Card } from "@/components/Shell";

const PLANS = [["Free", "$0", ["Food, workout, sleep, water logging", "AI coach", "Daily plans"]], ["Plus", "$9", ["Everything in Free", "7-day plans", "Full insights history"]], ["Pro", "$19", ["Everything in Plus", "Early access features"]]];
export default function Pricing() {
  return (
    <Shell protectedPage={false}>
      <h1 className="mb-6 text-3xl font-bold">Pricing</h1>
      <div className="grid gap-4 md:grid-cols-3">
        {PLANS.map(([n, p, f]: any) => <Card key={n} title={n} glow={n === "Plus"}><div className="text-4xl font-bold">{p}<span className="text-sm font-normal text-white/50">/mo</span></div><ul className="mt-3 space-y-1 text-sm text-white/75">{f.map((x: string) => <li key={x}>{x}</li>)}</ul><Link href="/register" className="btn btn-primary mt-4 inline-block text-sm">Choose {n}</Link></Card>)}
      </div>
      <p className="mt-4 text-xs text-white/50">Demo pricing. No payment processing is connected, so nothing is charged.</p>
    </Shell>
  );
}
