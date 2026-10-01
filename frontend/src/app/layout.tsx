import "./globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "V-E-L-D-O-R-A | AI health, nutrition & fitness",
  description: "Informational health, nutrition and fitness guidance. Not a medical device.",
};
export const viewport: Viewport = { themeColor: "#050204", width: "device-width", initialScale: 1 };

export default function Root({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
