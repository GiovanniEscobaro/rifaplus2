#!/usr/bin/env bash
# Actualizar RifaPlus en el servidor con una versión nueva (zip descomprimido en /tmp/rifaplus).
# Uso:  sudo /opt/rifaplus/despliegue/actualizar.sh
set -euo pipefail
/opt/rifaplus/despliegue/respaldo.sh                  # primero, copia de seguridad
rsync -a --exclude .env --exclude .venv --exclude uploads /tmp/rifaplus/ /opt/rifaplus/
chown -R rifaplus:rifaplus /opt/rifaplus
sudo -u rifaplus bash -c "cd /opt/rifaplus && .venv/bin/pip install -q -r requirements.txt && .venv/bin/alembic upgrade head"
systemctl restart rifaplus
echo "RifaPlus actualizado."
