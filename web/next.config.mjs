/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  experimental: {
    typedRoutes: false,
  },

  // Proxy client-side `/api/*` calls to the FastAPI service. The default
  // points at the docker-compose internal hostname; for local dev you can
  // override with API_INTERNAL_URL=http://localhost:8000 in `.env.local`.
  async rewrites() {
    const target = process.env.API_INTERNAL_URL ?? "http://epb-api:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${target}/:path*`,
      },
    ];
  },

  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
    };
    return config;
  },
};

export default nextConfig;
