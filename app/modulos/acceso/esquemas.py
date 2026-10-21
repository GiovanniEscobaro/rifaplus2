"""Validación de datos de entrada del módulo de acceso."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


def normalizar_celular(valor: str) -> str:
    """Deja el número en formato internacional. Asume Colombia (+57) si no trae indicativo."""
    digitos = re.sub(r"\D", "", valor or "")
    if valor.strip().startswith("+"):
        numero = "+" + digitos
    elif len(digitos) == 10 and digitos.startswith("3"):
        numero = "+57" + digitos
    elif digitos.startswith("57") and len(digitos) == 12:
        numero = "+" + digitos
    else:
        numero = "+" + digitos
    if not 11 <= len(numero) <= 16:
        raise ValueError("Escriba un número de celular válido, por ejemplo 300 123 4567.")
    return numero


class RegistroOrganizador(BaseModel):
    """Datos del formulario de registro, ya limpios y validados."""

    tipo_persona: str
    nombre: str = Field(min_length=3, max_length=150)
    email: EmailStr
    celular: str
    whatsapp: str
    direccion: str | None = Field(default=None, max_length=200)
    ciudad: str | None = Field(default=None, max_length=100)
    tipo_documento: str  # obligatorio: CC, CE, PP o NIT
    numero_documento: str = Field(max_length=20)  # obligatorio y único: una cuenta por documento
    acepta_datos: bool
    acepta_terminos: bool = False

    @field_validator("tipo_persona")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        """Solo se acepta persona natural o jurídica."""
        if v not in ("natural", "juridica"):
            raise ValueError("Escoja persona natural o jurídica.")
        return v

    @field_validator("celular", "whatsapp")
    @classmethod
    def telefono(cls, v: str) -> str:
        """Normaliza celular y WhatsApp al formato internacional (+57…)."""
        return normalizar_celular(v)

    @field_validator("email")
    @classmethod
    def email_minusculas(cls, v: str) -> str:
        """Guarda el correo en minúsculas y sin espacios, para que no se dupliquen cuentas."""
        return v.lower().strip()

    @field_validator("acepta_datos")
    @classmethod
    def debe_aceptar(cls, v: bool) -> bool:
        """La política de tratamiento de datos (Ley 1581) es obligatoria."""
        if not v:
            raise ValueError("Debe aceptar la política de tratamiento de datos para registrarse.")
        return v

    @field_validator("acepta_terminos")
    @classmethod
    def debe_aceptar_terminos(cls, v: bool) -> bool:
        """Los términos y condiciones son obligatorios."""
        if not v:
            raise ValueError("Debe aceptar los términos y condiciones de RifaPlus para registrarse.")
        return v

    @field_validator("tipo_documento")
    @classmethod
    def tipo_documento_valido(cls, v: str) -> str:
        """El organizador debe identificarse: cédula, cédula de extranjería, pasaporte o NIT."""
        if v not in ("CC", "CE", "PP", "NIT"):
            raise ValueError("Escoja el tipo de documento.")
        return v

    @field_validator("numero_documento")
    @classmethod
    def documento_completo(cls, v: str) -> str:
        """Quita puntos, espacios y guiones; exige al menos 5 caracteres."""
        v = "".join(c for c in (v or "") if c.isalnum()).upper()
        if len(v) < 5:
            raise ValueError("Escriba su número de documento completo, sin puntos.")
        return v

    @field_validator("direccion", "ciudad")
    @classmethod
    def vacio_a_none(cls, v):
        """Convierte los campos opcionales vacíos en None."""
        return (v or "").strip() or None
