"""Rutas de sorteos: registrar resultados, corregirlos y marcar premios entregados."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import obtener_db
from app.core.excepciones import ErrorNegocio, Redirigir
from app.modulos.acceso.dependencias import ip_cliente, organizador_actual
from app.modulos.acceso.modelos import Usuario
from app.modulos.rifas.servicio import rifa_del_organizador
from app.modulos.sorteos import servicio

router = APIRouter(prefix="/panel/rifas/{rifa_id}/premios/{premio_id}", tags=["sorteos"])


def _rifa(db, rifa_id, usuario):
    """Rifa del organizador conectado, o vuelve al panel."""
    rifa = rifa_del_organizador(db, rifa_id, usuario)
    if rifa is None:
        raise Redirigir("/panel")
    return rifa


def _volver(rifa_id: int, clave: str, valor: str) -> RedirectResponse:
    """Regresa a la sección de sorteos de la rifa con un mensaje de éxito o de error."""
    from urllib.parse import quote

    return RedirectResponse(f"/panel/rifas/{rifa_id}?{clave}={quote(valor)}#sorteos", status_code=303)


@router.post("/resultado")
def registrar(
    request: Request,
    rifa_id: int,
    premio_id: int,
    resultado_loteria: str = Form(""),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Registra el número que cayó en la lotería para un premio."""
    rifa = _rifa(db, rifa_id, usuario)
    try:
        servicio.registrar(db, usuario, rifa, premio_id, resultado_loteria, ip_cliente(request))
    except ErrorNegocio as e:
        db.rollback()
        return _volver(rifa_id, "aviso_error", str(e))
    return _volver(rifa_id, "aviso", "Resultado registrado.")


@router.post("/resultado/borrar")
def borrar(
    request: Request,
    rifa_id: int,
    premio_id: int,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Borra un resultado mal digitado para registrarlo de nuevo."""
    rifa = _rifa(db, rifa_id, usuario)
    try:
        servicio.borrar(db, usuario, rifa, premio_id, ip_cliente(request))
    except ErrorNegocio as e:
        return _volver(rifa_id, "aviso_error", str(e))
    return _volver(rifa_id, "aviso", "Resultado borrado. Puede registrarlo de nuevo.")


@router.post("/entregado")
def entregado(
    request: Request,
    rifa_id: int,
    premio_id: int,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Marca el premio como entregado al ganador."""
    rifa = _rifa(db, rifa_id, usuario)
    try:
        servicio.marcar_entregado(db, usuario, rifa, premio_id, ip_cliente(request))
    except ErrorNegocio as e:
        return _volver(rifa_id, "aviso_error", str(e))
    return _volver(rifa_id, "aviso", "Premio marcado como entregado.")
