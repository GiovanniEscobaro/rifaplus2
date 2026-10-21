"""Genera docs/REFERENCIA.md a partir del propio código: rutas, módulos, clases y funciones con su docstring.

Uso:  python -m herramientas.generar_referencia

Como sale del código, la referencia nunca queda desactualizada: después de cambiar algo,
vuelva a ejecutar este comando.
"""

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "app"
DESTINO = RAIZ / "docs" / "REFERENCIA.md"


def _primera_linea(texto: str | None) -> str:
    return (texto or "").strip().split("\n")[0]


def _rutas() -> list[str]:
    """Tabla de todas las direcciones de la aplicación, tomada del esquema OpenAPI que arma FastAPI."""
    from app.main import app  # importación tardía: solo se necesita al generar

    filas = ["| Método | Dirección | Qué hace |", "|---|---|---|"]
    for ruta, operaciones in sorted(app.openapi()["paths"].items()):
        for metodo, datos in sorted(operaciones.items()):
            filas.append(f"| {metodo.upper()} | `{ruta}` | {_primera_linea(datos.get('description'))} |")
    return filas


def _tablas() -> list[str]:
    """Cada tabla de la base de datos con su descripción y sus columnas, tomadas de los modelos."""
    import app.core.registro_modelos  # noqa: F401
    from app.core.database import Base

    clase_de = {m.local_table.name: m.class_ for m in Base.registry.mappers}
    salida = []
    for tabla in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        clase = clase_de.get(tabla.name)
        salida += [
            f"### `{tabla.name}`",
            "",
            _primera_linea(clase.__doc__ if clase else ""),
            "",
            "| Columna | Tipo | Obligatoria | Relación / regla |",
            "|---|---|---|---|",
        ]
        for col in tabla.columns:
            relacion = ", ".join(f"→ `{fk.target_fullname}`" for fk in col.foreign_keys)
            if col.primary_key:
                relacion = "llave primaria"
            elif col.unique:
                relacion = (relacion + " · única").strip(" ·")
            salida.append(f"| `{col.name}` | {col.type} | {'no' if col.nullable else 'sí'} | {relacion} |")
        reglas = [
            c
            for c in tabla.constraints
            if c.__class__.__name__ in ("CheckConstraint", "UniqueConstraint")
            and c.name
            and not c.name.startswith(("pk_",))
        ]
        for regla in reglas:
            texto = getattr(regla, "sqltext", None)
            columnas = ", ".join(f"`{c.name}`" for c in regla.columns)
            detalle = f"`{texto}`" if texto is not None else f"{columnas} únicos juntos"
            salida.append(f"| _regla_ | `{regla.name}` | | {detalle} |")
        salida.append("")
    return salida


def _archivo(ruta: Path) -> list[str]:
    """Sección de un archivo: su docstring y la lista de clases y funciones."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    relativo = ruta.relative_to(RAIZ).as_posix()
    salida = [f"### `{relativo}`", "", _primera_linea(ast.get_docstring(arbol)) or "_(sin descripción)_", ""]
    for nodo in arbol.body:
        if isinstance(nodo, ast.ClassDef):
            salida.append(f"- **clase `{nodo.name}`**: {_primera_linea(ast.get_docstring(nodo))}")
            for hijo in nodo.body:
                if isinstance(hijo, ast.FunctionDef | ast.AsyncFunctionDef) and not hijo.name.startswith("__"):
                    salida.append(f"  - `{hijo.name}`: {_primera_linea(ast.get_docstring(hijo))}")
        elif isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
            privada = " _(interna)_" if nodo.name.startswith("_") else ""
            salida.append(f"- `{nodo.name}()`{privada}: {_primera_linea(ast.get_docstring(nodo))}")
    return salida + [""]


def main() -> None:
    """Escribe docs/REFERENCIA.md."""
    partes = [
        "# Referencia del código de RifaPlus",
        "",
        "> Archivo generado con `python -m herramientas.generar_referencia`. No lo edite a mano:",
        "> la descripción de cada función está en su docstring, dentro del código.",
        "",
        "## Direcciones (rutas)",
        "",
        *_rutas(),
        "",
        "## Tablas de la base de datos",
        "",
        *_tablas(),
        "## Archivos, clases y funciones",
        "",
    ]
    for ruta in sorted(APP.rglob("*.py")):
        if ruta.name != "__init__.py":
            partes += _archivo(ruta)
    DESTINO.write_text("\n".join(partes), encoding="utf-8")
    print(f"Escrito {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
