"""Registro de cambios importantes: quién, qué, cuándo, antes y después."""

from sqlalchemy.orm import Session

from app.modulos.acceso.modelos import Usuario
from app.modulos.auditoria.modelos import Auditoria


def registrar(
    db: Session,
    usuario: Usuario | None,
    tabla: str,
    registro_id: int,
    accion: str,
    *,
    anterior: dict | None = None,
    nuevo: dict | None = None,
    ip: str | None = None,
) -> None:
    """Agrega una fila de auditoría. No hace commit: se guarda junto con el cambio que la origina."""
    db.add(
        Auditoria(
            usuario_id=usuario.id if usuario else None,
            organizador_id=usuario.organizador_id if usuario else None,
            tabla=tabla,
            registro_id=registro_id,
            accion=accion,
            valor_anterior=anterior,
            valor_nuevo=nuevo,
            ip=ip,
        )
    )
