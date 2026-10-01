"use client";
import { useEffect, useState } from "react";
import Shell, { Card, Loading } from "@/components/Shell";
import { api } from "@/lib/api";

export default function Sources() {
  const [d, setD] = useState<any>();
  useEffect(() => { api("/meta/datasets").then(setD).catch(() => {}); }, []);
  return (
    <Shell protectedPage={false}>
      <h1 className="mb-2 text-3xl font-bold">Data Sources &amp; Attribution</h1>
      <p className="mb-6 max-w-3xl text-white/65">Every nutrition value in the app comes from the datasets below. Entries marked unverified are missing confirmed publisher details.</p>
      {!d ? <Loading /> : <div className="grid gap-4 lg:grid-cols-2">{d.datasets.map((x: any) => (
        <Card key={x.id} title={x.name} glow={!x.verified}>
          <dl className="space-y-1.5 text-sm">
            {[["Source", x.source], ["Licence", x.license], ["Purpose", x.purpose], ["Version", x.version], ["Status", x.status], ["Citation", x.citation]].map(([k, v]) => <div key={k} className="grid grid-cols-[5.5rem_1fr] gap-2"><dt className="text-white/50">{k}</dt><dd className="break-words">{v}</dd></div>)}
            {!x.verified && <p className="pt-1 text-amber-200">Provenance not verified.</p>}
          </dl>
        </Card>))}</div>}
    </Shell>
  );
}
