"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { motion } from "framer-motion";
import Shell, { Card } from "@/components/Shell";

const AICore = dynamic(() => import("@/components/AICore"), { ssr: false, loading: () => <div className="h-full w-full" /> });

const FEATURES = [
  ["Say what you ate", "Type “2 eggs and 150 g chicken”. Every number comes from USDA FoodData Central and you confirm before it is logged."],
  ["Plans that follow your rules", "Allergies, diet choices and health conditions are hard filters. The plan shows which rules it applied and whether it met them."],
  ["Honest predictions", "Weight trends come with a range and a confidence label, never a promise."],
  ["Workouts with safety caps", "Session intensity is capped for conditions like hypertension or heart disease, and calories use MET × weight × time."],
];

export default function Landing() {
  return (
    <Shell protectedPage={false}>
      <section className="relative grid min-h-[70vh] items-center gap-8 lg:grid-cols-2">
        <div>
          <motion.h1 initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="text-5xl font-black leading-[1.05] sm:text-6xl lg:text-7xl">
            Next-generation<br />fitness, <span className="bg-premium bg-clip-text text-transparent">explained.</span>
          </motion.h1>
          <p className="mt-5 max-w-xl text-lg text-white/70">Track meals, workouts, sleep and water in one place. Get plans built from real nutrition data, with the reasoning shown.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/register" className="btn btn-primary" data-magnetic>Start free</Link>
            <Link href="/data-sources" className="btn btn-ghost" data-magnetic>See our data</Link>
          </div>
        </div>
        <div className="relative mx-auto h-[340px] w-full max-w-[460px] sm:h-[440px]"><AICore className="h-full w-full" /></div>
      </section>
      <section className="mt-16 grid gap-4 sm:grid-cols-2">
        {FEATURES.map(([t, d]) => <Card key={t} title={t} glow><p className="text-white/75">{d}</p></Card>)}
      </section>
      <section className="mt-16 grid gap-4 md:grid-cols-3" aria-label="Plans">
        {[["Free", "$0", "Tracking, AI coach, plans"], ["Plus", "$9", "Weekly plans and deeper insights"], ["Pro", "$19", "Everything, priority features"]].map(([n, p, d]) => (
          <Card key={n} title={n}><div className="text-4xl font-bold">{p}<span className="text-sm font-normal text-white/50">/mo</span></div><p className="mt-2 text-white/70">{d}</p></Card>
        ))}
      </section>
      <p className="mt-4 text-xs text-white/45">Pricing is a demo; no payment processing is connected.</p>
    </Shell>
  );
}
