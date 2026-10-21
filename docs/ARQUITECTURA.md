# Arquitectura de RifaPlus

## Vocabulario de RifaPlus

- **Boletas que vende:** cuántas boletas tiene la rifa (5, 10, 25 … 10.000).
- **Cifras por boleta:** cuántos números trae cada boleta (en el código: `series_por_boleta` / `numeros_por_boleta`).
- **Números del sorteo:** todos los números que se reparten: del 0 al 9, del 00 al 99, del 000 al 999 o del 0000 al 9999
  (en el código, `cifras` es la cantidad de dígitos de esos números y `total_numeros` cuántos son).
- **Boletas que vende × cifras por boleta = números del sorteo.** Así siempre hay ganador.

## En una frase

Aplicación web en **Python con FastAPI**, que guarda todo en **PostgreSQL** mediante **SQLAlchemy**, arma las
páginas con plantillas **Jinja2** en el servidor y usa un poco de JavaScript solo para ayudar en los formularios.

## Organización por módulos de negocio

El código no se agrupa por tipo de archivo ("todos los modelos juntos"), sino por tema. Cada tema es un módulo
dentro de `app/modulos/`:

| Módulo | Responsabilidad |
|---|---|
| `acceso` | Registro de organizadores, ingreso, sesiones, cambio de clave, bloqueo por intentos. |
| `legal` | Términos, tratamiento de datos y registro de lo que acepta cada organizador. |
| `rifas` | Crear rifas, opciones de boletas, reparto de números, plan de cuotas, publicar, eliminar. |
| `ventas` | Vender boletas, compradores, abonos, comprobantes, vendedores y su liquidación, boleta individual, WhatsApp. |
| `sorteos` | Registrar el resultado de la lotería, encontrar al ganador, premios secos y entregas. |
| `equipo` | Colaboradores del organizador: agregar, quitar acceso. |
| `soporte` | Chat de ayuda del panel: asistente con preguntas frecuentes y bandeja del superadministrador. |
| `informes` | Informes de boletas vendidas por comprador, vendedor, ciudad, rifa y estado; descarga para Excel. |
| `pagos` | Medios de pago, planes de RifaPlus, cobros por rifa. |
| `personas` | Modelos de compradores (clientes) y vendedores. |
| `admin` | Zona del superadministrador (`/admin`). |
| `panel` | Página de inicio del organizador. |
| `publico` | Página de inicio pública y verificación de boletas. |
| `auditoria` | Registro de quién cambió qué. |
| `mensajes` | Cola de WhatsApp (preparada para el envío automático). |

## Las capas de cada módulo

Cada módulo repite la misma estructura. Así, sabiendo dónde está algo en un módulo, sabe dónde está en todos.

```
modulos/ventas/
├── modelos.py     # QUÉ se guarda: tablas de la base de datos (SQLAlchemy)
├── esquemas.py    # QUÉ se acepta: validación de lo que llega de los formularios (Pydantic)
├── servicio.py    # QUÉ se hace: las reglas de negocio (el corazón del módulo)
└── rutas.py       # CÓMO se pide: direcciones web; reciben la petición y muestran la página
```

**La regla más importante:** las rutas no tienen lógica de negocio. Una ruta lee el formulario, llama a una
función del servicio y muestra el resultado. Si mañana hay una app de celular, se reutilizan los servicios
sin tocar nada.

Dirección de las dependencias (quién puede importar a quién):

```
rutas.py  ──►  servicio.py  ──►  modelos.py
   │               │
   └──► esquemas.py ◄┘
```

Un servicio nunca importa rutas ni plantillas.

## Recorrido de una petición

Ejemplo: el organizador registra un abono de $10.000.

1. El navegador envía el formulario a `POST /panel/rifas/7/boletas/15/pagos`.
2. FastAPI busca la ruta en `modulos/ventas/rutas.py` → función `registrar_pago`.
3. Antes de entrar, se resuelven las **dependencias**:
   - `obtener_db` (`core/database.py`) abre una conexión a la base de datos.
   - `organizador_actual` (`modulos/acceso/dependencias.py`) lee la cookie, busca la sesión y exige que sea un
     organizador con su clave ya cambiada. Si no, redirige al ingreso.
4. La ruta convierte el formulario en un esquema validado (`DatosPago`); los puntos de miles ya se quitaron.
5. Llama a `servicio.registrar_pago`, que bloquea la boleta, verifica que el valor no supere lo que falta,
   crea el pago, registra la auditoría y hace `commit`.
6. Si una regla falla, el servicio lanza `ErrorNegocio("mensaje claro")`; la ruta lo atrapa y vuelve a mostrar
   la página con el mensaje en rojo.
7. Si todo sale bien, la ruta redirige (303) a la página de la boleta, que muestra el pago nuevo.

## Piezas compartidas (`app/core/`)

| Archivo | Qué hace |
|---|---|
| `config.py` | Lee el `.env` (conexión a la base, entorno, tiempos de sesión). |
| `database.py` | Conexión a PostgreSQL, clase `Base` de los modelos y tipos comunes (`pk`, `creado`). |
| `seguridad.py` | Cifrado de claves (bcrypt), tokens aleatorios, códigos de verificación. |
| `excepciones.py` | `ErrorNegocio` (regla incumplida, con mensaje para el usuario) y `Redirigir`. |
| `plantillas.py` | Jinja2 y los filtros `pesos`, `miles`, `fecha_larga`. |
| `registro_modelos.py` | Importa todos los modelos para que SQLAlchemy y Alembic los conozcan. |
| `semillas.py` | Datos iniciales: loterías, medios de pago, planes. |

## La parte web (`app/web/`)

- `plantillas/base.html`: estructura común de todas las páginas.
- `plantillas/componentes/`: piezas reutilizables (cabecera y pie públicos).
- Una carpeta de plantillas por módulo (`acceso/`, `rifas/`, `ventas/`, `admin/`…). Cada plantilla empieza
  con un comentario `{# … #}` que dice qué muestra y qué ruta la usa.
- `estaticos/css/rifaplus.css`: un solo archivo de estilos, dividido en secciones comentadas.
- `estaticos/js/`: JavaScript pequeño y sin librerías. `formularios.js` (puntos de miles y validación
  inmediata) y `ver-clave.js` (el ojito) se cargan en todas las páginas.

## Convenciones

- **Todo en español**: nombres de tablas, columnas, funciones, variables y mensajes.
- **Dinero** en pesos enteros (`NUMERIC(12,0)`), sin centavos.
- **Fechas y horas** con zona horaria (`TIMESTAMPTZ`), guardadas en UTC; los cortes por día se hacen en hora
  de Colombia (`America/Bogota`).
- **Las reglas importantes viven también en la base de datos** (restricciones `CHECK`, `UNIQUE`, llaves
  foráneas): aunque alguien se salte la aplicación, PostgreSQL no deja guardar datos inválidos.
- **Nada con historia se borra** desde la aplicación del organizador (`ON DELETE RESTRICT`); el
  superadministrador puede borrar con confirmación y queda en la auditoría.
- **Cambios en la base de datos solo con Alembic** (`migraciones/`), nunca a mano.

## Seguridad, en resumen

- Claves cifradas con bcrypt; nadie puede verlas, ni el superadministrador.
- Sesiones en la base de datos con cookie `HttpOnly` y `SameSite=Lax`; al cambiar la clave se cierran las demás.
- Bloqueo tras 5 intentos fallidos e historial de ingresos.
- Cada organizador solo ve lo suyo: todas las consultas filtran por su `organizador_id`.
- Comprobantes fuera de la carpeta pública; solo los entrega una ruta que verifica al dueño.
- Al vender, la boleta se bloquea (`SELECT … FOR UPDATE`) para que dos personas no la vendan al mismo tiempo.

## Cómo agregar un módulo nuevo

1. Cree `app/modulos/<nombre>/` con `__init__.py`, `modelos.py`, `esquemas.py`, `servicio.py` y `rutas.py`.
2. Si tiene modelos, impórtelos en `app/core/registro_modelos.py`.
3. Registre el `router` en `app/main.py`.
4. Cree la migración: `alembic revision --autogenerate -m "descripción"` y revísela antes de aplicarla.
5. Agregue sus pruebas en `tests/` y sus plantillas en `app/web/plantillas/<nombre>/`.
6. Documente cada función y regenere la referencia: `python -m herramientas.generar_referencia`.
