"use client";
import { useEffect, useRef } from "react";

/** Gradient ring + trailing particles + magnetic pull on [data-magnetic]. Off for touch and reduced-motion. */
export default function Cursor() {
  const ring = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!fine || calm) return;
    document.body.classList.add("cursor-on");
    const c = canvas.current!, ctx = c.getContext("2d")!;
    const resize = () => { c.width = innerWidth; c.height = innerHeight; };
    resize(); addEventListener("resize", resize);
    let x = -100, y = -100, rx = -100, ry = -100, scale = 1, raf = 0;
    const parts: { x: number; y: number; life: number; hue: number }[] = [];
    const move = (e: MouseEvent) => {
      x = e.clientX; y = e.clientY;
      parts.push({ x, y, life: 1, hue: 340 + Math.random() * 60 });
      if (parts.length > 40) parts.shift();
      const t = (e.target as HTMLElement).closest("a,button,[data-magnetic],input,textarea");
      scale = t ? 1.9 : 1;
      if (t && (t as HTMLElement).dataset.magnetic !== undefined) {
        const r = t.getBoundingClientRect();
        x += (r.left + r.width / 2 - x) * 0.25; y += (r.top + r.height / 2 - y) * 0.25;
      }
    };
    const down = () => { scale = 0.7; ring.current?.animate([{ boxShadow: "0 0 0 0 rgba(220,20,60,.7)" }, { boxShadow: "0 0 0 22px rgba(220,20,60,0)" }], { duration: 450 }); };
    const up = () => (scale = 1);
    const loop = () => {
      rx += (x - rx) * 0.18; ry += (y - ry) * 0.18;
      if (ring.current) ring.current.style.transform = `translate(${rx - 16}px,${ry - 16}px) scale(${scale})`;
      ctx.clearRect(0, 0, c.width, c.height);
      for (const p of parts) { p.life -= 0.03; ctx.fillStyle = `hsla(${p.hue},90%,60%,${Math.max(p.life, 0) * 0.6})`; ctx.beginPath(); ctx.arc(p.x, p.y, 3 * p.life, 0, 7); ctx.fill(); }
      while (parts.length && parts[0].life <= 0) parts.shift();
      raf = requestAnimationFrame(loop);
    };
    addEventListener("mousemove", move); addEventListener("mousedown", down); addEventListener("mouseup", up);
    loop();
    return () => { cancelAnimationFrame(raf); removeEventListener("mousemove", move); removeEventListener("mousedown", down); removeEventListener("mouseup", up); removeEventListener("resize", resize); document.body.classList.remove("cursor-on"); };
  }, []);
  return (
    <>
      <canvas ref={canvas} aria-hidden className="pointer-events-none fixed inset-0 z-[60]" />
      <div ref={ring} aria-hidden className="pointer-events-none fixed left-0 top-0 z-[61] h-8 w-8 rounded-full border-2 border-transparent transition-[scale] duration-150 [background:linear-gradient(#050204,#050204)_padding-box,linear-gradient(135deg,#DC143C,#9333EA,#2563EB)_border-box]" />
    </>
  );
}
