# RifaPlus

Plataforma de rifas de **GE Desarrollo e Infraestructura de Software**.
FastAPI · PostgreSQL · SQLAlchemy 2 · Alembic · Jinja2.

## Documentación

Toda la documentación está en [`docs/`](docs/README.md):

- **ARQUITECTURA.md**: cómo está organizado el código y sus convenciones (léalo primero).
- **FLUJOS.md**: cada proceso paso a paso y qué archivo lo hace.
- **BASE_DE_DATOS.md**: tablas, relaciones y reglas de PostgreSQL.
- **REFERENCIA.md**: generada del código con `python -m herramientas.generar_referencia`
  (todas las direcciones, tablas con columnas, archivos y funciones).

Cada archivo, clase y función tiene su docstring, y `ruff check .` no deja pasar código nuevo sin documentar.

## Arquitectura

El código está organizado **por módulos de negocio**. Cada módulo tiene sus propias capas,
así que todo lo de rifas está en `rifas/`, todo lo de acceso en `acceso/`, etc.

```
rifaplus/
├── app/
│   ├── main.py                    # crea la aplicación FastAPI y registra los módulos
│   ├── cli.py                     # comandos de administración (semillas, superadmin)
│   ├── core/                      # infraestructura compartida
│   │   ├── config.py              #   configuración desde .env
│   │   ├── database.py            #   conexión, Base y tipos de columna
│   │   ├── seguridad.py           #   claves, tokens, códigos de verificación
│   │   ├── excepciones.py         #   ErrorNegocio, Redirigir
│   │   ├── plantillas.py          #   Jinja2 y filtros ($ pesos, fechas en español)
│   │   ├── registro_modelos.py    #   registra todos los modelos (SQLAlchemy y Alembic)
│   │   └── semillas.py            #   datos iniciales: loterías, medios de pago, planes
│   ├── modulos/
│   │   ├── acceso/                # registro, ingreso, sesiones, cambio de clave
│   │   │   ├── modelos.py         #   tablas
│   │   │   ├── esquemas.py        #   validación de entrada (Pydantic)
│   │   │   ├── servicio.py        #   reglas de negocio (casos de uso)
│   │   │   ├── dependencias.py    #   usuario actual, permisos
│   │   │   └── rutas.py           #   endpoints (solo HTTP, sin lógica)
│   │   ├── rifas/                 # rifas, boletas, números, resultados
│   │   │   └── generador.py       #   reparto de números y búsqueda del ganador
│   │   ├── pagos/                 # medios de pago, planes, cobros, pagos
│   │   ├── personas/              # clientes y vendedores
│   │   ├── mensajes/              # cola de WhatsApp
│   │   ├── auditoria/             # registro de cambios
│   │   ├── legal/                 # términos, tratamiento de datos y aceptaciones registradas
│   │   ├── ventas/                # venta de boletas, abonos, comprobantes, vendedores, WhatsApp
│   │   ├── admin/                 # zona del superadministrador (/admin)
│   │   ├── sorteos/               # resultados de la lotería, ganadores, premios secos y entregas
│   │   ├── publico/               # página de inicio y verificación de boletas
│   │   └── panel/                 # panel del organizador y del superadmin
│   └── web/
│       ├── plantillas/            # HTML (base, componentes, una carpeta por módulo)
│       └── estaticos/             # css/, js/, img/ (logos)
├── migraciones/                   # Alembic: historial de cambios de la base de datos
├── tests/                         # pruebas automáticas (pytest)
├── docs/                          # documentación, modelo entidad-relación y logos
├── herramientas/                  # generador de la referencia del código
├── despliegue/                    # archivos para el servidor (systemd, Nginx, respaldos, actualizar)
├── alembic.ini
├── pyproject.toml                 # configuración de pytest y ruff
├── requirements.txt / requirements-dev.txt
├── Dockerfile / docker-compose.yml
└── .env.example
```

**Regla de las capas:** las rutas solo reciben la petición y muestran la respuesta; las reglas
viven en `servicio.py`; los modelos solo describen tablas. Un servicio nunca importa rutas.

## Puesta en marcha (Windows)

```powershell
# 1. Entorno e instalación
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt

# 2. Configuración: copie .env.example como .env y ajuste DATABASE_URL

# 3. Base de datos (cree antes la base "rifaplus" en PostgreSQL)
alembic upgrade head
python -m app.cli semillas
python -m app.cli crear-superadmin

# 4. Arrancar
uvicorn app.main:app --reload
```

Abra http://localhost:8000

En Linux o Mac cambie solo la activación: `source .venv/bin/activate`.

### Con Docker (sin instalar PostgreSQL)

```bash
cp .env.example .env
docker compose up --build
```

## Trabajo diario

| Tarea | Comando |
|---|---|
| Arrancar en desarrollo | `uvicorn app.main:app --reload` |
| Pruebas automáticas | `pytest` (requiere `DATABASE_URL_PRUEBAS` con una base aparte) |
| Revisar estilo del código | `ruff check .` y `ruff format .` |
| Cambié un modelo | `alembic revision --autogenerate -m "descripción"` y luego `alembic upgrade head` |
| Ver en qué versión está la base | `alembic current` |

## Cuotas, premios secos y sorteos

- Al crear la rifa, el organizador define el **plan de cuotas** (cuántas, valor y fecha límite de cada una);
  deben sumar el valor de la boleta y la última vence a más tardar el día del sorteo.
- Puede agregar **premios secos**, cada uno con su lotería y fecha. Solo gana una boleta **al día**: con
  las cuotas vencidas hasta esa fecha ya pagadas.
- El organizador escoge las **reglas**: si un premio seco cae en una boleta atrasada o sin vender, queda
  desierto o se acumula; si el premio mayor cae en una boleta sin pagar completa, gana debiendo el saldo
  o queda desierto.
- El día del sorteo registra el número completo de la lotería; RifaPlus toma las últimas cifras, encuentra
  la boleta, aplica las reglas, muestra al ganador con botón de WhatsApp y permite marcar el premio entregado.

## Superadministrador (/admin)

Zona aparte, solo para el rol superadmin (se crea con `python -m app.cli crear-superadmin`):
resumen de RifaPlus, lista y búsqueda de organizadores, suspender o reactivar (el suspendido no puede
ingresar), aprobar o rechazar los cobros de rifas de pago, y eliminar rifas u organizadores. Para
eliminar hay que escribir el nombre de la rifa o el correo del organizador; queda en la auditoría.

## Planes (pago único por rifa)

| Boletas | Números por boleta | Valor |
|---|---|---|
| Hasta 10 | 1 a 2 | Gratis |
| Hasta 25 | 4 | $6.000 |
| Hasta 100 | 1 a 2 | $19.900 |
| Hasta 500 | 1 a 4 | $59.900 |
| Hasta 1.000 | 1 a 8 | $89.900 |
| Hasta 2.500 | 4 a 8 | $149.900 |
| Hasta 10.000 | 1 a 2 | $299.900 |

Toda rifa usa todos los números de sus cifras (0–9, 00–99, 000–999 o 0000–9999), así que siempre
hay ganador. Las opciones que ve el organizador se calculan solas a partir de esta tabla: si cambia
un precio o agrega un plan en la tabla `planes`, el formulario se actualiza sin tocar código.

## Administramos rifas, no rifamos

- RifaPlus no recibe el dinero de los compradores ni hace sorteos.
- Al registrarse, el organizador acepta términos y tratamiento de datos; al crear cada rifa firma
  una declaración de responsabilidad. Todo queda en la tabla `aceptaciones` con versión, fecha e IP.
- RifaPlus no pide ni verifica el permiso de cada rifa: tramitarlo es responsabilidad del organizador, y así lo acepta en los términos y en la declaración.
- Los textos de `/terminos` y `/tratamiento-de-datos` tienen campos entre corchetes por completar
  y **deben ser revisados por un abogado antes del lanzamiento**.

## Estado

**Listo:** venta de boletas con datos completos del comprador, abonos acreditados por el organizador
(efectivo, Nequi, Daviplata, transferencia) con comprobante, saldos, filtro de deudores, vendedores,
aviso por WhatsApp con mensaje listo, planes por número de boletas con opciones en tarjetas, rifas de 1 a 4 cifras,
búsqueda y páginas de boletas, aceptaciones legales, página pública, registro con clave temporal, cambio de clave obligatorio, bloqueo por
intentos, sesiones, creación de rifas con generación de boletas, planes, publicación de rifas gratis,
verificación pública de boletas, panel del superadmin, 22 tablas con sus restricciones, zona de superadministrador, cuotas, premios secos y sorteos, informes, liquidación de vendedores, boleta individual con QR, envío por WhatsApp y correo, edición de rifas, pago del plan al publicar, fotos de premios y vista previa de la boleta, pago con llave Bre-B, chat de soporte, base de datos de solo lectura, correos (clave temporal, recuperar clave, avisos), entregas de vendedores, guía de despliegue, planes y loterías editables por el superadmin, 142 pruebas.

**Siguientes etapas:** que el organizador suba el comprobante del pago de su rifa · entregas de dinero de
vendedores · envío automático de WhatsApp.

**Decisiones pendientes:** envío de la clave temporal por WhatsApp (conexión con Guau) · revisión legal de
términos y del Decreto 1486 de 2024.
# rifaplus2
