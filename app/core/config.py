"""Configuración de RifaPlus, leída de las variables de entorno o del archivo .env (ver .env.example)."""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    """Valores de configuración. Cada atributo se puede cambiar con una variable del mismo nombre en .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_nombre: str = "RifaPlus"
    app_entorno: str = "desarrollo"
    app_url: str = "http://localhost:8000"
    clave_secreta: str = "cambie-esto"
    database_url: str = "postgresql+psycopg://rifaplus:rifaplus@localhost:5432/rifaplus"  # DATABASE_URL
    sesion_horas: int = 8
    max_intentos_fallidos: int = 5
    minutos_bloqueo: int = 15
    carpeta_archivos: str = "uploads"  # comprobantes de pago (fuera de la carpeta pública)
    max_mb_comprobante: int = 5

    # Correo de salida (por ejemplo Gmail con una "contraseña de aplicación"). Si smtp_usuario está vacío,
    # los correos no se envían: solo se escriben en el registro del servidor.
    smtp_host: str = "smtp.gmail.com"
    smtp_puerto: int = 587
    smtp_usuario: str = ""
    smtp_clave: str = ""
    correo_remitente: str = ""  # si se deja vacío, se usa smtp_usuario
    correo_avisos_admin: str = ""  # a dónde le llegan al superadministrador los avisos de pagos y soporte

    # Datos del responsable de RifaPlus para los términos y la política de datos
    responsable_nombre: str = ""
    responsable_documento: str = ""
    responsable_ciudad: str = ""
    correo_contacto: str = ""

    @field_validator("database_url")
    @classmethod
    def usar_psycopg(cls, valor: str) -> str:
        """Acepta postgresql://… o postgres://… y lo convierte al controlador que trae RifaPlus (psycopg 3)."""
        for prefijo in ("postgres://", "postgresql://"):
            if valor.startswith(prefijo):
                return "postgresql+psycopg://" + valor[len(prefijo) :]
        return valor

    @model_validator(mode="after")
    def revisar_produccion(self):
        """En producción no se arranca con valores de ejemplo: evita publicar el sitio con claves conocidas."""
        if self.app_entorno == "produccion":
            faltan = []
            if self.clave_secreta in ("", "cambie-esto") or len(self.clave_secreta) < 32:
                faltan.append("CLAVE_SECRETA (mínimo 32 caracteres)")
            if "rifaplus:rifaplus@localhost" in self.database_url:
                faltan.append("DATABASE_URL")
            if not self.app_url.startswith("https://"):
                faltan.append("APP_URL (debe empezar por https://)")
            if faltan:
                raise ValueError("Faltan variables de producción en el entorno: " + ", ".join(faltan))
        return self

    @property
    def es_desarrollo(self) -> bool:
        """True en el computador del desarrollador: muestra la clave temporal en pantalla y la documentación /docs."""
        return self.app_entorno == "desarrollo"

    @property
    def correo_activo(self) -> bool:
        """True si hay datos de correo de salida configurados."""
        return bool(self.smtp_usuario and self.smtp_clave)


@lru_cache
def obtener_config() -> Configuracion:
    """Devuelve la configuración. Se lee una sola vez y queda en memoria (lru_cache)."""
    return Configuracion()
