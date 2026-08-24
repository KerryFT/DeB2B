import type { NextConfig } from "next";

const apiOrigin = process.env.NEXT_PUBLIC_API_URL ?? "";
const connectSource = apiOrigin ? `'self' ${apiOrigin}` : "'self'";

const config: NextConfig = {
  // Vercel supplies its own Next.js build adapter. Next 16.3 currently cannot combine that
  // adapter with standalone output; self-hosted Docker builds still need standalone.
  output: process.env.VERCEL ? undefined : "standalone",
  poweredByHeader: false,
  experimental: { typedEnv: true },
  async headers() {
    return [{
      source: "/:path*",
      headers: [
        { key: "Content-Security-Policy", value: `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src ${connectSource}; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'` },
        { key: "Referrer-Policy", value: "no-referrer" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Strict-Transport-Security", value: "max-age=31536000" },
      ],
    }];
  },
};

export default config;
