"""Versiones vigentes de los documentos legales y registro de aceptaciones."""

from sqlalchemy.orm import Session

from app.modulos.legal.modelos import Aceptacion

# Cambie la versión cada vez que modifique el texto: las aceptaciones guardan con cuál versión se aceptó.
VERSION_TERMINOS = "2026-10"
VERSION_TRATAMIENTO_DATOS = "2026-10"
VERSION_DECLARACION = "2026-10"

TEXTO_DECLARACION_RIFA = (
    "Declaro que soy el organizador y único responsable de esta rifa; que cuento o contaré con la autorización "
    "requerida antes de vender boletas; que el premio no es en dinero ni es un bien usado; y que RifaPlus solo "
    "me presta la herramienta de administración y no organiza, opera ni garantiza la rifa."
)

AVISO_PUBLICO = (
    "RifaPlus es una plataforma de administración. La rifa, sus premios y su autorización son responsabilidad "
    "exclusiva del organizador."
)


def registrar(
    db: Session,
    *,
    usuario_id: int,
    organizador_id: int | None,
    documento: str,
    version: str,
    ip: str | None,
    rifa_id: int | None = None,
    texto: str | None = None,
) -> None:
    """Guarda una aceptación legal. No hace commit: va en la misma transacción del registro o la rifa."""
    db.add(
        Aceptacion(
            usuario_id=usuario_id,
            organizador_id=organizador_id,
            rifa_id=rifa_id,
            documento=documento,
            version=version,
            texto_aceptado=texto,
            ip=ip,
        )
    )
