import type { Config } from "tailwindcss";
export default {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#050204", crimson: "#DC143C", blood: "#8B0000", wine: "#5B0217",
        ai: { blue: "#2563EB", cyan: "#06B6D4", indigo: "#4F46E5" },
        ok: { green: "#22C55E", emerald: "#10B981", teal: "#14B8A6" },
      },
      fontFamily: { sans: ["Avenir Next", "Segoe UI", "Helvetica Neue", "Arial", "system-ui", "sans-serif"] },
      backgroundImage: {
        primary: "linear-gradient(135deg,#000000,#5B0217 40%,#8B0000 70%,#DC143C)",
        secondary: "linear-gradient(135deg,#000000,#FF0000 55%,#FFFFFF)",
        aig: "linear-gradient(135deg,#2563EB,#06B6D4 50%,#4F46E5)",
        success: "linear-gradient(135deg,#22C55E,#10B981 50%,#14B8A6)",
        premium: "linear-gradient(135deg,#DC143C,#9333EA 50%,#2563EB)",
      },
    },
  },
} satisfies Config;
