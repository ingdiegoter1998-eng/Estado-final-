# Rollback 20260603-091333
cp -a /home/devdiego/Correspondencia-diciembre-1.0/deploy/backups/pre-deploy-20260603-091333/.env /home/devdiego/Correspondencia-diciembre-1.0/.env
MAINPID=$(systemctl show correspondencia -p MainPID --value)
sudo kill -HUP "$MAINPID"
