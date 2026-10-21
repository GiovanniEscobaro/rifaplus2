"""Configuración de Alembic: usa la conexión y los modelos de la aplicación."""

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.core.registro_modelos  # noqa: F401  (registra todos los modelos)
from app.core.config import obtener_config
from app.core.database import Base

config = context.config
config.set_main_option("sqlalchemy.url", obtener_config().database_url.replace("%", "%%"))
target_metadata = Base.metadata


def ejecutar_sin_conexion() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_con_conexion() -> None:
    motor = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    ejecutar_sin_conexion()
else:
    ejecutar_con_conexion()
