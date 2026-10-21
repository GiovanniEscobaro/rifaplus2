# RifaPlus en Docker (servidor con Caddy y PostgreSQL en contenedores)

Servidor: Ubuntu 24.04 con Docker Compose. Caddy hace de proxy con HTTPS y PostgreSQL 17 corre en otro contenedor.
RifaPlus queda en `https://rifaplus.gedev.co`.

## Archivos

| Archivo | Para qué |
|---|---|
| `Dockerfile` | Imagen de producción: Python 3.12, usuario sin privilegios, zona horaria America/Bogota, uvicorn en 0.0.0.0:8000 con `--proxy-headers`, 2 procesos y revisión de salud en `/health`. |
| `despliegue/docker-entrypoint.sh` | Al arrancar: migraciones (`alembic upgrade head`), datos iniciales que falten (`semillas`) y luego la app. |
| `docker-compose.yml` | Ejemplo del servicio `rifaplus` (redes, volumen de archivos, `.env`). |
| `.env.example` | Nombres de todas las variables, sin valores. |
| `.dockerignore` | Deja por fuera `.env`, entornos virtuales, cachés, `.git`, pruebas y archivos subidos. |

## Base de datos

La app lee la conexión **solo** de `DATABASE_URL`. Acepta `postgresql://…` (la convierte sola al controlador
psycopg 3) o `postgresql+psycopg://…`. Con su servidor:

```
DATABASE_URL=postgresql://rifaplus_user:LA_CLAVE@postgres:5432/rifaplus
```

**Las tablas se crean con Alembic** (no con `create_all`). Pasa solo al arrancar el contenedor: el script de arranque
ejecuta `alembic upgrade head`, que en una base vacía crea todas las tablas y en una base existente aplica solo lo que
falte. Después ejecuta `python -m app.cli semillas`, que carga loterías, medios de pago, tipos de rifa y precios **solo
si faltan** (no duplica ni cambia lo que usted editó). Arrancar varias veces es seguro.

Si prefiere hacerlo a mano, ponga `MIGRAR_AL_ARRANCAR=0` en el `.env` y ejecute:

```bash
docker compose run --rm rifaplus alembic upgrade head
docker compose run --rm rifaplus python -m app.cli semillas
```

Requisito: el usuario `rifaplus_user` debe ser dueño de la base `rifaplus` (o tener permiso para crear tablas en el
esquema `public`).

## Primera vez

```bash
cp .env.example .env && nano .env              # llenar los valores (ver la tabla de abajo)
mkdir -p uploads && sudo chown 1000:1000 uploads   # la app corre con el usuario 1000 dentro del contenedor
docker compose up -d --build
docker compose logs -f rifaplus                # debe decir «aplicando migraciones…» y luego «Uvicorn running»
docker exec -it rifaplus python -m app.cli crear-superadmin
```

En el Caddyfile:

```
rifaplus.gedev.co {
    reverse_proxy rifaplus:8000
    request_body {
        max_size 6MB
    }
}
```

`max_size` permite subir fotos y comprobantes de hasta 5 MB.

## Comprobar

- `https://rifaplus.gedev.co/health` debe responder `OK`. Si responde un error 503, la app está viva pero no llega
  a la base de datos: revise `DATABASE_URL` y que el contenedor esté en la misma red que `postgres`.
- `docker ps` muestra el contenedor como **healthy** cuando `/health` responde bien.

## Variables mínimas para producción

`APP_ENTORNO=produccion`, `APP_URL=https://rifaplus.gedev.co`, `CLAVE_SECRETA` (32 caracteres o más) y `DATABASE_URL`.
Si falta alguna, la app no arranca y el registro dice cuál falta. Para que salgan correos: `SMTP_USUARIO`,
`SMTP_CLAVE` y `CORREO_AVISOS_ADMIN`. Para los términos: las cuatro `RESPONSABLE_…` y `CORREO_CONTACTO`.

## Archivos subidos

Fotos de premios y comprobantes de pago se guardan en `/app/uploads` dentro del contenedor (variable
`CARPETA_ARCHIVOS`). El `docker-compose.yml` la monta en `./uploads` del servidor para que no se pierdan al recrear el
contenedor. **Incluya esa carpeta en sus copias de seguridad**, junto con la base de datos.

## Tarea programada (una vez al día)

Los avisos de vencimiento por correo los envía un comando. Agregue al `crontab` del servidor:

```
0 8 * * * docker exec rifaplus python -m app.cli avisar-vencimientos >> /var/log/rifaplus-avisos.log 2>&1
```

## Copias de seguridad

```bash
docker exec postgres pg_dump -U rifaplus_user -Fc rifaplus > rifaplus_$(date +%F).dump
tar -czf uploads_$(date +%F).tar.gz uploads
```

## Actualizar a una versión nueva

```bash
# con el código nuevo en la carpeta del proyecto
docker compose up -d --build     # al arrancar aplica las migraciones nuevas solas
```

Haga antes una copia de seguridad.
