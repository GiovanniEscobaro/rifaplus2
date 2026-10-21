"""Panel principal: organizador o superadministrador."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import obtener_db
from app.core.excepciones import Redirigir
from app.core.plantillas import plantillas
from app.modulos.acceso.dependencias import usuario_actual
from app.modulos.acceso.modelos import Usuario
from app.modulos.rifas.servicio import rifas_del_organizador

router = APIRouter(prefix="/panel", tags=["panel"])


@router.get("", response_class=HTMLResponse)
def inicio(
    request: Request, bienvenida: int = 0, db: Session = Depends(obtener_db), usuario: Usuario = Depends(usuario_actual)
):
    """Panel del organizador con sus rifas. El superadmin se envía a /admin."""
    if usuario.rol == "superadmin":
        raise Redirigir("/admin")
    rifas, vendidas = rifas_del_organizador(db, usuario.organizador_id)
    return plantillas.TemplateResponse(
        request,
        "panel/inicio.html",
        {"usuario": usuario, "rifas": rifas, "vendidas": vendidas, "bienvenida": bienvenida},
    )
