"""Rutas de venta de boletas, pagos, compradores y vendedores."""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import obtener_db
from app.core.excepciones import ErrorNegocio, Redirigir
from app.core.plantillas import errores_de_validacion, plantillas, solo_digitos
from app.modulos.acceso.dependencias import ip_cliente, organizador_actual
from app.modulos.acceso.modelos import Usuario
from app.modulos.pagos.modelos import Pago
from app.modulos.rifas import vigencia
from app.modulos.rifas.cuotas import estado_plan
from app.modulos.rifas.modelos import Boleta
from app.modulos.rifas.servicio import rifa_del_organizador
from app.modulos.ventas import archivos, boleta_individual, servicio
from app.modulos.ventas.esquemas import MEDIOS_DIFUSION, TIPOS_DOCUMENTO, Comprador, DatosPago, VendedorCrear

router = APIRouter(prefix="/panel", tags=["ventas"])

CAMPOS_COMPRADOR = (
    "tipo_documento",
    "numero_documento",
    "nombre",
    "celular",
    "whatsapp",
    "email",
    "direccion",
    "ciudad",
)


def _rifa(db, rifa_id, usuario):
    """Rifa del organizador conectado, o vuelve al panel."""
    rifa = rifa_del_organizador(db, rifa_id, usuario)
    if rifa is None:
        raise Redirigir("/panel")
    return rifa


def _pagina_boleta(request, db, usuario, rifa, boleta_id, *, errores=None, datos=None, codigo=200, aviso=None):
    """Muestra la página de una boleta: venta, plan de pagos, pagos y WhatsApp."""
    boleta = servicio.boleta_de_rifa(db, rifa, boleta_id)
    if boleta is None:
        raise Redirigir(f"/panel/rifas/{rifa.id}")
    estado = servicio.saldo(db, boleta)
    return plantillas.TemplateResponse(
        request,
        "ventas/boleta.html",
        {
            "usuario": usuario,
            "rifa": rifa,
            "boleta": boleta,
            "saldo": estado,
            "plan": estado_plan(rifa, estado.pagado),
            "pagos": servicio.pagos_de(db, boleta),
            "medios": servicio.medios_para_compradores(db),
            "vendedores": servicio.vendedores(db, usuario.organizador_id),
            "tipos_documento": TIPOS_DOCUMENTO,
            "medios_difusion": MEDIOS_DIFUSION,
            "whatsapp": servicio.enlace_whatsapp(boleta, estado),
            "correo": servicio.enlace_correo(boleta, estado),
            "errores": errores or [],
            "datos": datos or {},
            "aviso": aviso,
        },
        status_code=codigo,
    )


def _pago_del_formulario(formulario: dict) -> DatosPago | None:
    """El pago es opcional al vender: si no escriben monto, la boleta queda vendida debiendo."""
    monto = solo_digitos(formulario.get("monto"))
    if not monto:
        return None
    return DatosPago(
        monto=monto,
        medio_pago_id=formulario.get("medio_pago_id") or 0,
        referencia=formulario.get("referencia"),
    )


@router.get("/rifas/{rifa_id}/boletas/{boleta_id}", response_class=HTMLResponse)
def ver_boleta(
    request: Request,
    rifa_id: int,
    boleta_id: int,
    aviso: str | None = None,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Página de una boleta."""
    return _pagina_boleta(request, db, usuario, _rifa(db, rifa_id, usuario), boleta_id, aviso=aviso)


@router.post("/rifas/{rifa_id}/boletas/{boleta_id}/vender", response_class=HTMLResponse)
async def vender(
    request: Request,
    rifa_id: int,
    boleta_id: int,
    comprobante: UploadFile | None = File(None),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Vende la boleta: guarda o actualiza el comprador y registra el pago inicial si lo hay."""
    rifa = _rifa(db, rifa_id, usuario)
    formulario = {k: v.strip() for k, v in (await request.form()).items() if isinstance(v, str)}
    datos = {k: formulario.get(k, "") for k in CAMPOS_COMPRADOR}
    if formulario.get("mismo_numero") == "true":
        datos["whatsapp"] = datos["celular"]
    datos["acepta_whatsapp"] = formulario.get("acepta_whatsapp") == "true"
    try:
        comprador = Comprador(**datos)
        pago = _pago_del_formulario(formulario)
        ruta = await archivos.guardar_comprobante(comprobante, usuario.organizador_id) if pago else None
        vendedor_id = int(formulario["vendedor_id"]) if formulario.get("vendedor_id") else None
        servicio.vender(
            db,
            usuario,
            rifa,
            boleta_id,
            comprador,
            vendedor_id,
            formulario.get("medio_difusion"),
            pago,
            ruta,
            ip_cliente(request),
        )
    except (ValidationError, ErrorNegocio) as e:
        db.rollback()
        errores = errores_de_validacion(e) if isinstance(e, ValidationError) else [str(e)]
        return _pagina_boleta(request, db, usuario, rifa, boleta_id, errores=errores, datos=formulario, codigo=422)
    return RedirectResponse(f"/panel/rifas/{rifa.id}/boletas/{boleta_id}?aviso=vendida", status_code=303)


@router.post("/rifas/{rifa_id}/boletas/{boleta_id}/pagos", response_class=HTMLResponse)
async def registrar_pago(
    request: Request,
    rifa_id: int,
    boleta_id: int,
    comprobante: UploadFile | None = File(None),
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Registra un abono o el pago completo de una boleta vendida."""
    rifa = _rifa(db, rifa_id, usuario)
    formulario = {k: v.strip() for k, v in (await request.form()).items() if isinstance(v, str)}
    try:
        pago = _pago_del_formulario(formulario)
        if pago is None:
            raise ErrorNegocio("Escriba el valor que le pagaron.")
        ruta = await archivos.guardar_comprobante(comprobante, usuario.organizador_id)
        servicio.registrar_pago(db, usuario, rifa, boleta_id, pago, ruta, ip_cliente(request))
    except (ValidationError, ErrorNegocio) as e:
        db.rollback()
        errores = errores_de_validacion(e) if isinstance(e, ValidationError) else [str(e)]
        return _pagina_boleta(request, db, usuario, rifa, boleta_id, errores=errores, datos=formulario, codigo=422)
    return RedirectResponse(f"/panel/rifas/{rifa.id}/boletas/{boleta_id}?aviso=pago", status_code=303)


@router.post("/rifas/{rifa_id}/boletas/{boleta_id}/liberar", response_class=HTMLResponse)
def liberar(
    request: Request,
    rifa_id: int,
    boleta_id: int,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Deshace la venta de una boleta sin pagos."""
    rifa = _rifa(db, rifa_id, usuario)
    try:
        servicio.liberar(db, usuario, rifa, boleta_id, ip_cliente(request))
    except ErrorNegocio as e:
        return _pagina_boleta(request, db, usuario, rifa, boleta_id, errores=[str(e)], codigo=422)
    return RedirectResponse(f"/panel/rifas/{rifa.id}/boletas/{boleta_id}?aviso=liberada", status_code=303)


@router.get("/comprobantes/{pago_id}")
def ver_comprobante(pago_id: int, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)):
    """Entrega la foto del comprobante solo al organizador dueño de la rifa."""
    pago = db.get(Pago, pago_id)
    if pago is None or pago.comprobante_url is None:
        raise Redirigir("/panel")
    boleta = db.get(Boleta, pago.boleta_id)
    if boleta is None or boleta.rifa.organizador_id != usuario.organizador_id:
        raise Redirigir("/panel")
    ruta = archivos.ruta_absoluta(pago.comprobante_url)
    if ruta is None:
        raise Redirigir("/panel")
    return FileResponse(ruta)


@router.get("/compradores/buscar")
def buscar_comprador(documento: str, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)):
    """Para el formulario de venta: si el comprador ya existe, devuelve sus datos para no escribirlos de nuevo."""
    cliente = servicio.cliente_por_documento(db, usuario.organizador_id, documento)
    if cliente is None:
        return JSONResponse({"encontrado": False})
    return {
        "encontrado": True,
        **{c: getattr(cliente, c) for c in CAMPOS_COMPRADOR},
        "acepta_whatsapp": cliente.acepta_whatsapp,
    }


@router.get("/vendedores", response_class=HTMLResponse)
def lista_vendedores(
    request: Request, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)
):
    """Lista de vendedores con lo que ha vendido y cobrado cada uno."""
    return _pagina_vendedores(request, db, usuario)


def _pagina_vendedores(request, db, usuario, errores=None, datos=None, codigo=200):
    """Muestra la página de vendedores con su liquidación y los errores del formulario si los hay."""
    lista = servicio.vendedores(db, usuario.organizador_id, solo_activos=False)
    return plantillas.TemplateResponse(
        request,
        "ventas/vendedores.html",
        {
            "usuario": usuario,
            "liquidaciones": [servicio.liquidacion(db, v) for v in lista],
            "por_entregar": {v.id: sum(x.por_entregar for x in servicio.efectivo_del_vendedor(db, v)) for v in lista},
            "tipos_documento": TIPOS_DOCUMENTO,
            "errores": errores or [],
            "datos": datos or {},
        },
        status_code=codigo,
    )


@router.post("/vendedores", response_class=HTMLResponse)
async def crear_vendedor(
    request: Request, db: Session = Depends(obtener_db), usuario: Usuario = Depends(organizador_actual)
):
    """Agrega un vendedor nuevo."""
    formulario = {k: v.strip() for k, v in (await request.form()).items() if isinstance(v, str)}
    datos = {k: v for k, v in formulario.items() if v}
    try:
        servicio.crear_vendedor(db, usuario, VendedorCrear(**datos))
    except (ValidationError, ErrorNegocio) as e:
        errores = errores_de_validacion(e) if isinstance(e, ValidationError) else [str(e)]
        return _pagina_vendedores(request, db, usuario, errores, formulario, 422)
    return RedirectResponse("/panel/vendedores", status_code=303)


def _vendedor(db, usuario, vendedor_id):
    """Vendedor del organizador conectado, o vuelve a la lista."""
    vendedor = servicio.vendedor_del_organizador(db, usuario.organizador_id, vendedor_id)
    if vendedor is None:
        raise Redirigir("/panel/vendedores")
    return vendedor


def _pagina_vendedor(request, db, usuario, vendedor, errores=None, datos=None, aviso=None, codigo=200):
    """Muestra la liquidación de un vendedor: comisión por rifa, pagos hechos y saldo."""
    return plantillas.TemplateResponse(
        request,
        "ventas/vendedor.html",
        {
            "usuario": usuario,
            "l": servicio.liquidacion(db, vendedor),
            "pagos": servicio.pagos_comision_de(db, vendedor),
            "efectivo": servicio.efectivo_del_vendedor(db, vendedor),
            "entregas": servicio.entregas_de(db, vendedor),
            "medios_entrega": servicio.medios_para_compradores(db),
            "medios": servicio.medios_para_compradores(db),
            "errores": errores or [],
            "datos": datos or {},
            "aviso": aviso,
        },
        status_code=codigo,
    )


@router.get("/vendedores/{vendedor_id}", response_class=HTMLResponse)
def ver_vendedor(
    request: Request,
    vendedor_id: int,
    aviso: str | None = None,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Liquidación de un vendedor."""
    return _pagina_vendedor(request, db, usuario, _vendedor(db, usuario, vendedor_id), aviso=aviso)


@router.post("/vendedores/{vendedor_id}", response_class=HTMLResponse)
async def editar_vendedor(
    request: Request,
    vendedor_id: int,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Cambia el porcentaje de comisión o activa / desactiva al vendedor."""
    vendedor = _vendedor(db, usuario, vendedor_id)
    formulario = await request.form()
    try:
        comision = float(str(formulario.get("comision_porcentaje", "0")).replace(",", ".") or 0)
        servicio.actualizar_vendedor(
            db,
            usuario,
            vendedor,
            comision,
            formulario.get("activo") == "true",
            ip_cliente(request),
            str(formulario.get("llave_bre_b", "")),
        )
    except (ValueError, ErrorNegocio) as e:
        mensaje = str(e) if isinstance(e, ErrorNegocio) else "Escriba un porcentaje válido."
        return _pagina_vendedor(request, db, usuario, vendedor, errores=[mensaje], codigo=422)
    return RedirectResponse(f"/panel/vendedores/{vendedor.id}?aviso=guardado", status_code=303)


@router.post("/vendedores/{vendedor_id}/pagos", response_class=HTMLResponse)
async def pagar_comision(
    request: Request,
    vendedor_id: int,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Registra un pago de comisión al vendedor."""
    vendedor = _vendedor(db, usuario, vendedor_id)
    formulario = {k: v.strip() for k, v in (await request.form()).items() if isinstance(v, str)}
    try:
        pago = _pago_del_formulario(formulario)
        if pago is None:
            raise ErrorNegocio("Escriba el valor que le pagó al vendedor.")
        servicio.pagar_comision(db, usuario, vendedor, pago, formulario.get("observacion"), ip_cliente(request))
    except (ValidationError, ErrorNegocio) as e:
        db.rollback()
        errores = errores_de_validacion(e) if isinstance(e, ValidationError) else [str(e)]
        return _pagina_vendedor(request, db, usuario, vendedor, errores=errores, datos=formulario, codigo=422)
    return RedirectResponse(f"/panel/vendedores/{vendedor.id}?aviso=pagado", status_code=303)


@router.get("/rifas/{rifa_id}/boletas/{boleta_id}/imprimir", response_class=HTMLResponse)
def imprimir_boleta(
    request: Request,
    rifa_id: int,
    boleta_id: int,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Boleta individual con los datos completos del comprador, lista para imprimir o guardar en PDF."""
    rifa = _rifa(db, rifa_id, usuario)
    boleta = servicio.boleta_de_rifa(db, rifa, boleta_id)
    if boleta is None or boleta.estado != "vendida":
        raise Redirigir(f"/panel/rifas/{rifa.id}")
    if vigencia.bloqueada(rifa):
        raise Redirigir(
            f"/panel/rifas/{rifa.id}?aviso_error=La%20rifa%20est%C3%A1%20bloqueada%3A%20ren%C3%BAevela%20para%20imprimir%20boletas."
        )
    return plantillas.TemplateResponse(request, "boletas/boleta.html", {"b": boleta_individual.armar(db, boleta, True)})


@router.post("/vendedores/{vendedor_id}/entregas", response_class=HTMLResponse)
async def registrar_entrega(
    request: Request,
    vendedor_id: int,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(organizador_actual),
):
    """Registra el dinero en efectivo que el vendedor le entregó al organizador."""
    vendedor = _vendedor(db, usuario, vendedor_id)
    formulario = {k: v.strip() for k, v in (await request.form()).items() if isinstance(v, str)}
    try:
        servicio.registrar_entrega(
            db,
            usuario,
            vendedor,
            int(formulario.get("rifa_id") or 0),
            int(solo_digitos(formulario.get("monto")) or 0),
            int(formulario.get("medio_pago_id") or 0),
            formulario.get("observacion"),
            ip_cliente(request),
        )
    except ErrorNegocio as e:
        db.rollback()
        return _pagina_vendedor(request, db, usuario, vendedor, errores=[str(e)], datos=formulario, codigo=422)
    return RedirectResponse(f"/panel/vendedores/{vendedor.id}?aviso=entrega", status_code=303)
