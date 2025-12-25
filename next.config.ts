import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  rewrites: async () => {
    return [
      {
        source: "/conversations/:path*",
        destination:
          process.env.NODE_ENV === "development"
            ? "http://127.0.0.1:8000/conversations/:path*"
            : "/api/conversations/:path*",
      },
      {
        source: "/healthcheck",
        destination:
          process.env.NODE_ENV === "development"
            ? "http://127.0.0.1:8000/healthcheck"
            : "/api/healthcheck",
      },
    ];
  },
};

export default nextConfig;
