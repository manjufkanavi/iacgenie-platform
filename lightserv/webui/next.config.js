const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  devIndicators: false,
  // Force webpack, disable turbopack entirely
  experimental: {
    webpack: true,
  },
};

module.exports = nextConfig;
