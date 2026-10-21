"""Páginas legales públicas."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.plantillas import plantillas
from app.modulos.legal.servicio import VERSION_TERMINOS, VERSION_TRATAMIENTO_DATOS

router = APIRouter(tags=["legal"])


@router.get("/terminos", response_class=HTMLResponse)
def terminos(request: Request):
    """Página pública de términos y condiciones."""
    return plantillas.TemplateResponse(request, "legal/terminos.html", {"version": VERSION_TERMINOS})


@router.get("/tratamiento-de-datos", response_class=HTMLResponse)
def tratamiento_datos(request: Request):
    """Página pública de la política de tratamiento de datos personales."""
    return plantillas.TemplateResponse(request, "legal/tratamiento_datos.html", {"version": VERSION_TRATAMIENTO_DATOS})
