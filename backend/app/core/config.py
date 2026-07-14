"""Configuración de la aplicación (TEC-06, doc 05 §10).

`Settings` se lee de variables de entorno (o `.env` solo en local). Sin secretos
en el repositorio. `FeatureFlags` de sistema mantiene apagadas las
funcionalidades fuera del MVP (RN-091): donaciones, rendimientos bancarios, CDT,
inversiones y otros ingresos. Estas NO se implementan; solo existe el punto de
extensión.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FeatureFlags(BaseSettings):
    """Flags de sistema (por despliegue). Todos apagados en el MVP (RN-091)."""

    model_config = SettingsConfigDict(env_prefix="FLAG_", extra="ignore")

    donaciones: bool = False
    rendimientos_bancarios: bool = False
    cdt: bool = False
    inversiones: bool = False
    otros_ingresos: bool = False


class Settings(BaseSettings):
    """Configuración central. Se instancia una sola vez (ver `get_settings`)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Entorno ------------------------------------------------------------
    entorno: str = Field(default="local", description="local | test | prod")
    debug: bool = False

    # --- Base de datos ------------------------------------------------------
    # En local/CI sin Docker se usa SQLite (tests rápidos de API, doc 05 §9).
    # En integración financiera y producción: MySQL 8 (TEC-07).
    database_url: str = Field(
        default="sqlite+pysqlite:///./natillera_local.db",
        description="URL SQLAlchemy. MySQL en prod: mysql+pymysql://user:pass@host/db",
    )
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # --- Seguridad / JWT (RF-1001) -----------------------------------------
    jwt_secret: str = Field(
        default="cambia-esto-en-produccion-por-un-secreto-largo-y-aleatorio",
        description="Secreto de firma JWT. En prod SIEMPRE por variable de entorno.",
    )
    jwt_algoritmo: str = "HS256"
    access_token_minutos: int = 15
    refresh_token_dias: int = 14

    # --- Observabilidad -----------------------------------------------------
    log_json: bool = True
    log_nivel: str = "INFO"

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "prod"

    @property
    def usa_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def feature_flags(self) -> FeatureFlags:
        return FeatureFlags()


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuración (cacheado). Inyectable como dependencia."""
    return Settings()
