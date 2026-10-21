"""Conexión a PostgreSQL, clase base de los modelos y tipos de columna compartidos."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from sqlalchemy import BigInteger, DateTime, Identity, MetaData, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Session, mapped_column, sessionmaker

from app.core.config import obtener_config

# Nombres de restricciones predecibles (necesario para que Alembic genere migraciones estables)
CONVENCION_NOMBRES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Clase de la que heredan todos los modelos. Aplica la convención de nombres de restricciones."""

    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


# Tipos reutilizables
pk = Annotated[int, mapped_column(BigInteger, Identity(always=True), primary_key=True)]
creado = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)]

motor = create_engine(obtener_config().database_url, pool_pre_ping=True)
SesionLocal = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


def obtener_db() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión de base de datos por petición."""
    db = SesionLocal()
    try:
        yield db
    finally:
        db.close()
