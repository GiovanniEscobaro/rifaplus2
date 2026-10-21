"""Venta de boletas: comprador obligatorio, abonos acreditados por el organizador, saldos y WhatsApp."""

import datetime
import re
from urllib.parse import unquote

import pytest
from sqlalchemy import select

from app.modulos.pagos.modelos import MedioPago
from app.modulos.personas.modelos import Cliente
from app.modulos.rifas.modelos import Boleta, Loteria, Rifa

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


@pytest.fixture
def rifa_publicada(organizador, db):
    """Rifa gratis de 10 boletas a $20.000, ya publicada. Devuelve (url de la rifa, rifa)."""
    loteria = db.scalar(select(Loteria).where(Loteria.nombre == "Lotería de Boyacá"))
    r = organizador.post(
        "/panel/rifas/nueva",
        follow_redirects=False,
        data=dict(
            nombre="Rifa de prueba",
            premio_mayor="Juego de cocina",
            loteria_id=str(loteria.id),
            fecha_sorteo=(datetime.date.today() + datetime.timedelta(days=20)).isoformat(),
            opcion="1-1",
            valor_boleta="20000",
            acepta_declaracion="true",
        ),
    )
    url = r.headers["location"].split("?")[0]
    organizador.post(f"{url}/publicar")
    db.expire_all()
    return url, db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()


def medio(db, codigo):
    return str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == codigo)))


def comprador(**cambios):
    return {
        "tipo_documento": "CC",
        "numero_documento": "1.045.123.456",
        "nombre": "Pepito Pérez",
        "celular": "300 111 2222",
        "whatsapp": "310 333 4444",
        "email": "pepito@correo.com",
        "direccion": "Calle 30 # 12-45",
        "ciudad": "Soledad",
        "acepta_whatsapp": "true",
    } | cambios


def boleta(db, rifa, n=1):
    db.expire_all()
    return db.scalar(select(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.consecutivo == n))


def test_venta_con_pago_completo(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa)
    r = organizador.post(
        f"{url}/boletas/{b.id}/vender",
        follow_redirects=False,
        data=comprador(monto="20000", medio_pago_id=medio(db, "efectivo")),
    )
    assert r.status_code == 303
    pagina = organizador.get(r.headers["location"]).text
    assert "Pagada" in pagina and "Pepito Pérez" in pagina and "Avisar por WhatsApp" in pagina
    assert boleta(db, rifa).estado == "vendida"


def test_todos_los_datos_del_comprador_son_obligatorios(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa)
    for campo in ("tipo_documento", "email", "direccion", "ciudad", "whatsapp"):
        r = organizador.post(f"{url}/boletas/{b.id}/vender", data=comprador(**{campo: ""}))
        assert r.status_code == 422, campo
    assert boleta(db, rifa).estado == "disponible"


def test_abonos_hasta_completar(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa, 2)
    nequi = medio(db, "nequi")
    organizador.post(f"{url}/boletas/{b.id}/vender", data=comprador(monto="5000", medio_pago_id=nequi, referencia="M1"))
    pagina = organizador.get(f"{url}/boletas/{b.id}").text
    assert "Abonada" in pagina and "$15.000" in pagina
    r = organizador.post(f"{url}/boletas/{b.id}/pagos", data={"monto": "16000", "medio_pago_id": nequi})
    assert r.status_code == 422 and "supera lo que falta" in r.text
    r = organizador.post(
        f"{url}/boletas/{b.id}/pagos", data={"monto": "15000", "medio_pago_id": nequi, "referencia": "M1"}
    )
    assert r.status_code == 422 and "referencia" in r.text
    organizador.post(f"{url}/boletas/{b.id}/pagos", data={"monto": "15000", "medio_pago_id": medio(db, "daviplata")})
    assert "Pagada" in organizador.get(f"{url}/boletas/{b.id}").text


def test_resumen_y_filtro_de_deudores(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    efectivo = medio(db, "efectivo")
    b1, b2 = boleta(db, rifa, 1), boleta(db, rifa, 2)
    organizador.post(f"{url}/boletas/{b1.id}/vender", data=comprador(monto="20000", medio_pago_id=efectivo))
    organizador.post(
        f"{url}/boletas/{b2.id}/vender", data=comprador(numero_documento="999888", monto="8000", medio_pago_id=efectivo)
    )
    pagina = organizador.get(url).text
    assert "$28.000" in pagina and "$12.000" in pagina
    deben = organizador.get(url, params={"estado": "con_saldo"}).text
    assert "1 encontrada" in deben and "Debe $12.000" in deben


def test_comprador_conocido_se_reutiliza(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    organizador.post(f"{url}/boletas/{boleta(db, rifa, 1).id}/vender", data=comprador())
    organizador.post(f"{url}/boletas/{boleta(db, rifa, 3).id}/vender", data=comprador(ciudad="Barranquilla"))
    clientes = db.scalars(
        select(Cliente).where(Cliente.numero_documento == "1045123456", Cliente.organizador_id == rifa.organizador_id)
    ).all()
    assert len(clientes) == 1 and clientes[0].ciudad == "Barranquilla"
    datos = organizador.get("/panel/compradores/buscar", params={"documento": "1045123456"}).json()
    assert datos["encontrado"] and datos["nombre"] == "Pepito Pérez"


def test_no_se_vende_dos_veces_ni_en_borrador(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa, 4)
    organizador.post(f"{url}/boletas/{b.id}/vender", data=comprador())
    r = organizador.post(f"{url}/boletas/{b.id}/vender", data=comprador(numero_documento="777666"))
    assert r.status_code == 422 and "ya no está disponible" in r.text


def test_liberar_solo_sin_pagos(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa, 5)
    organizador.post(f"{url}/boletas/{b.id}/vender", data=comprador())
    organizador.post(f"{url}/boletas/{b.id}/liberar")
    assert boleta(db, rifa, 5).estado == "disponible"
    organizador.post(f"{url}/boletas/{b.id}/vender", data=comprador(monto="1000", medio_pago_id=medio(db, "efectivo")))
    r = organizador.post(f"{url}/boletas/{b.id}/liberar")
    assert r.status_code == 422 and boleta(db, rifa, 5).estado == "vendida"


def test_mensaje_de_whatsapp(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa, 6)
    organizador.post(f"{url}/boletas/{b.id}/vender", data=comprador(monto="20000", medio_pago_id=medio(db, "nequi")))
    enlace = re.search(r'href="(https://wa.me/[^"]+)"', organizador.get(f"{url}/boletas/{b.id}").text).group(1)
    texto = unquote(enlace.replace("&amp;", "&"))
    assert enlace.startswith("https://wa.me/573103334444")
    assert "Boleta 6 · Cifra: *6*" in texto and "pagada" in texto and "/boleta/" in texto


def test_comprobante_solo_lo_ve_su_organizador(organizador, rifa_publicada, db, cliente):
    url, rifa = rifa_publicada
    b = boleta(db, rifa, 7)
    organizador.post(
        f"{url}/boletas/{b.id}/vender",
        data=comprador(monto="20000", medio_pago_id=medio(db, "nequi")),
        files={"comprobante": ("pago.png", PNG, "image/png")},
    )
    enlace = re.search(r'href="(/panel/comprobantes/\d+)"', organizador.get(f"{url}/boletas/{b.id}").text).group(1)
    assert organizador.get(enlace).content == PNG
    organizador.post("/salir")
    assert organizador.get(enlace, follow_redirects=False).status_code == 303


def test_comprobante_debe_ser_imagen_o_pdf(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa, 8)
    r = organizador.post(
        f"{url}/boletas/{b.id}/vender",
        data=comprador(monto="20000", medio_pago_id=medio(db, "nequi")),
        files={"comprobante": ("virus.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert r.status_code == 422 and "JPG, PNG o WEBP" in r.text


def test_vendedores(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    r = organizador.post(
        "/panel/vendedores",
        data={
            "nombre": "Ana Gómez",
            "tipo_documento": "CC",
            "numero_documento": "55443322",
            "celular": "3005556677",
            "comision_porcentaje": "10",
            "llave_bre_b": "@VENDEDOR",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    vendedor_id = re.search(
        r'<option value="(\d+)" >Ana Gómez', organizador.get(f"{url}/boletas/{boleta(db, rifa, 9).id}").text
    )
    assert vendedor_id
    organizador.post(
        f"{url}/boletas/{boleta(db, rifa, 9).id}/vender",
        data=comprador(vendedor_id=vendedor_id.group(1), monto="20000", medio_pago_id=medio(db, "efectivo")),
    )
    pagina = organizador.get("/panel/vendedores").text
    assert "Ana Gómez" in pagina and "$20.000" in pagina


def test_verificacion_publica_muestra_si_esta_pagada(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa, 0)
    organizador.post(f"{url}/boletas/{b.id}/vender", data=comprador(monto="20000", medio_pago_id=medio(db, "efectivo")))
    pagina = organizador.get(f"/verificar/{b.codigo_verificacion}").text
    assert "Vendida y pagada" in pagina and "Pepito" not in pagina


def test_pago_con_puntos_de_miles(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    b = boleta(db, rifa, 1)
    organizador.post(
        f"{url}/boletas/{b.id}/vender", data=comprador(monto="20.000", medio_pago_id=medio(db, "efectivo"))
    )
    assert "Pagada" in organizador.get(f"{url}/boletas/{b.id}").text


def test_busqueda_por_cedula_en_la_rifa(organizador, rifa_publicada, db):
    url, rifa = rifa_publicada
    organizador.post(f"{url}/boletas/{boleta(db, rifa, 4).id}/vender", data=comprador(numero_documento="72345678"))
    en_rifa = organizador.get(url, params={"buscar": "72345678"}).text
    assert "1 encontrada" in en_rifa and "Pepito Pérez" in en_rifa
