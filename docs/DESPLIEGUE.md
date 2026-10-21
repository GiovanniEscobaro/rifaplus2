# Poner RifaPlus en un servidor

Guía paso a paso para un servidor **VPS con Ubuntu 24.04** (sirve cualquier proveedor: DigitalOcean, Hetzner,
Contabo, Vultr, AWS Lightsail…). Recomendado: **2 GB de RAM**, 1 o 2 CPU, 40 GB de disco.

Los archivos de apoyo están en la carpeta `despliegue/` del proyecto.

## 0. Antes de empezar

1. Compre el servidor y anote su **IP** y la clave de `root`.
2. Compre el dominio (por ejemplo `rifaplus.co`) y en su proveedor de dominio cree un **registro A** que apunte
   a la IP del servidor. Puede tardar unos minutos en propagarse.
3. Tenga a mano la contraseña de aplicación de Gmail (ver `.env.example`).

## 1. Preparar el servidor

Desde la terminal de su Mac:

```bash
ssh root@IP_DEL_SERVIDOR
```

Ya dentro del servidor:

```bash
apt update && apt upgrade -y
apt install -y python3-venv python3-pip postgresql nginx certbot python3-certbot-nginx rsync unzip
adduser --system --group --home /opt/rifaplus rifaplus
ufw allow OpenSSH && ufw allow "Nginx Full" && ufw --force enable
```

## 2. Base de datos

Genere una clave fuerte y guárdela (`python3 -c "import secrets; print(secrets.token_urlsafe(24))"`):

```bash
sudo -u postgres psql -c "CREATE USER rifaplus_app WITH PASSWORD 'LA_CLAVE_GENERADA';"
sudo -u postgres psql -c "CREATE DATABASE rifaplus OWNER rifaplus_app;"
```

PostgreSQL queda escuchando solo dentro del servidor; no se abre a internet.

## 3. Subir RifaPlus

Desde su Mac (otra terminal):

```bash
scp ~/Downloads/rifaplus.zip root@IP_DEL_SERVIDOR:/tmp/
```

En el servidor:

```bash
cd /tmp && unzip -o rifaplus.zip
rsync -a /tmp/rifaplus/ /opt/rifaplus/
cd /opt/rifaplus
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
```

En el `.env` de producción cambie como mínimo:

```
APP_ENTORNO=produccion
APP_URL=https://SU_DOMINIO
CLAVE_SECRETA=(genere una nueva y larga)
DATABASE_URL=postgresql+psycopg://rifaplus_app:LA_CLAVE_GENERADA@localhost:5432/rifaplus
SMTP_USUARIO=su_correo@gmail.com
SMTP_CLAVE=(la contraseña de aplicación de Gmail)
CORREO_AVISOS_ADMIN=su_correo@gmail.com
RESPONSABLE_NOMBRE=Su nombre completo
RESPONSABLE_DOCUMENTO=CC 0000000000
RESPONSABLE_CIUDAD=Su ciudad
CORREO_CONTACTO=su_correo@gmail.com
```

Borre las líneas de `DATABASE_URL_PRUEBAS` y `POSTGRES_*`, que no se usan en el servidor.

Luego cree las tablas, los datos iniciales y su usuario:

```bash
chown -R rifaplus:rifaplus /opt/rifaplus
chmod 600 /opt/rifaplus/.env
sudo -u rifaplus bash -c "cd /opt/rifaplus && .venv/bin/alembic upgrade head && .venv/bin/python -m app.cli semillas"
sudo -u rifaplus bash -c "cd /opt/rifaplus && .venv/bin/python -m app.cli crear-superadmin"
```

## 4. Dejarlo corriendo siempre (systemd)

```bash
cp /opt/rifaplus/despliegue/rifaplus.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now rifaplus
systemctl status rifaplus          # debe decir "active (running)"
curl http://127.0.0.1:8001/salud   # debe responder {"estado":"ok"}
```

## 5. Nginx y HTTPS

```bash
cp /opt/rifaplus/despliegue/nginx-rifaplus.conf /etc/nginx/sites-available/rifaplus
nano /etc/nginx/sites-available/rifaplus      # cambie SU_DOMINIO por su dominio
ln -s /etc/nginx/sites-available/rifaplus /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
certbot --nginx -d SU_DOMINIO                  # pone el candado (HTTPS) y lo renueva solo
```

Abra `https://SU_DOMINIO`: debe ver la página de RifaPlus con el candado.

## 6. Copias de seguridad

```bash
mkdir -p /opt/respaldos/rifaplus && chown rifaplus:rifaplus /opt/respaldos/rifaplus
sudo -u rifaplus /opt/rifaplus/despliegue/respaldo.sh      # probarlo una vez
sudo -u rifaplus crontab -e
```

En el crontab agregue esta línea (respaldo diario a las 2:30 a. m.; guarda 14 días):

```
30 2 * * * /opt/rifaplus/despliegue/respaldo.sh >> /opt/respaldos/rifaplus/respaldo.log 2>&1
0 8 * * * cd /opt/rifaplus && .venv/bin/python -m app.cli avisar-vencimientos >> /opt/respaldos/rifaplus/avisos.log 2>&1
```

La segunda línea envía cada mañana los correos de **vencimiento de rifas** (15 y 3 días antes, el día que vencen y
cuando quedan bloqueadas).

**Importante:** guarde también una copia **fuera del servidor**, por ejemplo una vez por semana desde su Mac:

```bash
scp root@IP_DEL_SERVIDOR:/opt/respaldos/rifaplus/*  ~/Respaldos/RifaPlus/
```

Para restaurar: `pg_restore --clean --dbname=URL_DE_LA_BASE bd_FECHA.dump` y descomprimir `uploads_FECHA.tar.gz`
en `/opt/rifaplus`.

## 7. Revisión final

1. Entre como superadministrador y registre su **llave Bre-B** en "Cuentas de RifaPlus".
2. Regístrese como organizador con otro correo: la clave temporal debe llegarle **al correo**.
3. Pruebe "¿Olvidó su clave?".
4. Cree una rifa gratis, véndale una boleta y ábrala desde el celular con el QR.
5. Revise los términos en `/terminos`: no debe aparecer ningún "[por completar]".

## Actualizar a una versión nueva

Suba el zip nuevo a `/tmp`, descomprímalo y ejecute:

```bash
cd /tmp && unzip -o rifaplus.zip
/opt/rifaplus/despliegue/actualizar.sh
```

El script hace primero una copia de seguridad, actualiza el código sin tocar su `.env` ni `uploads/`, aplica las
migraciones y reinicia RifaPlus.

## Si algo falla

| Síntoma | Qué revisar |
|---|---|
| La página no carga | `systemctl status rifaplus` y `journalctl -u rifaplus -n 50` |
| Error 502 de Nginx | RifaPlus está caído: `systemctl restart rifaplus` |
| No llegan correos | `journalctl -u rifaplus | grep correo`; revise `SMTP_USUARIO` y la contraseña de aplicación |
| No puede ingresar (la sesión no se guarda) | `APP_URL` debe empezar por `https://` y el sitio debe tener el candado |
