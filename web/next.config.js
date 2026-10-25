import "./src/env.js";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
  {
    // Keep the app unembeddable without locking down Next's inline scripts.
    key: "Content-Security-Policy",
    value: "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
  },
];

/** @type {import("next").NextConfig} */
const config = {
  poweredByHeader: false,
  // Workspace packages ship TypeScript source; Next compiles them with the app.
  transpilePackages: ["@spottr/api-client"],
  experimental: {
    serverActions: {
      // The coach only needs a short text question.
      bodySizeLimit: "16kb",
    },
  },
  async headers() {
    return [{ source: "/(.*)", headers: securityHeaders }];
  },
};

export default config;
