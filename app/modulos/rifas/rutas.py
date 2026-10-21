"""Rutas de rifas del organizador."""

from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.core.correo import avisar_admin
from app.core.database import obtener_db
from app.core.excepciones import ErrorNegocio, Redirigir
from app.core.plantillas import errores_de_validacion, pesos, plantillas, solo_digitos
from app.modulos.acceso.dependencias import ip_cliente, organizador_actual
from app.modulos.acceso.modelos import Usuario
from app.modulos.auditoria import servicio as auditoria
from app.modulos.legal.servicio import TEXTO_DECLARACION_RIFA
from app.modulos.pagos.servicio import cuentas_rifaplus, enviar_pago_rifa, medios_para_rifaplus
from app.modulos.rifas import servicio, vigencia
from app.modulos.rifas.esquemas import REGLAS_MAYOR, REGLAS_SECO, PremioSecoDatos, RifaCrear
from app.modulos.sorteos import servicio as servicio_sorteos
from app.modulos.ventas.archivos import foto_propia, guardar_comprobante, guardar_foto

router = APIRouter(prefix="/panel/rifas", tags=["rifas"])

CAMPOS_OPCIONALES = ("valor_premio", "descripcion")


def _obtener(db: Session, rifa_id: int, usuario: Usuario):
    """Rifa del organizador conectado, o vuelve al panel si no es suya."""
    rifa = servicio.rifa_del_organizador(db, rifa_id, usuario)
    if rifa is None:
        raise Redirigir("/panel")
    return rifa


def _cuotas_y_secos(formulario: dict, organizador_id: int) -> tuple[list[dict], list[dict]]:
    """Lee las filas dinámicas del formulario: cuota_valor_1, cuota_fecha_1… y seco_descripcion_1…"""
    cuotas, secos = [], []
    for i in range(1, 13):
        valor, fecha = formulario.get(f"cuota_valor_{i}", ""), formulario.get(f"cuota_fecha_{i}", "")
        if valor or fecha:
            cuotas.append({"valor": solo_digitos(valor) or 0, "fecha_limite": fecha or None})
    for i in range(1, 25):
        fila = {c: formulario.get(f"seco_{c}_{i}", "") for c in ("descripcion", "loteria_id", "fecha_juego")}
        valor = solo_digitos(formulario.get(f"seco_valor_estimado_{i}", ""))
        if any(fila.values()):
            foto = foto_propia(formulario.get(f"seco_foto_actual_{i}"), organizador_id)
            secos.append({k: v or None for k, v in fila.items()} | {"valor_estimado": valor or None, "foto_url": foto})
    return cuotas, secos


async def _guardar_fotos(formulario: dict, organizador_id: int) -> None:
    """Guarda las fotos subidas y deja su ruta en los campos ocultos *_actual del formulario.

    Así, si el formulario tiene errores y se vuelve a mostrar, las fotos ya subidas no se pierden.
    """
    for campo, destino in [("foto_mayor", "foto_mayor_actual")] + [
        (f"seco_foto_{i}", f"seco_foto_actual_{i}") for i in range(1, 25)
    ]:
        archivo = formulario.pop(campo, None)
        if archivo is not None and not isinstance(archivo, str):
            ruta = await guardar_foto(archivo, organizador_id)
            if ruta:
                formulario[destino] = ruta


def _datos_rifa(formulario: dict, organizador_id: int) -> dict:
    """Convierte el formulario de rifa en los datos de RifaCrear (dinero sin puntos, cuotas y premios secos)."""
    datos = {
        k: v
        for k, v in formulario.items()
        if not (k in CAMPOS_OPCIONALES and not v) and not k.startswith(("cuota_", "seco_"))
    }
    for clave in ("valor_boleta", "valor_premio"):
        if clave in datos:
            datos[clave] = solo_digitos(datos[clave]) or None
    datos["acepta_declaracion"] = formulario.get("acepta_declaracion") == "true"
    datos["cuotas"], datos["premios_secos"] = _cuotas_y_secos(formulario, organizador_id)
    datos["foto_mayor_url"] = foto_propia(formulario.get("foto_mayor_actual"), organizador_id)
    return datos


def _formulario(request, db, usuario, datos, errores, codigo=200, rifa=None):
    """Muestra el formulario de nueva rifa con opciones, loterías, reglas y errores."""
    return plantillas.TemplateResponse(
        request,
        "rifas/nueva.html",
        {
            "usuario": usuario,
            "loterias": servicio.loterias_activas(db),
            "opciones": servicio.opciones(db),
            "datos": datos,
            "errores": errores,
            "declaracion": TEXTO_DECLARACION_RIFA,
            "reglas_seco": REGLAS_SECO,
            "reglas_mayor": REGLAS_MAYOR,
            "rifa": rifa,
            "duraciones": vigencia.duraciones_activas(db),
            "precios": vigencia.precios_por_tipo(db),
        },
        status_code=codigo,
    )


@router.get("/nueva", response_class=HTMLResponse)
def nueva_formulario(
    request: Request, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)
):
    """Formulario vacío para crear una rifa."""
    return _formulario(request, db, usuario, {}, [])


@router.post("/nueva", response_class=HTMLResponse)
async def crear(request: Request, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)):
    """Recibe el formulario, crea la rifa con todas sus boletas y lleva a su página."""
    formulario = {k: v.strip() if isinstance(v, str) else v for k, v in (await request.form()).items()}
    try:
        await _guardar_fotos(formulario, usuario.organizador_id)
    except ErrorNegocio as e:
        return _formulario(request, db, usuario, formulario, [str(e)], 422)
    datos = _datos_rifa(formulario, usuario.organizador_id)
    if not datos.get("opcion"):
        return _formulario(request, db, usuario, formulario, ["Escoja una de las opciones de boletas."], 422)
    try:
        rifa = servicio.crear_rifa(db, usuario, RifaCrear(**datos), ip_cliente(request))
    except (ValidationError, ErrorNegocio) as e:
        errores = errores_de_validacion(e) if isinstance(e, ValidationError) else [str(e)]
        return _formulario(request, db, usuario, formulario, errores, 422)
    return RedirectResponse(f"/panel/rifas/{rifa.id}?creada=1", status_code=303)


@router.get("/{rifa_id}", response_class=HTMLResponse)
def detalle(
    request: Request,
    rifa_id: int,
    creada: int = 0,
    pagina: int = 1,
    buscar: str = "",
    estado: str = "",
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Página de la rifa: cifras de venta, sorteos, boletas con búsqueda, filtros y páginas."""
    d = servicio.detalle(db, _obtener(db, rifa_id, usuario), pagina, buscar, estado)
    return plantillas.TemplateResponse(
        request,
        "rifas/detalle.html",
        {
            "usuario": usuario,
            "d": d,
            "rifa": d.rifa,
            "creada": creada,
            "error": None,
            "filtros": servicio.FILTROS,
            "puede_eliminarse": servicio.motivo_para_no_eliminar(db, d.rifa) is None,
            "cuentas": servicio.cuentas(db, d.rifa),
            "sorteos": [(x, servicio_sorteos.whatsapp_ganador(x)) for x in servicio_sorteos.sorteos(db, d.rifa)],
            "textos_estado": servicio_sorteos.TEXTOS_ESTADO,
            "aviso": request.query_params.get("aviso"),
            "aviso_error": request.query_params.get("aviso_error"),
        },
    )


@router.post("/{rifa_id}/publicar", response_class=HTMLResponse)
def publicar(
    request: Request,
    rifa_id: int,
    tareas: BackgroundTasks,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Publica la rifa. Si su plan es de pago y aún no está aprobado, lleva a la pantalla para pagarlo."""
    rifa = _obtener(db, rifa_id, usuario)
    if rifa.estado == "borrador" and servicio.falta_verificacion(db, rifa):
        _avisar_verificacion(tareas, usuario)
        return RedirectResponse(
            f"/panel/rifas/{rifa.id}?aviso_error={quote(servicio.MENSAJE_VERIFICACION)}", status_code=303
        )
    if rifa.estado == "borrador" and servicio.detalle(db, rifa).estado_cobro not in ("gratis", "aprobado"):
        return RedirectResponse(f"/panel/rifas/{rifa.id}/pagar", status_code=303)
    try:
        servicio.publicar(db, usuario, rifa, ip_cliente(request))
    except ErrorNegocio as e:
        return RedirectResponse(f"/panel/rifas/{rifa.id}?aviso_error={quote(str(e))}", status_code=303)
    return RedirectResponse(
        f"/panel/rifas/{rifa.id}?aviso={quote('¡Rifa publicada! Ya puede vender boletas.')}", status_code=303
    )


@router.post("/{rifa_id}/eliminar", response_class=HTMLResponse)
def eliminar(
    request: Request, rifa_id: int, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)
):
    """Elimina una rifa del organizador que no tiene ventas ni pagos."""
    if usuario.rol != "admin":
        return RedirectResponse(
            f"/panel/rifas/{rifa_id}?aviso_error=Solo%20el%20organizador%20puede%20eliminar%20rifas.", status_code=303
        )
    rifa = _obtener(db, rifa_id, usuario)
    try:
        servicio.eliminar(db, usuario, rifa, ip_cliente(request))
    except ErrorNegocio as e:
        d = servicio.detalle(db, rifa)
        return plantillas.TemplateResponse(
            request,
            "rifas/detalle.html",
            {
                "usuario": usuario,
                "d": d,
                "rifa": rifa,
                "creada": 0,
                "error": str(e),
                "filtros": servicio.FILTROS,
                "puede_eliminarse": False,
            },
            status_code=422,
        )
    return RedirectResponse("/panel?eliminada=1", status_code=303)


@router.get("/{rifa_id}/editar", response_class=HTMLResponse)
def editar_formulario(
    request: Request, rifa_id: int, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)
):
    """Formulario para corregir la rifa: completo en borrador, limitado en venta."""
    rifa = _obtener(db, rifa_id, usuario)
    if rifa.estado == "borrador":
        return _formulario(request, db, usuario, servicio.datos_para_formulario(rifa), [], rifa=rifa)
    if rifa.estado == "en_venta":
        return _formulario_en_venta(request, db, usuario, rifa)
    raise Redirigir(f"/panel/rifas/{rifa.id}")


def _formulario_en_venta(request, db, usuario, rifa, errores=None, codigo=200):
    """Formulario limitado para una rifa en venta."""
    return plantillas.TemplateResponse(
        request,
        "rifas/editar_en_venta.html",
        {"usuario": usuario, "rifa": rifa, "loterias": servicio.loterias_activas(db), "errores": errores or []},
        status_code=codigo,
    )


@router.post("/{rifa_id}/editar", response_class=HTMLResponse)
async def editar(
    request: Request, rifa_id: int, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)
):
    """Guarda las correcciones de la rifa según su estado."""
    rifa = _obtener(db, rifa_id, usuario)
    formulario = {k: v.strip() if isinstance(v, str) else v for k, v in (await request.form()).items()}
    try:
        await _guardar_fotos(formulario, usuario.organizador_id)
        fotos_premios = {}
        for p in rifa.premios:  # en venta: foto nueva de un premio que no ha jugado
            archivo = formulario.pop(f"premio_foto_{p.id}", None)
            if archivo is not None and not isinstance(archivo, str):
                ruta = await guardar_foto(archivo, usuario.organizador_id)
                if ruta:
                    fotos_premios[p.id] = ruta
    except ErrorNegocio as e:
        if rifa.estado == "borrador":
            return _formulario(request, db, usuario, formulario, [str(e)], 422, rifa=rifa)
        return _formulario_en_venta(request, db, usuario, rifa, [str(e)], 422)
    if rifa.estado == "borrador":
        datos = _datos_rifa(formulario, usuario.organizador_id) | {"acepta_declaracion": True}  # ya la aceptó
        try:
            servicio.editar_borrador(db, usuario, rifa, RifaCrear(**datos), ip_cliente(request))
        except (ValidationError, ErrorNegocio) as e:
            db.rollback()
            errores = errores_de_validacion(e) if isinstance(e, ValidationError) else [str(e)]
            return _formulario(request, db, usuario, formulario, errores, 422, rifa=rifa)
    elif rifa.estado == "en_venta":
        premios = {}
        for p in rifa.premios:
            if f"premio_descripcion_{p.id}" in formulario:
                valor = solo_digitos(formulario.get(f"premio_valor_{p.id}"))
                premios[p.id] = (formulario[f"premio_descripcion_{p.id}"], int(valor) if valor else None)
        try:
            _, secos = _cuotas_y_secos(formulario, usuario.organizador_id)
            nuevos = [PremioSecoDatos(**x) for x in secos]
            servicio.editar_en_venta(
                db,
                usuario,
                rifa,
                formulario.get("nombre", ""),
                formulario.get("descripcion"),
                premios,
                nuevos,
                ip_cliente(request),
                fotos_premios,
            )
        except (ValidationError, ErrorNegocio) as e:
            db.rollback()
            errores = errores_de_validacion(e) if isinstance(e, ValidationError) else [str(e)]
            return _formulario_en_venta(request, db, usuario, rifa, errores, 422)
    return RedirectResponse(f"/panel/rifas/{rifa.id}?aviso=Cambios%20guardados.", status_code=303)


def _avisar_verificacion(tareas: BackgroundTasks, usuario: Usuario) -> None:
    """Le avisa al superadministrador que un organizador necesita verificación para publicar otra rifa."""
    org = usuario.organizador
    tareas.add_task(
        avisar_admin,
        f"Organizador por verificar: {org.nombre}",
        f"{org.nombre} ({org.tipo_documento} {org.numero_documento}) quiere publicar otra rifa y necesita "
        f"verificación de identidad.\n\nRevíselo en {obtener_config().app_url}/admin/organizadores/{org.id}",
    )


def _pagina_pago(request, db, usuario, rifa, errores=None, datos=None, codigo=200):
    """Pantalla para pagar el plan de la rifa a RifaPlus."""
    d = servicio.detalle(db, rifa)
    return plantillas.TemplateResponse(
        request,
        "rifas/pagar.html",
        {
            "usuario": usuario,
            "rifa": rifa,
            "cobro": d.cobro,
            "estado_cobro": d.estado_cobro,
            "cuentas": cuentas_rifaplus(db),
            "medios": medios_para_rifaplus(db),
            "errores": errores or [],
            "datos": datos or {},
        },
        status_code=codigo,
    )


@router.get("/{rifa_id}/pagar", response_class=HTMLResponse)
def pagar_formulario(
    request: Request, rifa_id: int, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)
):
    """Valor del plan, cuentas de RifaPlus y formulario para informar el pago."""
    rifa = _obtener(db, rifa_id, usuario)
    if rifa.estado != "borrador":
        raise Redirigir(f"/panel/rifas/{rifa.id}")
    if servicio.falta_verificacion(db, rifa):
        raise Redirigir(f"/panel/rifas/{rifa.id}?aviso_error={quote(servicio.MENSAJE_VERIFICACION)}")
    return _pagina_pago(request, db, usuario, rifa)


@router.post("/{rifa_id}/pagar", response_class=HTMLResponse)
async def pagar(
    request: Request,
    rifa_id: int,
    tareas: BackgroundTasks,
    comprobante: UploadFile | None = File(None),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Recibe la referencia y el comprobante del pago del plan; la rifa queda esperando la aprobación."""
    rifa = _obtener(db, rifa_id, usuario)
    formulario = {k: v.strip() for k, v in (await request.form()).items() if isinstance(v, str)}
    cobro = servicio.detalle(db, rifa).cobro
    try:
        servicio.exigir_verificacion(db, rifa)
        ruta = await guardar_comprobante(comprobante, usuario.organizador_id)
        medio = int(formulario.get("medio_pago_id") or 0)
        enviar_pago_rifa(db, cobro, medio, formulario.get("referencia"), ruta)
        auditoria.registrar(
            db,
            usuario,
            "cobros_rifa",
            cobro.id,
            "enviar_pago",
            ip=ip_cliente(request),
            nuevo={"rifa": rifa.nombre, "valor": int(cobro.valor), "referencia": cobro.referencia},
        )
        db.commit()
    except ErrorNegocio as e:
        db.rollback()
        return _pagina_pago(request, db, usuario, rifa, [str(e)], formulario, 422)
    tareas.add_task(
        avisar_admin,
        f"Pago por revisar: {rifa.nombre}",
        f"{usuario.organizador.nombre} pidió publicar la rifa «{rifa.nombre}» y envió el pago del plan "
        f"{rifa.plan.nombre} por {pesos(cobro.valor)}.\nReferencia: {cobro.referencia or '(solo comprobante)'}\n\n"
        f"Revíselo en {obtener_config().app_url}/admin/cobros",
    )
    aviso = "Recibimos su pago. Su rifa quedará publicada en cuanto RifaPlus lo confirme."
    return RedirectResponse(f"/panel/rifas/{rifa.id}?aviso={quote(aviso)}", status_code=303)


# ---------- Renovar la vigencia ----------
def _pagina_renovar(request, db, usuario, rifa, errores=None, datos=None, codigo=200):
    """Pantalla para renovar: duraciones con su precio, cuentas de RifaPlus y formulario del pago."""
    precios = vigencia.precios_por_tipo(db).get(rifa.plan_id, {})
    opciones = [(d, precios[d.id]) for d in vigencia.duraciones_activas(db) if d.id in precios]
    return plantillas.TemplateResponse(
        request,
        "rifas/renovar.html",
        {
            "usuario": usuario,
            "rifa": rifa,
            "opciones": opciones,
            "cuentas": cuentas_rifaplus(db),
            "medios": medios_para_rifaplus(db),
            "pendiente": vigencia.renovacion_pendiente(db, rifa),
            "rechazada": vigencia.ultima_rechazada(db, rifa),
            "bloqueada": vigencia.bloqueada(rifa),
            "errores": errores or [],
            "datos": datos or {},
        },
        status_code=codigo,
    )


@router.get("/{rifa_id}/renovar", response_class=HTMLResponse)
def renovar_formulario(
    request: Request, rifa_id: int, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)
):
    """Pantalla de renovación de una rifa publicada."""
    rifa = _obtener(db, rifa_id, usuario)
    if rifa.estado != "en_venta":
        raise Redirigir(f"/panel/rifas/{rifa.id}")
    return _pagina_renovar(request, db, usuario, rifa)


@router.post("/{rifa_id}/renovar", response_class=HTMLResponse)
async def renovar(
    request: Request,
    rifa_id: int,
    tareas: BackgroundTasks,
    comprobante: UploadFile | None = File(None),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Recibe el pago de la renovación; si es gratis se aplica de una vez, si no queda en revisión."""
    rifa = _obtener(db, rifa_id, usuario)
    formulario = {k: v.strip() for k, v in (await request.form()).items() if isinstance(v, str)}
    try:
        ruta = await guardar_comprobante(comprobante, usuario.organizador_id)
        renovacion = vigencia.solicitar_renovacion(
            db,
            rifa,
            int(formulario.get("duracion_id") or 0),
            int(formulario.get("medio_pago_id") or 0) or None,
            formulario.get("referencia"),
            ruta,
        )
        auditoria.registrar(
            db,
            usuario,
            "renovaciones_rifa",
            renovacion.id,
            "solicitar",
            ip=ip_cliente(request),
            nuevo={"rifa": rifa.nombre, "meses": renovacion.meses, "valor": int(renovacion.valor)},
        )
        db.commit()
    except ErrorNegocio as e:
        db.rollback()
        return _pagina_renovar(request, db, usuario, rifa, [str(e)], formulario, 422)
    if renovacion.estado == "aprobado":
        aviso = f"Rifa renovada: vigente hasta el {rifa.vigente_hasta.strftime('%d/%m/%Y')}."
    else:
        tareas.add_task(
            avisar_admin,
            f"Renovación por revisar: {rifa.nombre}",
            f"{usuario.organizador.nombre} envió la renovación de «{rifa.nombre}» por {renovacion.meses} meses, "
            f"{pesos(renovacion.valor)}.\nReferencia: {renovacion.referencia or '(solo comprobante)'}\n\n"
            f"Revísela en {obtener_config().app_url}/admin/cobros",
        )
        aviso = "Recibimos el pago de la renovación. La rifa se renueva en cuanto RifaPlus lo confirme."
    return RedirectResponse(f"/panel/rifas/{rifa.id}?aviso={quote(aviso)}", status_code=303)
