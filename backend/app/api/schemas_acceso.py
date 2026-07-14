"""DTOs de gestión de usuarios y accesos (RF-1002, doc 07)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Rol = Literal["ADMINISTRADOR", "SUPERVISOR", "CLIENTE"]


class AgregarMiembroRequest(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    rol: Rol
    participante_uuid: str | None = None


class CambiarRolRequest(BaseModel):
    rol: Rol
    participante_uuid: str | None = None


class ReiniciarClaveRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class MiembroResponse(BaseModel):
    usuario_uuid: str
    nombre: str
    email: str
    rol: str
    activo: bool
    participante_uuid: str | None
    participante_nombre: str | None


class AgregarMiembroResponse(BaseModel):
    usuario_uuid: str
    creado: bool
