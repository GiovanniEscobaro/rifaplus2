"""Rutas del equipo del organizador (/panel/equipo)."""

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import obtener_db
from app.core.excepciones import ErrorNegocio, Redirigir
from app.core.plantillas import plantillas
from app.modulos.acceso.dependencias import ip_cliente, organizador_actual
from app.modulos.acceso.modelos import Usuario
from app.modulos.acceso.notificaciones import enviar_invitacion_equipo
from app.modulos.equipo import servicio

router = APIRouter(prefix="/panel/equipo", tags=["equipo"])


def _dueno(usuario: Usuario = Depends(organizador_actual)) -> Usuario:
    """Solo el organizador dueño de la cuenta entra a Equipo."""
    if not servicio.es_dueno(usuario):
        raise Redirigir("/panel")
    return usuario


def _pagina(request, db, usuario, error=None, nuevo=None, codigo=200):
    """Página del equipo: lista de personas y formulario para agregar."""
    return plantillas.TemplateResponse(
        request,
        "equipo/equipo.html",
        {
            "usuario": usuario,
            "miembros": servicio.miembros(db, usuario.organizador_id),
            "error": error,
            "nuevo": nuevo,
            "aviso": request.query_params.get("ok"),
        },
        status_code=codigo,
    )


@router.get("", response_class=HTMLResponse)
def ver(request: Request, db: Session = Depends(obtener_db), usuario: Usuario = Depends(_dueno)):
    """Equipo del organizador."""
    return _pagina(request, db, usuario)


@router.post("", response_class=HTMLResponse)
def agregar(
    request: Request,
    tareas: BackgroundTasks,
    nombre: str = Form(""),
    email: str = Form(""),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(_dueno),
):
    """Agrega un colaborador; le llega la clave temporal al correo y el organizador también la ve una vez."""
    try:
        colaborador, clave = servicio.agregar(db, usuario, nombre, email, ip_cliente(request))
    except ErrorNegocio as e:
        return _pagina(request, db, usuario, str(e), codigo=422)
    tareas.add_task(enviar_invitacion_equipo, colaborador.nombre, colaborador.email, clave, usuario.organizador.nombre)
    return _pagina(
        request, db, usuario, nuevo={"nombre": colaborador.nombre, "email": colaborador.email, "clave": clave}
    )


@router.post("/{colaborador_id}", response_class=HTMLResponse)
def cambiar_estado(
    request: Request,
    colaborador_id: int,
    activo: str = Form(""),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(_dueno),
):
    """Activa o desactiva a un colaborador."""
    try:
        servicio.cambiar_estado(db, usuario, colaborador_id, activo == "true", ip_cliente(request))
    except ErrorNegocio as e:
        return _pagina(request, db, usuario, str(e), codigo=422)
    return RedirectResponse("/panel/equipo?ok=1", status_code=303)
