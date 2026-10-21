#!/usr/bin/env bash
# Copia de seguridad diaria: base de datos + carpeta uploads (fotos y comprobantes). Guarda 14 días.
# Programarla con cron (como el usuario rifaplus):  30 2 * * * /opt/rifaplus/despliegue/respaldo.sh
set -euo pipefail
DESTINO=/opt/respaldos/rifaplus
FECHA=$(date +%Y-%m-%d_%H%M)
mkdir -p "$DESTINO"
# La conexión se toma del .env (DATABASE_URL); pg_dump usa el formato postgresql:// sin "+psycopg"
URL=$(grep '^DATABASE_URL=' /opt/rifaplus/.env | cut -d= -f2- | sed 's/+psycopg//')
pg_dump --format=custom --file="$DESTINO/bd_$FECHA.dump" "$URL"
tar -czf "$DESTINO/uploads_$FECHA.tar.gz" -C /opt/rifaplus uploads
find "$DESTINO" -type f -mtime +14 -delete
echo "Respaldo listo: $DESTINO ($FECHA)"
