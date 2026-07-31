import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname, "../.."),
  },
  // Emits .next/standalone with only the traced runtime deps, so the container
  // image does not need node_modules or a package install step.
  output: "standalone",
  // Trace from the monorepo root: this app depends on the @align/generated-types
  // workspace package, which lives outside its own directory.
  outputFileTracingRoot: path.join(__dirname, "../.."),
};

export default nextConfig;
