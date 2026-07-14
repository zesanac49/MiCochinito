"""Reglas de acceso: roles de membresía y sus invariantes (RF-1002, doc 04 §3.2).

Dominio puro (TEC-03): no conoce SQLAlchemy, FastAPI ni el enum `Rol` de la capa
`core` (que arrastra FastAPI). Los roles se manejan como cadenas y las reglas se
expresan como funciones sobre datos primitivos, de modo que se pueden probar sin
infraestructura.
"""

from __future__ import annotations

from app.shared.domain.excepciones import ErrorDeDominio, ErrorDeValidacionDeDominio

# Roles de la membresía usuario-natillera. Deben coincidir con el CHECK de la
# tabla `usuarios_natilleras` y con el enum `Rol` de `app.core.auth`.
ROL_ADMINISTRADOR = "ADMINISTRADOR"
ROL_SUPERVISOR = "SUPERVISOR"
ROL_CLIENTE = "CLIENTE"
ROLES_VALIDOS = frozenset({ROL_ADMINISTRADOR, ROL_SUPERVISOR, ROL_CLIENTE})


class ClienteRequiereParticipante(ErrorDeDominio):
    """Un miembro con rol CLIENTE debe estar vinculado a un participante."""

    codigo = "CLIENTE_REQUIERE_PARTICIPANTE"


class UltimoAdministrador(ErrorDeDominio):
    """No se puede degradar/quitar al último ADMINISTRADOR de la natillera."""

    codigo = "ULTIMO_ADMINISTRADOR"


class MiembroYaExiste(ErrorDeDominio):
    """El usuario ya es miembro de esta natillera."""

    codigo = "MIEMBRO_YA_EXISTE"


class MiembroNoEncontrado(ErrorDeDominio):
    """El usuario no es miembro de esta natillera."""

    codigo = "NO_ENCONTRADO"


class ParticipanteNoEncontrado(ErrorDeDominio):
    """El participante indicado no existe en esta natillera."""

    codigo = "NO_ENCONTRADO"


def validar_rol(rol: str) -> None:
    """Verifica que `rol` sea uno de los roles conocidos (defensa en profundidad;
    la capa api ya lo restringe con un `Literal`)."""
    if rol not in ROLES_VALIDOS:
        raise ErrorDeValidacionDeDominio(
            f"Rol inválido: {rol!r}.", {"roles_validos": sorted(ROLES_VALIDOS)}
        )


def normalizar_participante(rol: str, participante_id: int | None) -> int | None:
    """Ajusta el participante vinculado según el rol (RN doc 04 §3.2):

    - CLIENTE exige participante; sin él es un error.
    - Cualquier otro rol no lleva participante vinculado (se descarta).
    """
    if rol == ROL_CLIENTE:
        if participante_id is None:
            raise ClienteRequiereParticipante(
                "Un miembro con rol CLIENTE debe vincularse a un participante."
            )
        return participante_id
    return None


def verificar_no_ultimo_admin(
    rol_actual: str, rol_nuevo: str | None, total_administradores: int
) -> None:
    """Impide dejar la natillera sin ningún ADMINISTRADOR.

    `rol_nuevo=None` representa la eliminación de la membresía. Solo aplica cuando
    el miembro afectado es hoy ADMINISTRADOR y con el cambio dejaría de serlo.
    """
    deja_de_ser_admin = (
        rol_actual == ROL_ADMINISTRADOR and rol_nuevo != ROL_ADMINISTRADOR
    )
    if deja_de_ser_admin and total_administradores <= 1:
        raise UltimoAdministrador(
            "No puedes dejar la natillera sin administrador; asigna otro antes."
        )
