# Documentación de RifaPlus

| Documento | Para qué sirve |
|---|---|
| [ARQUITECTURA.md](ARQUITECTURA.md) | Cómo está organizado el código, qué hace cada capa y las convenciones. Léalo primero. |
| [FLUJOS.md](FLUJOS.md) | Paso a paso de cada proceso: registro, crear rifa, vender, sorteos, superadministrador; qué archivo hace cada paso. |
| [BASE_DE_DATOS.md](BASE_DE_DATOS.md) | Las tablas agrupadas por tema, cómo se relacionan y las reglas que impone PostgreSQL. |
| [DOCKER.md](DOCKER.md) | **Servidor con Docker, Caddy y PostgreSQL en contenedores** (rifaplus.gedev.co): imagen, variables, tablas, archivos, tareas y copias. |
| [DESPLIEGUE.md](DESPLIEGUE.md) | Cómo poner RifaPlus en un servidor: instalación, HTTPS, copias de seguridad y actualizaciones. |
| [REFERENCIA.md](REFERENCIA.md) | **Generada del código**: todas las direcciones, todas las tablas con sus columnas y cada archivo con sus funciones. |
| [modelo-entidad-relacion.pdf](modelo-entidad-relacion.pdf) | El diagrama entidad-relación para imprimir (versión 4; las cuotas y reglas de sorteo se agregaron después y están en BASE_DE_DATOS.md). |
| `logos/` | Logos originales de RifaPlus. |

## Cómo mantener la documentación al día

1. **Cada función, clase y archivo nuevo lleva su docstring** (el texto entre `"""` debajo del `def`).
   `ruff check .` falla si falta alguno, así que no se puede olvidar.
2. Después de cambiar código, regenere la referencia:

   ```bash
   python -m herramientas.generar_referencia
   ```

3. Si cambia un proceso o una regla de negocio, actualice FLUJOS.md o BASE_DE_DATOS.md a mano.
