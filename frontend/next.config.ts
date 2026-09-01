import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // This repo already documents itself via README.md / docs/ — skip
  // Next's auto-generated AGENTS.md / CLAUDE.md scaffolding files.
  agentRules: false,
};

export default nextConfig;
