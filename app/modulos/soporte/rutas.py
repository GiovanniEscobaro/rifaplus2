"""Rutas del chat de soporte: el organizador escribe desde su panel y el superadministrador responde en /admin."""

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.core.correo import avisar_admin
from app.core.database import obtener_db
from app.core.excepciones import ErrorNegocio, Redirigir
from app.core.plantillas import plantillas
from app.modulos.acceso.dependencias import organizador_actual, superadmin
from app.modulos.acceso.modelos import Usuario
from app.modulos.soporte import servicio
from app.modulos.soporte.modelos import ConversacionSoporte

router = APIRouter(tags=["soporte"])


@router.get("/panel/soporte")
def ver_chat(db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)):
    """Mensajes del chat del organizador (lo consulta el chat del panel cada pocos segundos)."""
    return servicio.a_json(servicio.conversacion_de(db, usuario.organizador_id))


@router.post("/panel/soporte")
async def escribir(
    request: Request,
    tareas: BackgroundTasks,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Recibe un mensaje, una pregunta frecuente o la petición de hablar con una persona."""
    datos = await request.json()
    antes = servicio.conversacion_de(db, usuario.organizador_id).estado
    try:
        conv = servicio.escribir(
            db, usuario, str(datos.get("texto", "")), str(datos.get("pregunta", "")), bool(datos.get("persona"))
        )
    except ErrorNegocio as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    if antes != "pendiente" and conv.estado == "pendiente":  # consulta nueva para una persona: avisar por correo
        ultimo = next((m.texto for m in reversed(conv.mensajes) if m.autor == "organizador"), "")
        tareas.add_task(
            avisar_admin,
            f"Consulta de soporte: {usuario.organizador.nombre}",
            f"{usuario.organizador.nombre} escribió en el chat:\n\n«{ultimo}»\n\n"
            f"Respóndale en {obtener_config().app_url}/admin/soporte/{conv.id}",
        )
    return servicio.a_json(conv)


@router.get("/admin/soporte", response_class=HTMLResponse)
def bandeja(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Bandeja de conversaciones de soporte del superadministrador."""
    return plantillas.TemplateResponse(
        request,
        "admin/soporte.html",
        {"usuario": admin, "conversaciones": servicio.conversaciones(db), "seccion": "soporte", "actual": None},
    )


def _conversacion(db, conversacion_id):
    """Conversación por id, o vuelve a la bandeja."""
    conv = db.get(ConversacionSoporte, conversacion_id)
    if conv is None:
        raise Redirigir("/admin/soporte")
    return conv


@router.get("/admin/soporte/{conversacion_id}", response_class=HTMLResponse)
def conversacion(
    request: Request, conversacion_id: int, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)
):
    """Una conversación con su historial y el formulario para responder."""
    return plantillas.TemplateResponse(
        request,
        "admin/soporte.html",
        {
            "usuario": admin,
            "conversaciones": servicio.conversaciones(db),
            "seccion": "soporte",
            "actual": _conversacion(db, conversacion_id),
        },
    )


@router.post("/admin/soporte/{conversacion_id}")
def responder(
    conversacion_id: int,
    texto: str = Form(""),
    accion: str = Form("responder"),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Responde al organizador, o marca la consulta como atendida sin escribir."""
    conv = _conversacion(db, conversacion_id)
    if accion == "atendida":
        servicio.marcar_atendida(db, conv)
    elif texto.strip():
        servicio.responder(db, admin, conv, texto)
    return RedirectResponse(f"/admin/soporte/{conv.id}#final", status_code=303)
