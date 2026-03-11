import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,

  // Allow /embed/* pages to be loaded inside iframes on any third-party website.
  // All other pages keep the default SAMEORIGIN protection.
  async headers() {
    return [
      {
        source: "/embed/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: "frame-ancestors *",
          },
          // Explicitly remove X-Frame-Options for embed routes
          // (CSP frame-ancestors takes precedence in modern browsers,
          //  but removing X-Frame-Options avoids legacy browser conflicts)
          {
            key: "X-Frame-Options",
            value: "ALLOWALL",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
