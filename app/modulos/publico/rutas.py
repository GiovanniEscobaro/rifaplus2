"""Páginas públicas: inicio y verificación de boletas."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.database import obtener_db
from app.core.plantillas import plantillas
from app.modulos.acceso.dependencias import usuario_opcional
from app.modulos.acceso.modelos import Usuario
from app.modulos.pagos.servicio import planes_activos
from app.modulos.rifas import vigencia
from app.modulos.rifas.servicio import boleta_por_codigo
from app.modulos.sorteos.servicio import premios_de_boleta
from app.modulos.ventas import archivos, boleta_individual
from app.modulos.ventas.servicio import saldo

router = APIRouter(tags=["público"])


@router.get("/", response_class=HTMLResponse)
def inicio(request: Request, db: Session = Depends(obtener_db), usuario: Usuario | None = Depends(usuario_opcional)):
    """Página de inicio pública de RifaPlus, con los planes de la base de datos."""
    return plantillas.TemplateResponse(
        request,
        "publico/inicio.html",
        {
            "planes": planes_activos(db),
            "usuario": usuario,
            "duraciones": vigencia.duraciones_activas(db),
            "precios": vigencia.precios_por_tipo(db),
        },
    )


@router.get("/verificar", response_class=HTMLResponse)
def verificar_formulario(request: Request, codigo: str = ""):
    """Página para escribir el código de una boleta y verificarla."""
    if codigo:
        return RedirectResponse(f"/verificar/{codigo.strip().upper()}", status_code=303)
    return plantillas.TemplateResponse(request, "publico/verificar.html", {"boleta": None, "codigo": ""})


@router.get("/verificar/{codigo}", response_class=HTMLResponse)
def verificar(request: Request, codigo: str, db: Session = Depends(obtener_db)):
    """Muestra si una boleta es auténtica, su estado de pago y si ganó algún premio."""
    boleta = boleta_por_codigo(db, codigo)
    estado_pago = saldo(db, boleta).estado if boleta and boleta.estado == "vendida" else None
    return plantillas.TemplateResponse(
        request,
        "publico/verificar.html",
        {
            "boleta": boleta,
            "codigo": codigo.upper(),
            "estado_pago": estado_pago,
            "ganados": premios_de_boleta(db, boleta) if boleta else [],
        },
        status_code=200 if boleta else 404,
    )


@router.get("/boleta/{codigo}", response_class=HTMLResponse)
def boleta_publica(request: Request, codigo: str, db: Session = Depends(obtener_db)):
    """Boleta individual que recibe el comprador por WhatsApp (sin su documento ni celular)."""
    boleta = boleta_por_codigo(db, codigo)
    if boleta is None or boleta.estado != "vendida":
        return RedirectResponse(f"/verificar/{codigo.upper()}", status_code=303)
    return plantillas.TemplateResponse(
        request, "boletas/boleta.html", {"b": boleta_individual.armar(db, boleta, completa=False)}
    )


@router.get("/archivos/{ruta:path}")
def foto_publica(ruta: str):
    """Fotos de premios (públicas, se ven en la boleta). Solo sirve la carpeta fotos/, nunca comprobantes."""
    if not ruta.startswith("fotos/") or ".." in ruta:
        return Response(status_code=404)
    archivo = archivos.ruta_absoluta(ruta)
    if archivo is None:
        return Response(status_code=404)
    return FileResponse(archivo, headers={"Cache-Control": "public, max-age=604800"})
