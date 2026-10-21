# Flujos de RifaPlus

Cada proceso paso a paso, con el archivo y la función que lo hace. Las rutas están en `modulos/<m>/rutas.py`
y la lógica en `modulos/<m>/servicio.py`.

## 1. Registro e ingreso del organizador

| Paso | Qué pasa | Dónde |
|---|---|---|
| 1 | Llena el formulario de registro y acepta términos y tratamiento de datos. | `acceso/rutas.py → registro` |
| 2 | Se valida (correo, celular +57, aceptaciones). | `acceso/esquemas.py → RegistroOrganizador` |
| 3 | Se crea el organizador (estado *pendiente*) y su usuario con **clave temporal**; se guardan las aceptaciones. | `acceso/servicio.py → registrar_organizador` |
| 4 | Se envía la clave temporal (hoy: registro del servidor; en desarrollo se muestra en pantalla). | `acceso/notificaciones.py` |
| 5 | Ingresa: se verifica la clave, se aplica el bloqueo por intentos y se crea la sesión. | `acceso/servicio.py → ingresar` |
| 6 | Mientras no cambie la clave, todo lo lleva a "Cree su clave definitiva". | `acceso/dependencias.py → usuario_actual` |
| 7 | Cambia la clave: el organizador pasa a *activo* y se cierran sus otras sesiones. | `acceso/servicio.py → cambiar_clave` |

El superadministrador entra por el mismo "Ingresar" y lo envía a `/admin`.

**Correos** (`core/correo.py`, `acceso/notificaciones.py`): la clave temporal llega al correo del organizador; si
todavía no hay correo configurado en el `.env`, se muestra en pantalla para no dejarlo por fuera. «¿Olvidó su clave?»
envía un enlace de un solo uso que vence en una hora (`acceso/servicio.py → pedir_recuperacion, restablecer_con_token`).
El superadministrador puede restablecer la clave de un organizador desde su ficha (`restablecer_por_admin`) y recibe
avisos por correo de pagos por revisar y consultas de soporte nuevas (`correo.avisar_admin`).

## 2. Crear y publicar una rifa

| Paso | Qué pasa | Dónde |
|---|---|---|
| 1 | Las opciones de boletas (tarjetas) se calculan de la tabla `planes`. | `rifas/generador.py → opciones_disponibles` |
| 2 | Escoge opción, precio, forma de pago (cuotas), premios secos y reglas; firma la declaración. | `rifas/nueva.html`, `nueva-rifa.js` |
| 3 | Se valida todo, incluidas las cuotas (suman el precio, en orden, antes del sorteo). | `rifas/esquemas.py`, `rifas/cuotas.py → validar_plan` |
| 4 | En una sola transacción: rifa, premios, cuotas, **todas las boletas con sus números**, cobro del plan, declaración y auditoría. | `rifas/servicio.py → crear_rifa`, `rifas/generador.py → generar_boletas` |
| 5 | En borrador la revisa y la corrige cuantas veces quiera; no se le pide ningún pago. | `rifas/servicio.py → editar_borrador` |
| 6 | Toca **Publicar rifa**. Si el plan es gratis, queda *en venta* de inmediato. | `rifas/rutas.py → publicar` |
| 7 | Si es de pago, ve el valor y las cuentas de RifaPlus, y envía la referencia o el comprobante. La rifa queda "pago en revisión" y no se puede editar. | `rifas/rutas.py → pagar`, `pagos/servicio.py → enviar_pago_rifa` |
| 8 | El superadministrador aprueba (la rifa queda *en venta* sola) o rechaza con motivo (el organizador puede reenviar). | `admin/servicio.py → revisar_cobro` |

**Fotos y vista previa:** el premio mayor y cada premio seco pueden llevar una foto (JPG, PNG o WEBP). Se guardan en
`uploads/fotos/<organizador>/` y se ven en la boleta por `/archivos/fotos/…` (`publico/rutas.py → foto_publica`, que nunca
entrega comprobantes). Mientras llena el formulario, el organizador ve la boleta tal como quedará
(`componentes/boleta_vista_previa.html` + `nueva-rifa.js → actualizarPrevia`). Con foto, la boleta la muestra y el enlace
de WhatsApp la usa como imagen de vista previa; sin foto, la boleta queda solo con texto.

**Editar la rifa** (`rifas/servicio.py → editar_borrador, editar_en_venta`):

- En **borrador** se cambia todo con el mismo formulario de creación. Si cambia la opción de boletas, se borran y se
  generan de nuevo; si cambia de plan, el cobro se recalcula. Si el plan de pago ya fue aprobado, no se puede pasar a
  otro plan.
- En **venta** solo se corrige lo que no perjudica a quien ya compró: nombre, descripción, descripción y valor de los
  premios que no han jugado, y premios secos nuevos. Fecha, lotería, precio, cuotas, reglas y boletas no cambian.

**Reparto de números:** con 1 número por boleta, la boleta es su número (la 07 juega el 07). Con varios, se
mezclan al azar con `secrets` y se reparten sin repetir. En ambos casos se usan todos los números posibles,
así que siempre hay una boleta con el número ganador.

## 3. Vender una boleta y registrar pagos

| Paso | Qué pasa | Dónde |
|---|---|---|
| 1 | Toca una boleta disponible. Al escribir la cédula, si el comprador ya existe, se llenan sus datos. | `ventas/boleta.html`, `vender.js`, `ventas/rutas.py → buscar_comprador` |
| 2 | Cada campo se valida al salir de él; no deja enviar si algo está mal. | `estaticos/js/formularios.js` |
| 3 | Se bloquea la boleta, se crea o actualiza el comprador, la boleta queda *vendida* y se registra el pago inicial. | `ventas/servicio.py → vender` |
| 4 | Los abonos siguientes no pueden pasar de lo que falta ni repetir referencia. | `ventas/servicio.py → registrar_pago` |
| 5 | El saldo y el plan de cuotas (pagadas, próxima, vencidas) se calculan de los pagos. | `ventas/servicio.py → saldo`, `rifas/cuotas.py → estado_plan` |
| 6 | Botón de WhatsApp con el mensaje listo (números, lotería, fecha, saldo, próxima cuota). | `ventas/servicio.py → enlace_whatsapp` |

El organizador acredita sus propios pagos: quedan aprobados de inmediato.

## 3a. Vigencia, renovación y bloqueo

| Paso | Qué pasa | Dónde |
|---|---|---|
| 1 | Al crear la rifa, el organizador escoge la duración (6 meses, 1 año…) y ve el precio de ese tipo de rifa por esa duración. | `rifas/nueva.html`, `rifas/vigencia.py → precio` |
| 2 | Al publicarse (gratis o al aprobar el pago), queda vigente desde ese día por esos meses. | `vigencia.iniciar` |
| 3 | 15 y 3 días antes, el día que vence y al bloquearse, se le avisa en el panel y por correo (comando diario). | `vigencia.avisos_del_dia`, `python -m app.cli avisar-vencimientos` |
| 4 | Si vence sin renovar, la rifa queda **bloqueada** para el organizador: no vende, no registra pagos ni resultados, no imprime ni edita. Los compradores sí pueden verificar sus boletas. | `vigencia.exigir_vigente` |
| 5 | Renueva escogiendo duración y enviando el pago; el superadmin aprueba y la vigencia se extiende (desde el vencimiento, o desde hoy si ya venció). Si el precio es $0, se renueva sola. | `vigencia.solicitar_renovacion, revisar_renovacion` |

El superadministrador maneja los precios en una tabla de **tipos de rifa × duraciones**, y puede crear tipos de rifa
nuevos (boletas × cifras por boleta = 10, 100, 1.000 o 10.000) y duraciones nuevas (`admin/catalogos.py`).

## 3b. Boleta individual

| Qué | Dónde |
|---|---|
| Versión completa para imprimir o guardar en PDF (con documento y celular del comprador) | `ventas/rutas.py → imprimir_boleta` |
| Versión pública que recibe el comprador por WhatsApp (solo nombre e inicial del apellido) | `publico/rutas.py → boleta_publica` |
| Datos y código QR (apunta a `/boleta/{código}`) | `ventas/boleta_individual.py → armar` |
| Diseño (pantalla, celular e impresión en hoja carta) | `plantillas/boletas/boleta.html`, `estaticos/css/boleta.css` |
| Enviar por correo (abre el correo del organizador con todo escrito) | `ventas/servicio.py → enlace_correo` |
| Vista previa del enlace en WhatsApp (título, premio y logo) | etiquetas `og:` en `plantillas/base.html`; imagen `rifaplus-vista-previa.png` |

## 3c. Vendedores: efectivo, entregas y comisión

- **Efectivo por entregar:** los pagos en efectivo de las boletas de un vendedor los cobra él; lo demás (Bre-B, Nequi,
  Daviplata, transferencia) llega a la cuenta del organizador. Las entregas que registra el organizador lo bajan a cero.
  `ventas/servicio.py → efectivo_del_vendedor, registrar_entrega`

## 3c-bis. Liquidación de comisiones

1. Al vender, se escoge el vendedor de la boleta.
2. La comisión ganada = lo recaudado (pagos aprobados) en sus boletas × su porcentaje actual. `ventas/servicio.py → liquidacion`
3. El organizador registra pagos de comisión; no puede pagar más de lo que se debe. `ventas/servicio.py → pagar_comision`
4. Cuando el saldo llega a cero, el vendedor queda **a paz y salvo**.

## 3d. Informes

Filtros por comprador (cédula o nombre), vendedor, ciudad, rifa y estado de pago (pagadas, deben, atrasadas), con
totales de recaudado y por cobrar, y descarga para Excel. `informes/servicio.py → generar, a_csv`

## 4. Sorteos

| Paso | Qué pasa | Dónde |
|---|---|---|
| 1 | Escribe el número completo que cayó en la lotería del premio. | `rifas/detalle.html` (sección Premios y sorteos) |
| 2 | Se toman las últimas cifras y se busca qué boleta tiene ese número. | `sorteos/servicio.py → registrar`, `rifas/generador.py → numero_jugado` |
| 3 | Se aplican las reglas que escogió el organizador. | `sorteos/servicio.py → _decidir` |
| 4 | Si es el premio mayor, la rifa queda *sorteada*. | `sorteos/servicio.py → registrar` |
| 5 | Avisar al ganador por WhatsApp, marcar el premio entregado o corregir el resultado. | `sorteos/servicio.py → whatsapp_ganador, marcar_entregado, borrar` |

**Decisión (función `_decidir`):**

- Número no vendido → premio seco: desierto o acumulado (según la regla); premio mayor: desierto.
- Premio mayor → si la boleta está pagada completa, *con ganador*; si no, según la regla: *debe pagar el saldo* o *desierto*.
- Premio seco → si la boleta estaba **al día** (pagadas las cuotas vencidas hasta ese día, en hora de
  Colombia), *con ganador*; si no, según la regla: *desierto* o *acumulado* para el siguiente premio seco.

## 4b. Chat de soporte

| Paso | Qué pasa | Dónde |
|---|---|---|
| 1 | El organizador abre «💬 Ayuda» en su panel y toca una pregunta frecuente o escribe. | `estaticos/js/soporte.js`, `panel/base_panel.html` |
| 2 | Si la duda coincide con una pregunta frecuente, responde el asistente. | `soporte/preguntas.py → buscar`, `soporte/servicio.py → escribir` |
| 3 | Si no, o si toca «Hablar con una persona», la conversación queda **por responder**. | `soporte/servicio.py → escribir` |
| 4 | Usted responde desde `/admin/soporte`; el organizador lo ve en su chat (revisa cada 15 segundos). | `soporte/servicio.py → responder` |

Para cambiar o agregar respuestas automáticas, edite la lista `PREGUNTAS` en `app/modulos/soporte/preguntas.py`.

## 4c. Verificación de identidad y equipo

- **Registro:** el tipo y número de documento son obligatorios, y solo hay una cuenta por documento.
- **Verificación:** el superadministrador compara el nombre con el número de documento y toca «Marcar como
  verificado» en la ficha del organizador. Sin verificar, el organizador puede publicar **una** rifa; al intentar
  publicar o pagar la segunda, RifaPlus lo detiene y le avisa por correo al superadministrador.
  `rifas/servicio.py → falta_verificacion, exigir_verificacion`, `admin/servicio.py → cambiar_verificacion`
- **Equipo:** el organizador (rol `admin`) agrega colaboradores (rol `colaborador`) con nombre y correo; les llega una
  clave temporal. Trabajan sobre las rifas del organizador; no manejan el equipo ni eliminan rifas. Quitarles el acceso
  cierra sus sesiones. `equipo/servicio.py`
- **Cuentas de la rifa:** en el formulario y en la página de la rifa: recaudo si vende todo − premios − RifaPlus
  = ganancia esperada; y «así va hoy» con lo recaudado y las comisiones. `rifas/servicio.py → cuentas`
- **Duración sugerida:** el formulario calcula cuántos meses faltan para el sorteo, cuántas renovaciones necesita cada
  duración y marca con ★ la que sale más barata; el organizador decide. `nueva-rifa.js → costosPorDuracion`

## 5. Superadministrador

| Acción | Dónde |
|---|---|
| Resumen, lista y ficha de organizadores | `admin/servicio.py → resumen, organizadores, rifas_de` |
| Suspender o reactivar (el suspendido no puede ingresar; se cierran sus sesiones) | `admin/servicio.py → cambiar_estado` |
| Aprobar (publica la rifa) o rechazar los pagos de planes enviados por los organizadores | `admin/servicio.py → revisar_cobro` |
| Cuentas de RifaPlus donde pagan los organizadores (llave Bre-B, Nequi, Daviplata); el formulario de pago solo ofrece los medios de las cuentas activas | `admin/servicio.py → crear_cuenta`, `pagos/servicio.py → medios_para_rifaplus` |
| Base de datos en solo lectura: tablas, búsqueda, descarga y consultas SELECT con límite de tiempo | `admin/datos.py` |
| Precios de las rifas: un precio por cada uno de los 13 tipos (boletas que vende y cifras por boleta); aplican a las rifas nuevas | `admin/catalogos.py → guardar_precios` |
| Borrar los datos de prueba para empezar de cero (`python -m app.cli borrar-datos-prueba`) | `core/limpieza.py` |
| Loterías: agregar, renombrar, activar o desactivar | `admin/catalogos.py → guardar_loteria` |
| Cambiar el valor del cobro de una rifa (descuento o cortesía; con $0 queda aprobada) | `admin/catalogos.py → ajustar_cobro` |
| Restablecer la clave de un organizador y probar el correo | `admin/rutas.py → restablecer_clave, probar_correo` |
| Eliminar una rifa con todo lo suyo (escribiendo su nombre) | `admin/servicio.py → eliminar_rifa` |
| Eliminar un organizador sin rifas (escribiendo su correo) | `admin/servicio.py → eliminar_organizador` |

Toda acción queda en la tabla `auditoria`.
