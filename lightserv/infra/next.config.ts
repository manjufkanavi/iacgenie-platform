import type { NextConfig } from "next";
import * as path from "path";

const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: false,
  outputFileTracingRoot: path.resolve(__dirname),
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;