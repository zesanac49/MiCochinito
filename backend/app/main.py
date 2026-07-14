"""Factory de la aplicación FastAPI (doc 05 §3).

Ensambla: configuración, logging con request_id, handlers globales de error
(formato uniforme del doc 05 §7) y endpoints de salud. Los routers de cada
módulo se registran aquí a medida que existen (Sprint 1 en adelante).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.acceso_router import router as acceso_router
from app.api.auth_router import router as auth_router
from app.core.config import Settings, get_settings
from app.core.errors import (
    ErrorAPI,
    construir_respuesta_error,
    estado_http_para,
)
from app.core.eventbus import BusDeEventosEnMemoria
from app.core.logging import (
    configurar_logging,
    limpiar_contexto_request,
    nuevo_request_id,
    obtener_logger,
    vincular_contexto_request,
)
from app.modules.actividades.api.routers import router as actividades_router
from app.modules.contabilidad.api.routers import router as contabilidad_router
from app.modules.cuotas.api.routers import router as cuotas_router
from app.modules.liquidacion.api.routers import router as liquidacion_router
from app.modules.multas.api.routers import router as multas_router
from app.modules.natilleras.api.routers import router as natilleras_router
from app.modules.participantes.api.routers import router as participantes_router
from app.modules.prestamos.api.routers import router as prestamos_router
from app.shared.domain.excepciones import ErrorDeDominio
from app.shared.infrastructure.db import crear_engine, crear_session_factory
from app.shared.infrastructure.resolver_principal import ResolverPrincipalSQLAlchemy

_HEADER_REQUEST_ID = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Asigna un request_id por petición y lo vincula al contexto de logs."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(_HEADER_REQUEST_ID) or nuevo_request_id()
        request.state.request_id = request_id
        vincular_contexto_request(request_id, ruta=request.url.path, metodo=request.method)
        log = obtener_logger("http")
        try:
            respuesta = await call_next(request)
        finally:
            limpiar_contexto_request()
        respuesta.headers[_HEADER_REQUEST_ID] = request_id
        log.info("request_completado", status=respuesta.status_code)
        return respuesta


def _request_id_de(request: Request) -> str:
    return getattr(request.state, "request_id", "sin-request-id")


def _registrar_handlers(app: FastAPI) -> None:
    log = obtener_logger("errores")

    @app.exception_handler(ErrorDeDominio)
    async def _dominio(request: Request, exc: ErrorDeDominio) -> JSONResponse:
        estado = estado_http_para(exc)
        log.warning("error_dominio", codigo=exc.codigo, mensaje=exc.mensaje)
        return JSONResponse(
            status_code=estado,
            content=construir_respuesta_error(
                exc.codigo, exc.mensaje, _request_id_de(request), exc.detalle
            ),
        )

    @app.exception_handler(ErrorAPI)
    async def _api(request: Request, exc: ErrorAPI) -> JSONResponse:
        log.warning("error_api", codigo=exc.codigo, mensaje=exc.mensaje)
        return JSONResponse(
            status_code=exc.estado_http,
            content=construir_respuesta_error(
                exc.codigo, exc.mensaje, _request_id_de(request), exc.detalle
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=construir_respuesta_error(
                "VALIDACION",
                "Los datos enviados no son válidos.",
                _request_id_de(request),
                {"errores": exc.errors()},
            ),
        )

    @app.exception_handler(Exception)
    async def _fallback(request: Request, exc: Exception) -> JSONResponse:
        log.error("error_interno", tipo=type(exc).__name__, error=str(exc))
        return JSONResponse(
            status_code=500,
            content=construir_respuesta_error(
                "ERROR_INTERNO",
                "Ocurrió un error interno.",
                _request_id_de(request),
            ),
        )


def crear_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configurar_logging(settings)

    app = FastAPI(
        title="Plataforma de Administración de Natilleras",
        version="0.1.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )
    app.state.settings = settings

    # Infraestructura de BD, bus y resolver de membresía (composición).
    engine = crear_engine(settings)
    app.state.engine = engine
    app.state.session_factory = crear_session_factory(engine)
    app.state.bus = BusDeEventosEnMemoria()
    app.state.fabrica_resolver = ResolverPrincipalSQLAlchemy

    app.add_middleware(RequestIDMiddleware)
    _registrar_handlers(app)

    app.include_router(auth_router)
    app.include_router(acceso_router)
    app.include_router(natilleras_router)
    app.include_router(participantes_router)
    app.include_router(contabilidad_router)
    app.include_router(cuotas_router)
    app.include_router(prestamos_router)
    app.include_router(multas_router)
    app.include_router(actividades_router)
    app.include_router(liquidacion_router)

    @app.get("/health", tags=["salud"])
    async def health() -> dict[str, str]:
        """Liveness: la app responde."""
        return {"estado": "ok"}

    @app.get("/ready", tags=["salud"])
    async def ready() -> dict[str, str]:
        """Readiness: la BD responde."""
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"estado": "listo"}

    return app


app = crear_app()
