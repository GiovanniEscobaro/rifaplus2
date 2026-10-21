"""Borra los datos de prueba para empezar de cero, conservando la configuración de RifaPlus.

Se BORRA: organizadores y sus usuarios, rifas, boletas, cifras, premios, cuotas, resultados, compradores, vendedores,
pagos, cobros de planes, comisiones, entregas, mensajes, chat de soporte, aceptaciones legales, sesiones, historial
de ingresos y auditoría.
Se CONSERVA: los superadministradores, las loterías, los medios de pago, los precios de las rifas y las cuentas
de RifaPlus (llave Bre-B).
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

# Orden pensado para respetar las llaves foráneas: primero lo que depende de otras tablas
TABLAS = [
    "mensajes_soporte",
    "conversaciones_soporte",
    "mensajes_whatsapp",
    "pagos_comision",
    "entregas_vendedor",
    "pagos",
    "resultados",
    "numeros_boleta",
    "boletas",
    "cuotas_rifa",
    "premios",
    "cobros_rifa",
    "renovaciones_rifa",
    "aceptaciones",
    "rifas",
    "clientes",
    "vendedores",
]


def contar(db: Session) -> dict[str, int]:
    """Cuántos registros se borrarían de cada tabla (para mostrarlos antes de confirmar)."""
    resultado = {t: db.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in TABLAS}  # noqa: S608
    resultado["organizadores"] = db.execute(text("SELECT count(*) FROM organizadores")).scalar()
    resultado["usuarios (no superadmin)"] = db.execute(
        text("SELECT count(*) FROM usuarios WHERE rol <> 'superadmin'")
    ).scalar()
    return resultado


def borrar_datos_de_prueba(db: Session) -> None:
    """Borra todo lo de organizadores y rifas en una sola transacción: o se borra todo, o nada."""
    for tabla in TABLAS:
        db.execute(text(f"DELETE FROM {tabla}"))  # noqa: S608 - nombres fijos de la lista, nunca del usuario
    db.execute(text("DELETE FROM cuentas_cobro WHERE organizador_id IS NOT NULL"))
    db.execute(text("DELETE FROM auditoria"))
    db.execute(text("DELETE FROM historial_accesos"))
    no_admin = "SELECT id FROM usuarios WHERE rol <> 'superadmin'"
    db.execute(text(f"DELETE FROM sesiones WHERE usuario_id IN ({no_admin})"))
    db.execute(text(f"DELETE FROM tokens_seguridad WHERE usuario_id IN ({no_admin})"))
    db.execute(text("DELETE FROM usuarios WHERE rol <> 'superadmin'"))
    db.execute(text("DELETE FROM organizadores"))
    # Si por alguna razón faltan tipos de rifa (por ejemplo, sin la migración de precios), se crean de nuevo
    from app.core.semillas import crear_tipos_faltantes

    crear_tipos_faltantes(db)
    db.commit()
