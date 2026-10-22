import "./src/env.js";

/** @type {import("next").NextConfig} */
const config = {
  // Workspace packages ship TypeScript source; Next compiles them with the app.
  transpilePackages: ["@spottr/ui", "@spottr/api-client"],
};

export default config;
