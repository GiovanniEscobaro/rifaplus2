"""Validación de los datos de venta: comprador, vendedor y pagos."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modulos.acceso.esquemas import normalizar_celular

TIPOS_DOCUMENTO = {
    "CC": "Cédula de ciudadanía",
    "CE": "Cédula de extranjería",
    "TI": "Tarjeta de identidad",
    "PP": "Pasaporte",
    "NIT": "NIT",
}
MEDIOS_DIFUSION = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "whatsapp": "WhatsApp",
    "publicidad": "Publicidad impresa",
    "recomendacion": "Recomendación",
    "otro": "Otro",
}


class _ConDocumento(BaseModel):
    """Base para personas con documento: tipo válido y número limpio."""

    tipo_documento: str
    numero_documento: str = Field(min_length=3, max_length=20)

    @field_validator("tipo_documento")
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        """Solo se aceptan los tipos de documento de la lista."""
        if v not in TIPOS_DOCUMENTO:
            raise ValueError("Escoja el tipo de documento.")
        return v

    @field_validator("numero_documento")
    @classmethod
    def documento_limpio(cls, v: str) -> str:
        """Quita puntos, espacios y guiones del documento: '1.045.123' -> '1045123'."""
        v = "".join(c for c in v if c.isalnum()).upper()
        if len(v) < 3:
            raise ValueError("Escriba el número de documento completo.")
        return v


class Comprador(_ConDocumento):
    """Todos los datos son obligatorios: si gana, hay que poder ubicarlo y entregarle el premio."""

    nombre: str = Field(min_length=3, max_length=150)
    celular: str
    whatsapp: str
    email: EmailStr
    direccion: str = Field(min_length=5, max_length=200)
    ciudad: str = Field(min_length=2, max_length=100)
    acepta_whatsapp: bool = False

    @field_validator("celular", "whatsapp")
    @classmethod
    def telefono(cls, v: str) -> str:
        """Normaliza el número al formato internacional (+57…)."""
        return normalizar_celular(v)

    @field_validator("email")
    @classmethod
    def email_minusculas(cls, v: str) -> str:
        """Guarda el correo en minúsculas y sin espacios."""
        return v.lower().strip()

    @field_validator("nombre", "direccion", "ciudad")
    @classmethod
    def sin_espacios(cls, v: str) -> str:
        """Quita espacios repetidos en nombre, dirección y ciudad."""
        return " ".join(v.split())


class DatosPago(BaseModel):
    """Un pago registrado por el organizador: valor, medio y referencia."""

    monto: int = Field(gt=0)
    medio_pago_id: int
    referencia: str | None = Field(default=None, max_length=100)

    @field_validator("referencia")
    @classmethod
    def vacio_a_none(cls, v):
        """Referencia vacía -> None."""
        return (v or "").strip() or None


class VendedorCrear(_ConDocumento):
    """Datos para agregar un vendedor."""

    nombre: str = Field(min_length=3, max_length=150)
    celular: str
    ciudad: str | None = Field(default=None, max_length=100)
    comision_porcentaje: float = Field(default=0, ge=0, le=100)
    llave_bre_b: str = Field(min_length=3, max_length=60)  # obligatoria: a dónde se le paga la comisión

    @field_validator("llave_bre_b")
    @classmethod
    def llave_limpia(cls, v: str) -> str:
        """Quita espacios sobrantes de la llave (celular, cédula, correo o alias como @PEPITO)."""
        v = " ".join(v.split())
        if len(v) < 3:
            raise ValueError("Escriba la llave Bre-B del vendedor para poder pagarle su comisión.")
        return v

    @field_validator("celular")
    @classmethod
    def telefono(cls, v: str) -> str:
        """Normaliza el número al formato internacional (+57…)."""
        return normalizar_celular(v)
