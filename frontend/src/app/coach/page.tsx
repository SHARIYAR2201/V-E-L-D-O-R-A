"use client";
import { useEffect, useRef, useState } from "react";
import Shell, { Card } from "@/components/Shell";
import { api } from "@/lib/api";

type Msg = { role: "me" | "ai"; text: string; why?: string[] };
const PROMPTS = ["What should I eat tonight?", "I have 500 calories left", "How is my progress?", "What workout should I do today?"];

export default function Coach() {
  const [msgs, setMsgs] = useState<Msg[]>([{ role: "ai", text: "Ask about meals, workouts, progress, sleep or water. I answer from your own logs and targets." }]);
  const [text, setText] = useState(""), [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [msgs]);
  const send = async (t: string) => {
    if (!t.trim() || busy) return;
    setMsgs((m) => [...m, { role: "me", text: t }]); setText(""); setBusy(true);
    try { const r = await api("/ai/assistant", { body: { message: t } }); setMsgs((m) => [...m, { role: "ai", text: r.reply, why: r.why }]); }
    catch (e: any) { setMsgs((m) => [...m, { role: "ai", text: e.message }]); } finally { setBusy(false); }
  };
  return (
    <Shell>
      <h1 className="mb-4 text-3xl font-bold">AI Coach</h1>
      <Card glow className="flex h-[65vh] flex-col">
        <div className="flex-1 space-y-3 overflow-y-auto pr-1" aria-live="polite">
          {msgs.map((m, i) => (
            <div key={i} className={`max-w-[85%] rounded-2xl px-4 py-2.5 ${m.role === "me" ? "ml-auto bg-gradient-to-br from-blood to-crimson" : "bg-white/8 bg-aig/20"}`}>
              <p>{m.text}</p>
              {m.why?.length ? <details className="mt-1 text-xs text-white/65"><summary className="cursor-pointer">Why this answer</summary>{m.why.map((w) => <p key={w}>{w}</p>)}</details> : null}
            </div>
          ))}
          {busy && <p className="text-sm text-white/50">Thinking…</p>}
          <div ref={end} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">{PROMPTS.map((p) => <button key={p} className="btn btn-ghost !py-1 text-xs" onClick={() => send(p)}>{p}</button>)}</div>
        <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(text); }}>
          <input className="input" aria-label="Message" placeholder="Ask your coach…" value={text} onChange={(e) => setText(e.target.value)} maxLength={500} />
          <button className="btn btn-ai" disabled={busy}>Send</button>
        </form>
      </Card>
    </Shell>
  );
}
