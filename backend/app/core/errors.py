"""Errores de aplicación, catálogo cerrado y formato uniforme (TEC-08).

- El dominio lanza `ErrorDeDominio` (Python puro, sin HTTP).
- La capa de aplicación/api lanza `ErrorAPI` para casos con semántica HTTP
  directa (auth, permisos, no encontrado, feature flags, idempotencia).
- `CODIGO_A_HTTP` es el catálogo cerrado del doc 07 §4: un código nuevo sin
  aprobación no debe existir.
- `construir_respuesta_error` produce el sobre único del doc 05 §7.
"""

from __future__ import annotations

from typing import Final

from app.shared.domain.excepciones import ErrorDeDominio

# Catálogo cerrado de códigos → HTTP (doc 07 §4). No agregar sin aprobación.
CODIGO_A_HTTP: Final[dict[str, int]] = {
    "NO_AUTENTICADO": 401,
    "TOKEN_EXPIRADO": 401,
    "PROHIBIDO": 403,
    "SIN_MEMBRESIA": 403,
    "NO_ENCONTRADO": 404,
    "VALIDACION": 422,
    "TRANSICION_INVALIDA": 409,
    "OPERACION_NO_PERMITIDA_EN_ESTADO": 409,
    "SALDO_INSUFICIENTE": 409,
    "VIOLACION_SEPARACION_FONDOS": 409,
    "TOPE_PRESTAMOS_EXCEDIDO": 409,
    "TOPE_CAPITAL_EXCEDIDO": 409,
    "PERIODO_YA_PAGADO": 409,
    "NUMERO_NO_DISPONIBLE": 409,
    "SORTEO_YA_REGISTRADO": 409,
    "ACTIVIDAD_NO_CERRABLE": 409,
    "LIQUIDACION_BLOQUEADA": 409,
    "CONFIRMACION_INCORRECTA": 409,
    "CLIENTE_REQUIERE_PARTICIPANTE": 409,
    "ULTIMO_ADMINISTRADOR": 409,
    "MIEMBRO_YA_EXISTE": 409,
    "FUNCIONALIDAD_NO_DISPONIBLE": 409,
    "CONFLICTO_IDEMPOTENCIA": 409,
    "ERROR_INTERNO": 500,
}

# HTTP por defecto para un ErrorDeDominio cuyo código no está tabulado: los
# errores de dominio son conflictos con el estado del negocio (409).
_HTTP_DOMINIO_DEFECTO: Final[int] = 409


class ErrorAPI(Exception):
    """Error con semántica HTTP directa (auth, permisos, recursos, flags)."""

    codigo: str = "ERROR_INTERNO"
    estado_http: int = 500

    def __init__(self, mensaje: str, detalle: dict[str, object] | None = None) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalle: dict[str, object] = detalle or {}


class NoAutenticado(ErrorAPI):
    codigo = "NO_AUTENTICADO"
    estado_http = 401


class TokenExpirado(ErrorAPI):
    codigo = "TOKEN_EXPIRADO"
    estado_http = 401


class Prohibido(ErrorAPI):
    codigo = "PROHIBIDO"
    estado_http = 403


class SinMembresia(ErrorAPI):
    codigo = "SIN_MEMBRESIA"
    estado_http = 403


class NoEncontrado(ErrorAPI):
    codigo = "NO_ENCONTRADO"
    estado_http = 404


class FuncionalidadNoDisponible(ErrorAPI):
    """Feature flag apagado (RN-091, TEC-06)."""

    codigo = "FUNCIONALIDAD_NO_DISPONIBLE"
    estado_http = 409


class ConflictoIdempotencia(ErrorAPI):
    codigo = "CONFLICTO_IDEMPOTENCIA"
    estado_http = 409


def estado_http_para(error: ErrorDeDominio | ErrorAPI) -> int:
    """Resuelve el estado HTTP para un error de dominio o de API."""
    if isinstance(error, ErrorAPI):
        return error.estado_http
    return CODIGO_A_HTTP.get(error.codigo, _HTTP_DOMINIO_DEFECTO)


def construir_respuesta_error(
    codigo: str,
    mensaje: str,
    request_id: str,
    detalle: dict[str, object] | None = None,
) -> dict[str, object]:
    """Sobre único de error (doc 05 §7)."""
    return {
        "error": {
            "codigo": codigo,
            "mensaje": mensaje,
            "detalle": detalle or {},
            "request_id": request_id,
        }
    }
