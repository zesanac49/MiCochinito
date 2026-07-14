"""DTOs de autenticación (doc 07 §2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MembresiaResponse(BaseModel):
    natillera_uuid: str
    natillera_nombre: str
    natillera_estado: str
    rol: str


class MeResponse(BaseModel):
    uuid: str
    email: str
    nombre: str
    membresias: list[MembresiaResponse]
