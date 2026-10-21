"""Vista de la base de datos para el superadministrador: tablas, registros y consultas SQL de SOLO LECTURA.

Nada de aquí puede modificar datos: las tablas se leen con SELECT armados por el sistema, y las consultas escritas
a mano corren en una transacción de solo lectura con tiempo límite. Las claves y los tokens se muestran ocultos.
"""

import csv
import io
from dataclasses import dataclass

from sqlalchemy import String, cast, func, or_, select, text
from sqlalchemy.orm import Session

import app.core.registro_modelos  # noqa: F401
from app.core.database import Base
from app.core.excepciones import ErrorNegocio

FILAS_POR_PAGINA = 50
MAX_FILAS_CONSULTA = 500
COLUMNAS_OCULTAS = {"password_hash", "token_hash"}  # nunca se muestran
OCULTO = "•••"
PALABRAS_PROHIBIDAS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "copy",
    "vacuum",
    "call",
    "do",
    "execute",
    "lock",
    "set",
    "reset",
    "comment",
    "refresh",
)


@dataclass
class Resultado:
    """Columnas y filas para mostrar en una tabla de la pantalla."""

    columnas: list[str]
    filas: list[list]
    total: int = 0
    pagina: int = 1
    paginas: int = 1


def _valor(columna: str, valor):
    """Oculta las columnas sensibles y deja el resto como texto legible."""
    if columna in COLUMNAS_OCULTAS and valor is not None:
        return OCULTO
    return valor


def tablas(db: Session) -> list[tuple[str, int]]:
    """Todas las tablas de RifaPlus con su número de registros, en orden alfabético."""
    salida = []
    for nombre, tabla in sorted(Base.metadata.tables.items()):
        salida.append((nombre, db.scalar(select(func.count()).select_from(tabla)) or 0))
    return salida


def ver_tabla(db: Session, nombre: str, pagina: int = 1, buscar: str = "", todas: bool = False) -> Resultado:
    """Registros de una tabla, del más nuevo al más viejo. buscar filtra en todas las columnas."""
    tabla = Base.metadata.tables.get(nombre)
    if tabla is None:  # solo tablas conocidas: el nombre nunca se mete directo en el SQL
        raise ErrorNegocio("Esa tabla no existe.")
    consulta = select(tabla)
    if buscar.strip():
        patron = f"%{buscar.strip()}%"
        visibles = [c for c in tabla.columns if c.name not in COLUMNAS_OCULTAS]
        consulta = consulta.where(or_(*(cast(c, String).ilike(patron) for c in visibles)))
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    orden = [c.desc() for c in tabla.primary_key.columns] or list(tabla.columns)[:1]
    consulta = consulta.order_by(*orden)
    paginas = max(1, -(-total // FILAS_POR_PAGINA))
    pagina = min(max(1, pagina), paginas)
    if not todas:
        consulta = consulta.offset((pagina - 1) * FILAS_POR_PAGINA).limit(FILAS_POR_PAGINA)
    columnas = [c.name for c in tabla.columns]
    filas = [[_valor(c, v) for c, v in zip(columnas, fila, strict=True)] for fila in db.execute(consulta)]
    return Resultado(columnas, filas, total, pagina, paginas)


def consultar(db: Session, sql: str) -> Resultado:
    """Ejecuta un SELECT escrito a mano, en solo lectura, con 5 segundos de límite y máximo 500 filas."""
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise ErrorNegocio("Escriba una consulta.")
    minusculas = " " + " ".join(sql.lower().split()) + " "
    if not (minusculas.lstrip().startswith("select") or minusculas.lstrip().startswith("with")):
        raise ErrorNegocio("Solo se permiten consultas que empiecen por SELECT o WITH.")
    if ";" in sql:
        raise ErrorNegocio("Escriba una sola consulta, sin punto y coma en medio.")
    prohibida = next((p for p in PALABRAS_PROHIBIDAS if f" {p} " in minusculas.replace("(", " ")), None)
    if prohibida:
        raise ErrorNegocio(f"La consulta no puede usar «{prohibida.upper()}»: esta herramienta es solo de lectura.")
    conexion = db.connection()
    try:
        conexion.execute(text("SET TRANSACTION READ ONLY"))  # aunque algo se colara, PostgreSQL no deja escribir
        conexion.execute(text("SET LOCAL statement_timeout = '5s'"))
        cursor = conexion.execute(text(sql))
        columnas = list(cursor.keys())
        filas = [
            [_valor(c, v) for c, v in zip(columnas, fila, strict=True)] for fila in cursor.fetchmany(MAX_FILAS_CONSULTA)
        ]
    except ErrorNegocio:
        raise
    except Exception as e:  # el mensaje de PostgreSQL se muestra para que pueda corregir la consulta
        db.rollback()
        raise ErrorNegocio(f"La consulta tiene un error: {str(getattr(e, 'orig', e)).splitlines()[0]}") from e
    db.rollback()  # cierra la transacción de solo lectura
    return Resultado(columnas, filas, len(filas))


def a_csv(resultado: Resultado) -> str:
    """Resultado en CSV para Excel (punto y coma, marca UTF-8)."""
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow(resultado.columnas)
    escritor.writerows(resultado.filas)
    return "\ufeff" + salida.getvalue()
