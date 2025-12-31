/** @type {import('next').NextConfig} */
const path = require("path");

const nextConfig = {
  // Enable standalone output for Docker optimization
  output: "standalone",
  // Handle ESM packages compatibility
  experimental: {
    esmExternals: "loose",
  },
  webpack: (config, { isServer }) => {
    // Fix for mermaid's cytoscape dependency - use CJS version
    config.resolve.alias = {
      ...config.resolve.alias,
      cytoscape: path.resolve(
        __dirname,
        "node_modules/cytoscape/dist/cytoscape.cjs.js",
      ),
    };

    return config;
  },
  // Transpile mermaid and related packages
  transpilePackages: ["mermaid"],
};

module.exports = nextConfig;
