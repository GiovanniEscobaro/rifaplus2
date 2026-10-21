#!/bin/sh
# Arranque del contenedor de RifaPlus.
# 1) Crea o actualiza las tablas (alembic upgrade head). En una base vacía crea todas; si ya están al día, no hace nada.
# 2) Carga los datos iniciales que falten (loterías, medios de pago, tipos de rifa y precios). No duplica ni cambia lo
#    que usted ya editó.
# 3) Arranca la app (el CMD del Dockerfile).
# Para desactivar los pasos 1 y 2 (por ejemplo, si prefiere correr las migraciones a mano): MIGRAR_AL_ARRANCAR=0
set -e

if [ "${MIGRAR_AL_ARRANCAR:-1}" != "0" ]; then
    echo "RifaPlus: aplicando migraciones…"
    alembic upgrade head
    echo "RifaPlus: cargando datos iniciales que falten…"
    python -m app.cli semillas
fi

exec "$@"
