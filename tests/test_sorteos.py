"""Plan de cuotas, premios secos, reglas del organizador y registro de resultados."""

import datetime

import pytest
from sqlalchemy import select

from app.modulos.pagos.modelos import MedioPago
from app.modulos.rifas.modelos import Boleta, Loteria, Rifa

HOY = datetime.date.today()


def dia(n):
    return (HOY + datetime.timedelta(days=n)).isoformat()


def datos_rifa(db, **cambios):
    boyaca = db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Boyacá"))
    bogota = db.scalar(select(Loteria.id).where(Loteria.nombre == "Lotería de Bogotá"))
    base = dict(
        nombre="Rifa con cuotas",
        premio_mayor="Juego de cocina",
        loteria_id=str(boyaca),
        fecha_sorteo=dia(60),
        opcion="1-1",
        valor_boleta="40000",
        acepta_declaracion="true",
        regla_seco_atrasado="desierto",
        regla_mayor_sin_pagar="paga_saldo",
    )
    for i, n in enumerate((5, 20, 35, 50), start=1):  # 4 cuotas de $10.000
        base[f"cuota_valor_{i}"], base[f"cuota_fecha_{i}"] = "10000", dia(n)
    base |= {
        "seco_descripcion_1": "Licuadora",
        "seco_loteria_id_1": str(bogota),
        "seco_fecha_juego_1": dia(10),
        "seco_descripcion_2": "Olla arrocera",
        "seco_loteria_id_2": str(bogota),
        "seco_fecha_juego_2": dia(25),
    }
    return base | cambios


@pytest.fixture
def rifa(organizador, db):
    def crear(**cambios):
        r = organizador.post("/panel/rifas/nueva", data=datos_rifa(db, **cambios), follow_redirects=False)
        assert r.status_code == 303, r.text[:3000]
        url = r.headers["location"].split("?")[0]
        organizador.post(f"{url}/publicar")
        db.expire_all()
        return url, db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()

    return crear


def vender(cliente, db, url, rifa, numero, pagado, doc):
    boleta = db.scalar(select(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.consecutivo == numero))
    datos = {
        "tipo_documento": "CC",
        "numero_documento": doc,
        "nombre": f"Comprador {doc}",
        "celular": "3001112222",
        "whatsapp": "3001112222",
        "email": f"{doc}@correo.co",
        "direccion": "Calle 1 # 2-3",
        "ciudad": "Soledad",
        "acepta_whatsapp": "true",
    }
    if pagado:
        datos |= {
            "monto": str(pagado),
            "medio_pago_id": str(db.scalar(select(MedioPago.id).where(MedioPago.codigo == "efectivo"))),
        }
    cliente.post(f"{url}/boletas/{boleta.id}/vender", data=datos)
    return boleta


def premio(rifa, nombre):
    return next(p for p in rifa.premios if p.descripcion == nombre)


def registrar(cliente, url, rifa, nombre, numero):
    return cliente.post(f"{url}/premios/{premio(rifa, nombre).id}/resultado", data={"resultado_loteria": numero})


def test_guarda_cuotas_secos_y_reglas(rifa):
    _, r = rifa(regla_seco_atrasado="acumula")
    assert [int(c.valor) for c in r.cuotas] == [10000] * 4
    assert sorted(p.descripcion for p in r.premios if p.tipo == "seco") == ["Licuadora", "Olla arrocera"]
    assert r.regla_seco_atrasado == "acumula"


@pytest.mark.parametrize(
    "cambios,mensaje",
    [
        ({"cuota_valor_4": "5000"}, "deben ser iguales"),
        ({"cuota_fecha_2": dia(3)}, "debe vencer después"),
        ({"cuota_fecha_4": dia(70)}, "a más tardar el día del sorteo"),
        ({"seco_fecha_juego_1": dia(90)}, "a más tardar el día del sorteo"),
    ],
)
def test_valida_el_plan(organizador, db, cambios, mensaje):
    r = organizador.post("/panel/rifas/nueva", data=datos_rifa(db, **cambios))
    assert r.status_code == 422 and mensaje in r.text


def test_sin_cuotas_queda_pago_unico(organizador, db):
    datos = {k: v for k, v in datos_rifa(db).items() if not k.startswith("cuota_")}
    organizador.post("/panel/rifas/nueva", data=datos)
    db.expire_all()
    r = db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()
    assert [(int(c.valor), c.fecha_limite) for c in r.cuotas] == [(40000, HOY + datetime.timedelta(days=60))]


def test_premio_seco_con_ganador_al_dia(organizador, db, rifa):
    url, r = rifa()
    vender(organizador, db, url, r, 3, 10000, "111")
    registrar(organizador, url, r, "Licuadora", "4723")
    db.expire_all()
    resultado = premio(r, "Licuadora").resultado
    assert (resultado.numero_jugado, resultado.estado) == ("3", "con_ganador")
    assert "Comprador 111" in organizador.get(url).text


def test_premio_seco_atrasado_queda_desierto(organizador, db, rifa):
    url, r = rifa()
    vender(organizador, db, url, r, 3, 5000, "222")
    registrar(organizador, url, r, "Licuadora", "4723")
    db.expire_all()
    assert premio(r, "Licuadora").resultado.estado == "desierto"


def test_premio_seco_atrasado_se_acumula(organizador, db, rifa):
    url, r = rifa(regla_seco_atrasado="acumula")
    vender(organizador, db, url, r, 3, 0, "333")
    registrar(organizador, url, r, "Licuadora", "4723")
    pagina = organizador.get(url).text
    assert "Incluye acumulado:</b> Licuadora" in pagina


def test_numero_no_vendido(organizador, db, rifa):
    url, r = rifa()
    registrar(organizador, url, r, "Licuadora", "9")
    db.expire_all()
    assert premio(r, "Licuadora").resultado.estado == "desierto"


def test_premio_mayor_pagado_cierra_la_rifa(organizador, db, rifa):
    url, r = rifa()
    boleta = vender(organizador, db, url, r, 7, 40000, "444")
    registrar(organizador, url, r, "Juego de cocina", "1237")
    db.expire_all()
    assert premio(r, "Juego de cocina").resultado.estado == "con_ganador"
    assert db.get(Rifa, r.id).estado == "sorteada"
    assert "Esta boleta ganó: Juego de cocina" in organizador.get(f"/verificar/{boleta.codigo_verificacion}").text


@pytest.mark.parametrize("regla,estado", [("paga_saldo", "debe_saldo"), ("desierto", "desierto")])
def test_premio_mayor_sin_pagar_aplica_la_regla(organizador, db, rifa, regla, estado):
    url, r = rifa(regla_mayor_sin_pagar=regla)
    vender(organizador, db, url, r, 7, 20000, "555")
    registrar(organizador, url, r, "Juego de cocina", "1237")
    db.expire_all()
    assert premio(r, "Juego de cocina").resultado.estado == estado


def test_corregir_y_entregar(organizador, db, rifa):
    url, r = rifa()
    vender(organizador, db, url, r, 3, 10000, "666")
    registrar(organizador, url, r, "Licuadora", "1111")
    organizador.post(f"{url}/premios/{premio(r, 'Licuadora').id}/resultado/borrar")
    registrar(organizador, url, r, "Licuadora", "4723")
    organizador.post(f"{url}/premios/{premio(r, 'Licuadora').id}/entregado")
    db.expire_all()
    resultado = premio(r, "Licuadora").resultado
    assert resultado.numero_jugado == "3" and resultado.premio_entregado_en is not None
    r2 = organizador.post(f"{url}/premios/{premio(r, 'Licuadora').id}/resultado/borrar", follow_redirects=False)
    assert "aviso_error" in r2.headers["location"]


def test_boleta_muestra_plan_y_atrasadas(organizador, db, rifa):
    url, r = rifa()
    boleta = vender(organizador, db, url, r, 2, 10000, "777")
    pagina = organizador.get(f"{url}/boletas/{boleta.id}").text
    assert "Plan de pagos" in pagina and "Próxima" in pagina
    assert "Atrasadas" in organizador.get(url).text


def test_valores_con_puntos_de_miles(organizador, db):
    datos = datos_rifa(db, valor_boleta="40.000", valor_premio="2.500.000")
    for i in range(1, 5):
        datos[f"cuota_valor_{i}"] = "10.000"
    r = organizador.post("/panel/rifas/nueva", data=datos, follow_redirects=False)
    assert r.status_code == 303
    db.expire_all()
    rifa = db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()
    assert int(rifa.valor_boleta) == 40000 and int(rifa.premios[0].valor_estimado) == 2500000
