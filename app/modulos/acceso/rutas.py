"""Rutas de acceso: registro, ingreso, salida y cambio de clave."""

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import obtener_config
from app.core.database import obtener_db
from app.core.excepciones import ErrorNegocio
from app.core.plantillas import errores_de_validacion, plantillas
from app.modulos.acceso import servicio, sesiones
from app.modulos.acceso.dependencias import ip_cliente, usuario_con_clave_pendiente
from app.modulos.acceso.esquemas import RegistroOrganizador
from app.modulos.acceso.modelos import Usuario
from app.modulos.acceso.notificaciones import enviar_clave_temporal, enviar_enlace_recuperacion

router = APIRouter(tags=["acceso"])


@router.get("/registro", response_class=HTMLResponse)
def registro_formulario(request: Request):
    """Muestra el formulario de registro vacío."""
    return plantillas.TemplateResponse(request, "acceso/registro.html", {"datos": {}, "errores": []})


@router.post("/registro", response_class=HTMLResponse)
def registro(
    request: Request,
    tareas: BackgroundTasks,
    db: Session = Depends(obtener_db),
    tipo_persona: str = Form(""),
    nombre: str = Form(""),
    email: str = Form(""),
    celular: str = Form(""),
    whatsapp: str = Form(""),
    mismo_numero: bool = Form(False),
    direccion: str = Form(""),
    ciudad: str = Form(""),
    tipo_documento: str = Form(""),
    numero_documento: str = Form(""),
    acepta_datos: bool = Form(False),
    acepta_terminos: bool = Form(False),
):
    """Recibe el registro, crea organizador y usuario con clave temporal, y muestra la confirmación."""
    datos = dict(
        tipo_persona=tipo_persona,
        nombre=nombre.strip(),
        email=email,
        celular=celular,
        whatsapp=celular if mismo_numero else whatsapp,
        direccion=direccion,
        ciudad=ciudad,
        tipo_documento=tipo_documento,
        numero_documento=numero_documento,
        acepta_datos=acepta_datos,
        acepta_terminos=acepta_terminos,
    )
    try:
        resultado = servicio.registrar_organizador(db, RegistroOrganizador(**datos), ip_cliente(request))
    except (ValidationError, ErrorNegocio) as e:
        errores = errores_de_validacion(e) if isinstance(e, ValidationError) else [str(e)]
        return plantillas.TemplateResponse(
            request,
            "acceso/registro.html",
            {"datos": datos | {"mismo_numero": mismo_numero}, "errores": errores},
            status_code=422,
        )
    org = resultado.organizador
    tareas.add_task(enviar_clave_temporal, org.nombre, org.email, org.whatsapp, resultado.clave_temporal)
    cfg = obtener_config()
    contexto = {"email": org.email, "correo_activo": cfg.correo_activo}
    if cfg.es_desarrollo or not cfg.correo_activo:
        # En desarrollo, o si todavía no hay correo configurado, la clave se muestra en pantalla para no
        # dejar al organizador sin poder entrar. Con correo configurado en producción, solo llega al correo.
        contexto["clave_desarrollo"] = resultado.clave_temporal
    return plantillas.TemplateResponse(request, "acceso/registro_exitoso.html", contexto)


@router.get("/ingresar", response_class=HTMLResponse)
def ingresar_formulario(request: Request):
    """Muestra el formulario de ingreso."""
    return plantillas.TemplateResponse(request, "acceso/ingresar.html", {"email": "", "error": None})


@router.post("/ingresar")
def ingresar(request: Request, db: Session = Depends(obtener_db), email: str = Form(""), clave: str = Form("")):
    """Valida correo y clave, crea la sesión (cookie) y envía al panel, al admin o a cambiar la clave."""
    try:
        resultado = servicio.ingresar(db, email, clave, ip_cliente(request), request.headers.get("user-agent"))
    except ErrorNegocio as e:
        return plantillas.TemplateResponse(
            request, "acceso/ingresar.html", {"email": email, "error": str(e)}, status_code=401
        )
    cfg = obtener_config()
    if resultado.usuario.debe_cambiar_clave:
        destino = "/cambiar-clave"
    elif resultado.usuario.rol == "superadmin":
        destino = "/admin"  # el mismo "Ingresar" de la página principal lleva al superadministrador
    else:
        destino = "/panel"
    respuesta = RedirectResponse(destino, status_code=303)
    respuesta.set_cookie(
        sesiones.NOMBRE_COOKIE,
        resultado.token,
        httponly=True,
        samesite="lax",
        secure=not cfg.es_desarrollo,
        max_age=cfg.sesion_horas * 3600,
    )
    return respuesta


@router.post("/salir")
def salir(request: Request, db: Session = Depends(obtener_db)):
    """Cierra la sesión actual y borra la cookie."""
    sesiones.cerrar_sesion(db, request.cookies.get(sesiones.NOMBRE_COOKIE))
    db.commit()
    respuesta = RedirectResponse("/ingresar", status_code=303)
    respuesta.delete_cookie(sesiones.NOMBRE_COOKIE)
    return respuesta


@router.get("/cambiar-clave", response_class=HTMLResponse)
def cambiar_clave_formulario(request: Request, usuario: Usuario = Depends(usuario_con_clave_pendiente)):
    """Muestra el formulario para crear o cambiar la clave."""
    return plantillas.TemplateResponse(request, "acceso/cambiar_clave.html", {"usuario": usuario, "error": None})


@router.post("/cambiar-clave", response_class=HTMLResponse)
def cambiar_clave(
    request: Request,
    db: Session = Depends(obtener_db),
    usuario: Usuario = Depends(usuario_con_clave_pendiente),
    clave_actual: str = Form(""),
    clave_nueva: str = Form(""),
    confirmacion: str = Form(""),
):
    """Guarda la clave nueva. En el primer ingreso, activa al organizador."""
    try:
        primer_ingreso = servicio.cambiar_clave(
            db,
            usuario,
            clave_actual,
            clave_nueva,
            confirmacion,
            request.cookies.get(sesiones.NOMBRE_COOKIE),
            ip_cliente(request),
        )
    except ErrorNegocio as e:
        return plantillas.TemplateResponse(
            request, "acceso/cambiar_clave.html", {"usuario": usuario, "error": str(e)}, status_code=422
        )
    return RedirectResponse("/panel?bienvenida=1" if primer_ingreso else "/panel", status_code=303)


# ---------- Olvidé mi clave ----------
@router.get("/recuperar-clave", response_class=HTMLResponse)
def recuperar_formulario(request: Request):
    """Formulario para pedir el enlace de cambio de clave."""
    return plantillas.TemplateResponse(request, "acceso/recuperar_clave.html", {"enviado": False, "email": ""})


@router.post("/recuperar-clave", response_class=HTMLResponse)
def recuperar(request: Request, tareas: BackgroundTasks, email: str = Form(""), db: Session = Depends(obtener_db)):
    """Envía el enlace si existe la cuenta. Siempre muestra el mismo mensaje (no revela quién tiene cuenta)."""
    resultado = servicio.pedir_recuperacion(db, email)
    cfg = obtener_config()
    enlace = None
    if resultado:
        usuario, token = resultado
        tareas.add_task(enviar_enlace_recuperacion, usuario.nombre, usuario.email, token)
        if cfg.es_desarrollo and not cfg.correo_activo:  # para probar en el computador sin correo configurado
            enlace = f"/restablecer-clave/{token}"
    return plantillas.TemplateResponse(
        request,
        "acceso/recuperar_clave.html",
        {"enviado": True, "email": email, "enlace_desarrollo": enlace, "correo_activo": cfg.correo_activo},
    )


@router.get("/restablecer-clave/{token}", response_class=HTMLResponse)
def restablecer_formulario(request: Request, token: str, db: Session = Depends(obtener_db)):
    """Formulario para crear la clave nueva desde el enlace del correo."""
    valido = servicio.token_valido(db, token) is not None
    return plantillas.TemplateResponse(
        request, "acceso/restablecer_clave.html", {"token": token, "valido": valido, "error": None}
    )


@router.post("/restablecer-clave/{token}", response_class=HTMLResponse)
def restablecer(
    request: Request,
    token: str,
    clave_nueva: str = Form(""),
    confirmacion: str = Form(""),
    db: Session = Depends(obtener_db),
):
    """Guarda la clave nueva y lleva al ingreso."""
    try:
        servicio.restablecer_con_token(db, token, clave_nueva, confirmacion, ip_cliente(request))
    except ErrorNegocio as e:
        valido = servicio.token_valido(db, token) is not None
        return plantillas.TemplateResponse(
            request,
            "acceso/restablecer_clave.html",
            {"token": token, "valido": valido, "error": str(e)},
            status_code=422,
        )
    return RedirectResponse("/ingresar?clave_cambiada=1", status_code=303)
