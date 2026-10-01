"use client";
import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";

function Core() {
  const g = useRef<THREE.Group>(null);
  const pts = useMemo(() => {
    const a: number[] = [];
    for (let i = 0; i < 420; i++) { const v = new THREE.Vector3().randomDirection().multiplyScalar(1.6 + Math.random() * 0.9); a.push(v.x, v.y, v.z); }
    return new Float32Array(a);
  }, []);
  useFrame((s, d) => { if (g.current) { g.current.rotation.y += d * 0.18; g.current.rotation.x = Math.sin(s.clock.elapsedTime * 0.3) * 0.15; } });
  return (
    <group ref={g}>
      <mesh><icosahedronGeometry args={[1.05, 2]} /><meshBasicMaterial color="#06B6D4" wireframe transparent opacity={0.5} /></mesh>
      <mesh><icosahedronGeometry args={[0.6, 1]} /><meshBasicMaterial color="#DC143C" wireframe transparent opacity={0.8} /></mesh>
      <points><bufferGeometry><bufferAttribute attach="attributes-position" array={pts} count={pts.length / 3} itemSize={3} /></bufferGeometry>
        <pointsMaterial size={0.03} color="#9333EA" transparent opacity={0.85} /></points>
    </group>
  );
}

/** Decorative 3D core. Static fallback is handled by the parent when reduced-motion is requested. */
export default function AICore({ className = "" }: { className?: string }) {
  return (
    <div className={className} aria-hidden>
      <Canvas camera={{ position: [0, 0, 4.6], fov: 50 }} dpr={[1, 1.5]} frameloop="always"><Core /></Canvas>
    </div>
  );
}
