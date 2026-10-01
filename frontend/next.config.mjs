/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Browser talks to /api/* on the web origin; Next proxies to FastAPI (no CORS, token never leaves first-party origin).
    return [{ source: "/api/:path*", destination: `${process.env.API_URL || "http://localhost:8000"}/api/:path*` }];
  },
};
export default nextConfig;
