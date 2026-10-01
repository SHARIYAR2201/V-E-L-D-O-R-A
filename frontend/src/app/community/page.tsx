"use client";
import { useEffect, useState } from "react";
import Shell, { Card } from "@/components/Shell";
import { api } from "@/lib/api";

export default function Community() {
  const [a, setA] = useState<any[]>([]);
  useEffect(() => { api("/achievements").then(setA).catch(() => {}); }, []);
  return (
    <Shell>
      <h1 className="mb-6 text-3xl font-bold">Achievements</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {a.map((x) => (
          <Card key={x.key} glow={x.earned}><div className={x.earned ? "" : "opacity-45"}><div className="text-lg font-semibold">{x.title}</div><div className="text-sm text-white/60">{x.earned ? `Earned ${x.earned_at?.slice(0, 10)}` : "Not yet"}</div></div></Card>
        ))}
      </div>
      <p className="mt-6 text-sm text-white/55">Posts, challenges and leaderboards are not part of this release; they need moderation and privacy design first.</p>
    </Shell>
  );
}
