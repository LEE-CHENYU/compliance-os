/** @type {import('next').NextConfig} */
const nextConfig = {
  // Skip in-build typecheck + lint — tsc under QEMU amd64-on-arm64
  // emulation can hang for 50+ minutes during Docker builds. We
  // typecheck on arm64 native (`npm run build` locally + CI) before
  // pushing, so skipping inside the container is safe.
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
