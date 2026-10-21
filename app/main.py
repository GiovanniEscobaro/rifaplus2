"""Punto de entrada de RifaPlus.

Desarrollo:  uvicorn app.main:app --reload
"""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

import app.core.registro_modelos  # noqa: F401  (registra todos los modelos antes de usarlos)
from app.core.config import obtener_config
from app.core.database import motor
from app.core.excepciones import Redirigir
from app.modulos.acceso.rutas import router as rutas_acceso
from app.modulos.admin.rutas import router as rutas_admin
from app.modulos.equipo.rutas import router as rutas_equipo
from app.modulos.informes.rutas import router as rutas_informes
from app.modulos.legal.rutas import router as rutas_legal
from app.modulos.panel.rutas import router as rutas_panel
from app.modulos.publico.rutas import router as rutas_publico
from app.modulos.rifas.rutas import router as rutas_rifas
from app.modulos.soporte.rutas import router as rutas_soporte
from app.modulos.sorteos.rutas import router as rutas_sorteos
from app.modulos.ventas.rutas import router as rutas_ventas

ESTATICOS = Path(__file__).resolve().parent / "web" / "estaticos"


def crear_app() -> FastAPI:
    """Construye la aplicación: estáticos, rutas de cada módulo y manejo de redirecciones."""
    cfg = obtener_config()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = FastAPI(title=cfg.app_nombre, docs_url="/docs" if cfg.es_desarrollo else None, redoc_url=None)
    app.mount("/estaticos", StaticFiles(directory=ESTATICOS), name="estaticos")
    for router in (
        rutas_publico,
        rutas_legal,
        rutas_acceso,
        rutas_panel,
        rutas_rifas,
        rutas_ventas,
        rutas_admin,
        rutas_sorteos,
        rutas_informes,
        rutas_soporte,
        rutas_equipo,
    ):
        app.include_router(router)

    @app.exception_handler(Redirigir)
    async def redirigir(request: Request, exc: Redirigir):
        """Convierte la excepción Redirigir en una redirección 303 (por ejemplo, al ingreso)."""
        return RedirectResponse(exc.url, status_code=303)

    @app.get("/health", include_in_schema=False, response_class=PlainTextResponse)
    def health():
        """Responde «OK» si la app está viva y llega a la base de datos; si no, error 503. Para Docker y monitores."""
        try:
            with motor.connect() as conexion:
                conexion.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001 - cualquier falla de conexión cuenta como «no está lista»
            return PlainTextResponse("ERROR: sin conexión a la base de datos", status_code=503)
        return "OK"

    @app.get("/salud", include_in_schema=False)
    def salud():
        """Igual que /health, en el formato anterior ({"estado": "ok"})."""
        return {"estado": "ok"}

    return app


app = crear_app()
