"""Zona del superadministrador (/admin): solo para el rol superadmin."""

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.core.correo import enviar_con_detalle
from app.core.database import obtener_db
from app.core.excepciones import ErrorNegocio, Redirigir
from app.core.plantillas import plantillas, solo_digitos
from app.modulos.acceso.dependencias import ip_cliente, superadmin
from app.modulos.acceso.modelos import Organizador, Usuario
from app.modulos.acceso.notificaciones import enviar_clave_restablecida
from app.modulos.acceso.servicio import restablecer_por_admin
from app.modulos.admin import catalogos, servicio
from app.modulos.admin import datos as datos_bd
from app.modulos.auditoria import servicio as auditoria
from app.modulos.pagos.modelos import CobroRifa, CuentaCobro, Duracion, RenovacionRifa
from app.modulos.pagos.servicio import medios_para_rifaplus
from app.modulos.rifas import vigencia
from app.modulos.rifas.modelos import Loteria, Rifa
from app.modulos.ventas import archivos

router = APIRouter(prefix="/admin", tags=["superadministrador"])

AVISOS = {
    "suspendido": "El organizador quedó suspendido: ya no puede ingresar.",
    "verificado": "Organizador verificado: ya puede publicar todas sus rifas.",
    "sin_verificar": "Se quitó la verificación del organizador.",
    "activo": "El organizador quedó activo.",
    "rifa_eliminada": "La rifa fue eliminada con todas sus boletas y pagos.",
    "organizador_eliminado": "El organizador fue eliminado.",
    "aprobado": "Pago aprobado: la rifa quedó publicada.",
    "cuenta": "Cuenta guardada.",
    "plan": "Precios guardados. Aplican a las rifas que se creen desde ahora.",
    "tipos": "Se crearon los tipos de rifa que faltaban, con su precio inicial. Revíselos y guarde.",
    "tipo": "Tipo de rifa agregado. Póngale precios, márquelo en «Se ofrece» y guarde la tabla.",
    "duracion": "Duración guardada. Si es nueva, póngale precios a cada tipo de rifa y guarde la tabla.",
    "loteria": "Lotería guardada.",
    "cobro": "Valor del cobro actualizado.",
    "rechazado": "Cobro rechazado.",
    "renovacion_aprobado": "Renovación aprobada: la rifa quedó vigente por el nuevo período.",
    "renovacion_rechazado": "Renovación rechazada.",
}


def _pagina(request, nombre, contexto, codigo=200):
    """Muestra una plantilla de /admin agregando el aviso de la acción anterior (?ok=...)."""
    contexto.setdefault("aviso", AVISOS.get(request.query_params.get("ok", "")))
    return plantillas.TemplateResponse(request, f"admin/{nombre}.html", contexto, status_code=codigo)


@router.get("", response_class=HTMLResponse)
def inicio(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Resumen general de RifaPlus para el superadministrador."""
    return _pagina(
        request,
        "inicio",
        {
            "usuario": admin,
            "r": servicio.resumen(db),
            "seccion": "inicio",
            "ultimos": servicio.organizadores(db)[:8],
            "correo_activo": obtener_config().correo_activo,
        },
    )


@router.get("/organizadores", response_class=HTMLResponse)
def organizadores(
    request: Request,
    buscar: str = "",
    estado: str = "",
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Lista de organizadores con búsqueda y filtro por estado."""
    return _pagina(
        request,
        "organizadores",
        {
            "usuario": admin,
            "filas": servicio.organizadores(db, buscar, estado),
            "buscar": buscar,
            "estado": estado,
            "seccion": "organizadores",
        },
    )


def _organizador(db, organizador_id):
    """Busca el organizador o vuelve a la lista si no existe."""
    organizador = db.get(Organizador, organizador_id)
    if organizador is None:
        raise Redirigir("/admin/organizadores")
    return organizador


def _detalle(request, db, admin, organizador, error=None, codigo=200, clave_temporal=None):
    """Muestra la ficha de un organizador con sus rifas."""
    return _pagina(
        request,
        "organizador",
        {
            "usuario": admin,
            "o": organizador,
            "rifas": servicio.rifas_de(db, organizador.id),
            "error": error,
            "seccion": "organizadores",
            "clave_temporal": clave_temporal,
        },
        codigo,
    )


@router.get("/organizadores/{organizador_id}", response_class=HTMLResponse)
def organizador(
    request: Request, organizador_id: int, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)
):
    """Ficha de un organizador: contacto, rifas y acciones."""
    return _detalle(request, db, admin, _organizador(db, organizador_id))


@router.post("/organizadores/{organizador_id}/estado")
def cambiar_estado(
    request: Request,
    organizador_id: int,
    nuevo: str = Form(...),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Suspende o reactiva a un organizador."""
    servicio.cambiar_estado(db, admin, _organizador(db, organizador_id), nuevo, ip_cliente(request))
    return RedirectResponse(f"/admin/organizadores/{organizador_id}?ok={nuevo}", status_code=303)


@router.post("/organizadores/{organizador_id}/eliminar", response_class=HTMLResponse)
def eliminar_organizador(
    request: Request,
    organizador_id: int,
    confirmacion: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Elimina un organizador sin rifas, después de confirmar su correo."""
    organizador = _organizador(db, organizador_id)
    try:
        servicio.eliminar_organizador(db, admin, organizador, confirmacion, ip_cliente(request))
    except ErrorNegocio as e:
        db.rollback()
        return _detalle(request, db, admin, organizador, str(e), 422)
    return RedirectResponse("/admin/organizadores?ok=organizador_eliminado", status_code=303)


@router.post("/rifas/{rifa_id}/eliminar", response_class=HTMLResponse)
def eliminar_rifa(
    request: Request,
    rifa_id: int,
    confirmacion: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Elimina una rifa con todo lo suyo, después de confirmar su nombre."""
    rifa = db.get(Rifa, rifa_id)
    if rifa is None:
        raise Redirigir("/admin/organizadores")
    organizador_id = rifa.organizador_id
    try:
        servicio.eliminar_rifa(db, admin, rifa, confirmacion, ip_cliente(request))
    except ErrorNegocio as e:
        db.rollback()
        return _detalle(request, db, admin, _organizador(db, organizador_id), str(e), 422)
    return RedirectResponse(f"/admin/organizadores/{organizador_id}?ok=rifa_eliminada", status_code=303)


@router.get("/cobros", response_class=HTMLResponse)
def cobros(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Lista de cobros de rifas de pago que esperan revisión."""
    return _pagina(
        request,
        "cobros",
        {
            "usuario": admin,
            "cobros": servicio.cobros_pendientes(db),
            "seccion": "cobros",
            "error": None,
            "renovaciones": vigencia.renovaciones_por_revisar(db),
        },
    )


@router.post("/cobros/{cobro_id}", response_class=HTMLResponse)
def revisar_cobro(
    request: Request,
    cobro_id: int,
    accion: str = Form(...),
    referencia: str = Form(""),
    motivo: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Aprueba o rechaza el cobro del plan de una rifa."""
    cobro = db.get(CobroRifa, cobro_id)
    if cobro is None:
        raise Redirigir("/admin/cobros")
    try:
        servicio.revisar_cobro(db, admin, cobro, accion == "aprobar", referencia, motivo, ip_cliente(request))
    except ErrorNegocio as e:
        return _pagina(
            request,
            "cobros",
            {
                "usuario": admin,
                "cobros": servicio.cobros_pendientes(db),
                "seccion": "cobros",
                "error": str(e),
                "renovaciones": vigencia.renovaciones_por_revisar(db),
            },
            422,
        )
    return RedirectResponse(f"/admin/cobros?ok={cobro.estado}", status_code=303)


@router.get("/cobros/{cobro_id}/comprobante")
def ver_comprobante(cobro_id: int, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Foto del comprobante que envió el organizador para pagar su plan."""
    cobro = db.get(CobroRifa, cobro_id)
    ruta = archivos.ruta_absoluta(cobro.comprobante_url) if cobro and cobro.comprobante_url else None
    if ruta is None:
        raise Redirigir("/admin/cobros")
    return FileResponse(ruta)


def _pagina_cuentas(request, db, admin, error=None, codigo=200):
    """Cuentas de Nequi y Daviplata de RifaPlus."""
    return _pagina(
        request,
        "cuentas",
        {
            "usuario": admin,
            "cuentas": servicio.cuentas_rifaplus(db),
            "medios": medios_para_rifaplus(db),
            "seccion": "cuentas",
            "error": error,
        },
        codigo,
    )


@router.get("/cuentas", response_class=HTMLResponse)
def cuentas(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Cuentas donde los organizadores pagan sus planes."""
    return _pagina_cuentas(request, db, admin)


@router.post("/cuentas", response_class=HTMLResponse)
def crear_cuenta(
    request: Request,
    medio_pago_id: int = Form(0),
    numero_cuenta: str = Form(""),
    titular: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Agrega una cuenta de RifaPlus."""
    try:
        servicio.crear_cuenta(db, admin, medio_pago_id, numero_cuenta, titular, ip_cliente(request))
    except ErrorNegocio as e:
        return _pagina_cuentas(request, db, admin, str(e), 422)
    return RedirectResponse("/admin/cuentas?ok=cuenta", status_code=303)


@router.post("/cuentas/{cuenta_id}")
def cambiar_cuenta(
    request: Request,
    cuenta_id: int,
    activa: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Activa o desactiva una cuenta de RifaPlus."""
    cuenta = db.get(CuentaCobro, cuenta_id)
    if cuenta is not None and cuenta.organizador_id is None:
        servicio.cambiar_cuenta(db, admin, cuenta, activa == "true", ip_cliente(request))
    return RedirectResponse("/admin/cuentas?ok=cuenta", status_code=303)


# ---------- Base de datos (solo lectura) ----------
@router.get("/datos", response_class=HTMLResponse)
def datos(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Lista de tablas de la base de datos con su número de registros."""
    return _pagina(request, "datos", {"usuario": admin, "tablas": datos_bd.tablas(db), "seccion": "datos"})


@router.get("/datos/consulta", response_class=HTMLResponse)
def consulta_formulario(request: Request, admin: Usuario = Depends(superadmin)):
    """Formulario para escribir una consulta SQL de solo lectura."""
    return _pagina(request, "consulta", {"usuario": admin, "sql": "", "r": None, "seccion": "datos"})


@router.post("/datos/consulta", response_class=HTMLResponse)
def consulta(
    request: Request,
    sql: str = Form(""),
    descargar: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Ejecuta la consulta en solo lectura y muestra el resultado (o lo descarga en CSV)."""
    try:
        resultado = datos_bd.consultar(db, sql)
    except ErrorNegocio as e:
        return _pagina(
            request, "consulta", {"usuario": admin, "sql": sql, "r": None, "error": str(e), "seccion": "datos"}, 422
        )
    auditoria.registrar(db, admin, "consultas_sql", 0, "consultar", ip=ip_cliente(request), nuevo={"sql": sql[:2000]})
    db.commit()
    if descargar:
        return Response(
            datos_bd.a_csv(resultado),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="consulta-rifaplus.csv"'},
        )
    return _pagina(request, "consulta", {"usuario": admin, "sql": sql, "r": resultado, "seccion": "datos"})


@router.get("/datos/{tabla}.csv")
def tabla_csv(tabla: str, buscar: str = "", db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Descarga la tabla completa (con el filtro de búsqueda, si lo hay) en CSV para Excel."""
    try:
        resultado = datos_bd.ver_tabla(db, tabla, buscar=buscar, todas=True)
    except ErrorNegocio:
        raise Redirigir("/admin/datos") from None
    return Response(
        datos_bd.a_csv(resultado),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{tabla}.csv"'},
    )


@router.get("/datos/{tabla}", response_class=HTMLResponse)
def ver_tabla(
    request: Request,
    tabla: str,
    pagina: int = 1,
    buscar: str = "",
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Registros de una tabla, por páginas y con búsqueda."""
    try:
        resultado = datos_bd.ver_tabla(db, tabla, pagina, buscar)
    except ErrorNegocio:
        raise Redirigir("/admin/datos") from None
    return _pagina(
        request, "tabla", {"usuario": admin, "tabla": tabla, "r": resultado, "buscar": buscar, "seccion": "datos"}
    )


@router.post("/organizadores/{organizador_id}/restablecer-clave", response_class=HTMLResponse)
def restablecer_clave(
    request: Request,
    organizador_id: int,
    tareas: BackgroundTasks,
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Le pone una clave temporal nueva al organizador, se la envía al correo y se la muestra al superadmin una vez."""
    organizador = _organizador(db, organizador_id)
    usuario = db.scalar(select(Usuario).where(Usuario.organizador_id == organizador.id, Usuario.rol == "admin"))
    if usuario is None:
        return _detalle(request, db, admin, organizador, "Este organizador no tiene usuario para ingresar.", 422)
    clave = restablecer_por_admin(db, usuario)
    auditoria.registrar(db, admin, "usuarios", usuario.id, "restablecer_clave", ip=ip_cliente(request))
    db.commit()
    tareas.add_task(enviar_clave_restablecida, usuario.nombre, usuario.email, clave)
    return _detalle(request, db, admin, organizador, clave_temporal=clave)


@router.post("/probar-correo", response_class=HTMLResponse)
def probar_correo(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Envía un correo de prueba y muestra qué pasó, para revisar la configuración de Gmail."""
    destino = obtener_config().correo_avisos_admin or admin.email
    ok, mensaje = enviar_con_detalle(
        destino, "Prueba de correo de RifaPlus", "Si recibe este mensaje, el correo de RifaPlus está bien configurado."
    )
    contexto = {
        "usuario": admin,
        "r": servicio.resumen(db),
        "seccion": "inicio",
        "ultimos": servicio.organizadores(db)[:8],
        "correo_activo": obtener_config().correo_activo,
    }
    contexto["aviso" if ok else "error"] = mensaje
    return _pagina(request, "inicio", contexto, 200 if ok else 422)


# ---------- Precios por tipo de rifa y duración ----------
def _pagina_planes(request, db, admin, error=None, codigo=200):
    """Tabla de tipos de rifa × duraciones, más los formularios para agregar tipos y duraciones."""
    return _pagina(
        request,
        "planes",
        {
            "usuario": admin,
            "tipos": catalogos.tipos_de_rifa(db),
            "duraciones": catalogos.duraciones(db),
            "precios": vigencia.precios_por_tipo(db),
            "seccion": "planes",
            "error": error,
        },
        codigo,
    )


@router.get("/planes", response_class=HTMLResponse)
def ver_planes(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Precios de cada tipo de rifa por cada duración."""
    return _pagina_planes(request, db, admin)


@router.post("/planes/crear-tipos")
def crear_tipos(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Crea los tipos de rifa iniciales que falten, con su precio inicial (no cambia los que ya existen)."""
    from app.core.semillas import crear_tipos_faltantes

    creados = crear_tipos_faltantes(db)
    auditoria.registrar(db, admin, "planes", 0, "crear_tipos", ip=ip_cliente(request), nuevo={"creados": creados})
    db.commit()
    return RedirectResponse("/admin/planes?ok=tipos", status_code=303)


@router.post("/planes/tipo", response_class=HTMLResponse)
def crear_tipo(
    request: Request,
    boletas: str = Form(""),
    cifras: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Agrega un tipo de rifa nuevo (queda inactivo y con precios en 0 para que usted los ponga)."""
    try:
        catalogos.crear_tipo(
            db, admin, int(solo_digitos(boletas) or 0), int(solo_digitos(cifras) or 0), ip_cliente(request)
        )
    except ErrorNegocio as e:
        db.rollback()
        return _pagina_planes(request, db, admin, str(e), 422)
    return RedirectResponse("/admin/planes?ok=tipo", status_code=303)


@router.post("/planes/duracion", response_class=HTMLResponse)
@router.post("/planes/duracion/{duracion_id}", response_class=HTMLResponse)
def guardar_duracion(
    request: Request,
    duracion_id: int | None = None,
    nombre: str = Form(""),
    meses: str = Form(""),
    activa: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Crea o cambia una duración (por ejemplo «6 meses» o «1 año»)."""
    duracion = db.get(Duracion, duracion_id) if duracion_id else None
    try:
        catalogos.guardar_duracion(
            db, admin, duracion, nombre, int(solo_digitos(meses) or 0), activa == "true", ip_cliente(request)
        )
    except ErrorNegocio as e:
        db.rollback()
        return _pagina_planes(request, db, admin, str(e), 422)
    return RedirectResponse("/admin/planes?ok=duracion", status_code=303)


@router.post("/planes", response_class=HTMLResponse)
async def guardar_precios(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Guarda de una vez la tabla de precios (tipo × duración) y qué tipos se ofrecen."""
    f = await request.form()
    precios, activos = {}, set()
    for clave, valor in f.items():
        if clave.startswith("precio_"):
            _, plan_id, duracion_id = clave.split("_")
            precios[(int(plan_id), int(duracion_id))] = int(solo_digitos(valor) or 0)
        elif clave.startswith("activo_") and valor == "true":
            activos.add(int(clave.split("_")[1]))
    try:
        catalogos.guardar_precios(db, admin, precios, activos, ip_cliente(request))
    except ErrorNegocio as e:
        db.rollback()
        return _pagina_planes(request, db, admin, str(e), 422)
    return RedirectResponse("/admin/planes?ok=plan", status_code=303)


# ---------- Loterías ----------
def _pagina_loterias(request, db, admin, error=None, codigo=200):
    """Loterías con las que juegan las rifas."""
    return _pagina(
        request,
        "loterias",
        {"usuario": admin, "loterias": catalogos.loterias(db), "seccion": "loterias", "error": error},
        codigo,
    )


@router.get("/loterias", response_class=HTMLResponse)
def ver_loterias(request: Request, db: Session = Depends(obtener_db), admin: Usuario = Depends(superadmin)):
    """Loterías disponibles para las rifas."""
    return _pagina_loterias(request, db, admin)


@router.post("/loterias", response_class=HTMLResponse)
@router.post("/loterias/{loteria_id}", response_class=HTMLResponse)
def guardar_loteria(
    request: Request,
    loteria_id: int | None = None,
    nombre: str = Form(""),
    dias: str = Form(""),
    activa: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Agrega una lotería o guarda los cambios de una existente."""
    loteria = db.get(Loteria, loteria_id) if loteria_id else None
    try:
        catalogos.guardar_loteria(db, admin, loteria, nombre, dias, activa == "true", ip_cliente(request))
    except ErrorNegocio as e:
        db.rollback()
        return _pagina_loterias(request, db, admin, str(e), 422)
    return RedirectResponse("/admin/loterias?ok=loteria", status_code=303)


# ---------- Valor del cobro de una rifa ----------
@router.post("/rifas/{rifa_id}/cobro", response_class=HTMLResponse)
def ajustar_cobro(
    request: Request,
    rifa_id: int,
    valor: str = Form(""),
    motivo: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Cambia el valor que paga una rifa (descuento o cortesía)."""
    rifa = db.get(Rifa, rifa_id)
    if rifa is None:
        raise Redirigir("/admin/organizadores")
    try:
        catalogos.ajustar_cobro(db, admin, rifa, int(solo_digitos(valor) or 0), motivo, ip_cliente(request))
    except ErrorNegocio as e:
        db.rollback()
        return _detalle(request, db, admin, _organizador(db, rifa.organizador_id), str(e), 422)
    return RedirectResponse(f"/admin/organizadores/{rifa.organizador_id}?ok=cobro", status_code=303)


@router.post("/renovaciones/{renovacion_id}", response_class=HTMLResponse)
def revisar_renovacion(
    request: Request,
    renovacion_id: int,
    accion: str = Form(...),
    motivo: str = Form(""),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Aprueba (extiende la vigencia y desbloquea) o rechaza una renovación."""
    renovacion = db.get(RenovacionRifa, renovacion_id)
    if renovacion is None:
        raise Redirigir("/admin/cobros")
    try:
        vigencia.revisar_renovacion(db, renovacion, admin.id, accion == "aprobar", motivo)
        auditoria.registrar(
            db,
            admin,
            "renovaciones_rifa",
            renovacion.id,
            renovacion.estado,
            ip=ip_cliente(request),
            nuevo={"rifa_id": renovacion.rifa_id, "meses": renovacion.meses},
        )
        db.commit()
    except ErrorNegocio as e:
        db.rollback()
        return _pagina(
            request,
            "cobros",
            {
                "usuario": admin,
                "cobros": servicio.cobros_pendientes(db),
                "renovaciones": vigencia.renovaciones_por_revisar(db),
                "seccion": "cobros",
                "error": str(e),
            },
            422,
        )
    return RedirectResponse(f"/admin/cobros?ok=renovacion_{renovacion.estado}", status_code=303)


@router.post("/organizadores/{organizador_id}/verificacion", response_class=HTMLResponse)
def cambiar_verificacion(
    request: Request,
    organizador_id: int,
    accion: str = Form(...),
    db: Session = Depends(obtener_db),
    admin: Usuario = Depends(superadmin),
):
    """Verifica o quita la verificación de identidad del organizador."""
    organizador = _organizador(db, organizador_id)
    try:
        servicio.cambiar_verificacion(db, admin, organizador, accion == "verificar", ip_cliente(request))
    except ErrorNegocio as e:
        return _detalle(request, db, admin, organizador, str(e), 422)
    return RedirectResponse(
        f"/admin/organizadores/{organizador.id}?ok={'verificado' if accion == 'verificar' else 'sin_verificar'}",
        status_code=303,
    )
