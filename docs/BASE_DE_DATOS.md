# Base de datos de RifaPlus

PostgreSQL. Las tablas se crean y cambian **solo con Alembic** (`migraciones/versiones/`). El detalle de cada
columna está en [REFERENCIA.md](REFERENCIA.md#tablas-de-la-base-de-datos), generado de los modelos.

## Tablas por tema

| Tema | Tablas | Para qué |
|---|---|---|
| Plataforma y acceso | `organizadores`, `usuarios`, `sesiones`, `tokens_seguridad`, `historial_accesos` | Quién usa RifaPlus y cómo ingresa. |
| Legal y auditoría | `aceptaciones`, `auditoria` | Qué aceptó cada organizador; quién cambió qué. |
| Rifas | `loterias`, `rifas`, `cuotas_rifa`, `premios`, `boletas`, `numeros_boleta`, `resultados` | La rifa, su forma de pago, premios, boletas, números y sorteos. |
| Personas | `clientes`, `vendedores` | Compradores y vendedores de cada organizador. |
| Dinero | `medios_pago`, `cuentas_cobro`, `planes`, `duraciones`, `precios_rifa`, `renovaciones_rifa`, `cobros_rifa`, `pagos`, `pagos_comision`, `entregas_vendedor` | Cómo se paga, cuánto cuesta cada plan, pagos de boletas y comisiones a vendedores. |
| Mensajería | `mensajes_whatsapp`, `conversaciones_soporte`, `mensajes_soporte` | Cola de WhatsApp y chat de soporte con los organizadores. |

Además hay una vista, `boletas_saldo`, con lo pagado y el saldo de cada boleta.

## Cómo se relacionan (lo esencial)

```
organizadores ─┬─ usuarios ─── sesiones / tokens_seguridad / historial_accesos
               ├─ clientes ─────────────┐
               ├─ vendedores ───────────┤
               └─ rifas ─┬─ cuotas_rifa │
                         ├─ premios ─── resultados ──► numeros_boleta
                         ├─ cobros_rifa ◄── planes
                         └─ boletas ◄───┘ (comprador, vendedor)
                              ├─ numeros_boleta
                              └─ pagos ◄── medios_pago
```

## Reglas que impone la base de datos

Aunque alguien se salte la aplicación, PostgreSQL rechaza estos datos:

| Regla | Restricción |
|---|---|
| Un número no se repite en la misma rifa | `uq_numero_por_rifa` (rifa_id, numero) |
| Un número pertenece a una boleta de su misma rifa | llave foránea compuesta `fk_numero_boleta_misma_rifa` |
| La rifa usa todos los números de sus cifras (10, 100, 1.000 o 10.000) | `ck_rifas_rango_completo` |
| Las boletas reparten los números en partes exactas | `ck_rifas_division_exacta`, `ck_rifas_total_boletas` |
| Rifas de 1 a 4 cifras | `ck_rifas_cifras` |
| Estados válidos de rifas, boletas, pagos, resultados… | `ck_<tabla>_estado` |
| Una referencia de pago no se repite con el mismo medio | índice único `uq_pago_referencia` |
| Un comprador o vendedor no se repite con el mismo documento por organizador | `uq_cliente_documento`, `uq_vendedor_documento` |
| Correo único por cuenta | `uq_usuarios_email`, `uq_organizadores_email` |
| Una boleta no recibe dos veces el aviso de pagada o de ganador | índice único `uq_msg_unico_por_boleta` |
| Un premio tiene un solo resultado | `uq_resultados_premio_id` |
| Un tipo de rifa (boletas × cifras por boleta) no se repite | índice único `uq_tipo_de_rifa` |
| Lo que tiene historia no se borra en cascada | llaves foráneas `ON DELETE RESTRICT` |

## Migraciones

| Archivo | Qué hizo |
|---|---|
| `…esquema_inicial` | Las 21 tablas del modelo v4 y la vista `boletas_saldo`. |
| `…planes_por_numeros_rango_completo_y_` | Planes por números por boleta, rifas de 1 a 4 cifras con rango completo, tabla `aceptaciones`. |
| `…venta_de_boletas` | WhatsApp y datos obligatorios del comprador; medios de pago para compradores (efectivo, transferencia). |
| `…cuotas_premios_secos_y_resultados` | Tabla `cuotas_rifa`, reglas del organizador y nuevos estados de resultado. |
| `…pagos_de_comision` | Tabla `pagos_comision` para liquidar a los vendedores. |
| `…fotos_de_premios` | Columna `premios.foto_url` para la foto opcional de cada premio. |
| `…llave_bre_b` | Medio de pago "Llave Bre-B" para pagar el plan a RifaPlus y para los compradores. |
| `…chat_de_soporte` | Tablas `conversaciones_soporte` y `mensajes_soporte`. |
| `…llave_bre_b_vendedor` | Columna `vendedores.llave_bre_b` para pagarle la comisión al vendedor. |
| `…precio_por_tipo_de_rifa` | Un plan exacto por cada tipo de rifa (13), con el precio que tenía; los planes por rangos quedan inactivos. |
| `…verificacion_y_colaboradores` | Columnas `verificado_en` y `verificado_por_id` en `organizadores`; rol `colaborador` en `usuarios`. |
| `…tipos_de_rifa_sin_repetir` | Quita tipos de rifa repetidos (conserva el usado o el de precios editados) y crea el índice único `uq_tipo_de_rifa`. |
| `…vigencia_y_renovaciones` | Tablas `duraciones` (6 meses, 1 año), `precios_rifa` (tipo × duración) y `renovaciones_rifa`; columnas de vigencia en `rifas`. |

Comandos: `alembic upgrade head` (aplicar), `alembic current` (ver versión),
`alembic revision --autogenerate -m "…"` (crear una nueva a partir de los modelos).
