const basePath = process.env.NEXT_BASE_PATH || "";
const backendOrigin =
  process.env.NEXT_BACKEND_ORIGIN || "http://127.0.0.1";

/** @type {import('next').NextConfig} */
const nextConfig = {
  basePath,
  async redirects() {
    if (basePath) return [];
    return [
      {
        source: "/monitoreo",
        destination: "/",
        permanent: false,
      },
      {
        source: "/monitoreo/",
        destination: "/",
        permanent: false,
      },
      {
        source: "/monitoreo/:path*",
        destination: "/:path*",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/static/:path*",
        destination: `${backendOrigin}/static/:path*`,
      },
      {
        source: "/media/:path*",
        destination: `${backendOrigin}/media/:path*`,
      },
      {
        source: "/registros/:path*",
        destination: `${backendOrigin}/registros/:path*/`,
      },
    ];
  },
};

export default nextConfig;
