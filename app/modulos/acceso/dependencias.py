"""Dependencias de FastAPI: quién está conectado y qué puede hacer."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.database import obtener_db
from app.core.excepciones import Redirigir
from app.modulos.acceso.modelos import Usuario
from app.modulos.acceso.sesiones import NOMBRE_COOKIE, usuario_de_token


def ip_cliente(request: Request) -> str | None:
    """IP de quien hace la petición; respeta X-Forwarded-For cuando hay un proxy (Nginx) delante."""
    reenviada = request.headers.get("x-forwarded-for")
    return reenviada.split(",")[0].strip() if reenviada else (request.client.host if request.client else None)


def usuario_opcional(request: Request, db: Session = Depends(obtener_db)) -> Usuario | None:
    """Usuario de la cookie de sesión, o None si nadie ha ingresado. Para páginas públicas."""
    return usuario_de_token(db, request.cookies.get(NOMBRE_COOKIE))


def usuario_con_clave_pendiente(usuario: Usuario | None = Depends(usuario_opcional)) -> Usuario:
    """Usuario conectado, aunque todavía no haya cambiado su clave temporal."""
    if usuario is None:
        raise Redirigir("/ingresar")
    return usuario


def usuario_actual(usuario: Usuario = Depends(usuario_con_clave_pendiente)) -> Usuario:
    """Usuario conectado que ya cambió su clave; si no la ha cambiado, se le obliga."""
    if usuario.debe_cambiar_clave:
        raise Redirigir("/cambiar-clave")
    return usuario


def organizador_actual(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Exige un usuario de organizador (no superadmin). Lo usan todas las rutas del panel."""
    if usuario.organizador_id is None:
        raise Redirigir("/panel")
    return usuario


def superadmin(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Exige el rol superadmin. Lo usan todas las rutas de /admin."""
    if usuario.rol != "superadmin":
        raise Redirigir("/panel")
    return usuario
