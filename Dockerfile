# RifaPlus para producción. Va detrás de Caddy (HTTPS) en la red de Docker y se conecta al contenedor de PostgreSQL.
# Construir:  docker build -t rifaplus .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=America/Bogota \
    APP_ENTORNO=produccion \
    CARPETA_ARCHIVOS=/app/uploads

# Zona horaria del sistema (fechas de vencimiento, cuotas y sorteos en hora de Colombia)
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios: la app nunca corre como root
RUN groupadd --gid 1000 rifaplus && useradd --uid 1000 --gid rifaplus --create-home rifaplus

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=rifaplus:rifaplus . .
# Carpeta de fotos y comprobantes: montar aquí un volumen para que no se pierdan al recrear el contenedor
RUN mkdir -p /app/uploads && chown rifaplus:rifaplus /app/uploads && chmod +x /app/despliegue/docker-entrypoint.sh

USER rifaplus
EXPOSE 8000

# Docker revisa cada 30 s que la app responda «OK» en /health (incluye la conexión a la base de datos)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

# El script de arranque aplica las migraciones y los datos iniciales, y después ejecuta el CMD
ENTRYPOINT ["/app/despliegue/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--workers", "2"]
