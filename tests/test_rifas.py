"""Opciones por plan, creación de rifas, declaración, publicación, búsqueda, verificación y reglas de la base."""

import datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.modulos.legal.modelos import Aceptacion
from app.modulos.rifas.generador import opciones_disponibles
from app.modulos.rifas.modelos import Boleta, Loteria, NumeroBoleta, Rifa


@pytest.fixture
def datos_rifa(db):
    loteria = db.scalar(select(Loteria).where(Loteria.nombre == "Lotería de Boyacá"))
    return dict(
        nombre="Rifa juego de cocina",
        premio_mayor="Juego de cocina completo",
        loteria_id=str(loteria.id),
        fecha_sorteo=(datetime.date.today() + datetime.timedelta(days=30)).isoformat(),
        opcion="2-4",
        valor_boleta="10000",
        acepta_declaracion="true",
    )


def crear(cliente, datos, **cambios):
    return cliente.post("/panel/rifas/nueva", data=datos | cambios, follow_redirects=False)


def ultima_rifa(db):
    db.expire_all()
    return db.scalars(select(Rifa).order_by(Rifa.id.desc())).first()


def test_opciones_salen_de_los_planes(db):
    resumen = [(o.cifras, o.numeros_por_boleta, o.boletas, o.valor) for o in opciones_disponibles(db)]
    assert resumen == [
        (1, 2, 5, 0),
        (1, 1, 10, 0),
        (2, 4, 25, 6000),
        (2, 2, 50, 19900),
        (2, 1, 100, 19900),
        (3, 4, 250, 59900),
        (3, 2, 500, 59900),
        (3, 1, 1000, 89900),
        (4, 8, 1250, 149900),
        (4, 5, 2000, 149900),
        (4, 4, 2500, 149900),
        (4, 2, 5000, 299900),
        (4, 1, 10000, 299900),
    ]


def test_formulario_muestra_las_opciones(organizador):
    pagina = organizador.get("/panel/rifas/nueva").text
    assert pagina.count('name="opcion"') == 13 and "2.500 boletas" in pagina and "Declaración del organizador" in pagina


def test_rifa_gratis_de_una_cifra(organizador, datos_rifa, db):
    assert crear(organizador, datos_rifa, opcion="1-1").status_code == 303
    rifa = ultima_rifa(db)
    numeros = sorted(db.scalars(select(NumeroBoleta.numero).where(NumeroBoleta.rifa_id == rifa.id)))
    assert (rifa.total_boletas, rifa.total_numeros) == (10, 10)
    assert numeros == [str(i) for i in range(10)]


def test_con_un_numero_la_boleta_es_su_numero(organizador, datos_rifa, db):
    url = crear(organizador, datos_rifa, opcion="1-1").headers["location"].split("?")[0]
    rifa = ultima_rifa(db)
    boletas = db.scalars(select(Boleta).where(Boleta.rifa_id == rifa.id).order_by(Boleta.consecutivo)).all()
    assert [(b.consecutivo, [n.numero for n in b.numeros]) for b in boletas] == [(i, [str(i)]) for i in range(10)]
    assert "Boleta 7" in organizador.get(url).text


def test_con_varios_numeros_la_boleta_lleva_consecutivo(organizador, datos_rifa, db):
    url = crear(organizador, datos_rifa, opcion="1-2").headers["location"].split("?")[0]
    pagina = organizador.get(url).text
    assert "Boleta 1" in pagina and "Boleta 5" in pagina and "Cifras de la boleta" in pagina


def test_rifa_de_2500_boletas_con_cuatro_numeros(organizador, datos_rifa, db):
    assert crear(organizador, datos_rifa, opcion="4-4").status_code == 303
    rifa = ultima_rifa(db)
    distintos = db.scalar(select(func.count(func.distinct(NumeroBoleta.numero))).where(NumeroBoleta.rifa_id == rifa.id))
    assert (rifa.total_boletas, distintos, rifa.plan.nombre) == (2500, 10000, "2.500 boletas de 4 cifras")


def test_crear_rifa_exige_la_declaracion(organizador, datos_rifa):
    r = crear(organizador, datos_rifa, acepta_declaracion="")
    assert r.status_code == 422 and "declaración de responsabilidad" in r.text


def test_crear_rifa_guarda_la_declaracion(organizador, datos_rifa, db):
    crear(organizador, datos_rifa)
    rifa = ultima_rifa(db)
    declaracion = db.scalar(select(Aceptacion).where(Aceptacion.rifa_id == rifa.id))
    assert declaracion.documento == "declaracion_rifa" and "único responsable" in declaracion.texto_aceptado


@pytest.mark.parametrize("opcion", ["2-3", "2-5", "3-8"])
def test_rechaza_combinaciones_fuera_de_los_planes(organizador, datos_rifa, opcion):
    r = crear(organizador, datos_rifa, opcion=opcion)
    assert r.status_code == 422


def test_rifa_gratis_se_publica(organizador, datos_rifa):
    url = crear(organizador, datos_rifa, opcion="1-2").headers["location"].split("?")[0]
    assert "Publicar rifa" in organizador.get(url).text
    organizador.post(f"{url}/publicar")
    assert "en venta" in organizador.get(url).text


def test_rifa_de_pago_pide_el_pago_al_publicar(organizador, datos_rifa):
    url = crear(organizador, datos_rifa, opcion="3-4").headers["location"].split("?")[0]
    pagina = organizador.get(url).text
    assert "Publicar rifa" in pagina and "$59.900" in pagina and "Para publicar esta rifa debe pagar" not in pagina
    r = organizador.post(f"{url}/publicar", follow_redirects=False)
    assert r.headers["location"] == f"{url}/pagar"
    assert "en venta" not in organizador.get(url).text


def test_busqueda_y_paginas(organizador, datos_rifa, db):
    url = crear(organizador, datos_rifa, opcion="3-2").headers["location"].split("?")[0]
    assert "Página 1 de 5" in organizador.get(url).text
    rifa = ultima_rifa(db)
    numero = db.scalar(select(NumeroBoleta).where(NumeroBoleta.rifa_id == rifa.id, NumeroBoleta.numero == "777"))
    r = organizador.get(url, params={"buscar": "777"})
    assert "1 encontrada" in r.text and ">777<" in r.text
    assert numero is not None


def test_ver_una_rifa_exige_sesion(organizador, datos_rifa):
    url = crear(organizador, datos_rifa).headers["location"].split("?")[0]
    organizador.post("/salir")
    assert organizador.get(url, follow_redirects=False).status_code == 303


def test_verificacion_publica_muestra_al_organizador(organizador, datos_rifa, db):
    crear(organizador, datos_rifa)
    rifa = ultima_rifa(db)
    codigo = db.scalar(select(Boleta.codigo_verificacion).where(Boleta.rifa_id == rifa.id))
    r = organizador.get(f"/verificar/{codigo}")
    assert "Boleta auténtica" in r.text and "Organiza:" in r.text and "plataforma de administración" in r.text
    assert organizador.get("/verificar/NOEXISTE00").status_code == 404


def test_la_base_de_datos_impide_numeros_repetidos(organizador, datos_rifa, db):
    crear(organizador, datos_rifa)
    rifa = ultima_rifa(db)
    existente = db.scalar(select(NumeroBoleta).where(NumeroBoleta.rifa_id == rifa.id))
    db.add(NumeroBoleta(rifa_id=rifa.id, boleta_id=existente.boleta_id, numero=existente.numero))
    with pytest.raises(IntegrityError, match="uq_numero_por_rifa"):
        db.commit()
    db.rollback()


def test_la_base_de_datos_exige_rango_completo(organizador, datos_rifa, db):
    crear(organizador, datos_rifa)
    rifa_id = ultima_rifa(db).id
    with pytest.raises(IntegrityError, match="rango_completo"):
        db.execute(
            text("UPDATE rifas SET total_numeros = 50, total_boletas = 25, series_por_boleta = 2 WHERE id = :id"),
            {"id": rifa_id},
        )
        db.commit()
    db.rollback()


def test_eliminar_rifa_sin_ventas(organizador, datos_rifa, db):
    url = crear(organizador, datos_rifa, opcion="1-1").headers["location"].split("?")[0]
    rifa_id = ultima_rifa(db).id
    assert "Eliminar rifa" in organizador.get(url).text
    r = organizador.post(f"{url}/eliminar", follow_redirects=False)
    assert r.headers["location"] == "/panel?eliminada=1"
    db.expire_all()
    assert db.get(Rifa, rifa_id) is None
    assert db.scalar(select(func.count()).select_from(Boleta).where(Boleta.rifa_id == rifa_id)) == 0
    declaracion = db.scalar(
        select(Aceptacion).where(Aceptacion.documento == "declaracion_rifa").order_by(Aceptacion.id.desc())
    )
    assert declaracion.rifa_id is None  # la declaración se conserva


def test_no_se_elimina_rifa_con_ventas(organizador, datos_rifa, db):
    url = crear(organizador, datos_rifa, opcion="1-1").headers["location"].split("?")[0]
    organizador.post(f"{url}/publicar")
    rifa = ultima_rifa(db)
    boleta = db.scalar(select(Boleta).where(Boleta.rifa_id == rifa.id, Boleta.consecutivo == 3))
    organizador.post(
        f"{url}/boletas/{boleta.id}/vender",
        data={
            "tipo_documento": "CC",
            "numero_documento": "123456",
            "nombre": "Pepito Pérez",
            "celular": "3001112222",
            "whatsapp": "3001112222",
            "email": "p@p.co",
            "direccion": "Calle 1 # 2-3",
            "ciudad": "Soledad",
        },
    )
    assert "Eliminar rifa" not in organizador.get(url).text
    r = organizador.post(f"{url}/eliminar")
    assert r.status_code == 422 and "boletas vendidas" in r.text
