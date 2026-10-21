"""Comandos de administración.

python -m app.cli semillas            Carga loterías, medios de pago y planes
python -m app.cli crear-superadmin    Crea su usuario de superadministrador
python -m app.cli avisar-vencimientos Avisa por correo las rifas que vencen (una vez al día, con cron)
python -m app.cli borrar-datos-prueba Borra organizadores, rifas y ventas para empezar de cero (pide confirmación)
"""

import argparse
import getpass

from sqlalchemy import select

import app.core.registro_modelos  # noqa: F401
from app.core import semillas
from app.core.database import SesionLocal
from app.core.seguridad import cifrar_clave, validar_clave_nueva
from app.modulos.acceso.modelos import Usuario


def cmd_semillas(_: argparse.Namespace) -> None:
    """Carga los datos iniciales (loterías, medios de pago y planes) sin duplicar los existentes."""
    with SesionLocal() as db:
        semillas.cargar(db)
    print("Datos iniciales cargados: loterías, medios de pago y planes.")


def cmd_borrar_datos_prueba(_: argparse.Namespace) -> None:
    """Muestra qué se va a borrar, pide escribir BORRAR y borra los datos de prueba (ver app/core/limpieza.py)."""
    from app.core import limpieza

    with SesionLocal() as db:
        print("Se van a borrar estos registros:")
        for tabla, cantidad in limpieza.contar(db).items():
            print(f"  {tabla:28} {cantidad:>8,}".replace(",", "."))
        print("\nSe conservan: superadministradores, loterías, medios de pago, precios y cuentas de RifaPlus.")
        if input("\nPara confirmar escriba BORRAR: ").strip() != "BORRAR":
            raise SystemExit("No se borró nada.")
        limpieza.borrar_datos_de_prueba(db)
    print(
        "Listo: RifaPlus quedó sin datos de prueba.\n"
        "Si quiere quitar también las fotos y comprobantes, borre la carpeta uploads/."
    )


def cmd_avisar_vencimientos(_: argparse.Namespace) -> None:
    """Envía por correo los avisos de vencimiento del día (programarlo una vez al día con cron)."""
    from datetime import date

    from app.core.config import obtener_config
    from app.core.correo import enviar
    from app.modulos.rifas import vigencia

    with SesionLocal() as db:
        enviados = 0
        for rifa, dias in vigencia.avisos_del_dia(db):
            asunto, texto = vigencia.texto_aviso(rifa, dias, obtener_config().app_url)
            if enviar(rifa.organizador.email, asunto, texto):
                enviados += 1
            rifa.ultimo_aviso_vencimiento = date.today()
        db.commit()
    print(f"Avisos de vencimiento enviados: {enviados}")


def cmd_crear_superadmin(_: argparse.Namespace) -> None:
    """Pide nombre, correo y clave por consola y crea un usuario con rol superadmin."""
    nombre = input("Nombre: ").strip()
    email = input("Correo: ").strip().lower()
    clave = getpass.getpass("Clave: ")
    error = validar_clave_nueva(clave, getpass.getpass("Confirme la clave: "))
    if error:
        raise SystemExit(error)
    with SesionLocal() as db:
        if db.scalar(select(Usuario).where(Usuario.email == email)):
            raise SystemExit("Ya existe un usuario con ese correo.")
        db.add(
            Usuario(
                nombre=nombre,
                email=email,
                password_hash=cifrar_clave(clave),
                rol="superadmin",
                organizador_id=None,
                debe_cambiar_clave=False,
                email_verificado=True,
            )
        )
        db.commit()
    print(f"Superadministrador {email} creado.")


def main() -> None:
    """Lee el subcomando escrito en la consola y ejecuta la función que le corresponde."""
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Administración de RifaPlus")
    sub = parser.add_subparsers(required=True)
    sub.add_parser("semillas", help="Carga los datos iniciales").set_defaults(func=cmd_semillas)
    sub.add_parser("crear-superadmin", help="Crea el superadministrador").set_defaults(func=cmd_crear_superadmin)
    sub.add_parser("avisar-vencimientos", help="Envía los avisos de vencimiento del día").set_defaults(
        func=cmd_avisar_vencimientos
    )
    sub.add_parser("borrar-datos-prueba", help="Borra organizadores, rifas y ventas (pide confirmación)").set_defaults(
        func=cmd_borrar_datos_prueba
    )
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
