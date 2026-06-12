/** @type {import('next').NextConfig} */
const nextConfig = {
  // BasePath para que Next.js corra bajo /calendario en producción
  // En desarrollo (npm run dev) esto NO aplica, accedes en localhost:3000
  // En producción, Nginx proxyea /calendario → :3000 y basePath hace el mapeo
  basePath: process.env.NODE_ENV === 'production' ? '/calendario' : '',

  // Rewrite para proxiar llamadas API al backend Django
  async rewrites() {
    const backendOrigin = process.env.NEXT_BACKEND_ORIGIN || 'http://127.0.0.1:8004'
    return [
      {
        source: '/registros/correspondencia/api/:path*',
        destination: `${backendOrigin}/registros/correspondencia/api/:path*/`,
      },
    ]
  },

  // Necesario cuando Nginx hace proxy (X-Forwarded-Proto puede ser http)
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
        ],
      },
    ]
  },
};

export default nextConfig;
