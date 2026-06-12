// pm2 ecosystem config para el Calendario de Informes (Next.js)
// Uso:
//   pm2 start ecosystem.config.cjs        # iniciar
//   pm2 save                              # persistir en reinicios
//   pm2 startup                           # habilitar autostart

module.exports = {
  apps: [
    {
      name: 'calendario-next',
      cwd: '/home/devdiego/Correspondencia-diciembre-1.0/calendario-informes-nextjs',
      script: 'node_modules/.bin/next',
      args: 'start --port 3000 --hostname 127.0.0.1',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
        PORT: '3000',
        HOSTNAME: '127.0.0.1',
        // Django corre detrás del mismo Nginx, mismo origen
        NEXT_PUBLIC_DJANGO_URL: 'http://192.168.3.230',
      },
      // Log rotation
      log_file: '/home/devdiego/Correspondencia-diciembre-1.0/deploy/logs/next.log',
      out_file: '/home/devdiego/Correspondencia-diciembre-1.0/deploy/logs/next-out.log',
      error_file: '/home/devdiego/Correspondencia-diciembre-1.0/deploy/logs/next-err.log',
      time: true,
    },
  ],
};
