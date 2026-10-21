"""Editar una rifa en borrador (todo) y corregirla en venta (solo lo que no perjudica a compradores)."""

import datetime

import pytest
from sqlalchemy import func, select

from app.modulos.pagos.modelos import CobroRifa
from app.modulos.rifas.modelos import Boleta, Loteria, NumeroBoleta, Rifa

HOY = datetime.date.today()


def dia(n):
    return (HOY + datetime.timedelta(days=n)).isoformat()


@pytest.fixture
def base(db):
    boyaca = str(db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá")))
    return dict(
        nombre="Rifa a editar",
        premio_mayor="Bicicleta",
        loteria_id=boyaca,
        fecha_sorteo=dia(40),
        opcion="1-1",
        valor_boleta="10.000",
        acepta_declaracion="true",
        cuota_valor_1="10.000",
        cuota_fecha_1=dia(30),
        seco_descripcion_1="Gorra",
        seco_loteria_id_1=boyaca,
        seco_fecha_juego_1=dia(10),
    )


def crear(organizador, db, datos):
    r = organizador.post("/panel/rifas/nueva", data=datos, follow_redirects=False)
    db.expire_all()
    return r.headers["location"].split("?")[0], db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()


def test_formulario_de_edicion_trae_los_datos(organizador, db, base):
    url, _ = crear(organizador, db, base)
    pagina = organizador.get(f"{url}/editar").text
    assert "Editar rifa" in pagina and 'value="Rifa a editar"' in pagina and 'value="10.000"' in pagina
    assert 'value="Gorra"' in pagina and "Declaración del organizador" not in pagina


def test_editar_borrador_cambia_todo_y_regenera_boletas(organizador, db, base):
    url, rifa = crear(organizador, db, base)
    nuevos = base | dict(
        nombre="Rifa corregida",
        premio_mayor="Moto",
        valor_premio="3.000.000",
        opcion="1-2",
        valor_boleta="20.000",
        cuota_valor_1="10.000",
        cuota_fecha_1=dia(15),
        cuota_valor_2="10.000",
        cuota_fecha_2=dia(35),
        seco_descripcion_1="Licuadora",
    )
    r = organizador.post(f"{url}/editar", data=nuevos, follow_redirects=False)
    assert r.status_code == 303
    db.expire_all()
    rifa = db.get(Rifa, rifa.id)
    assert (rifa.nombre, rifa.total_boletas, int(rifa.valor_boleta), len(rifa.cuotas)) == (
        "Rifa corregida",
        5,
        20000,
        2,
    )
    assert {p.descripcion for p in rifa.premios} == {"Moto", "Licuadora"}
    assert db.scalar(select(func.count()).select_from(Boleta).where(Boleta.rifa_id == rifa.id)) == 5
    assert db.scalar(select(func.count()).select_from(NumeroBoleta).where(NumeroBoleta.rifa_id == rifa.id)) == 10


def test_editar_borrador_valida_igual_que_crear(organizador, db, base):
    url, _ = crear(organizador, db, base)
    r = organizador.post(f"{url}/editar", data=base | {"cuota_valor_1": "5.000"})
    assert r.status_code == 422 and "deben ser iguales" in r.text


def test_cambiar_a_plan_de_pago_deja_el_cobro_pendiente(organizador, db, base):
    url, rifa = crear(organizador, db, base)
    organizador.post(f"{url}/editar", data=base | {"opcion": "2-4"})  # 25 boletas: plan de $6.000
    db.expire_all()
    cobro = db.scalar(select(CobroRifa).where(CobroRifa.rifa_id == rifa.id))
    assert (cobro.estado, int(cobro.valor)) == ("pendiente", 6000)


def test_en_venta_solo_se_corrigen_algunos_datos(organizador, db, base):
    url, rifa = crear(organizador, db, base)
    organizador.post(f"{url}/publicar")
    pagina = organizador.get(f"{url}/editar").text
    assert "Corregir rifa" in pagina and "fecha_sorteo" not in pagina
    mayor = next(p for p in rifa.premios if p.tipo == "mayor")
    r = organizador.post(
        f"{url}/editar",
        follow_redirects=False,
        data={
            "nombre": "Rifa en venta corregida",
            f"premio_descripcion_{mayor.id}": "Bicicleta de montaña",
            f"premio_valor_{mayor.id}": "1.200.000",
            "seco_descripcion_1": "Termo",
            "seco_loteria_id_1": base["loteria_id"],
            "seco_fecha_juego_1": dia(20),
            "fecha_sorteo": dia(90),
            "valor_boleta": "99.000",
        },
    )
    assert r.status_code == 303
    db.expire_all()
    rifa = db.get(Rifa, rifa.id)
    assert rifa.nombre == "Rifa en venta corregida" and int(rifa.valor_boleta) == 10000
    assert rifa.fecha_sorteo == HOY + datetime.timedelta(days=40)
    assert {"Bicicleta de montaña", "Gorra", "Termo"} == {p.descripcion for p in rifa.premios}


def test_en_venta_no_acepta_secos_despues_del_sorteo(organizador, db, base):
    url, _ = crear(organizador, db, base)
    organizador.post(f"{url}/publicar")
    r = organizador.post(
        f"{url}/editar",
        data={
            "nombre": "Rifa",
            "seco_descripcion_1": "Termo",
            "seco_loteria_id_1": base["loteria_id"],
            "seco_fecha_juego_1": dia(60),
        },
    )
    assert r.status_code == 422 and "antes del sorteo" in r.text
