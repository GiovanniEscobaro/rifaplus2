"""Vigencia por períodos: precio por duración, bloqueo al vencer, renovaciones y la tabla de precios del superadmin."""

import datetime
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.seguridad import cifrar_clave
from app.main import app
from app.modulos.acceso.modelos import Usuario
from app.modulos.pagos.modelos import CobroRifa, Duracion, MedioPago, Plan, PrecioRifa
from app.modulos.rifas import vigencia
from app.modulos.rifas.modelos import Boleta, Loteria, Rifa

HOY = datetime.date.today()


@pytest.fixture
def admin(db):
    if not db.scalar(select(Usuario).where(Usuario.email == "vigencia@rifaplus.co")):
        db.add(
            Usuario(
                nombre="Giovanni",
                email="vigencia@rifaplus.co",
                password_hash=cifrar_clave("Admin2026"),
                rol="superadmin",
                organizador_id=None,
                debe_cambiar_clave=False,
            )
        )
        db.commit()
    c = TestClient(app)
    c.post("/ingresar", data={"email": "vigencia@rifaplus.co", "clave": "Admin2026"})
    return c


def duracion(db, meses):
    return db.scalar(select(Duracion).where(Duracion.meses == meses))


def crear(organizador, db, opcion="1-1", meses=6, nombre="Rifa vigencia"):
    loteria = str(db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá")))
    r = organizador.post(
        "/panel/rifas/nueva",
        follow_redirects=False,
        data=dict(
            nombre=nombre,
            premio_mayor="Televisor",
            loteria_id=loteria,
            opcion=opcion,
            valor_boleta="10.000",
            fecha_sorteo=(HOY + datetime.timedelta(days=60)).isoformat(),
            acepta_declaracion="true",
            duracion_id=str(duracion(db, meses).id),
        ),
    )
    assert r.status_code == 303, r.text[:2000]
    db.expire_all()
    return r.headers["location"].split("?")[0], db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()


def test_el_precio_depende_de_la_duracion(organizador, db):
    plan = db.scalar(select(Plan).where(Plan.boletas_min == 25, Plan.boletas_max == 25))
    precio_ano = int(
        db.scalar(
            select(PrecioRifa.valor).where(PrecioRifa.plan_id == plan.id, PrecioRifa.duracion_id == duracion(db, 12).id)
        )
    )
    _, rifa = crear(organizador, db, opcion="2-4", meses=12)
    assert rifa.duracion_meses == 12
    assert int(db.scalar(select(CobroRifa.valor).where(CobroRifa.rifa_id == rifa.id))) == precio_ano
    pagina = organizador.get("/panel/rifas/nueva").text
    assert "¿Por cuánto tiempo quiere la rifa?" in pagina and "1 año" in pagina


def test_al_publicar_empieza_la_vigencia(organizador, db):
    url, rifa = crear(organizador, db)
    organizador.post(f"{url}/publicar")
    db.expire_all()
    assert db.get(Rifa, rifa.id).vigente_hasta == vigencia.sumar_meses(HOY, 6)
    assert "Vigente hasta" in organizador.get(url).text


def test_rifa_vencida_queda_bloqueada_para_el_organizador(organizador, db, cliente):
    url, rifa = crear(organizador, db)
    organizador.post(f"{url}/publicar")
    db.expire_all()
    rifa = db.get(Rifa, rifa.id)
    rifa.vigente_hasta = HOY - datetime.timedelta(days=1)
    db.commit()
    assert "Rifa bloqueada por falta de renovación" in organizador.get(url).text
    assert "bloqueada" in organizador.get("/panel").text
    boleta = db.scalar(select(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.consecutivo == 1))
    r = organizador.post(
        f"{url}/boletas/{boleta.id}/vender",
        data={
            "tipo_documento": "CC",
            "numero_documento": "555",
            "nombre": "Ana Ruiz",
            "celular": "3001112222",
            "whatsapp": "3001112222",
            "email": "a@a.co",
            "direccion": "Calle 1 # 2-3",
            "ciudad": "Soledad",
        },
    )
    assert r.status_code == 422 and "bloqueada" in r.text
    assert cliente.get(f"/verificar/{boleta.codigo_verificacion}").status_code == 200  # el comprador sí verifica


def test_renovacion_pagada_y_aprobada(organizador, admin, db):
    url, rifa = crear(organizador, db, opcion="2-4")
    organizador.post(
        f"{url}/pagar",
        data={
            "medio_pago_id": str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == "bre_b"))),
            "referencia": "INI-1",
        },
    )
    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    admin.post(f"/admin/cobros/{cobro.id}", data={"accion": "aprobar"})
    db.expire_all()
    rifa = db.get(Rifa, rifa.id)
    rifa.vigente_hasta = HOY - datetime.timedelta(days=3)  # vencida
    db.commit()
    pagina = organizador.get(f"{url}/renovar").text
    assert "La rifa está bloqueada" in pagina and "1 año" in pagina
    bre_b = str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == "bre_b")))
    organizador.post(
        f"{url}/renovar", data={"duracion_id": str(duracion(db, 6).id), "medio_pago_id": bre_b, "referencia": "REN-1"}
    )
    assert "REN-1" in admin.get("/admin/cobros").text
    renovacion_id = re.search(r'action="/admin/renovaciones/(\d+)"', admin.get("/admin/cobros").text).group(1)
    admin.post(f"/admin/renovaciones/{renovacion_id}", data={"accion": "aprobar"})
    db.expire_all()
    assert db.get(Rifa, rifa.id).vigente_hasta == vigencia.sumar_meses(HOY, 6)  # ya vencida: cuenta desde hoy
    assert "Rifa bloqueada" not in organizador.get(url).text


def test_renovacion_gratis_se_aplica_sola(organizador, db):
    url, rifa = crear(organizador, db)  # 10 boletas: gratis
    organizador.post(f"{url}/publicar")
    db.expire_all()
    antes = db.get(Rifa, rifa.id).vigente_hasta
    organizador.post(f"{url}/renovar", data={"duracion_id": str(duracion(db, 12).id)})
    db.expire_all()
    assert db.get(Rifa, rifa.id).vigente_hasta == vigencia.sumar_meses(antes, 12)


def test_tabla_de_precios_por_duracion(admin, db):
    pagina = admin.get("/admin/planes").text
    assert "6 meses" in pagina and "1 año" in pagina and pagina.count('name="precio_') == 26
    plan = db.scalar(select(Plan).where(Plan.boletas_min == 100, Plan.boletas_max == 100))
    datos = {k: v for k, v in re.findall(r'name="(precio_\d+_\d+)"[^>]*value="([^"]*)"', pagina)}
    datos |= {f"activo_{t}": "true" for t in re.findall(r'name="activo_(\d+)" value="true" checked', pagina)}
    datos[f"precio_{plan.id}_{duracion(db, 12).id}"] = "33.300"
    admin.post("/admin/planes", data=datos)
    db.expire_all()
    assert (
        int(
            db.scalar(
                select(PrecioRifa.valor).where(
                    PrecioRifa.plan_id == plan.id, PrecioRifa.duracion_id == duracion(db, 12).id
                )
            )
        )
        == 33300
    )


def test_crear_tipo_de_rifa_y_duracion(admin, db):
    r = admin.post("/admin/planes/tipo", data={"boletas": "30", "cifras": "3"})
    assert r.status_code == 422 and "10, 100, 1.000 o 10.000" in r.text
    admin.post("/admin/planes/tipo", data={"boletas": "20", "cifras": "5"})
    assert db.scalar(select(Plan).where(Plan.boletas_min == 20, Plan.numeros_min == 5)) is not None
    admin.post("/admin/planes/duracion", data={"nombre": "3 meses", "meses": "3", "activa": "true"})
    assert admin.get("/admin/planes").text.count('name="precio_') > 26


def test_avisos_de_vencimiento(organizador, db):
    url, rifa = crear(organizador, db)
    organizador.post(f"{url}/publicar")
    db.expire_all()
    rifa = db.get(Rifa, rifa.id)
    rifa.vigente_hasta = HOY + datetime.timedelta(days=3)
    db.commit()
    avisos = dict((r.id, d) for r, d in vigencia.avisos_del_dia(db))
    assert avisos.get(rifa.id) == 3
    asunto, texto = vigencia.texto_aviso(rifa, 3, "https://rifaplus.co")
    assert "vence en 3 días" in asunto and "/renovar" in texto
    assert "vence en 3 días" in organizador.get(url).text
