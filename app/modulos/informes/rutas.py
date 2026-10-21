"""Rutas de informes de ventas (reemplazan la antigua búsqueda de compradores)."""

from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import obtener_db
from app.core.plantillas import plantillas
from app.modulos.acceso.dependencias import organizador_actual
from app.modulos.acceso.modelos import Usuario
from app.modulos.informes import servicio
from app.modulos.rifas.modelos import Rifa
from app.modulos.ventas.servicio import vendedores

router = APIRouter(prefix="/panel", tags=["informes"])


def _filtros(rifa: str, vendedor: str, ciudad: str, comprador: str, estado: str) -> servicio.Filtros:
    """Convierte los parámetros de la dirección en filtros."""
    return servicio.Filtros(
        rifa_id=int(rifa) if rifa.isdigit() else None,
        vendedor=vendedor,
        ciudad=ciudad,
        comprador=comprador,
        estado=estado if estado in servicio.ESTADOS else "",
    )


@router.get("/informes", response_class=HTMLResponse)
def informes(
    request: Request,
    rifa: str = "",
    vendedor: str = "",
    ciudad: str = "",
    comprador: str = "",
    estado: str = "",
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Informe de boletas vendidas con filtros por rifa, vendedor, ciudad, comprador y estado de pago."""
    filtros = _filtros(rifa, vendedor, ciudad, comprador, estado)
    # Al abrir la página no se consulta nada; al tocar "Ver informe" (aunque sin filtros) se muestra todo
    informe = servicio.generar(db, usuario.organizador_id, filtros) if request.url.query else None
    rifas = db.scalars(
        select(Rifa).where(Rifa.organizador_id == usuario.organizador_id).order_by(Rifa.fecha_creacion.desc())
    ).all()
    return plantillas.TemplateResponse(
        request,
        "informes/informes.html",
        {
            "usuario": usuario,
            "f": filtros,
            "informe": informe,
            "rifas": rifas,
            "estados": servicio.ESTADOS,
            "vendedores": vendedores(db, usuario.organizador_id, solo_activos=False),
            "max_filas": servicio.MAX_FILAS_PANTALLA,
            "consulta": request.url.query,
        },
    )


@router.get("/informes.csv")
def informes_csv(
    rifa: str = "",
    vendedor: str = "",
    ciudad: str = "",
    comprador: str = "",
    estado: str = "",
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Descarga el mismo informe en CSV para abrirlo en Excel."""
    informe = servicio.generar(db, usuario.organizador_id, _filtros(rifa, vendedor, ciudad, comprador, estado))
    nombre = f"informe-rifaplus-{date.today().isoformat()}.csv"
    return Response(
        servicio.a_csv(informe),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/compradores")
def compradores_antiguo(buscar: str = ""):
    """La antigua página de compradores ahora es parte de Informes."""
    return RedirectResponse(f"/panel/informes?comprador={buscar}", status_code=303)
