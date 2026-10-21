# Referencia del código de RifaPlus

> Archivo generado con `python -m herramientas.generar_referencia`. No lo edite a mano:
> la descripción de cada función está en su docstring, dentro del código.

## Direcciones (rutas)

| Método | Dirección | Qué hace |
|---|---|---|
| GET | `/` | Página de inicio pública de RifaPlus, con los planes de la base de datos. |
| GET | `/admin` | Resumen general de RifaPlus para el superadministrador. |
| GET | `/admin/cobros` | Lista de cobros de rifas de pago que esperan revisión. |
| POST | `/admin/cobros/{cobro_id}` | Aprueba o rechaza el cobro del plan de una rifa. |
| GET | `/admin/cobros/{cobro_id}/comprobante` | Foto del comprobante que envió el organizador para pagar su plan. |
| GET | `/admin/cuentas` | Cuentas donde los organizadores pagan sus planes. |
| POST | `/admin/cuentas` | Agrega una cuenta de RifaPlus. |
| POST | `/admin/cuentas/{cuenta_id}` | Activa o desactiva una cuenta de RifaPlus. |
| GET | `/admin/datos` | Lista de tablas de la base de datos con su número de registros. |
| GET | `/admin/datos/consulta` | Formulario para escribir una consulta SQL de solo lectura. |
| POST | `/admin/datos/consulta` | Ejecuta la consulta en solo lectura y muestra el resultado (o lo descarga en CSV). |
| GET | `/admin/datos/{tabla}` | Registros de una tabla, por páginas y con búsqueda. |
| GET | `/admin/datos/{tabla}.csv` | Descarga la tabla completa (con el filtro de búsqueda, si lo hay) en CSV para Excel. |
| GET | `/admin/loterias` | Loterías disponibles para las rifas. |
| POST | `/admin/loterias` | Agrega una lotería o guarda los cambios de una existente. |
| POST | `/admin/loterias/{loteria_id}` | Agrega una lotería o guarda los cambios de una existente. |
| GET | `/admin/organizadores` | Lista de organizadores con búsqueda y filtro por estado. |
| GET | `/admin/organizadores/{organizador_id}` | Ficha de un organizador: contacto, rifas y acciones. |
| POST | `/admin/organizadores/{organizador_id}/eliminar` | Elimina un organizador sin rifas, después de confirmar su correo. |
| POST | `/admin/organizadores/{organizador_id}/estado` | Suspende o reactiva a un organizador. |
| POST | `/admin/organizadores/{organizador_id}/restablecer-clave` | Le pone una clave temporal nueva al organizador, se la envía al correo y se la muestra al superadmin una vez. |
| POST | `/admin/organizadores/{organizador_id}/verificacion` | Verifica o quita la verificación de identidad del organizador. |
| GET | `/admin/planes` | Precios de cada tipo de rifa por cada duración. |
| POST | `/admin/planes` | Guarda de una vez la tabla de precios (tipo × duración) y qué tipos se ofrecen. |
| POST | `/admin/planes/crear-tipos` | Crea los tipos de rifa iniciales que falten, con su precio inicial (no cambia los que ya existen). |
| POST | `/admin/planes/duracion` | Crea o cambia una duración (por ejemplo «6 meses» o «1 año»). |
| POST | `/admin/planes/duracion/{duracion_id}` | Crea o cambia una duración (por ejemplo «6 meses» o «1 año»). |
| POST | `/admin/planes/tipo` | Agrega un tipo de rifa nuevo (queda inactivo y con precios en 0 para que usted los ponga). |
| POST | `/admin/probar-correo` | Envía un correo de prueba y muestra qué pasó, para revisar la configuración de Gmail. |
| POST | `/admin/renovaciones/{renovacion_id}` | Aprueba (extiende la vigencia y desbloquea) o rechaza una renovación. |
| POST | `/admin/rifas/{rifa_id}/cobro` | Cambia el valor que paga una rifa (descuento o cortesía). |
| POST | `/admin/rifas/{rifa_id}/eliminar` | Elimina una rifa con todo lo suyo, después de confirmar su nombre. |
| GET | `/admin/soporte` | Bandeja de conversaciones de soporte del superadministrador. |
| GET | `/admin/soporte/{conversacion_id}` | Una conversación con su historial y el formulario para responder. |
| POST | `/admin/soporte/{conversacion_id}` | Responde al organizador, o marca la consulta como atendida sin escribir. |
| GET | `/archivos/{ruta}` | Fotos de premios (públicas, se ven en la boleta). Solo sirve la carpeta fotos/, nunca comprobantes. |
| GET | `/boleta/{codigo}` | Boleta individual que recibe el comprador por WhatsApp (sin su documento ni celular). |
| GET | `/cambiar-clave` | Muestra el formulario para crear o cambiar la clave. |
| POST | `/cambiar-clave` | Guarda la clave nueva. En el primer ingreso, activa al organizador. |
| GET | `/ingresar` | Muestra el formulario de ingreso. |
| POST | `/ingresar` | Valida correo y clave, crea la sesión (cookie) y envía al panel, al admin o a cambiar la clave. |
| GET | `/panel` | Panel del organizador con sus rifas. El superadmin se envía a /admin. |
| GET | `/panel/compradores` | La antigua página de compradores ahora es parte de Informes. |
| GET | `/panel/compradores/buscar` | Para el formulario de venta: si el comprador ya existe, devuelve sus datos para no escribirlos de nuevo. |
| GET | `/panel/comprobantes/{pago_id}` | Entrega la foto del comprobante solo al organizador dueño de la rifa. |
| GET | `/panel/equipo` | Equipo del organizador. |
| POST | `/panel/equipo` | Agrega un colaborador; le llega la clave temporal al correo y el organizador también la ve una vez. |
| POST | `/panel/equipo/{colaborador_id}` | Activa o desactiva a un colaborador. |
| GET | `/panel/informes` | Informe de boletas vendidas con filtros por rifa, vendedor, ciudad, comprador y estado de pago. |
| GET | `/panel/informes.csv` | Descarga el mismo informe en CSV para abrirlo en Excel. |
| GET | `/panel/rifas/nueva` | Formulario vacío para crear una rifa. |
| POST | `/panel/rifas/nueva` | Recibe el formulario, crea la rifa con todas sus boletas y lleva a su página. |
| GET | `/panel/rifas/{rifa_id}` | Página de la rifa: cifras de venta, sorteos, boletas con búsqueda, filtros y páginas. |
| GET | `/panel/rifas/{rifa_id}/boletas/{boleta_id}` | Página de una boleta. |
| GET | `/panel/rifas/{rifa_id}/boletas/{boleta_id}/imprimir` | Boleta individual con los datos completos del comprador, lista para imprimir o guardar en PDF. |
| POST | `/panel/rifas/{rifa_id}/boletas/{boleta_id}/liberar` | Deshace la venta de una boleta sin pagos. |
| POST | `/panel/rifas/{rifa_id}/boletas/{boleta_id}/pagos` | Registra un abono o el pago completo de una boleta vendida. |
| POST | `/panel/rifas/{rifa_id}/boletas/{boleta_id}/vender` | Vende la boleta: guarda o actualiza el comprador y registra el pago inicial si lo hay. |
| GET | `/panel/rifas/{rifa_id}/editar` | Formulario para corregir la rifa: completo en borrador, limitado en venta. |
| POST | `/panel/rifas/{rifa_id}/editar` | Guarda las correcciones de la rifa según su estado. |
| POST | `/panel/rifas/{rifa_id}/eliminar` | Elimina una rifa del organizador que no tiene ventas ni pagos. |
| GET | `/panel/rifas/{rifa_id}/pagar` | Valor del plan, cuentas de RifaPlus y formulario para informar el pago. |
| POST | `/panel/rifas/{rifa_id}/pagar` | Recibe la referencia y el comprobante del pago del plan; la rifa queda esperando la aprobación. |
| POST | `/panel/rifas/{rifa_id}/premios/{premio_id}/entregado` | Marca el premio como entregado al ganador. |
| POST | `/panel/rifas/{rifa_id}/premios/{premio_id}/resultado` | Registra el número que cayó en la lotería para un premio. |
| POST | `/panel/rifas/{rifa_id}/premios/{premio_id}/resultado/borrar` | Borra un resultado mal digitado para registrarlo de nuevo. |
| POST | `/panel/rifas/{rifa_id}/publicar` | Publica la rifa. Si su plan es de pago y aún no está aprobado, lleva a la pantalla para pagarlo. |
| GET | `/panel/rifas/{rifa_id}/renovar` | Pantalla de renovación de una rifa publicada. |
| POST | `/panel/rifas/{rifa_id}/renovar` | Recibe el pago de la renovación; si es gratis se aplica de una vez, si no queda en revisión. |
| GET | `/panel/soporte` | Mensajes del chat del organizador (lo consulta el chat del panel cada pocos segundos). |
| POST | `/panel/soporte` | Recibe un mensaje, una pregunta frecuente o la petición de hablar con una persona. |
| GET | `/panel/vendedores` | Lista de vendedores con lo que ha vendido y cobrado cada uno. |
| POST | `/panel/vendedores` | Agrega un vendedor nuevo. |
| GET | `/panel/vendedores/{vendedor_id}` | Liquidación de un vendedor. |
| POST | `/panel/vendedores/{vendedor_id}` | Cambia el porcentaje de comisión o activa / desactiva al vendedor. |
| POST | `/panel/vendedores/{vendedor_id}/entregas` | Registra el dinero en efectivo que el vendedor le entregó al organizador. |
| POST | `/panel/vendedores/{vendedor_id}/pagos` | Registra un pago de comisión al vendedor. |
| GET | `/recuperar-clave` | Formulario para pedir el enlace de cambio de clave. |
| POST | `/recuperar-clave` | Envía el enlace si existe la cuenta. Siempre muestra el mismo mensaje (no revela quién tiene cuenta). |
| GET | `/registro` | Muestra el formulario de registro vacío. |
| POST | `/registro` | Recibe el registro, crea organizador y usuario con clave temporal, y muestra la confirmación. |
| GET | `/restablecer-clave/{token}` | Formulario para crear la clave nueva desde el enlace del correo. |
| POST | `/restablecer-clave/{token}` | Guarda la clave nueva y lleva al ingreso. |
| POST | `/salir` | Cierra la sesión actual y borra la cookie. |
| GET | `/terminos` | Página pública de términos y condiciones. |
| GET | `/tratamiento-de-datos` | Página pública de la política de tratamiento de datos personales. |
| GET | `/verificar` | Página para escribir el código de una boleta y verificarla. |
| GET | `/verificar/{codigo}` | Muestra si una boleta es auténtica, su estado de pago y si ganó algún premio. |

## Tablas de la base de datos

### `aceptaciones`

Constancia de que un usuario aceptó un documento legal: cuál, qué versión, cuándo y desde qué IP.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `usuario_id` | BIGINT | sí | → `usuarios.id` |
| `organizador_id` | BIGINT | no | → `organizadores.id` |
| `rifa_id` | BIGINT | no | → `rifas.id` |
| `documento` | VARCHAR(30) | sí |  |
| `version` | VARCHAR(20) | sí |  |
| `texto_aceptado` | VARCHAR(600) | no |  |
| `ip` | VARCHAR(45) | no |  |
| `fecha` | DATETIME | sí |  |
| _regla_ | `ck_aceptaciones_documento` | | `documento IN ('terminos', 'tratamiento_datos', 'declaracion_rifa')` |

### `auditoria`

Registro de cambios importantes: quién, qué tabla y registro, qué acción, antes y después.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `usuario_id` | BIGINT | no | → `usuarios.id` |
| `organizador_id` | BIGINT | no | → `organizadores.id` |
| `tabla` | VARCHAR(50) | sí |  |
| `registro_id` | BIGINT | sí |  |
| `accion` | VARCHAR(20) | sí |  |
| `valor_anterior` | JSONB | no |  |
| `valor_nuevo` | JSONB | no |  |
| `ip` | VARCHAR(45) | no |  |
| `fecha` | DATETIME | sí |  |

### `boletas`

Boleta de una rifa: consecutivo, código de verificación, comprador, vendedor y estado.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `rifa_id` | BIGINT | sí | → `rifas.id` |
| `consecutivo` | INTEGER | sí |  |
| `codigo_verificacion` | VARCHAR(20) | sí | única |
| `cliente_id` | BIGINT | no | → `clientes.id` |
| `vendedor_id` | BIGINT | no | → `vendedores.id` |
| `formato` | VARCHAR(10) | sí |  |
| `estado` | VARCHAR(15) | sí |  |
| `reservada_hasta` | DATETIME | no |  |
| `medio_difusion` | VARCHAR(20) | no |  |
| `fecha_venta` | DATETIME | no |  |
| _regla_ | `uq_boleta_consecutivo` | | `rifa_id`, `consecutivo` únicos juntos |
| _regla_ | `ck_boletas_estado` | | `estado IN ('disponible','reservada','vendida','anulada')` |
| _regla_ | `uq_boletas_codigo_verificacion` | | `codigo_verificacion` únicos juntos |
| _regla_ | `ck_boletas_formato` | | `formato IN ('virtual','impresa')` |
| _regla_ | `uq_boleta_id_rifa` | | `id`, `rifa_id` únicos juntos |
| _regla_ | `ck_boletas_reserva` | | `estado <> 'reservada' OR reservada_hasta IS NOT NULL` |

### `clientes`

Comprador de boletas. Su documento es único por organizador; todos sus datos son obligatorios.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `organizador_id` | BIGINT | sí | → `organizadores.id` |
| `tipo_documento` | VARCHAR(5) | sí |  |
| `numero_documento` | VARCHAR(20) | sí |  |
| `nombre` | VARCHAR(150) | sí |  |
| `celular` | VARCHAR(20) | sí |  |
| `whatsapp` | VARCHAR(20) | sí |  |
| `email` | VARCHAR(150) | sí |  |
| `direccion` | VARCHAR(200) | sí |  |
| `ciudad` | VARCHAR(100) | sí |  |
| `pais` | VARCHAR(100) | sí |  |
| `acepta_whatsapp` | BOOLEAN | sí |  |
| `referido_por_id` | BIGINT | no | → `clientes.id` |
| `fecha_creacion` | DATETIME | sí |  |
| _regla_ | `uq_cliente_documento` | | `organizador_id`, `numero_documento` únicos juntos |

### `cobros_rifa`

Pago del organizador a RifaPlus por publicar una rifa.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `rifa_id` | BIGINT | sí | → `rifas.id` · única |
| `plan_id` | BIGINT | sí | → `planes.id` |
| `valor` | NUMERIC(12, 0) | sí |  |
| `medio_pago_id` | BIGINT | no | → `medios_pago.id` |
| `cuenta_destino_id` | BIGINT | no | → `cuentas_cobro.id` |
| `referencia` | VARCHAR(100) | no |  |
| `comprobante_url` | VARCHAR(300) | no |  |
| `estado` | VARCHAR(12) | sí |  |
| `revisado_por_id` | BIGINT | no | → `usuarios.id` |
| `motivo_rechazo` | VARCHAR(300) | no |  |
| `fecha_pago` | DATETIME | no |  |
| `fecha_revision` | DATETIME | no |  |
| _regla_ | `ck_cobros_rifa_estado` | | `estado IN ('pendiente','aprobado','rechazado')` |
| _regla_ | `uq_cobros_rifa_rifa_id` | | `rifa_id` únicos juntos |

### `conversaciones_soporte`

Conversación de soporte de un organizador. 'pendiente' = espera respuesta de RifaPlus.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `organizador_id` | BIGINT | sí | → `organizadores.id` · única |
| `estado` | VARCHAR(10) | sí |  |
| `sin_leer_organizador` | BOOLEAN | sí |  |
| `actualizada_en` | DATETIME | sí |  |
| `fecha_creacion` | DATETIME | sí |  |
| _regla_ | `ck_conversaciones_soporte_estado` | | `estado IN ('pendiente','atendida')` |
| _regla_ | `uq_conversaciones_soporte_organizador_id` | | `organizador_id` únicos juntos |

### `cuentas_cobro`

Cuenta donde se recibe dinero. organizador_id vacío = cuenta de RifaPlus.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `organizador_id` | BIGINT | no | → `organizadores.id` |
| `medio_pago_id` | BIGINT | sí | → `medios_pago.id` |
| `numero_cuenta` | VARCHAR(30) | sí |  |
| `titular` | VARCHAR(150) | sí |  |
| `activa` | BOOLEAN | sí |  |
| `fecha_creacion` | DATETIME | sí |  |

### `cuotas_rifa`

Plan de pagos de la boleta, definido por el organizador: cuánto y hasta cuándo.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `rifa_id` | BIGINT | sí | → `rifas.id` |
| `numero` | SMALLINT | sí |  |
| `valor` | NUMERIC(12, 0) | sí |  |
| `fecha_limite` | DATE | sí |  |
| _regla_ | `ck_cuotas_rifa_valor` | | `valor > 0` |
| _regla_ | `uq_cuota_numero` | | `rifa_id`, `numero` únicos juntos |

### `duraciones`

Cuánto tiempo cubre un pago: por ejemplo 6 meses o 1 año. El superadministrador las crea y las activa.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `nombre` | VARCHAR(40) | sí |  |
| `meses` | SMALLINT | sí | única |
| `activa` | BOOLEAN | sí |  |
| _regla_ | `uq_duraciones_meses` | | `meses` únicos juntos |
| _regla_ | `ck_duraciones_meses` | | `meses BETWEEN 1 AND 36` |

### `entregas_vendedor`

Dinero que un vendedor le entrega al organizador (rendición de cuentas).

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `vendedor_id` | BIGINT | sí | → `vendedores.id` |
| `rifa_id` | BIGINT | sí | → `rifas.id` |
| `medio_pago_id` | BIGINT | sí | → `medios_pago.id` |
| `monto` | NUMERIC(12, 0) | sí |  |
| `comprobante_url` | VARCHAR(300) | no |  |
| `recibido_por_id` | BIGINT | sí | → `usuarios.id` |
| `fecha` | DATETIME | sí |  |
| `observacion` | VARCHAR(300) | no |  |
| _regla_ | `ck_entregas_vendedor_monto` | | `monto > 0` |

### `historial_accesos`

Registro de cada intento de ingreso, exitoso o fallido, con IP y fecha.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `usuario_id` | BIGINT | no | → `usuarios.id` |
| `email_intentado` | VARCHAR(150) | sí |  |
| `evento` | VARCHAR(30) | sí |  |
| `exitoso` | BOOLEAN | sí |  |
| `ip` | VARCHAR(45) | no |  |
| `fecha` | DATETIME | sí |  |

### `loterias`

Lotería oficial con la que juegan las rifas.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `nombre` | VARCHAR(100) | sí | única |
| `dias_sorteo` | VARCHAR(50) | no |  |
| `activa` | BOOLEAN | sí |  |
| _regla_ | `uq_loterias_nombre` | | `nombre` únicos juntos |

### `medios_pago`

Forma de pago (Nequi, Daviplata, efectivo…). Se activan o desactivan sin tocar el código.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `codigo` | VARCHAR(20) | sí | única |
| `nombre` | VARCHAR(50) | sí |  |
| `requiere_comprobante` | BOOLEAN | sí |  |
| `activo` | BOOLEAN | sí |  |
| `para_compradores` | BOOLEAN | sí |  |
| `para_rifaplus` | BOOLEAN | sí |  |
| `orden` | SMALLINT | sí |  |
| _regla_ | `uq_medios_pago_codigo` | | `codigo` únicos juntos |

### `mensajes_soporte`

Un mensaje del chat. autor: organizador, asistente (respuesta automática) o rifaplus (el superadministrador).

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `conversacion_id` | BIGINT | sí | → `conversaciones_soporte.id` |
| `autor` | VARCHAR(12) | sí |  |
| `usuario_id` | BIGINT | no | → `usuarios.id` |
| `texto` | TEXT | sí |  |
| `fecha` | DATETIME | sí |  |
| _regla_ | `ck_mensajes_soporte_autor` | | `autor IN ('organizador','asistente','rifaplus')` |

### `mensajes_whatsapp`

Cola de mensajes de WhatsApp para compradores (preparada para el envío automático).

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `organizador_id` | BIGINT | sí | → `organizadores.id` |
| `cliente_id` | BIGINT | sí | → `clientes.id` |
| `boleta_id` | BIGINT | no | → `boletas.id` |
| `tipo` | VARCHAR(25) | sí |  |
| `canal` | VARCHAR(10) | sí |  |
| `telefono_destino` | VARCHAR(20) | sí |  |
| `mensaje` | TEXT | sí |  |
| `estado` | VARCHAR(12) | sí |  |
| `intentos` | SMALLINT | sí |  |
| `programado_para` | DATETIME | no |  |
| `enviado_en` | DATETIME | no |  |
| `error` | TEXT | no |  |
| `fecha_creacion` | DATETIME | sí |  |
| _regla_ | `ck_mensajes_whatsapp_canal` | | `canal IN ('automatico','manual')` |
| _regla_ | `ck_mensajes_whatsapp_estado` | | `estado IN ('pendiente','enviado','fallido','cancelado')` |
| _regla_ | `ck_mensajes_whatsapp_tipo` | | `tipo IN ('boleta_pagada','saldo_pendiente','recordatorio_sorteo','ganador')` |

### `numeros_boleta`

Número que juega una boleta. Único por rifa: la base de datos impide repetirlo.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `rifa_id` | BIGINT | sí | → `rifas.id`, → `boletas.rifa_id` |
| `boleta_id` | BIGINT | sí | → `boletas.id` |
| `numero` | VARCHAR(4) | sí |  |
| _regla_ | `uq_numero_por_rifa` | | `rifa_id`, `numero` únicos juntos |

### `organizadores`

Persona o empresa que se registra en RifaPlus para administrar sus rifas (tabla organizadores).

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `tipo_persona` | VARCHAR(10) | sí |  |
| `nombre` | VARCHAR(150) | sí |  |
| `tipo_documento` | VARCHAR(5) | no |  |
| `numero_documento` | VARCHAR(20) | no | única |
| `celular` | VARCHAR(20) | sí |  |
| `whatsapp` | VARCHAR(20) | sí |  |
| `email` | VARCHAR(150) | sí | única |
| `direccion` | VARCHAR(200) | no |  |
| `ciudad` | VARCHAR(100) | no |  |
| `estado` | VARCHAR(15) | sí |  |
| `whatsapp_estado` | VARCHAR(15) | sí |  |
| `whatsapp_ultima_conexion` | DATETIME | no |  |
| `limite_mensajes_hora` | SMALLINT | sí |  |
| `acepta_tratamiento_datos` | DATETIME | sí |  |
| `verificado_en` | DATETIME | no |  |
| `verificado_por_id` | BIGINT | no | → `usuarios.id` |
| `fecha_creacion` | DATETIME | sí |  |
| _regla_ | `ck_organizadores_tipo_persona` | | `tipo_persona IN ('natural','juridica')` |
| _regla_ | `ck_organizadores_estado` | | `estado IN ('pendiente','activo','suspendido')` |
| _regla_ | `uq_organizadores_numero_documento` | | `numero_documento` únicos juntos |
| _regla_ | `uq_organizadores_email` | | `email` únicos juntos |
| _regla_ | `ck_organizadores_wa_estado` | | `whatsapp_estado IN ('conectado','desconectado')` |

### `pagos`

Pago de un comprador por su boleta (va al organizador).

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `boleta_id` | BIGINT | sí | → `boletas.id` |
| `medio_pago_id` | BIGINT | sí | → `medios_pago.id` |
| `cuenta_destino_id` | BIGINT | no | → `cuentas_cobro.id` |
| `monto` | NUMERIC(12, 0) | sí |  |
| `referencia` | VARCHAR(100) | no |  |
| `comprobante_url` | VARCHAR(300) | no |  |
| `estado` | VARCHAR(12) | sí |  |
| `registrado_por_id` | BIGINT | sí | → `usuarios.id` |
| `verificado_por_id` | BIGINT | no | → `usuarios.id` |
| `fecha_pago` | DATETIME | sí |  |
| `fecha_verificacion` | DATETIME | no |  |
| _regla_ | `ck_pagos_monto` | | `monto > 0` |
| _regla_ | `ck_pagos_estado` | | `estado IN ('pendiente','aprobado','rechazado')` |

### `pagos_comision`

Pago de comisión que el organizador le hace a un vendedor. Con estos pagos su saldo llega a cero.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `vendedor_id` | BIGINT | sí | → `vendedores.id` |
| `monto` | NUMERIC(12, 0) | sí |  |
| `medio_pago_id` | BIGINT | sí | → `medios_pago.id` |
| `referencia` | VARCHAR(100) | no |  |
| `observacion` | VARCHAR(300) | no |  |
| `registrado_por_id` | BIGINT | sí | → `usuarios.id` |
| `fecha` | DATETIME | sí |  |
| _regla_ | `ck_pagos_comision_monto` | | `monto > 0` |

### `planes`

Tipo de rifa: boletas que vende (boletas_min = boletas_max) y cifras por boleta (numeros_min = numeros_max).

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `nombre` | VARCHAR(50) | sí |  |
| `boletas_min` | INTEGER | sí |  |
| `boletas_max` | INTEGER | sí |  |
| `valor` | NUMERIC(12, 0) | sí |  |
| `numeros_min` | SMALLINT | sí |  |
| `numeros_max` | SMALLINT | sí |  |
| `activo` | BOOLEAN | sí |  |
| _regla_ | `ck_planes_rango` | | `boletas_min >= 1 AND boletas_max >= boletas_min` |
| _regla_ | `ck_planes_valor` | | `valor >= 0` |
| _regla_ | `ck_planes_numeros` | | `numeros_min >= 1 AND numeros_max >= numeros_min` |

### `precios_rifa`

Precio de un tipo de rifa por una duración: «1.000 boletas de 1 cifra, por 6 meses, $89.900».

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `plan_id` | BIGINT | sí | → `planes.id` |
| `duracion_id` | BIGINT | sí | → `duraciones.id` |
| `valor` | NUMERIC(12, 0) | sí |  |
| _regla_ | `uq_precio_tipo_duracion` | | `plan_id`, `duracion_id` únicos juntos |
| _regla_ | `ck_precios_rifa_valor` | | `valor >= 0` |

### `premios`

Premio de la rifa: el mayor o un premio seco, cada uno con su lotería y fecha.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `rifa_id` | BIGINT | sí | → `rifas.id` |
| `tipo` | VARCHAR(10) | sí |  |
| `descripcion` | VARCHAR(300) | sí |  |
| `valor_estimado` | NUMERIC(14, 0) | no |  |
| `loteria_id` | BIGINT | no | → `loterias.id` |
| `fecha_juego` | DATE | no |  |
| `orden` | SMALLINT | sí |  |
| `foto_url` | VARCHAR(300) | no |  |
| _regla_ | `ck_premios_tipo` | | `tipo IN ('mayor','seco')` |

### `renovaciones_rifa`

Pago para extender la vigencia de una rifa publicada. Mientras no se apruebe, la rifa vencida sigue bloqueada.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `rifa_id` | BIGINT | sí | → `rifas.id` |
| `meses` | SMALLINT | sí |  |
| `valor` | NUMERIC(12, 0) | sí |  |
| `medio_pago_id` | BIGINT | no | → `medios_pago.id` |
| `referencia` | VARCHAR(100) | no |  |
| `comprobante_url` | VARCHAR(300) | no |  |
| `estado` | VARCHAR(12) | sí |  |
| `motivo_rechazo` | VARCHAR(300) | no |  |
| `revisado_por_id` | BIGINT | no | → `usuarios.id` |
| `fecha_pago` | DATETIME | no |  |
| `fecha_revision` | DATETIME | no |  |
| `fecha_creacion` | DATETIME | sí |  |
| _regla_ | `ck_renovaciones_rifa_estado` | | `estado IN ('pendiente','aprobado','rechazado')` |
| _regla_ | `ck_renovaciones_rifa_meses` | | `meses > 0` |

### `resultados`

Resultado de la lotería para un premio: número que cayó, boleta que lo tenía y decisión.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `premio_id` | BIGINT | sí | → `premios.id` · única |
| `numero_loteria` | VARCHAR(10) | sí |  |
| `numero_jugado` | VARCHAR(4) | sí |  |
| `numero_boleta_id` | BIGINT | no | → `numeros_boleta.id` |
| `estado` | VARCHAR(15) | sí |  |
| `registrado_por_id` | BIGINT | sí | → `usuarios.id` |
| `fecha_registro` | DATETIME | sí |  |
| `premio_entregado_en` | DATETIME | no |  |
| `evidencia_entrega_url` | VARCHAR(300) | no |  |
| `observacion` | VARCHAR(300) | no |  |
| _regla_ | `uq_resultados_premio_id` | | `premio_id` únicos juntos |
| _regla_ | `ck_resultados_estado` | | `estado IN ('pendiente','con_ganador','debe_saldo','desierto','acumulado','sin_ganador')` |

### `rifas`

Rifa de un organizador: opción de boletas, plan, precio, reglas y estado (borrador → en venta → sorteada).

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `organizador_id` | BIGINT | sí | → `organizadores.id` |
| `loteria_id` | BIGINT | sí | → `loterias.id` |
| `plan_id` | BIGINT | sí | → `planes.id` |
| `nombre` | VARCHAR(150) | sí |  |
| `descripcion` | TEXT | no |  |
| `numero_autorizacion` | VARCHAR(50) | no |  |
| `entidad_autoriza` | VARCHAR(150) | no |  |
| `fecha_autorizacion` | DATE | no |  |
| `fecha_sorteo` | DATE | sí |  |
| `cifras` | SMALLINT | sí |  |
| `total_numeros` | INTEGER | sí |  |
| `series_por_boleta` | SMALLINT | sí |  |
| `total_boletas` | INTEGER | sí |  |
| `valor_boleta` | NUMERIC(12, 0) | sí |  |
| `estado` | VARCHAR(20) | sí |  |
| `regla_seco_atrasado` | VARCHAR(10) | sí |  |
| `regla_mayor_sin_pagar` | VARCHAR(12) | sí |  |
| `duracion_meses` | SMALLINT | sí |  |
| `vigente_hasta` | DATE | no |  |
| `ultimo_aviso_vencimiento` | DATE | no |  |
| `fecha_creacion` | DATETIME | sí |  |
| _regla_ | `ck_rifas_regla_seco` | | `regla_seco_atrasado IN ('desierto','acumula')` |
| _regla_ | `ck_rifas_regla_mayor` | | `regla_mayor_sin_pagar IN ('paga_saldo','desierto')` |
| _regla_ | `ck_rifas_rango_completo` | | `total_numeros = power(10, cifras)` |
| _regla_ | `ck_rifas_valor` | | `valor_boleta > 0` |
| _regla_ | `ck_rifas_division_exacta` | | `mod(total_numeros, series_por_boleta) = 0` |
| _regla_ | `ck_rifas_estado` | | `estado IN ('borrador','en_venta','cerrada','sorteada','anulada')` |
| _regla_ | `ck_rifas_series` | | `series_por_boleta >= 1` |
| _regla_ | `ck_rifas_total_boletas` | | `total_boletas = total_numeros / series_por_boleta` |
| _regla_ | `ck_rifas_cifras` | | `cifras BETWEEN 1 AND 4` |

### `sesiones`

Sesión abierta en un navegador. La cookie guarda un token y aquí solo su hash, con vencimiento.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `usuario_id` | BIGINT | sí | → `usuarios.id` |
| `token_hash` | VARCHAR(128) | sí | única |
| `ip` | VARCHAR(45) | no |  |
| `navegador` | VARCHAR(300) | no |  |
| `creada_en` | DATETIME | sí |  |
| `expira_en` | DATETIME | sí |  |
| `cerrada_en` | DATETIME | no |  |
| _regla_ | `uq_sesiones_token_hash` | | `token_hash` únicos juntos |

### `tokens_seguridad`

Enlace de un solo uso para recuperar la clave o verificar el correo (hash, vencimiento, uso).

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `usuario_id` | BIGINT | sí | → `usuarios.id` |
| `tipo` | VARCHAR(20) | sí |  |
| `token_hash` | VARCHAR(128) | sí | única |
| `creado_en` | DATETIME | sí |  |
| `expira_en` | DATETIME | sí |  |
| `usado_en` | DATETIME | no |  |
| _regla_ | `uq_tokens_seguridad_token_hash` | | `token_hash` únicos juntos |
| _regla_ | `ck_tokens_seguridad_tipo` | | `tipo IN ('verificar_email','recuperar_clave')` |

### `usuarios`

Cuenta con la que se ingresa. Un organizador tiene su usuario admin; el superadmin no tiene organizador.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `organizador_id` | BIGINT | no | → `organizadores.id` |
| `nombre` | VARCHAR(150) | sí |  |
| `email` | VARCHAR(150) | sí | única |
| `password_hash` | VARCHAR(255) | sí |  |
| `rol` | VARCHAR(20) | sí |  |
| `debe_cambiar_clave` | BOOLEAN | sí |  |
| `clave_cambiada_en` | DATETIME | no |  |
| `email_verificado` | BOOLEAN | sí |  |
| `intentos_fallidos` | SMALLINT | sí |  |
| `bloqueado_hasta` | DATETIME | no |  |
| `activo` | BOOLEAN | sí |  |
| `ultimo_acceso` | DATETIME | no |  |
| `fecha_creacion` | DATETIME | sí |  |
| _regla_ | `uq_usuarios_email` | | `email` únicos juntos |
| _regla_ | `ck_usuarios_rol` | | `rol IN ('superadmin','admin','vendedor','colaborador')` |
| _regla_ | `ck_usuarios_superadmin_sin_org` | | `(rol = 'superadmin') = (organizador_id IS NULL)` |

### `vendedores`

Persona que vende boletas para un organizador, con su comisión.

| Columna | Tipo | Obligatoria | Relación / regla |
|---|---|---|---|
| `id` | BIGINT | sí | llave primaria |
| `organizador_id` | BIGINT | sí | → `organizadores.id` |
| `usuario_id` | BIGINT | no | → `usuarios.id` · única |
| `tipo_documento` | VARCHAR(5) | sí |  |
| `numero_documento` | VARCHAR(20) | sí |  |
| `nombre` | VARCHAR(150) | sí |  |
| `celular` | VARCHAR(20) | sí |  |
| `ciudad` | VARCHAR(100) | no |  |
| `comision_porcentaje` | NUMERIC(5, 2) | sí |  |
| `llave_bre_b` | VARCHAR(60) | no |  |
| `activo` | BOOLEAN | sí |  |
| `fecha_creacion` | DATETIME | sí |  |
| _regla_ | `uq_vendedores_usuario_id` | | `usuario_id` únicos juntos |
| _regla_ | `uq_vendedor_documento` | | `organizador_id`, `numero_documento` únicos juntos |

## Archivos, clases y funciones

### `app/cli.py`

Comandos de administración.

- `cmd_semillas()`: Carga los datos iniciales (loterías, medios de pago y planes) sin duplicar los existentes.
- `cmd_borrar_datos_prueba()`: Muestra qué se va a borrar, pide escribir BORRAR y borra los datos de prueba (ver app/core/limpieza.py).
- `cmd_avisar_vencimientos()`: Envía por correo los avisos de vencimiento del día (programarlo una vez al día con cron).
- `cmd_crear_superadmin()`: Pide nombre, correo y clave por consola y crea un usuario con rol superadmin.
- `main()`: Lee el subcomando escrito en la consola y ejecuta la función que le corresponde.

### `app/core/config.py`

Configuración de RifaPlus, leída de las variables de entorno o del archivo .env (ver .env.example).

- **clase `Configuracion`**: Valores de configuración. Cada atributo se puede cambiar con una variable del mismo nombre en .env.
  - `usar_psycopg`: Acepta postgresql://… o postgres://… y lo convierte al controlador que trae RifaPlus (psycopg 3).
  - `revisar_produccion`: En producción no se arranca con valores de ejemplo: evita publicar el sitio con claves conocidas.
  - `es_desarrollo`: True en el computador del desarrollador: muestra la clave temporal en pantalla y la documentación /docs.
  - `correo_activo`: True si hay datos de correo de salida configurados.
- `obtener_config()`: Devuelve la configuración. Se lee una sola vez y queda en memoria (lru_cache).

### `app/core/correo.py`

Envío de correos (clave temporal, recuperar clave, avisos al superadministrador).

- `enviar()`: Envía un correo de texto. Devuelve True si se envió; nunca lanza error (solo lo registra).
- `enviar_con_detalle()`: Igual que enviar(), pero devuelve también qué pasó, en palabras, para el botón «Probar correo».
- `avisar_admin()`: Aviso para el superadministrador (pagos por revisar, consultas de soporte).

### `app/core/database.py`

Conexión a PostgreSQL, clase base de los modelos y tipos de columna compartidos.

- **clase `Base`**: Clase de la que heredan todos los modelos. Aplica la convención de nombres de restricciones.
- `obtener_db()`: Dependencia de FastAPI: una sesión de base de datos por petición.

### `app/core/excepciones.py`

Excepciones de la aplicación.

- **clase `ErrorNegocio`**: Regla de negocio incumplida. El mensaje está listo para mostrárselo al usuario.
- **clase `Redirigir`**: Envía al usuario a otra página (por ejemplo, al ingreso o al cambio de clave).

### `app/core/limpieza.py`

Borra los datos de prueba para empezar de cero, conservando la configuración de RifaPlus.

- `contar()`: Cuántos registros se borrarían de cada tabla (para mostrarlos antes de confirmar).
- `borrar_datos_de_prueba()`: Borra todo lo de organizadores y rifas en una sola transacción: o se borra todo, o nada.

### `app/core/plantillas.py`

Motor de plantillas Jinja2 y filtros de formato colombiano.

- `pesos()`: 12345 -> $12.345
- `solo_digitos()`: '100.000' -> '100000' (los campos de dinero llegan con puntos de miles).
- `miles()`: Formatea un número con puntos de miles sin el signo $: 12345 -> '12.345'.
- `fecha_larga()`: Escribe una fecha en español: date(2026, 12, 13) -> '13 de diciembre de 2026'.
- `hora_colombia()`: Fecha y hora guardadas en UTC, mostradas en hora de Colombia.
- **clase `_Hoy`**: Fecha de hoy al momento de mostrar la página (no al arrancar el servidor).
- `_version_estaticos()` _(interna)_: Número que cambia cuando cambia algún CSS o JS; se agrega a sus enlaces para evitar la caché vieja.
- `errores_de_validacion()`: Convierte los errores de Pydantic en mensajes legibles para el formulario.

### `app/core/registro_modelos.py`

Importa todos los modelos para que SQLAlchemy y Alembic los conozcan.


### `app/core/seguridad.py`

Claves, tokens y hashing.

- `cifrar_clave()`: Cifra una clave con bcrypt. En la base de datos solo se guarda este resultado, nunca la clave.
- `verificar_clave()`: Compara una clave escrita con su versión cifrada. Devuelve False si no coinciden o el hash es inválido.
- `generar_clave_temporal()`: Genera la clave temporal del registro, sin caracteres que se confunden al leer (0/O, 1/l/I).
- `generar_token()`: Token aleatorio para cookies de sesión y enlaces de un solo uso.
- `hash_token()`: En la base de datos solo se guarda el hash del token, nunca el token.
- `generar_codigo_verificacion()`: Código impreso en la boleta (y en su QR) para verificar que es auténtica.
- `validar_clave_nueva()`: Devuelve un mensaje de error, o None si la clave es válida.

### `app/core/semillas.py`

Datos iniciales: loterías, medios de pago y planes. Se pueden cargar varias veces sin duplicar.

- `nombre_tipo()`: Nombre de un tipo de rifa: '25 boletas de 4 cifras'.
- `precio_inicial()`: Precio inicial por duración: el de 6 meses tal cual; cada 6 meses más suma la mitad (1 año = 1,5 veces).
- `crear_precios_faltantes()`: Crea las duraciones iniciales si no hay ninguna y el precio que falte de cada tipo de rifa por cada duración.
- `crear_tipos_faltantes()`: Crea los tipos de rifa que falten, con su precio inicial. No toca los que ya están. Devuelve cuántos creó.
- `cargar()`: Inserta loterías, medios de pago y planes que falten. Se puede ejecutar varias veces sin duplicar.

### `app/main.py`

Punto de entrada de RifaPlus.

- `crear_app()`: Construye la aplicación: estáticos, rutas de cada módulo y manejo de redirecciones.

### `app/modulos/acceso/dependencias.py`

Dependencias de FastAPI: quién está conectado y qué puede hacer.

- `ip_cliente()`: IP de quien hace la petición; respeta X-Forwarded-For cuando hay un proxy (Nginx) delante.
- `usuario_opcional()`: Usuario de la cookie de sesión, o None si nadie ha ingresado. Para páginas públicas.
- `usuario_con_clave_pendiente()`: Usuario conectado, aunque todavía no haya cambiado su clave temporal.
- `usuario_actual()`: Usuario conectado que ya cambió su clave; si no la ha cambiado, se le obliga.
- `organizador_actual()`: Exige un usuario de organizador (no superadmin). Lo usan todas las rutas del panel.
- `superadmin()`: Exige el rol superadmin. Lo usan todas las rutas de /admin.

### `app/modulos/acceso/esquemas.py`

Validación de datos de entrada del módulo de acceso.

- `normalizar_celular()`: Deja el número en formato internacional. Asume Colombia (+57) si no trae indicativo.
- **clase `RegistroOrganizador`**: Datos del formulario de registro, ya limpios y validados.
  - `tipo_valido`: Solo se acepta persona natural o jurídica.
  - `telefono`: Normaliza celular y WhatsApp al formato internacional (+57…).
  - `email_minusculas`: Guarda el correo en minúsculas y sin espacios, para que no se dupliquen cuentas.
  - `debe_aceptar`: La política de tratamiento de datos (Ley 1581) es obligatoria.
  - `debe_aceptar_terminos`: Los términos y condiciones son obligatorios.
  - `tipo_documento_valido`: El organizador debe identificarse: cédula, cédula de extranjería, pasaporte o NIT.
  - `documento_completo`: Quita puntos, espacios y guiones; exige al menos 5 caracteres.
  - `vacio_a_none`: Convierte los campos opcionales vacíos en None.

### `app/modulos/acceso/modelos.py`

Cuentas y acceso: organizadores, usuarios, sesiones, tokens de seguridad e historial de ingresos.

- **clase `Organizador`**: Persona o empresa que se registra en RifaPlus para administrar sus rifas (tabla organizadores).
  - `verificado`: True si el superadministrador ya verificó su nombre y documento.
- **clase `Usuario`**: Cuenta con la que se ingresa. Un organizador tiene su usuario admin; el superadmin no tiene organizador.
- **clase `Sesion`**: Sesión abierta en un navegador. La cookie guarda un token y aquí solo su hash, con vencimiento.
- **clase `TokenSeguridad`**: Enlace de un solo uso para recuperar la clave o verificar el correo (hash, vencimiento, uso).
- **clase `HistorialAcceso`**: Registro de cada intento de ingreso, exitoso o fallido, con IP y fecha.

### `app/modulos/acceso/notificaciones.py`

Correos al organizador sobre su cuenta: clave temporal y recuperación de clave.

- `enviar_clave_temporal()`: Envía al correo del organizador la clave temporal con la que ingresa la primera vez.
- `enviar_enlace_recuperacion()`: Envía el enlace de un solo uso para crear una clave nueva (vence en una hora).
- `enviar_clave_restablecida()`: Cuando el superadministrador restablece la clave, le envía al organizador la nueva clave temporal.
- `enviar_invitacion_equipo()`: Le avisa a un colaborador que el organizador lo agregó a su equipo, con su clave temporal.

### `app/modulos/acceso/rutas.py`

Rutas de acceso: registro, ingreso, salida y cambio de clave.

- `registro_formulario()`: Muestra el formulario de registro vacío.
- `registro()`: Recibe el registro, crea organizador y usuario con clave temporal, y muestra la confirmación.
- `ingresar_formulario()`: Muestra el formulario de ingreso.
- `ingresar()`: Valida correo y clave, crea la sesión (cookie) y envía al panel, al admin o a cambiar la clave.
- `salir()`: Cierra la sesión actual y borra la cookie.
- `cambiar_clave_formulario()`: Muestra el formulario para crear o cambiar la clave.
- `cambiar_clave()`: Guarda la clave nueva. En el primer ingreso, activa al organizador.
- `recuperar_formulario()`: Formulario para pedir el enlace de cambio de clave.
- `recuperar()`: Envía el enlace si existe la cuenta. Siempre muestra el mismo mensaje (no revela quién tiene cuenta).
- `restablecer_formulario()`: Formulario para crear la clave nueva desde el enlace del correo.
- `restablecer()`: Guarda la clave nueva y lleva al ingreso.

### `app/modulos/acceso/servicio.py`

Casos de uso del módulo de acceso: registro, ingreso y cambio de clave.

- `_ahora()` _(interna)_: Fecha y hora actual en UTC.
- **clase `ResultadoRegistro`**: Lo que devuelve el registro: el organizador creado y su clave temporal.
- **clase `ResultadoIngreso`**: Lo que devuelve un ingreso exitoso: el usuario y el token para la cookie.
- `registrar_organizador()`: Crea organizador, usuario admin con clave temporal y aceptaciones legales; envía la clave.
- `ingresar()`: Verifica correo y clave, aplica bloqueo por intentos fallidos y abre la sesión.
- `cambiar_clave()`: Cambia la clave. Devuelve True si era el primer ingreso (clave temporal).
- `pedir_recuperacion()`: Crea un enlace de un solo uso para cambiar la clave. Devuelve (usuario, token) o None si el correo no existe.
- `token_valido()`: El token de recuperación si existe, no se ha usado y no ha vencido.
- `restablecer_con_token()`: Cambia la clave con el enlace del correo: lo marca usado, desbloquea la cuenta y cierra las sesiones.
- `restablecer_por_admin()`: El superadministrador le pone una clave temporal nueva a un usuario; debe cambiarla al ingresar.

### `app/modulos/acceso/sesiones.py`

Sesiones de usuario guardadas en la base de datos (cookie con token aleatorio).

- `ahora()`: Fecha y hora actual en UTC.
- `crear_sesion()`: Crea una sesión nueva y devuelve el token que va en la cookie (en la base solo queda su hash).
- `usuario_de_token()`: Usuario dueño del token si la sesión está abierta, vigente y el organizador no está suspendido.
- `cerrar_sesion()`: Marca como cerrada la sesión de ese token.
- `cerrar_otras_sesiones()`: Al cambiar la clave se cierran las sesiones abiertas en otros dispositivos.

### `app/modulos/admin/catalogos.py`

Lo que el superadministrador puede cambiar sin tocar el código: planes y precios, loterías y el valor del cobro

- `tipos_de_rifa()`: Los 13 tipos de rifa con su precio (un plan exacto por cada combinación de boletas y cifras por boleta).
- `guardar_precios()`: Guarda la tabla completa: precio de cada tipo de rifa por cada duración, y qué tipos se ofrecen.
- `crear_tipo()`: Agrega un tipo de rifa nuevo. Boletas × cifras debe dar 10, 100, 1.000 o 10.000 números del sorteo.
- `duraciones()`: Todas las duraciones, de la más corta a la más larga.
- `guardar_duracion()`: Crea o cambia una duración. Una duración nueva arranca con precios en 0 para que usted los ponga.
- `loterias()`: Todas las loterías, en orden alfabético.
- `guardar_loteria()`: Agrega una lotería o cambia su nombre, sus días de sorteo o si está activa.
- `ajustar_cobro()`: Cambia lo que paga una rifa (descuento o cortesía). Con $0 queda aprobada y el organizador puede publicar.

### `app/modulos/admin/datos.py`

Vista de la base de datos para el superadministrador: tablas, registros y consultas SQL de SOLO LECTURA.

- **clase `Resultado`**: Columnas y filas para mostrar en una tabla de la pantalla.
- `_valor()` _(interna)_: Oculta las columnas sensibles y deja el resto como texto legible.
- `tablas()`: Todas las tablas de RifaPlus con su número de registros, en orden alfabético.
- `ver_tabla()`: Registros de una tabla, del más nuevo al más viejo. buscar filtra en todas las columnas.
- `consultar()`: Ejecuta un SELECT escrito a mano, en solo lectura, con 5 segundos de límite y máximo 500 filas.
- `a_csv()`: Resultado en CSV para Excel (punto y coma, marca UTF-8).

### `app/modulos/admin/rutas.py`

Zona del superadministrador (/admin): solo para el rol superadmin.

- `_pagina()` _(interna)_: Muestra una plantilla de /admin agregando el aviso de la acción anterior (?ok=...).
- `inicio()`: Resumen general de RifaPlus para el superadministrador.
- `organizadores()`: Lista de organizadores con búsqueda y filtro por estado.
- `_organizador()` _(interna)_: Busca el organizador o vuelve a la lista si no existe.
- `_detalle()` _(interna)_: Muestra la ficha de un organizador con sus rifas.
- `organizador()`: Ficha de un organizador: contacto, rifas y acciones.
- `cambiar_estado()`: Suspende o reactiva a un organizador.
- `eliminar_organizador()`: Elimina un organizador sin rifas, después de confirmar su correo.
- `eliminar_rifa()`: Elimina una rifa con todo lo suyo, después de confirmar su nombre.
- `cobros()`: Lista de cobros de rifas de pago que esperan revisión.
- `revisar_cobro()`: Aprueba o rechaza el cobro del plan de una rifa.
- `ver_comprobante()`: Foto del comprobante que envió el organizador para pagar su plan.
- `_pagina_cuentas()` _(interna)_: Cuentas de Nequi y Daviplata de RifaPlus.
- `cuentas()`: Cuentas donde los organizadores pagan sus planes.
- `crear_cuenta()`: Agrega una cuenta de RifaPlus.
- `cambiar_cuenta()`: Activa o desactiva una cuenta de RifaPlus.
- `datos()`: Lista de tablas de la base de datos con su número de registros.
- `consulta_formulario()`: Formulario para escribir una consulta SQL de solo lectura.
- `consulta()`: Ejecuta la consulta en solo lectura y muestra el resultado (o lo descarga en CSV).
- `tabla_csv()`: Descarga la tabla completa (con el filtro de búsqueda, si lo hay) en CSV para Excel.
- `ver_tabla()`: Registros de una tabla, por páginas y con búsqueda.
- `restablecer_clave()`: Le pone una clave temporal nueva al organizador, se la envía al correo y se la muestra al superadmin una vez.
- `probar_correo()`: Envía un correo de prueba y muestra qué pasó, para revisar la configuración de Gmail.
- `_pagina_planes()` _(interna)_: Tabla de tipos de rifa × duraciones, más los formularios para agregar tipos y duraciones.
- `ver_planes()`: Precios de cada tipo de rifa por cada duración.
- `crear_tipos()`: Crea los tipos de rifa iniciales que falten, con su precio inicial (no cambia los que ya existen).
- `crear_tipo()`: Agrega un tipo de rifa nuevo (queda inactivo y con precios en 0 para que usted los ponga).
- `guardar_duracion()`: Crea o cambia una duración (por ejemplo «6 meses» o «1 año»).
- `guardar_precios()`: Guarda de una vez la tabla de precios (tipo × duración) y qué tipos se ofrecen.
- `_pagina_loterias()` _(interna)_: Loterías con las que juegan las rifas.
- `ver_loterias()`: Loterías disponibles para las rifas.
- `guardar_loteria()`: Agrega una lotería o guarda los cambios de una existente.
- `ajustar_cobro()`: Cambia el valor que paga una rifa (descuento o cortesía).
- `revisar_renovacion()`: Aprueba (extiende la vigencia y desbloquea) o rechaza una renovación.
- `cambiar_verificacion()`: Verifica o quita la verificación de identidad del organizador.

### `app/modulos/admin/servicio.py`

Superadministrador: organizadores, sus rifas, cobros de planes y borrados con confirmación.

- **clase `FilaOrganizador`**: Organizador con su número de rifas y su último ingreso, para las tablas.
- **clase `FilaRifa`**: Rifa con boletas vendidas, dinero recaudado y su cobro, para la ficha del organizador.
- `resumen()`: Cifras generales: organizadores, rifas, cobros por revisar e ingresos aprobados.
- `organizadores()`: Organizadores filtrados por texto (nombre, correo, celular, documento) y estado.
- `rifas_de()`: Rifas de un organizador con sus cifras de venta y su cobro.
- `cobros_pendientes()`: Pagos de planes que los organizadores ya enviaron y esperan revisión (del más antiguo al más nuevo).
- `cambiar_estado()`: Activa o suspende al organizador; al suspender, cierra sus sesiones abiertas.
- `cambiar_verificacion()`: Marca al organizador como verificado (revisó su nombre y documento) o le quita la verificación.
- `revisar_cobro()`: Aprueba o rechaza el pago de un plan. Al aprobar, la rifa queda publicada; rechazar exige el motivo.
- `cuentas_rifaplus()`: Todas las cuentas de RifaPlus (activas e inactivas).
- `crear_cuenta()`: Agrega una cuenta de RifaPlus (llave Bre-B, Nequi o Daviplata) para recibir los pagos de los planes.
- `cambiar_cuenta()`: Activa o desactiva una cuenta de RifaPlus (las inactivas no se muestran a los organizadores).
- `_confirmar()` _(interna)_: Exige que el texto de confirmación coincida (sin importar mayúsculas) antes de borrar.
- `eliminar_rifa()`: Borra la rifa con TODO lo suyo: boletas, números, pagos, premios, resultados y su cobro.
- `eliminar_organizador()`: Borra un organizador sin rifas, con sus usuarios, compradores y vendedores.
- `plan_de()`: Plan por su id.

### `app/modulos/auditoria/modelos.py`

Registro de cambios importantes.

- **clase `Auditoria`**: Registro de cambios importantes: quién, qué tabla y registro, qué acción, antes y después.

### `app/modulos/auditoria/servicio.py`

Registro de cambios importantes: quién, qué, cuándo, antes y después.

- `registrar()`: Agrega una fila de auditoría. No hace commit: se guarda junto con el cambio que la origina.

### `app/modulos/equipo/rutas.py`

Rutas del equipo del organizador (/panel/equipo).

- `_dueno()` _(interna)_: Solo el organizador dueño de la cuenta entra a Equipo.
- `_pagina()` _(interna)_: Página del equipo: lista de personas y formulario para agregar.
- `ver()`: Equipo del organizador.
- `agregar()`: Agrega un colaborador; le llega la clave temporal al correo y el organizador también la ve una vez.
- `cambiar_estado()`: Activa o desactiva a un colaborador.

### `app/modulos/equipo/servicio.py`

Equipo del organizador: personas que le ayudan a manejar sus rifas con su propio usuario y clave.

- `es_dueno()`: True si es el dueño de la cuenta del organizador (no un colaborador).
- `exigir_dueno()`: Solo el organizador puede hacer esto; los colaboradores no.
- `miembros()`: Todos los usuarios del organizador: él primero y luego sus colaboradores.
- `agregar()`: Crea el usuario del colaborador con una clave temporal (debe cambiarla al entrar). Devuelve (usuario, clave).
- `cambiar_estado()`: Activa o desactiva a un colaborador. Al desactivarlo se cierran sus sesiones al instante.

### `app/modulos/informes/rutas.py`

Rutas de informes de ventas (reemplazan la antigua búsqueda de compradores).

- `_filtros()` _(interna)_: Convierte los parámetros de la dirección en filtros.
- `informes()`: Informe de boletas vendidas con filtros por rifa, vendedor, ciudad, comprador y estado de pago.
- `informes_csv()`: Descarga el mismo informe en CSV para abrirlo en Excel.
- `compradores_antiguo()`: La antigua página de compradores ahora es parte de Informes.

### `app/modulos/informes/servicio.py`

Informes de ventas: boletas vendidas filtradas por rifa, vendedor, ciudad, comprador y estado de pago.

- **clase `Filtros`**: Filtros del informe; todos son opcionales.
  - `activos`: True si se escribió o escogió algún filtro.
- **clase `Fila`**: Una boleta vendida en el informe, con lo pagado y lo que debe.
  - `estado`: Texto corto del estado de pago.
- **clase `Informe`**: Resultado del informe: filas y totales.
  - `total_recaudado`: Suma de lo pagado en las boletas del informe.
  - `total_por_cobrar`: Suma de lo que deben las boletas del informe.
- `generar()`: Arma el informe: filtra en la base de datos y calcula pagos, saldos y atrasos de cada boleta.
- `a_csv()`: Convierte el informe en CSV para Excel (separado por punto y coma, con marca UTF-8).

### `app/modulos/legal/modelos.py`

Aceptación de términos y declaraciones de responsabilidad.

- **clase `Aceptacion`**: Constancia de que un usuario aceptó un documento legal: cuál, qué versión, cuándo y desde qué IP.

### `app/modulos/legal/rutas.py`

Páginas legales públicas.

- `terminos()`: Página pública de términos y condiciones.
- `tratamiento_datos()`: Página pública de la política de tratamiento de datos personales.

### `app/modulos/legal/servicio.py`

Versiones vigentes de los documentos legales y registro de aceptaciones.

- `registrar()`: Guarda una aceptación legal. No hace commit: va en la misma transacción del registro o la rifa.

### `app/modulos/mensajes/modelos.py`

Cola de mensajes de WhatsApp.

- **clase `MensajeWhatsapp`**: Cola de mensajes de WhatsApp para compradores (preparada para el envío automático).

### `app/modulos/pagos/modelos.py`

Dinero: medios de pago, cuentas de cobro, planes, pagos de boletas, cobros de rifas y entregas de vendedores.

- **clase `MedioPago`**: Forma de pago (Nequi, Daviplata, efectivo…). Se activan o desactivan sin tocar el código.
- **clase `CuentaCobro`**: Cuenta donde se recibe dinero. organizador_id vacío = cuenta de RifaPlus.
- **clase `Plan`**: Tipo de rifa: boletas que vende (boletas_min = boletas_max) y cifras por boleta (numeros_min = numeros_max).
- **clase `Pago`**: Pago de un comprador por su boleta (va al organizador).
- **clase `CobroRifa`**: Pago del organizador a RifaPlus por publicar una rifa.
- **clase `EntregaVendedor`**: Dinero que un vendedor le entrega al organizador (rendición de cuentas).
- **clase `PagoComision`**: Pago de comisión que el organizador le hace a un vendedor. Con estos pagos su saldo llega a cero.
- **clase `Duracion`**: Cuánto tiempo cubre un pago: por ejemplo 6 meses o 1 año. El superadministrador las crea y las activa.
- **clase `PrecioRifa`**: Precio de un tipo de rifa por una duración: «1.000 boletas de 1 cifra, por 6 meses, $89.900».
- **clase `RenovacionRifa`**: Pago para extender la vigencia de una rifa publicada. Mientras no se apruebe, la rifa vencida sigue bloqueada.

### `app/modulos/pagos/servicio.py`

Planes de cobro por rifa.

- `planes_activos()`: Planes activos ordenados de menor a mayor, para la página de precios.
- `plan_para()`: Plan activo cuyo rango contiene la cantidad de boletas de la rifa.
- `estado_cobro()`: Situación del pago del plan de una rifa.
- `cuentas_rifaplus()`: Cuentas activas de RifaPlus (sin organizador) donde los organizadores pagan sus planes.
- `medios_para_rifaplus()`: Medios con los que se le puede pagar a RifaPlus: solo los de las cuentas activas que registró el superadmin.
- `enviar_pago_rifa()`: El organizador informa el pago de su plan. Queda en revisión hasta que el superadministrador lo apruebe.

### `app/modulos/panel/rutas.py`

Panel principal: organizador o superadministrador.

- `inicio()`: Panel del organizador con sus rifas. El superadmin se envía a /admin.

### `app/modulos/personas/modelos.py`

Personas de cada organizador: vendedores y clientes (compradores).

- **clase `Vendedor`**: Persona que vende boletas para un organizador, con su comisión.
- **clase `Cliente`**: Comprador de boletas. Su documento es único por organizador; todos sus datos son obligatorios.

### `app/modulos/publico/rutas.py`

Páginas públicas: inicio y verificación de boletas.

- `inicio()`: Página de inicio pública de RifaPlus, con los planes de la base de datos.
- `verificar_formulario()`: Página para escribir el código de una boleta y verificarla.
- `verificar()`: Muestra si una boleta es auténtica, su estado de pago y si ganó algún premio.
- `boleta_publica()`: Boleta individual que recibe el comprador por WhatsApp (sin su documento ni celular).
- `foto_publica()`: Fotos de premios (públicas, se ven en la boleta). Solo sirve la carpeta fotos/, nunca comprobantes.

### `app/modulos/rifas/cuotas.py`

Plan de cuotas de la boleta: lo define el organizador y con él se sabe quién está al día.

- **clase `EstadoCuota`**: Una cuota del plan con lo que se debe llevar pagado al terminarla, si está pagada y si venció.
- **clase `EstadoPlan`**: Plan de cuotas de una boleta en una fecha: sus cuotas y lo que ya debería estar pagado.
  - `proxima`: Primera cuota que todavía no está cubierta, o None si la boleta está pagada.
  - `atrasada`: True si alguna cuota ya venció y no está cubierta.
- `validar_plan()`: Revisa que las cuotas sumen el valor de la boleta, vayan en orden y venzan a tiempo.
- `_plan()` _(interna)_: Cuotas de la rifa como (valor, fecha). Sin cuotas guardadas, una sola cuota hasta el sorteo.
- `debido_hasta()`: Lo que una boleta debe llevar pagado al terminar ese día.
- `estado_plan()`: Estado de cada cuota de una boleta según lo que lleva pagado.

### `app/modulos/rifas/esquemas.py`

Validación de datos de entrada para las rifas.

- **clase `CuotaDatos`**: Una fila de la forma de pago: valor y fecha límite.
- **clase `PremioSecoDatos`**: Una fila de premio seco: descripción, lotería y fecha.
- **clase `RifaCrear`**: Todo lo que llega del formulario de nueva rifa, validado.
  - `fecha_futura`: La fecha del sorteo no puede ser hoy ni una fecha pasada.
  - `debe_aceptar`: La declaración de responsabilidad del organizador es obligatoria.
  - `regla_seco`: Solo se aceptan las reglas conocidas para premios secos.
  - `regla_mayor`: Solo se aceptan las reglas conocidas para el premio mayor.
  - `premios_secos_en_fecha`: Cada premio seco juega después de hoy y a más tardar el día del premio mayor.
  - `cifras`: Cifras de la opción escogida (la parte antes del guion de '4-4').
  - `numeros_por_boleta`: Números por boleta de la opción escogida (la parte después del guion).

### `app/modulos/rifas/generador.py`

Reglas matemáticas de la rifa: reparto de números en boletas y búsqueda del ganador.

- **clase `Opcion`**: Una forma válida de armar una rifa: cuántas cifras, cuántos números por boleta y su plan.
  - `clave`: Identificador de la opción en el formulario: 'cifras-números', por ejemplo '4-4'.
  - `total_numeros`: Cantidad de números de la rifa: 10, 100, 1.000 o 10.000.
  - `rango`: Rango para mostrar, por ejemplo '00 al 99'.
- `calcular_boletas()`: La rifa usa todos los números de sus cifras; la división entre boletas debe ser exacta.
- `opciones_disponibles()`: Todas las combinaciones válidas según los planes activos (se calculan, no se escriben a mano).
- `buscar_opcion()`: Busca la opción válida para esas cifras y números por boleta, o explica por qué no existe.
- `repartir_numeros()`: Mezcla los números de forma no predecible (secrets) y los reparte en boletas.
- `generar_boletas()`: Crea todas las boletas y sus números. Se llama dentro de la transacción que crea la rifa.
- `numero_jugado()`: Últimas cifras del resultado de la lotería según las cifras de la rifa.
- `buscar_ganador()`: Número de boleta que tiene las últimas cifras del resultado de la lotería.

### `app/modulos/rifas/modelos.py`

Rifas: loterías, rifas, premios, boletas, números y resultados.

- **clase `Loteria`**: Lotería oficial con la que juegan las rifas.
- **clase `Rifa`**: Rifa de un organizador: opción de boletas, plan, precio, reglas y estado (borrador → en venta → sorteada).
- **clase `Premio`**: Premio de la rifa: el mayor o un premio seco, cada uno con su lotería y fecha.
  - `fecha`: Fecha en que juega el premio (si no tiene, la del sorteo de la rifa).
  - `nombre_loteria`: Nombre de la lotería del premio (si no tiene, la de la rifa).
- **clase `Cuota`**: Plan de pagos de la boleta, definido por el organizador: cuánto y hasta cuándo.
- **clase `Boleta`**: Boleta de una rifa: consecutivo, código de verificación, comprador, vendedor y estado.
  - `etiqueta`: Cómo se nombra la boleta: con un solo número, es su número (07); con varios, su consecutivo (1, 2…).
- **clase `NumeroBoleta`**: Número que juega una boleta. Único por rifa: la base de datos impide repetirlo.
- **clase `Resultado`**: Resultado de la lotería para un premio: número que cayó, boleta que lo tenía y decisión.

### `app/modulos/rifas/rutas.py`

Rutas de rifas del organizador.

- `_obtener()` _(interna)_: Rifa del organizador conectado, o vuelve al panel si no es suya.
- `_cuotas_y_secos()` _(interna)_: Lee las filas dinámicas del formulario: cuota_valor_1, cuota_fecha_1… y seco_descripcion_1…
- `_guardar_fotos()` _(interna)_: Guarda las fotos subidas y deja su ruta en los campos ocultos *_actual del formulario.
- `_datos_rifa()` _(interna)_: Convierte el formulario de rifa en los datos de RifaCrear (dinero sin puntos, cuotas y premios secos).
- `_formulario()` _(interna)_: Muestra el formulario de nueva rifa con opciones, loterías, reglas y errores.
- `nueva_formulario()`: Formulario vacío para crear una rifa.
- `crear()`: Recibe el formulario, crea la rifa con todas sus boletas y lleva a su página.
- `detalle()`: Página de la rifa: cifras de venta, sorteos, boletas con búsqueda, filtros y páginas.
- `publicar()`: Publica la rifa. Si su plan es de pago y aún no está aprobado, lleva a la pantalla para pagarlo.
- `eliminar()`: Elimina una rifa del organizador que no tiene ventas ni pagos.
- `editar_formulario()`: Formulario para corregir la rifa: completo en borrador, limitado en venta.
- `_formulario_en_venta()` _(interna)_: Formulario limitado para una rifa en venta.
- `editar()`: Guarda las correcciones de la rifa según su estado.
- `_avisar_verificacion()` _(interna)_: Le avisa al superadministrador que un organizador necesita verificación para publicar otra rifa.
- `_pagina_pago()` _(interna)_: Pantalla para pagar el plan de la rifa a RifaPlus.
- `pagar_formulario()`: Valor del plan, cuentas de RifaPlus y formulario para informar el pago.
- `pagar()`: Recibe la referencia y el comprobante del pago del plan; la rifa queda esperando la aprobación.
- `_pagina_renovar()` _(interna)_: Pantalla para renovar: duraciones con su precio, cuentas de RifaPlus y formulario del pago.
- `renovar_formulario()`: Pantalla de renovación de una rifa publicada.
- `renovar()`: Recibe el pago de la renovación; si es gratis se aplica de una vez, si no queda en revisión.

### `app/modulos/rifas/servicio.py`

Casos de uso de las rifas: crear, consultar, buscar boletas y publicar.

- **clase `DetalleRifa`**: Todo lo que muestra la página de una rifa: boletas de la página, cobro, cifras y filtros.
  - `pago_aprobado`: True si el plan de la rifa ya está pagado y aprobado (o es gratis).
  - `estado_cobro`: gratis, sin_enviar, en_revision, aprobado o rechazado (ver pagos.servicio.estado_cobro).
  - `puede_publicarse`: True si la rifa está en borrador y su plan está aprobado.
- `loterias_activas()`: Loterías activas en orden alfabético.
- `opciones()`: Opciones de boletas que se pueden escoger hoy, según los planes.
- `crear_rifa()`: Crea la rifa, su premio, todas las boletas, su cobro y la declaración, en una sola transacción.
- `datos_para_formulario()`: Llena el formulario de rifa con los datos guardados (para editarla en borrador).
- `editar_borrador()`: Cambia todo lo de una rifa en borrador. Si cambia la opción de boletas, las vuelve a generar.
- `editar_en_venta()`: En venta solo se corrige lo que no perjudica a quien ya compró: textos, valores y fotos, secos nuevos.
- `rifa_del_organizador()`: La rifa solo si pertenece al organizador del usuario; si no, None.
- `rifas_del_organizador()`: Rifas del organizador y cuántas boletas lleva vendidas cada una.
- `detalle()`: Resumen de la rifa y una página de boletas; buscar acepta número, N.° de boleta o nombre del comprador.
- **clase `CuentasRifa`**: Las cuentas de una rifa para el organizador: lo que espera recaudar, lo que lleva y lo que le queda.
  - `ganancia_esperada`: Si vende todo: recaudo − premios − RifaPlus (antes de comisiones).
  - `ganancia_hoy`: Con lo recaudado hasta hoy: recaudado − premios − RifaPlus − comisiones.
- `cuentas()`: Calcula las cuentas de la rifa con sus datos actuales.
- `falta_verificacion()`: True si el organizador no está verificado y ya tiene otra rifa publicada (la primera va sin verificar).
- `exigir_verificacion()`: Detiene la publicación (o el pago para publicar) si el organizador debe verificarse primero.
- `publicar()`: Solo se publica con el plan pagado. La autorización legal es responsabilidad del organizador.
- `motivo_para_no_eliminar()`: Una rifa se puede eliminar solo si no tiene ventas, pagos ni plan pagado.
- `eliminar()`: Borra la rifa con sus boletas y números. La declaración del organizador se conserva como respaldo.
- `boleta_por_codigo()`: Boleta por su código de verificación (sin importar mayúsculas).

### `app/modulos/rifas/vigencia.py`

Vigencia de las rifas: cada rifa publicada funciona por un período pagado (por ejemplo 6 meses o 1 año).

- `sumar_meses()`: Suma meses a una fecha; si el día no existe en el mes destino, usa el último día (31 ene + 1 mes = 28 feb).
- `duraciones_activas()`: Duraciones que puede escoger el organizador, de la más corta a la más larga.
- `precios_por_tipo()`: {plan_id: {duracion_id: valor}} con todos los precios guardados.
- `precio()`: La duración y el precio de un tipo de rifa por esa duración. Error si no está disponible.
- `bloqueada()`: True si la rifa está en venta y ya pasó su fecha de vigencia sin renovar.
- `dias_restantes()`: Días que le quedan de vigencia (negativo si ya venció); None si no aplica.
- `exigir_vigente()`: Detiene cualquier acción del organizador sobre una rifa bloqueada por falta de renovación.
- `iniciar()`: Al publicar: la rifa queda vigente desde hoy por los meses que pagó.
- `extender()`: Al aprobar una renovación: suma los meses desde el vencimiento, o desde hoy si ya estaba vencida.
- `renovacion_pendiente()`: La renovación que el organizador envió y espera revisión, si la hay.
- `ultima_rechazada()`: La última renovación rechazada (para mostrar el motivo).
- `solicitar_renovacion()`: El organizador pide renovar. Si el precio es $0, se aprueba sola; si no, queda en revisión.
- `revisar_renovacion()`: El superadministrador aprueba (extiende la vigencia y desbloquea) o rechaza con motivo.
- `renovaciones_por_revisar()`: Renovaciones enviadas que esperan revisión del superadministrador.
- `avisos_del_dia()`: Rifas a las que hoy les toca aviso: faltan 15 o 3 días, vencen hoy o vencieron ayer. Una sola vez por día.
- `texto_aviso()`: Asunto y mensaje del correo de aviso al organizador.

### `app/modulos/soporte/modelos.py`

Chat de soporte: una conversación por organizador, con mensajes del organizador, del asistente y de RifaPlus.

- **clase `ConversacionSoporte`**: Conversación de soporte de un organizador. 'pendiente' = espera respuesta de RifaPlus.
- **clase `MensajeSoporte`**: Un mensaje del chat. autor: organizador, asistente (respuesta automática) o rifaplus (el superadministrador).

### `app/modulos/soporte/preguntas.py`

Preguntas frecuentes del asistente del chat. Para agregar o cambiar respuestas, edite la lista PREGUNTAS.

- **clase `Pregunta`**: Una pregunta frecuente con su respuesta.
- `normalizar()`: Minúsculas y sin tildes, para comparar palabras: 'Comisión' -> 'comision'.
- `por_clave()`: La pregunta con esa clave (cuando el organizador toca un botón de pregunta frecuente).
- `buscar()`: La pregunta que mejor coincide con lo que escribió el organizador, o None si no hay coincidencia clara.

### `app/modulos/soporte/rutas.py`

Rutas del chat de soporte: el organizador escribe desde su panel y el superadministrador responde en /admin.

- `ver_chat()`: Mensajes del chat del organizador (lo consulta el chat del panel cada pocos segundos).
- `escribir()`: Recibe un mensaje, una pregunta frecuente o la petición de hablar con una persona.
- `bandeja()`: Bandeja de conversaciones de soporte del superadministrador.
- `_conversacion()` _(interna)_: Conversación por id, o vuelve a la bandeja.
- `conversacion()`: Una conversación con su historial y el formulario para responder.
- `responder()`: Responde al organizador, o marca la consulta como atendida sin escribir.

### `app/modulos/soporte/servicio.py`

Chat de soporte: guarda mensajes, responde lo común con el asistente y deja lo demás para RifaPlus.

- `_ahora()` _(interna)_: Fecha y hora actual en UTC.
- `conversacion_de()`: La conversación del organizador; la crea con el saludo del asistente si no existe.
- `_respuesta()` _(interna)_: Texto de la respuesta. La de precios se arma con los planes vigentes, porque el superadmin los puede cambiar.
- `_agregar()` _(interna)_: Agrega un mensaje y actualiza la fecha de la conversación.
- `escribir()`: Procesa lo que envía el organizador.
- `responder()`: El superadministrador responde; el organizador lo verá en su chat como mensaje de RifaPlus.
- `marcar_atendida()`: Cierra la consulta sin escribir (por ejemplo, si el organizador ya resolvió solo).
- `conversaciones()`: Todas las conversaciones: primero las pendientes, luego las más recientes.
- `pendientes()`: Cuántas conversaciones esperan respuesta de RifaPlus (para el aviso en el menú).
- `a_json()`: La conversación lista para el chat del panel.

### `app/modulos/sorteos/rutas.py`

Rutas de sorteos: registrar resultados, corregirlos y marcar premios entregados.

- `_rifa()` _(interna)_: Rifa del organizador conectado, o vuelve al panel.
- `_volver()` _(interna)_: Regresa a la sección de sorteos de la rifa con un mensaje de éxito o de error.
- `registrar()`: Registra el número que cayó en la lotería para un premio.
- `borrar()`: Borra un resultado mal digitado para registrarlo de nuevo.
- `entregado()`: Marca el premio como entregado al ganador.

### `app/modulos/sorteos/servicio.py`

Sorteos: registrar el resultado de la lotería, encontrar al ganador y aplicar las reglas del organizador.

- **clase `Sorteo`**: Un premio con su resultado, la boleta que tenía el número y los premios acumulados que incluye.
  - `ganador`: Comprador que ganó el premio, o None si quedó desierto, acumulado o sin resultado.
- `pagado_hasta()`: Pagos aprobados hasta el final de ese día, en hora de Colombia.
- `sorteos()`: Premios de la rifa en orden de fecha, con resultados y acumulados de premios secos.
- `registrar()`: Guarda el resultado de un premio, busca la boleta y aplica las reglas del organizador.
- `_decidir()` _(interna)_: Aplica las reglas que el organizador escogió al crear la rifa.
- `borrar()`: Corrige un resultado mal digitado. No se puede si el premio ya se entregó.
- `marcar_entregado()`: Registra la fecha de entrega del premio. Solo para ganadores al día o pagados.
- `whatsapp_ganador()`: Enlace de WhatsApp con el mensaje de felicitación listo para el ganador.
- `premios_de_boleta()`: Resultados en los que esta boleta resultó ganadora (para la verificación pública).

### `app/modulos/ventas/archivos.py`

Guardado de comprobantes de pago. Se guardan fuera de la carpeta pública y solo los ve su organizador.

- `carpeta_base()`: Carpeta donde se guardan los comprobantes (fuera de la carpeta pública).
- `_guardar()` _(interna)_: Guarda un archivo subido si es de un tipo permitido (se revisa el contenido, no la extensión).
- `guardar_comprobante()`: Guarda un comprobante de pago (privado). Devuelve su ruta relativa, o None si no se envió.
- `guardar_foto()`: Guarda la foto de un premio (pública en la boleta). Devuelve su ruta relativa, o None si no se envió.
- `foto_propia()`: Acepta una ruta de foto ya guardada solo si es de este organizador (evita usar archivos ajenos).
- `ruta_absoluta()`: Ruta real de un comprobante, verificando que no se salga de la carpeta de archivos.

### `app/modulos/ventas/boleta_individual.py`

Boleta individual de un comprador: los datos para imprimirla o enviarla, con su código QR.

- **clase `BoletaIndividual`**: Todo lo que se pinta en la boleta individual.
  - `mayor`: El premio mayor de la rifa.
  - `secos`: Los premios secos, en orden de fecha.
  - `nombre_comprador`: Nombre completo para el organizador; en el enlace público solo nombre e inicial del apellido.
- `url_publica()`: Dirección pública de la boleta, la que se envía al comprador y va en el código QR.
- `armar()`: Reúne saldo, plan de cuotas, premios y el QR de la boleta.

### `app/modulos/ventas/esquemas.py`

Validación de los datos de venta: comprador, vendedor y pagos.

- **clase `_ConDocumento`**: Base para personas con documento: tipo válido y número limpio.
  - `tipo_valido`: Solo se aceptan los tipos de documento de la lista.
  - `documento_limpio`: Quita puntos, espacios y guiones del documento: '1.045.123' -> '1045123'.
- **clase `Comprador`**: Todos los datos son obligatorios: si gana, hay que poder ubicarlo y entregarle el premio.
  - `telefono`: Normaliza el número al formato internacional (+57…).
  - `email_minusculas`: Guarda el correo en minúsculas y sin espacios.
  - `sin_espacios`: Quita espacios repetidos en nombre, dirección y ciudad.
- **clase `DatosPago`**: Un pago registrado por el organizador: valor, medio y referencia.
  - `vacio_a_none`: Referencia vacía -> None.
- **clase `VendedorCrear`**: Datos para agregar un vendedor.
  - `llave_limpia`: Quita espacios sobrantes de la llave (celular, cédula, correo o alias como @PEPITO).
  - `telefono`: Normaliza el número al formato internacional (+57…).

### `app/modulos/ventas/rutas.py`

Rutas de venta de boletas, pagos, compradores y vendedores.

- `_rifa()` _(interna)_: Rifa del organizador conectado, o vuelve al panel.
- `_pagina_boleta()` _(interna)_: Muestra la página de una boleta: venta, plan de pagos, pagos y WhatsApp.
- `_pago_del_formulario()` _(interna)_: El pago es opcional al vender: si no escriben monto, la boleta queda vendida debiendo.
- `ver_boleta()`: Página de una boleta.
- `vender()`: Vende la boleta: guarda o actualiza el comprador y registra el pago inicial si lo hay.
- `registrar_pago()`: Registra un abono o el pago completo de una boleta vendida.
- `liberar()`: Deshace la venta de una boleta sin pagos.
- `ver_comprobante()`: Entrega la foto del comprobante solo al organizador dueño de la rifa.
- `buscar_comprador()`: Para el formulario de venta: si el comprador ya existe, devuelve sus datos para no escribirlos de nuevo.
- `lista_vendedores()`: Lista de vendedores con lo que ha vendido y cobrado cada uno.
- `_pagina_vendedores()` _(interna)_: Muestra la página de vendedores con su liquidación y los errores del formulario si los hay.
- `crear_vendedor()`: Agrega un vendedor nuevo.
- `_vendedor()` _(interna)_: Vendedor del organizador conectado, o vuelve a la lista.
- `_pagina_vendedor()` _(interna)_: Muestra la liquidación de un vendedor: comisión por rifa, pagos hechos y saldo.
- `ver_vendedor()`: Liquidación de un vendedor.
- `editar_vendedor()`: Cambia el porcentaje de comisión o activa / desactiva al vendedor.
- `pagar_comision()`: Registra un pago de comisión al vendedor.
- `imprimir_boleta()`: Boleta individual con los datos completos del comprador, lista para imprimir o guardar en PDF.
- `registrar_entrega()`: Registra el dinero en efectivo que el vendedor le entregó al organizador.

### `app/modulos/ventas/servicio.py`

Venta de boletas: comprador, abonos acreditados por el organizador, saldos y aviso por WhatsApp.

- `_ahora()` _(interna)_: Fecha y hora actual en UTC.
- **clase `Saldo`**: Lo que vale una boleta y lo que lleva pagado; de ahí salen lo pendiente y el estado.
  - `pendiente`: Lo que falta por pagar (nunca negativo).
  - `estado`: 'debe' sin pagos, 'abonada' con pagos parciales, 'pagada' completa.
- **clase `ResumenVentas`**: Cifras de venta de una rifa: vendidas, pagadas, con saldo, recaudado y por cobrar.
- `medios_para_compradores()`: Medios de pago activos para los pagos de compradores.
- `pagado_por_boleta()`: Total pagado (pagos aprobados) de cada boleta de la lista: {boleta_id: total}.
- `saldo()`: Saldo de una boleta: valor y lo pagado.
- `pagos_de()`: Pagos de una boleta, del más reciente al más antiguo.
- `resumen()`: Cifras de venta de la rifa calculadas en la base de datos con una sola consulta.
- `boleta_de_rifa()`: Boleta de esa rifa. Con bloquear=True la reserva (SELECT … FOR UPDATE) para que nadie la venda a la vez.
- `cliente_por_documento()`: Comprador del organizador con ese documento, o None.
- **clase `CompraDe`**: Una boleta de un comprador con su saldo, para la búsqueda de compradores.
- `buscar_compradores()`: Busca por cédula (completa o el comienzo) o por nombre, y trae las boletas de cada comprador.
- **clase `LineaLiquidacion`**: Lo que un vendedor lleva en una rifa: boletas vendidas, dinero recaudado y comisión ganada.
- **clase `Liquidacion`**: Cuenta de un vendedor: comisión ganada en todas sus rifas, lo que ya se le pagó y lo que falta.
  - `comision`: Comisión ganada en total.
  - `recaudado`: Dinero recaudado en total por las boletas que vendió.
  - `saldo`: Lo que falta por pagarle. Cuando llega a cero, el vendedor está a paz y salvo.
- `_comision()` _(interna)_: Comisión en pesos enteros, redondeada al peso más cercano.
- `liquidacion()`: Calcula por rifa lo recaudado en las boletas del vendedor (pagos aprobados) y su comisión.
- `pagos_comision_de()`: Pagos de comisión hechos al vendedor, del más reciente al más antiguo.
- `vendedor_del_organizador()`: El vendedor solo si es de este organizador.
- `pagar_comision()`: Registra un pago de comisión al vendedor. No deja pagar más de lo que se le debe.
- `actualizar_vendedor()`: Cambia la comisión, la llave Bre-B o activa / desactiva al vendedor.
- **clase `EfectivoRifa`**: Por rifa: efectivo que cobró el vendedor, lo que ya entregó y lo que le falta entregar.
  - `por_entregar`: Efectivo que el vendedor todavía tiene en su poder.
- `efectivo_del_vendedor()`: Pagos en efectivo de las boletas del vendedor (los cobra él) frente a lo que ya le entregó al organizador.
- `entregas_de()`: Entregas de dinero del vendedor, de la más reciente a la más antigua.
- `registrar_entrega()`: El organizador registra el dinero que le entregó el vendedor. No puede pasar de lo que el vendedor tiene.
- `vendedores()`: Vendedores del organizador en orden alfabético.
- `crear_vendedor()`: Crea el vendedor si su documento no está repetido.
- `ventas_por_vendedor()`: vendedor_id -> (boletas vendidas, dinero cobrado).
- `_medio_valido()` _(interna)_: El medio de pago debe existir, estar activo y servir para compradores.
- `_agregar_pago()` _(interna)_: Agrega un pago aprobado sin pasarse de lo que falta por pagar.
- `vender()`: Asigna la boleta al comprador (lo crea o actualiza), la marca vendida y registra el pago inicial.
- `registrar_pago()`: Agrega un pago a una boleta vendida.
- `liberar()`: Deshace una venta sin pagos (por ejemplo, el comprador se arrepintió antes de pagar).
- `_confirmar()` _(interna)_: Guarda los cambios y traduce los choques de la base de datos a mensajes claros.
- `enlace_correo()`: Enlace mailto: abre el correo del organizador con destinatario, asunto, mensaje y enlace a la boleta.
- `enlace_whatsapp()`: Abre WhatsApp con el mensaje listo para el comprador; el organizador solo toca enviar.
